"""
ui/widgets.py — Reusable custom widgets cho UI hiện đại, chuẩn security password manager.
"""

from __future__ import annotations

import math
import time
from typing import Optional

import pyotp
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPen,
)
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGraphicsDropShadowEffect, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy, QSlider, QVBoxLayout, QWidget,
)

from core.password_gen import PasswordConfig, entropy_bits, generate
from ui.theme import (
    COLORS, FONTS, RADIUS, SPACE, get_all_themes, get_current_theme,
    get_current_theme_id, set_theme, site_color, site_initials,
)


# ==============================================================================
# ELIDED LABEL (PREVENTS OVERFLOW & TEXT OVERLAPPING)
# ==============================================================================

class ElidedLabel(QLabel):
    """QLabel that automatically truncates text with ellipsis (...) to prevent overflow."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, text: str) -> None:
        self._full_text = text
        self._elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        fm = self.fontMetrics()
        w = max(20, self.width())
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, w)
        super().setText(elided)


# ==============================================================================
# AVATAR WIDGET
# ==============================================================================

class Avatar(QWidget):
    """Round avatar displaying site initials with smooth gradient & crisp text."""

    def __init__(self, name: str, size: int = 42, parent=None) -> None:
        super().__init__(parent)
        self._name = name
        self._size = size
        self.setFixedSize(size, size)

    def set_name(self, name: str) -> None:
        self._name = name
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0.5, 0.5, self._size - 1, self._size - 1)
        base_hex = site_color(self._name)
        base_color = QColor(base_hex)

        # Subtle gradient
        grad = QLinearGradient(0, 0, self._size, self._size)
        grad.setColorAt(0, base_color.lighter(115))
        grad.setColorAt(1, base_color.darker(110))
        p.setBrush(QBrush(grad))

        # Thin outer border for contrast on dark/light
        p.setPen(QPen(QColor(255, 255, 255, 45), 1))
        p.drawEllipse(rect)

        # Initials
        p.setPen(QColor("#ffffff"))
        font = QFont(*FONTS["ui_bold"])
        font.setPointSize(max(8, self._size // 3))
        p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, site_initials(self._name))


# ==============================================================================
# TOTP COUNTDOWN RING (60 FPS SMOOTH ANIMATION)
# ==============================================================================

class TotpRing(QWidget):
    """Circular countdown ring for TOTP with smooth 60 FPS animation & pulse effect."""

    clicked = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._totp_secret = ""
        self._period = 30
        self.setFixedSize(160, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(16)  # ~60 FPS

    def set_secret(self, secret: str, period: int = 30) -> None:
        self._totp_secret = secret
        self._period = period
        self.update()

    def update_state(self, code: str, remaining: int, total: int = 30) -> None:
        """Backward compatibility shim."""
        self.update()

    def clear(self) -> None:
        self._totp_secret = ""
        self.update()

    def _tick(self) -> None:
        if self._totp_secret:
            self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._totp_secret:
            self.clicked.emit()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height())
        margin = 10
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

        # Background track
        p.setPen(QPen(QColor(COLORS["border"]), 6))
        p.drawEllipse(rect)

        if not self._totp_secret:
            p.setPen(QColor(COLORS["text_muted"]))
            font = QFont(*FONTS["body"])
            p.setFont(font)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No 2FA")
            return

        now = time.time()
        elapsed_in_period = now % self._period
        remaining = self._period - elapsed_in_period
        progress = remaining / self._period

        # Generate current code
        try:
            code = pyotp.TOTP(self._totp_secret).now()
            formatted = f"{code[:3]} {code[3:]}"
        except Exception:
            p.setPen(QColor(COLORS["danger"]))
            font = QFont(*FONTS["body"])
            p.setFont(font)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "ERR")
            return

        # Critical seconds pulse
        pulse_scale = 1.0
        if remaining <= 5:
            pulse_scale = 1.0 + 0.04 * math.sin(now * 8)
            arc_alpha = 220 + int(35 * math.sin(now * 8))
            arc_alpha = max(140, min(255, arc_alpha))
        else:
            arc_alpha = 230

        arc_rect = rect
        if pulse_scale != 1.0:
            dx = (pulse_scale - 1.0) * rect.width() / 2
            arc_rect = QRectF(
                rect.x() - dx, rect.y() - dx,
                rect.width() * pulse_scale, rect.height() * pulse_scale
            )

        # Gradient stroke
        grad = QLinearGradient(arc_rect.topLeft(), arc_rect.bottomRight())
        grad.setColorAt(0, QColor(COLORS["primary"]))
        if remaining > 10:
            end_color = QColor(COLORS["totp_safe"])
        elif remaining > 5:
            end_color = QColor(COLORS["totp_warn"])
        else:
            end_color = QColor(COLORS["totp_critical"])
        end_color.setAlpha(arc_alpha)
        grad.setColorAt(1, end_color)

        pen = QPen(QBrush(grad), 6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        start_angle = 90 * 16  # 12 o'clock
        span = -int(360 * 16 * progress)
        p.drawArc(arc_rect, start_angle, span)

        # Center Code
        p.save()
        if pulse_scale != 1.0:
            center = rect.center()
            p.translate(center)
            p.scale(pulse_scale, pulse_scale)
            p.translate(-center)

        p.setPen(QColor(COLORS["text"]))
        font = QFont(*FONTS["mono_xl"])
        font.setPointSize(19)
        p.setFont(font)
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, formatted)
        p.restore()

        # Remaining seconds label below
        small_rect = QRectF(rect.left(), rect.bottom() - 28, rect.width(), 24)
        p.setPen(QColor(COLORS["text_muted"]))
        font2 = QFont(*FONTS["small"])
        p.setFont(font2)
        secs = int(math.ceil(remaining))
        p.drawText(small_rect, Qt.AlignmentFlag.AlignCenter, f"{secs}s left")


# ==============================================================================
# PASSWORD STRENGTH METER BAR
# ==============================================================================

class PasswordStrengthBar(QWidget):
    """Segmented 4-bar password strength meter with bits entropy & label."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._score = 0  # 0 to 4
        self._bits = 0.0
        self._label = ""
        self._color = COLORS["text_muted"]
        self.setFixedHeight(18)

    def set_password(self, password: str) -> None:
        if not password:
            self._score = 0
            self._bits = 0.0
            self._label = ""
            self._color = COLORS["text_muted"]
            self.update()
            return

        bits = entropy_bits(password, 94)
        self._bits = bits

        if bits < 32 or len(password) < 8:
            self._score = 1
            self._label = "Very Weak"
            self._color = COLORS["danger"]
        elif bits < 50 or len(password) < 12:
            self._score = 2
            self._label = "Weak"
            self._color = COLORS["warning"]
        elif bits < 75 or len(password) < 16:
            self._score = 3
            self._label = "Strong"
            self._color = COLORS["success"]
        else:
            self._score = 4
            self._label = "Very Strong"
            self._color = COLORS["accent"]

        self.update()

    def get_info(self) -> tuple[int, float, str]:
        return self._score, self._bits, self._label

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = 5  # Bar height
        total_bars = 4
        spacing = 4
        bar_w = max(10, (w - 110 - (total_bars - 1) * spacing) // total_bars)

        # Draw 4 segments
        for i in range(total_bars):
            rx = i * (bar_w + spacing)
            rect = QRectF(rx, 6, bar_w, h)
            if i < self._score:
                p.setBrush(QBrush(QColor(self._color)))
                p.setPen(Qt.PenStyle.NoPen)
            else:
                p.setBrush(QBrush(QColor(COLORS["border"])))
                p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rect, 2, 2)

        # Text label on right
        if self._label:
            text_rect = QRectF(total_bars * (bar_w + spacing) + 4, 0, 100, 18)
            p.setPen(QColor(self._color))
            font = QFont(*FONTS["small"])
            p.setFont(font)
            p.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                f"{self._label} ({self._bits:.0f}b)",
            )


# ==============================================================================
# CARD CONTAINER
# ==============================================================================

class Card(QFrame):
    """Base card widget với shadow và border tokens."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.apply_theme()
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QFrame#Card {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['md']}px;
            }}
            QFrame#Card:hover {{
                border: 1px solid {COLORS['border_strong']};
            }}
        """)


# ==============================================================================
# ITEM CARD (VAULT LIST ROW)
# ==============================================================================

class ItemCard(QFrame):
    """Modern card displaying a vault item with avatar, status chips, and active state."""

    clicked = pyqtSignal(str)  # emits item_id
    copy_requested = pyqtSignal(str, str)  # emits (item_id, field)

    def __init__(self, item_data: dict, is_selected: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.item_id = item_data["id"]
        self.item_data = item_data
        self._is_selected = is_selected
        self.setObjectName("ItemCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(68)
        self._build(item_data)
        self.apply_style()

    def set_selected(self, selected: bool) -> None:
        if self._is_selected != selected:
            self._is_selected = selected
            self.apply_style()

    def apply_style(self) -> None:
        self.avatar.update()
        if self._is_selected:
            self.setStyleSheet(f"""
                QFrame#ItemCard {{
                    background: {COLORS['surface_press']};
                    border: 1.5px solid {COLORS['primary']};
                    border-radius: {RADIUS['md']}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#ItemCard {{
                    background: {COLORS['surface']};
                    border: 1px solid {COLORS['border']};
                    border-radius: {RADIUS['md']}px;
                }}
                QFrame#ItemCard:hover {{
                    background: {COLORS['surface_hover']};
                    border: 1px solid {COLORS['border_strong']};
                }}
            """)

    def _build(self, d: dict) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE["md"], SPACE["sm"], SPACE["md"], SPACE["sm"])
        layout.setSpacing(SPACE["md"])

        # Avatar
        self.avatar = Avatar(d.get("name", ""), size=40)
        layout.addWidget(self.avatar)

        # Name and user text
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.name_lbl = ElidedLabel(d.get("name", "Untitled"))
        self.name_lbl.setFont(QFont(*FONTS["ui_bold"]))
        self.name_lbl.setStyleSheet(f"color: {COLORS['text']}; background: transparent; border: 0;")
        text_col.addWidget(self.name_lbl)

        user_text = d.get("username") or d.get("url") or "(no username)"
        self.user_lbl = ElidedLabel(user_text)
        self.user_lbl.setFont(QFont(*FONTS["small"]))
        self.user_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent; border: 0;")
        text_col.addWidget(self.user_lbl)

        layout.addLayout(text_col, stretch=1)

        # Badges (2FA badge, Weak warning, Favorite)
        badges_col = QVBoxLayout()
        badges_col.setSpacing(4)
        badges_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(4)
        badges_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Weak password alert badge
        pw = d.get("password", "")
        if pw and (len(pw) < 8 or entropy_bits(pw, 94) < 36):
            weak_badge = QLabel("WEAK")
            weak_badge.setFixedHeight(18)
            weak_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            weak_badge.setStyleSheet(f"""
                background: {COLORS['danger']};
                color: #ffffff;
                border-radius: {RADIUS['xs']}px;
                padding: 1px 5px;
                font-size: 8px;
                font-weight: bold;
            """)
            badges_row.addWidget(weak_badge)

        # 2FA badge
        if d.get("has_totp"):
            totp_badge = QLabel("2FA")
            totp_badge.setFixedHeight(18)
            totp_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            totp_badge.setStyleSheet(f"""
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border-radius: {RADIUS['xs']}px;
                padding: 1px 6px;
                font-size: 8px;
                font-weight: bold;
            """)
            badges_row.addWidget(totp_badge)

        badges_col.addLayout(badges_row)

        # Masked password hint
        pw_len = len(pw) if pw else 8
        masked = "••••••••" if pw else ""
        if masked:
            pw_lbl = QLabel(masked)
            pw_lbl.setFont(QFont(*FONTS["mono"]))
            pw_lbl.setStyleSheet(f"color: {COLORS['text_disabled']}; background: transparent; border: 0;")
            badges_col.addWidget(pw_lbl, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(badges_col)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(event)


# ==============================================================================
# STANDALONE PASSWORD GENERATOR DIALOG
# ==============================================================================

class PasswordGeneratorDialog(QDialog):
    """Dedicated modal for CSPRNG password generation with length slider & options."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Password Generator — PassVault")
        self.setModal(True)
        self.setFixedSize(480, 420)
        self._build_ui()
        self._regenerate()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"""
            QDialog {{ background: {COLORS['bg']}; }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["xl"])
        root.setSpacing(SPACE["lg"])

        # Title
        title = QLabel("Password Generator")
        title.setFont(QFont(*FONTS["h2"]))
        title.setStyleSheet(f"color: {COLORS['text']};")
        root.addWidget(title)

        # Display Card
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        card_layout.setSpacing(SPACE["sm"])

        self.pw_display = QLineEdit()
        self.pw_display.setReadOnly(True)
        self.pw_display.setFont(QFont(*FONTS["mono_lg"]))
        self.pw_display.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['bg_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['sm']}px;
                padding: 10px 14px;
                font-size: 15px;
                letter-spacing: 1px;
            }}
        """)
        card_layout.addWidget(self.pw_display)

        # Strength Bar
        self.strength_bar = PasswordStrengthBar()
        card_layout.addWidget(self.strength_bar)

        root.addWidget(card)

        # Controls
        controls = Card()
        ctrl_layout = QVBoxLayout(controls)
        ctrl_layout.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        ctrl_layout.setSpacing(SPACE["md"])

        # Slider row
        slider_row = QHBoxLayout()
        lbl_len = QLabel("Length:")
        lbl_len.setFont(QFont(*FONTS["body"]))
        lbl_len.setStyleSheet(f"color: {COLORS['text']};")
        slider_row.addWidget(lbl_len)

        self.len_val_lbl = QLabel("20")
        self.len_val_lbl.setFont(QFont(*FONTS["ui_bold"]))
        self.len_val_lbl.setStyleSheet(f"color: {COLORS['primary']};")
        slider_row.addWidget(self.len_val_lbl)
        slider_row.addStretch()

        ctrl_layout.addLayout(slider_row)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(8, 64)
        self.slider.setValue(20)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {COLORS['border']};
                height: 6px;
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['primary']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['text']};
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }}
        """)
        self.slider.valueChanged.connect(self._on_slider_changed)
        ctrl_layout.addWidget(self.slider)

        # Checkboxes row
        cb_row1 = QHBoxLayout()
        self.cb_upper = QCheckBox("Uppercase (A-Z)")
        self.cb_upper.setChecked(True)
        self.cb_lower = QCheckBox("Lowercase (a-z)")
        self.cb_lower.setChecked(True)
        for cb in [self.cb_upper, self.cb_lower]:
            cb.setStyleSheet(f"color: {COLORS['text']}; font-size: 11px;")
            cb.stateChanged.connect(self._regenerate)
            cb_row1.addWidget(cb)
        ctrl_layout.addLayout(cb_row1)

        cb_row2 = QHBoxLayout()
        self.cb_digits = QCheckBox("Numbers (0-9)")
        self.cb_digits.setChecked(True)
        self.cb_symbols = QCheckBox("Symbols (!@#$...)")
        self.cb_symbols.setChecked(True)
        for cb in [self.cb_digits, self.cb_symbols]:
            cb.setStyleSheet(f"color: {COLORS['text']}; font-size: 11px;")
            cb.stateChanged.connect(self._regenerate)
            cb_row2.addWidget(cb)
        ctrl_layout.addLayout(cb_row2)

        root.addWidget(controls)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACE["sm"])

        regen_btn = QPushButton("Regenerate")
        regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        regen_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {RADIUS['sm']}px;
                padding: 10px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {COLORS['surface_hover']}; }}
        """)
        regen_btn.clicked.connect(self._regenerate)
        btn_row.addWidget(regen_btn)

        copy_btn = QPushButton("Copy Password")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
        """)
        copy_btn.clicked.connect(self._copy)
        btn_row.addWidget(copy_btn)

        root.addLayout(btn_row)

    def _on_slider_changed(self, val: int) -> None:
        self.len_val_lbl.setText(str(val))
        self._regenerate()

    def _regenerate(self) -> None:
        cfg = PasswordConfig(
            length=self.slider.value(),
            use_upper=self.cb_upper.isChecked(),
            use_lower=self.cb_lower.isChecked(),
            use_digits=self.cb_digits.isChecked(),
            use_symbols=self.cb_symbols.isChecked(),
        )
        try:
            pw = generate(cfg)
            self.pw_display.setText(pw)
            self.strength_bar.set_password(pw)
        except Exception:
            pass

    def _copy(self) -> None:
        pw = self.pw_display.text()
        if pw:
            QGuiApplication.clipboard().setText(pw)
            self.accept()

    def get_password(self) -> str:
        return self.pw_display.text()


# ==============================================================================
# THEME PICKER DIALOG / MENU
# ==============================================================================

class ThemeSelectorDialog(QDialog):
    """Interactive dialog to select from the 8 famous themes with visual swatches."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Choose Theme — PassVault")
        self.setModal(True)
        self.setFixedSize(460, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        root.setSpacing(SPACE["md"])

        header = QLabel("Appearance Themes")
        header.setFont(QFont(*FONTS["h2"]))
        header.setStyleSheet(f"color: {COLORS['text']};")
        root.addWidget(header)

        sub = QLabel("Select from 8 iconic themes tailored for security:")
        sub.setFont(QFont(*FONTS["body"]))
        sub.setStyleSheet(f"color: {COLORS['text_muted']};")
        root.addWidget(sub)

        themes = get_all_themes()
        cur_id = get_current_theme_id()

        for tid, tdata in themes.items():
            btn = QFrame()
            btn.setObjectName("ThemeRow")
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = (tid == cur_id)

            border_style = f"2px solid {COLORS['primary']}" if is_active else f"1px solid {COLORS['border']}"
            btn.setStyleSheet(f"""
                QFrame#ThemeRow {{
                    background: {COLORS['surface']};
                    border: {border_style};
                    border-radius: {RADIUS['md']}px;
                }}
                QFrame#ThemeRow:hover {{
                    background: {COLORS['surface_hover']};
                    border: 1px solid {COLORS['primary']};
                }}
            """)

            row = QHBoxLayout(btn)
            row.setContentsMargins(SPACE["md"], 0, SPACE["md"], 0)
            row.setSpacing(SPACE["sm"])

            name_lbl = QLabel(tdata["name"])
            name_lbl.setFont(QFont(*FONTS["ui_bold"]))
            name_lbl.setStyleSheet(f"color: {COLORS['text']}; background: transparent; border: 0; font-size: 12px;")
            row.addWidget(name_lbl)

            if is_active:
                active_pill = QLabel("ACTIVE")
                active_pill.setFixedHeight(18)
                active_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
                active_pill.setStyleSheet(f"""
                    background: {COLORS['primary']};
                    color: {COLORS['primary_fg']};
                    border-radius: {RADIUS['xs']}px;
                    padding: 1px 6px;
                    font-size: 8px;
                    font-weight: bold;
                """)
                row.addWidget(active_pill)

            row.addStretch()

            # Mini swatches
            for color_hex in tdata.get("swatch", []):
                dot = QWidget()
                dot.setFixedSize(14, 14)
                dot.setStyleSheet(f"""
                    background: {color_hex};
                    border-radius: 7px;
                    border: 1px solid rgba(0, 0, 0, 0.2);
                """)
                row.addWidget(dot)

            # Click handler
            btn.mousePressEvent = lambda _e, t=tid: self._select_theme(t)
            root.addWidget(btn)

        root.addStretch()

        close_btn = QPushButton("Done")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
        """)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)

    def _select_theme(self, tid: str) -> None:
        set_theme(tid)
        self.accept()


# ==============================================================================
# TOAST NOTIFICATION
# ==============================================================================

class Toast(QLabel):
    """Floating notification badge with auto-dismiss."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.apply_theme()
        self.setFixedHeight(36)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def apply_theme(self) -> None:
        self.setStyleSheet(f"""
            background: {COLORS['surface_hover']};
            color: {COLORS['text']};
            border: 1.5px solid {COLORS['primary']};
            border-radius: {RADIUS['pill']}px;
            padding: {SPACE['sm']}px {SPACE['xl']}px;
            font-size: 11px;
            font-weight: bold;
        """)

    def show_message(self, text: str, ms: int = 2500) -> None:
        self.apply_theme()
        self.setText(f"  {text}  ")
        self.adjustSize()
        if self.parent():
            pw = self.parent().width()
            x = (pw - self.width()) // 2
            y = self.parent().height() - self.height() - 36
            self.move(x, y)
        self.show()
        self.raise_()
        self._timer.start(ms)
