"""
core/qr_scanner.py — Screen capture + QR decode + otpauth URI parsing.

Workflow:
  1. capture_region(x, y, w, h) -> PIL Image
  2. decode_qr_codes(image) -> list of decoded strings
  3. parse_otpauth_uri(uri) -> {issuer, account, secret, type}

The QR code từ các site 2FA thường có format:
  otpauth://totp/Issuer:Account?secret=BASE32SECRET&issuer=Issuer
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs

import cv2
import mss
import numpy as np
from PIL import Image


# ---------- Screen capture ----------

def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    """Capture a screen region using mss. Returns RGB PIL Image."""
    with mss.mss() as sct:
        monitor = {"left": x, "top": y, "width": w, "height": h}
        sct_img = sct.grab(monitor)
        img = Image.frombytes(
            "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
        )
    return img


def capture_full_screen() -> Image.Image:
    """Capture the primary monitor."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        img = Image.frombytes(
            "RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"
        )
    return img


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of primary monitor."""
    with mss.mss() as sct:
        m = sct.monitors[1]
        return m["width"], m["height"]


# ---------- QR decode ----------

# Cache detector (thread-safe singleton)
_detector = None


def _get_detector():
    global _detector
    if _detector is None:
        _detector = cv2.QRCodeDetector()
    return _detector


def _pil_to_cv(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to OpenCV BGR uint8 array (handles all modes)."""
    # Force convert to RGB first (handles P, L, 1, I, etc.)
    if image.mode != "RGB":
        image = image.convert("RGB")
    arr = np.array(image, dtype=np.uint8)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def _to_gray(bgr: np.ndarray) -> np.ndarray:
    """Convert to grayscale uint8."""
    if bgr.dtype != np.uint8:
        bgr = bgr.astype(np.uint8)
    if bgr.ndim == 2:
        return bgr
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def decode_qr_codes(image: Image.Image) -> list[str]:
    """Decode tất cả QR codes trong image. Returns list of decoded strings."""
    try:
        img_bgr = _pil_to_cv(image)
    except Exception as e:
        return []

    results = []
    detector = _get_detector()

    def _try_decode(img) -> list[str]:
        try:
            retval = detector.detectAndDecode(img)
        except cv2.error:
            return []
        if not isinstance(retval, tuple) or len(retval) < 2:
            return []
        data, vertices = retval[0], retval[1]
        if not data or vertices is None:
            return []
        # data can be str, list[str], or numpy array
        if isinstance(data, str):
            return [data] if data else []
        try:
            return [str(d) for d in data if d]
        except (TypeError, ValueError):
            return []

    # Attempt 1: BGR
    results = _try_decode(img_bgr)
    # Attempt 2: grayscale
    if not results:
        results = _try_decode(_to_gray(img_bgr))
    # Attempt 3: upsample small images
    if not results and image.size[0] < 500:
        try:
            upscaled = image.resize(
                (image.size[0] * 3, image.size[1] * 3),
                Image.Resampling.LANCZOS
            )
            results = _try_decode(_pil_to_cv(upscaled))
        except Exception:
            pass

    return results


def find_qr_in_image(image: Image.Image) -> Optional[tuple[str, tuple]]:
    """Find first QR code. Returns (data, (x, y, w, h)) hoặc None."""
    try:
        img_bgr = _pil_to_cv(image)
    except Exception:
        return None

    detector = _get_detector()
    text = None
    vertices = None

    def _try(img):
        nonlocal text, vertices
        try:
            retval = detector.detectAndDecode(img)
        except cv2.error:
            return
        if not isinstance(retval, tuple) or len(retval) < 2:
            return
        d, v = retval[0], retval[1]
        if not d or v is None:
            return
        if isinstance(d, str):
            text = d
        else:
            try:
                text = str(d[0]) if len(d) > 0 else None
            except (TypeError, IndexError):
                text = None
        vertices = v

    _try(img_bgr)
    if not text:
        _try(_to_gray(img_bgr))

    if not text or vertices is None or len(vertices) == 0:
        return None

    pts = vertices[0]
    x = int(min(p[0] for p in pts))
    y = int(min(p[1] for p in pts))
    w = int(max(p[0] for p in pts)) - x
    h = int(max(p[1] for p in pts)) - y
    return (text, (x, y, w, h))


# ---------- otpauth URI parsing ----------

def parse_otpauth_uri(uri: str) -> dict:
    """
    Parse otpauth:// URI thành dict.

    Returns dict with keys:
      - type: 'totp' or 'hotp'
      - issuer: string (e.g. 'GitHub')
      - account: string (e.g. 'alice@example.com')
      - secret: BASE32 string
      - digits: int (default 6)
      - period: int (default 30)
      - algorithm: str (default 'SHA1')

    Returns empty dict nếu URI không hợp lệ.
    """
    result = {}
    try:
        uri = uri.strip()
        parsed = urlparse(uri)
        if parsed.scheme != "otpauth":
            return {}

        result["type"] = parsed.netloc.lower()  # totp / hotp
        if result["type"] not in ("totp", "hotp"):
            return {}

        # Path is "/Issuer:Account" hoặc "/Account"
        path = parsed.path.lstrip("/")
        if ":" in path:
            issuer_from_path, account = path.split(":", 1)
            issuer_from_path = _decode_uri(issuer_from_path)
            account = _decode_uri(account)
        else:
            issuer_from_path = ""
            account = _decode_uri(path)

        qs = parse_qs(parsed.query)
        secret = qs.get("secret", [""])[0].strip()
        if not secret:
            return {}

        issuer_from_qs = qs.get("issuer", [""])[0].strip()
        # Issuer: prefer QS, fallback to path
        issuer = issuer_from_qs or issuer_from_path

        result.update({
            "issuer": _decode_uri(issuer),
            "account": account,
            "secret": secret.upper().replace(" ", "").replace("-", ""),
            "digits": int(qs.get("digits", ["6"])[0]),
            "period": int(qs.get("period", ["30"])[0]),
            "algorithm": qs.get("algorithm", ["SHA1"])[0].upper(),
        })
        return result
    except Exception:
        return {}


def _decode_uri(s: str) -> str:
    """Decode URL-encoded string, replacing + with space."""
    from urllib.parse import unquote_plus
    return unquote_plus(s).strip()


# ---------- High-level helpers ----------

def extract_otpauth_from_string(s: str) -> Optional[dict]:
    """Try to extract otpauth data from any string (URL, secret only, etc.)."""
    s = s.strip()

    # Direct otpauth URI
    if s.lower().startswith("otpauth://"):
        data = parse_otpauth_uri(s)
        return data if data else None

    # Maybe it's just the secret? (BASE32: A-Z 2-7, min length 16)
    cleaned = s.upper().replace(" ", "").replace("-", "")
    if re.match(r"^[A-Z2-7]{16,}=*$", cleaned):
        return {
            "type": "totp",
            "issuer": "",
            "account": "",
            "secret": s.upper().replace(" ", "").replace("-", ""),
            "digits": 6,
            "period": 30,
            "algorithm": "SHA1",
        }

    return None
