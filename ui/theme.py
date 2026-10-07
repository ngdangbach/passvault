"""
ui/theme.py — Hệ thống Design System & Theme Engine chuyên nghiệp cho PassVault.

Hỗ trợ 8 themes nổi tiếng:
  - tokyo-night
  - catppuccin-mocha
  - dracula
  - nord
  - gruvbox-dark
  - solarized-dark
  - solarized-light
  - matrix
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import QApplication


# ==============================================================================
# 8 NỔI TIẾNG THEME PALETTES
# ==============================================================================

THEMES: Dict[str, dict] = {
    "tokyo-night": {
        "id": "tokyo-night",
        "name": "Tokyo Night",
        "type": "dark",
        "bg":             "#1a1b26",
        "bg_alt":         "#16161e",
        "surface":        "#24283b",
        "surface_hover":  "#2e344e",
        "surface_press":  "#383e5c",
        "surface_alt":    "#1f2335",
        "border":         "#2c324c",
        "border_strong":  "#414868",
        "text":           "#c0caf5",
        "text_secondary": "#a9b1d6",
        "text_muted":     "#565f89",
        "text_disabled":  "#414868",
        "primary":        "#7aa2f7",
        "primary_hover":  "#8fb4ff",
        "primary_press":  "#6688d6",
        "primary_fg":     "#15161e",
        "accent":         "#bb9af7",
        "accent_fg":      "#15161e",
        "success":        "#9ece6a",
        "warning":        "#e0af68",
        "danger":         "#f7768e",
        "danger_hover":   "#ff8ca0",
        "totp_safe":      "#9ece6a",
        "totp_warn":      "#e0af68",
        "totp_critical":  "#f7768e",
        "swatch":         ["#7aa2f7", "#bb9af7", "#9ece6a", "#e0af68", "#f7768e"],
    },
    "catppuccin-mocha": {
        "id": "catppuccin-mocha",
        "name": "Catppuccin Mocha",
        "type": "dark",
        "bg":             "#1e1e2e",
        "bg_alt":         "#181825",
        "surface":        "#252538",
        "surface_hover":  "#313244",
        "surface_press":  "#45475a",
        "surface_alt":    "#181825",
        "border":         "#313244",
        "border_strong":  "#45475a",
        "text":           "#cdd6f4",
        "text_secondary": "#bac2de",
        "text_muted":     "#6c7086",
        "text_disabled":  "#585b70",
        "primary":        "#cba6f7",
        "primary_hover":  "#dcbcfa",
        "primary_press":  "#b48def",
        "primary_fg":     "#11111b",
        "accent":         "#89dceb",
        "accent_fg":      "#11111b",
        "success":        "#a6e3a1",
        "warning":        "#f9e2af",
        "danger":         "#f38ba8",
        "danger_hover":   "#f8a2bb",
        "totp_safe":      "#a6e3a1",
        "totp_warn":      "#f9e2af",
        "totp_critical":  "#f38ba8",
        "swatch":         ["#89b4fa", "#cba6f7", "#a6e3a1", "#f9e2af", "#f38ba8"],
    },
    "dracula": {
        "id": "dracula",
        "name": "Dracula",
        "type": "dark",
        "bg":             "#282a36",
        "bg_alt":         "#21222c",
        "surface":        "#343746",
        "surface_hover":  "#44475a",
        "surface_press":  "#52566c",
        "surface_alt":    "#2b2d3c",
        "border":         "#44475a",
        "border_strong":  "#6272a4",
        "text":           "#f8f8f2",
        "text_secondary": "#e2e2dc",
        "text_muted":     "#6272a4",
        "text_disabled":  "#4d546f",
        "primary":        "#bd93f9",
        "primary_hover":  "#cfabfb",
        "primary_press":  "#a77aeb",
        "primary_fg":     "#282a36",
        "accent":         "#ff79c6",
        "accent_fg":      "#282a36",
        "success":        "#50fa7b",
        "warning":        "#ffb86c",
        "danger":         "#ff5555",
        "danger_hover":   "#ff6e6e",
        "totp_safe":      "#50fa7b",
        "totp_warn":      "#ffb86c",
        "totp_critical":  "#ff5555",
        "swatch":         ["#bd93f9", "#ff79c6", "#50fa7b", "#f1fa8c", "#ff5555"],
    },
    "nord": {
        "id": "nord",
        "name": "Nord",
        "type": "dark",
        "bg":             "#2e3440",
        "bg_alt":         "#242933",
        "surface":        "#3b4252",
        "surface_hover":  "#434c5e",
        "surface_press":  "#4c566a",
        "surface_alt":    "#353c4a",
        "border":         "#434c5e",
        "border_strong":  "#4c566a",
        "text":           "#eceff4",
        "text_secondary": "#e5e9f0",
        "text_muted":     "#7b88a1",
        "text_disabled":  "#4c566a",
        "primary":        "#88c0d0",
        "primary_hover":  "#9ed4e3",
        "primary_press":  "#72adbd",
        "primary_fg":     "#2e3440",
        "accent":         "#81a1c1",
        "accent_fg":      "#2e3440",
        "success":        "#a3be8c",
        "warning":        "#ebcb8b",
        "danger":         "#bf616a",
        "danger_hover":   "#ce737c",
        "totp_safe":      "#a3be8c",
        "totp_warn":      "#ebcb8b",
        "totp_critical":  "#bf616a",
        "swatch":         ["#88c0d0", "#81a1c1", "#a3be8c", "#ebcb8b", "#bf616a"],
    },
    "gruvbox-dark": {
        "id": "gruvbox-dark",
        "name": "Gruvbox Dark",
        "type": "dark",
        "bg":             "#282828",
        "bg_alt":         "#1d2021",
        "surface":        "#32302f",
        "surface_hover":  "#3c3836",
        "surface_press":  "#504945",
        "surface_alt":    "#2b2928",
        "border":         "#3c3836",
        "border_strong":  "#504945",
        "text":           "#ebdbb2",
        "text_secondary": "#d5c4a1",
        "text_muted":     "#928374",
        "text_disabled":  "#665c54",
        "primary":        "#fe8019",
        "primary_hover":  "#ffa04d",
        "primary_press":  "#e06b0b",
        "primary_fg":     "#282828",
        "accent":         "#fabd2f",
        "accent_fg":      "#282828",
        "success":        "#b8bb26",
        "warning":        "#fabd2f",
        "danger":         "#fb4934",
        "danger_hover":   "#ff624f",
        "totp_safe":      "#b8bb26",
        "totp_warn":      "#fabd2f",
        "totp_critical":  "#fb4934",
        "swatch":         ["#fabd2f", "#d3869b", "#b8bb26", "#fe8019", "#fb4934"],
    },
    "solarized-dark": {
        "id": "solarized-dark",
        "name": "Solarized Dark",
        "type": "dark",
        "bg":             "#002b36",
        "bg_alt":         "#00212b",
        "surface":        "#073642",
        "surface_hover":  "#0e4352",
        "surface_press":  "#165162",
        "surface_alt":    "#052c36",
        "border":         "#0e4a5a",
        "border_strong":  "#586e75",
        "text":           "#839496",
        "text_secondary": "#93a1a1",
        "text_muted":     "#586e75",
        "text_disabled":  "#093c4a",
        "primary":        "#268bd2",
        "primary_hover":  "#3d9be0",
        "primary_press":  "#1d75b3",
        "primary_fg":     "#ffffff",
        "accent":         "#2aa198",
        "accent_fg":      "#002b36",
        "success":        "#859900",
        "warning":        "#b58900",
        "danger":         "#dc322f",
        "danger_hover":   "#eb4744",
        "totp_safe":      "#859900",
        "totp_warn":      "#b58900",
        "totp_critical":  "#dc322f",
        "swatch":         ["#268bd2", "#6c71c4", "#859900", "#b58900", "#dc322f"],
    },
    "solarized-light": {
        "id": "solarized-light",
        "name": "Solarized Light",
        "type": "light",
        "bg":             "#fdf6e3",
        "bg_alt":         "#f5eed9",
        "surface":        "#eee8d5",
        "surface_hover":  "#e3dcba",
        "surface_press":  "#d8d1af",
        "surface_alt":    "#f6efe0",
        "border":         "#dfd7bf",
        "border_strong":  "#93a1a1",
        "text":           "#073642",
        "text_secondary": "#586e75",
        "text_muted":     "#839496",
        "text_disabled":  "#a4b5b8",
        "primary":        "#268bd2",
        "primary_hover":  "#1c78b8",
        "primary_press":  "#145e91",
        "primary_fg":     "#ffffff",
        "accent":         "#2aa198",
        "accent_fg":      "#ffffff",
        "success":        "#859900",
        "warning":        "#b58900",
        "danger":         "#dc322f",
        "danger_hover":   "#c42623",
        "totp_safe":      "#859900",
        "totp_warn":      "#b58900",
        "totp_critical":  "#dc322f",
        "swatch":         ["#268bd2", "#6c71c4", "#859900", "#b58900", "#dc322f"],
    },
    "matrix": {
        "id": "matrix",
        "name": "Matrix",
        "type": "dark",
        "bg":             "#0a0e0a",
        "bg_alt":         "#050805",
        "surface":        "#111811",
        "surface_hover":  "#182618",
        "surface_press":  "#203520",
        "surface_alt":    "#0d140d",
        "border":         "#1d331d",
        "border_strong":  "#2b4e2b",
        "text":           "#e0ffe5",
        "text_secondary": "#88e096",
        "text_muted":     "#3d7a46",
        "text_disabled":  "#234a29",
        "primary":        "#00ff66",
        "primary_hover":  "#33ff85",
        "primary_press":  "#00d957",
        "primary_fg":     "#050805",
        "accent":         "#00e5ff",
        "accent_fg":      "#050805",
        "success":        "#00ff66",
        "warning":        "#e6e600",
        "danger":         "#ff3355",
        "danger_hover":   "#ff5975",
        "totp_safe":      "#00ff66",
        "totp_warn":      "#e6e600",
        "totp_critical":  "#ff3355",
        "swatch":         ["#00e5ff", "#33ff85", "#00ff66", "#e6e600", "#ff3355"],
    },
}

DEFAULT_THEME = "tokyo-night"


# ==============================================================================
# THEME ENGINE STATE & LISTENERS
# ==============================================================================

_current_theme_id: str = DEFAULT_THEME
_listeners: List[Callable[[dict], None]] = []


class ThemeDictProxy(dict):
    """Proxy dictionary cho COLORS để backwards compatibility hoàn hảo.
    
    Khi gọi COLORS["bg"], nó sẽ luôn lấy giá trị từ theme đang active.
    """
    def __getitem__(self, key: str) -> str:
        theme = THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])
        return theme.get(key, "#ffffff")

    def get(self, key: str, default: str = "#ffffff") -> str:
        theme = THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])
        return theme.get(key, default)

    def __contains__(self, key: object) -> bool:
        theme = THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])
        return key in theme

    def keys(self):
        theme = THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])
        return theme.keys()

    def values(self):
        theme = THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])
        return theme.values()

    def items(self):
        theme = THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])
        return theme.items()


# Active color tokens proxy
COLORS = ThemeDictProxy()


# ==============================================================================
# TYPOGRAPHY SYSTEM (Modern App UI Font Stack)
# Ranked UI Fonts: Segoe UI Variable / Inter / Segoe UI / Cascadia Code
# ==============================================================================

_FAMILY_TEXT = "Segoe UI Variable Text, Segoe UI, Inter, SF Pro Text, sans-serif"
_FAMILY_DISPLAY = "Segoe UI Variable Display, Segoe UI, Inter, SF Pro Display, sans-serif"
_MONO = "Cascadia Code, Cascadia Mono, Consolas, JetBrains Mono, monospace"

FONTS = {
    "ui":         (_FAMILY_TEXT, 10),
    "ui_bold":    (_FAMILY_TEXT, 10, QFont.Weight.Bold),
    "h1":         (_FAMILY_DISPLAY, 18, QFont.Weight.Bold),
    "h2":         (_FAMILY_DISPLAY, 14, QFont.Weight.Bold),
    "h3":         (_FAMILY_DISPLAY, 12, QFont.Weight.Bold),
    "body":       (_FAMILY_TEXT, 10),
    "small":      (_FAMILY_TEXT, 9),
    "caption":    (_FAMILY_TEXT, 8, QFont.Weight.DemiBold),
    "mono":       (_MONO, 10),
    "mono_lg":    (_MONO, 14, QFont.Weight.Bold),
    "mono_xl":    (_MONO, 20, QFont.Weight.Bold),
}

# Spacing scale
SPACE = {
    "xs":  4,
    "sm":  8,
    "md":  12,
    "lg":  16,
    "xl":  24,
    "2xl": 32,
}

# Border radius
RADIUS = {
    "xs":   4,
    "sm":   6,
    "md":   10,
    "lg":   14,
    "xl":   20,
    "pill": 999,
}


# ==============================================================================
# SETTINGS PERSISTENCE
# ==============================================================================

def _get_settings_path() -> Path:
    from pathlib import Path
    import sys
    # Portable check
    try:
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "portable.flag").exists():
            data_dir = exe_dir / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            return data_dir / "settings.json"
    except Exception:
        pass
    data_dir = Path.home() / ".passvault"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "settings.json"


def load_saved_theme() -> str:
    """Đọc theme đã lưu từ settings.json."""
    try:
        p = _get_settings_path()
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            saved = data.get("theme")
            if saved in THEMES:
                return saved
    except Exception:
        pass
    return DEFAULT_THEME


def save_theme_preference(theme_id: str) -> None:
    """Lưu theme preference vào settings.json."""
    if theme_id not in THEMES:
        return
    try:
        p = _get_settings_path()
        current_data = {}
        if p.exists():
            try:
                current_data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                current_data = {}
        current_data["theme"] = theme_id
        p.write_text(json.dumps(current_data, indent=2), encoding="utf-8")
    except Exception:
        pass


def get_current_theme_id() -> str:
    return _current_theme_id


def get_current_theme() -> dict:
    return THEMES.get(_current_theme_id, THEMES[DEFAULT_THEME])


def get_all_themes() -> Dict[str, dict]:
    return THEMES


def register_theme_listener(fn: Callable[[dict], None]) -> None:
    """Đăng ký callback khi theme thay đổi."""
    if fn not in _listeners:
        _listeners.append(fn)


def unregister_theme_listener(fn: Callable[[dict], None]) -> None:
    if fn in _listeners:
        _listeners.remove(fn)


def set_theme(theme_id: str, save_preference: bool = True) -> None:
    """Chuyển theme hiện tại và thông báo cho mọi widgets."""
    global _current_theme_id
    if theme_id not in THEMES:
        return
    _current_theme_id = theme_id
    if save_preference:
        save_theme_preference(theme_id)

    app = QApplication.instance()
    if app is not None and isinstance(app, QApplication):
        apply_theme_to_app(app)

    theme_data = get_current_theme()
    # Notify all listeners
    for fn in list(_listeners):
        try:
            fn(theme_data)
        except Exception:
            pass


def apply_theme_to_app(app: QApplication) -> None:
    """Áp dụng màu sắc và styling toàn cục vào QApplication."""
    theme = get_current_theme()
    palette = QPalette()

    # Surfaces
    palette.setColor(QPalette.ColorRole.Window, QColor(theme["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme["bg_alt"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme["surface"]))
    
    # Text
    palette.setColor(QPalette.ColorRole.Text, QColor(theme["text"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme["text_muted"]))
    
    # Buttons
    palette.setColor(QPalette.ColorRole.Button, QColor(theme["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme["text"]))
    
    # Highlights
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme["primary"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme["primary_fg"]))
    
    # Tooltips
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme["surface_alt"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme["text"]))

    app.setPalette(palette)
    app.setStyle("Fusion")
    app.setFont(QFont(_FAMILY_TEXT, 10))


# Initialize saved theme on import
_current_theme_id = load_saved_theme()


# ==============================================================================
# COLOR & AVATAR HELPERS
# ==============================================================================

def site_color(name: str) -> str:
    """Generate consistent color per site name (for avatar backgrounds)."""
    theme = get_current_theme()
    # Blend with swatch or curated color set
    palette = [
        theme["primary"],
        theme["accent"],
        theme["success"],
        theme["warning"],
        "#a855f7", "#ec4899", "#06b6d4", "#f97316", "#14b8a6", "#6366f1"
    ]
    if not name:
        return palette[0]
    h = sum(ord(c) for c in name)
    return palette[h % len(palette)]


def site_initials(name: str) -> str:
    """First letter(s) of site name for avatar."""
    if not name:
        return "?"
    name = name.strip()
    if not name:
        return "?"
    words = name.split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return name[:2].upper() if len(name) >= 2 else name[0].upper()
