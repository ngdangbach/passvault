"""
ui/unlock_dialog.py — Modern master password prompt với dynamic theme switcher.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from ui.theme import (
    COLORS, FONTS, RADIUS, SPACE, get_current_theme, get_current_theme_id,
    register_theme_listener, unregister_theme_listener,
)
from ui.widgets import Card, PasswordStrengthBar, ThemeSelectorDialog


def make_logo_icon(size: int = 64) -> QPixmap:
    """Draw professional security shield + lock icon using current theme colors."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    scale = size / 64.0
    p.scale(scale, scale)

    # Shield background gradient
    grad = QLinearGradient(0, 0, 64, 64)
    grad.setColorAt(0, QColor(COLORS["primary"]))
    grad.setColorAt(1, QColor(COLORS["accent"]))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)

    pp = QPainterPath()
    pp.moveTo(32, 6)
    pp.cubicTo(48, 14, 56, 14, 56, 14)
    pp.cubicTo(56, 36, 50, 50, 32, 58)
    pp.cubicTo(14, 50, 8, 36, 8, 14)
    pp.cubicTo(8, 14, 16, 14, 32, 6)
    p.drawPath(pp)

    # Lock body
    p.setBrush(QBrush(QColor("#ffffff")))
    p.drawRoundedRect(22, 30, 20, 16, 3, 3)

    # Lock shackle
    pen = QPen(QColor("#ffffff"), 3)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawArc(25, 22, 14, 14, 180 * 16, 180 * 16)

    # Keyhole dot
    p.setBrush(QBrush(QColor(COLORS["primary"])))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(30, 35, 4, 4)

    p.end()
    return pm


class UnlockDialog(QDialog):
    """Modern unlock screen with live theme switcher, caps-lock hint, and password strength."""

    def __init__(self, parent: Optional[QWidget], is_new_vault: bool) -> None:
        super().__init__(parent)
        self.is_new = is_new_vault
        self.setWindowTitle("PassVault — Master Authentication")
        self.setModal(True)
        self.setFixedSize(450, 560 if self.is_new else 490)

        self._build_ui()
        register_theme_listener(self._on_theme_changed)

    def _build_ui(self) -> None:
        self.setWindowIcon(QIcon(make_logo_icon(64)))
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header with Logo & Title & Theme switcher
        self.header = QWidget()
        self.header.setStyleSheet(f"background: {COLORS['bg']};")
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(SPACE["xl"], SPACE["lg"], SPACE["xl"], SPACE["md"])
        header_layout.setSpacing(SPACE["sm"])
        header_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Top row: theme button
        top_row = QHBoxLayout()
        top_row.addStretch()

        self.theme_btn = QPushButton("Theme")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['pill']}px;
                padding: 4px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
                border: 1px solid {COLORS['primary']};
                color: {COLORS['text']};
            }}
        """)
        self.theme_btn.clicked.connect(self._open_theme_selector)
        top_row.addWidget(self.theme_btn)
        header_layout.addLayout(top_row)

        self.logo_label = QLabel()
        self.logo_label.setPixmap(make_logo_icon(72))
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.logo_label)

        self.title_lbl = QLabel("PassVault")
        self.title_lbl.setFont(QFont(*FONTS["h1"]))
        self.title_lbl.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title_lbl)

        self.subtitle_lbl = QLabel(
            "Create your master vault" if self.is_new else "Unlock your secure vault"
        )
        self.subtitle_lbl.setFont(QFont(*FONTS["body"]))
        self.subtitle_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        self.subtitle_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.subtitle_lbl)

        root.addWidget(self.header)

        # Form Card
        self.card = Card()
        self.card.setStyleSheet(f"""
            QFrame#Card {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['lg']}px;
            }}
        """)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(SPACE["xl"], SPACE["lg"], SPACE["xl"], SPACE["lg"])
        card_layout.setSpacing(SPACE["sm"])

        lbl1 = QLabel("Master Password")
        lbl1.setFont(QFont(*FONTS["small"]))
        lbl1.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent; font-weight: bold;")
        card_layout.addWidget(lbl1)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter master password (≥ 8 chars)")
        self.password_edit.setMinimumHeight(42)
        self.password_edit.setStyleSheet(self._input_style())
        card_layout.addWidget(self.password_edit)

        # Strength bar if new
        if self.is_new:
            self.strength_bar = PasswordStrengthBar()
            self.password_edit.textChanged.connect(self.strength_bar.set_password)
            card_layout.addWidget(self.strength_bar)

            card_layout.addSpacing(SPACE["xs"])
            lbl2 = QLabel("Confirm Master Password")
            lbl2.setFont(QFont(*FONTS["small"]))
            lbl2.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent; font-weight: bold;")
            card_layout.addWidget(lbl2)

            self.confirm_edit = QLineEdit()
            self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_edit.setPlaceholderText("Retype master password")
            self.confirm_edit.setMinimumHeight(42)
            self.confirm_edit.setStyleSheet(self._input_style())
            card_layout.addWidget(self.confirm_edit)
        else:
            self.strength_bar = None
            self.confirm_edit = None

        # Visibility and Caps lock hint row
        aux_row = QHBoxLayout()
        self.show_pw_btn = QPushButton("Show password")
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pw_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: 0;
                text-align: left;
                padding: 2px 0;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {COLORS['primary']}; }}
        """)
        self.show_pw_btn.toggled.connect(self._toggle_visibility)
        aux_row.addWidget(self.show_pw_btn)
        aux_row.addStretch()

        self.caps_lbl = QLabel("")
        self.caps_lbl.setFont(QFont(*FONTS["caption"]))
        self.caps_lbl.setStyleSheet(f"color: {COLORS['warning']}; background: transparent;")
        aux_row.addWidget(self.caps_lbl)
        card_layout.addLayout(aux_row)

        # Error notification banner
        self.error_banner = QLabel("")
        self.error_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_banner.setFixedHeight(26)
        self.error_banner.setStyleSheet(f"""
            color: {COLORS['danger']};
            background: rgba(239, 68, 68, 0.12);
            border-radius: {RADIUS['xs']}px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.error_banner.hide()
        card_layout.addWidget(self.error_banner)

        # Action submit button
        card_layout.addSpacing(SPACE["sm"])
        self.action_btn = QPushButton("Create Vault" if self.is_new else "Unlock Vault")
        self.action_btn.setMinimumHeight(44)
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
            QPushButton:pressed {{ background: {COLORS['primary_press']}; }}
        """)
        self.action_btn.clicked.connect(self._submit)
        self.action_btn.setDefault(True)
        card_layout.addWidget(self.action_btn)

        wrapper = QWidget()
        wrapper.setStyleSheet(f"background: {COLORS['bg']};")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(SPACE["xl"], 0, SPACE["xl"], SPACE["lg"])
        wrapper_layout.addWidget(self.card)
        wrapper_layout.addStretch()
        root.addWidget(wrapper, stretch=1)

        # Security footer hint
        if self.is_new:
            self.hint_lbl = QLabel("Notice: Master password is never saved. Keep it in a safe place.")
            self.hint_lbl.setFont(QFont(*FONTS["small"]))
            self.hint_lbl.setStyleSheet(f"color: {COLORS['warning']}; background: {COLORS['bg']};")
            self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.hint_lbl.setContentsMargins(0, 0, 0, SPACE["md"])
            root.addWidget(self.hint_lbl)

        self.password_edit.returnPressed.connect(self._submit)
        if self.confirm_edit is not None:
            self.confirm_edit.returnPressed.connect(self._submit)

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {COLORS['bg_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['sm']}px;
                padding: 8px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {COLORS['primary']};
            }}
        """

    def _open_theme_selector(self) -> None:
        dlg = ThemeSelectorDialog(self)
        dlg.exec()

    def _on_theme_changed(self, theme_data: dict) -> None:
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")
        self.setWindowIcon(QIcon(make_logo_icon(64)))
        self.theme_btn.setText("Theme")
        self.logo_label.setPixmap(make_logo_icon(72))
        self.title_lbl.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        self.subtitle_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        self.card.setStyleSheet(f"""
            QFrame#Card {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['lg']}px;
            }}
        """)
        self.password_edit.setStyleSheet(self._input_style())
        if self.confirm_edit:
            self.confirm_edit.setStyleSheet(self._input_style())
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
            QPushButton:pressed {{ background: {COLORS['primary_press']}; }}
        """)

    def get_password(self) -> Optional[str]:
        if self.result() == QDialog.DialogCode.Accepted:
            return self.password_edit.text()
        return None

    def _toggle_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.password_edit.setEchoMode(mode)
        if self.confirm_edit is not None:
            self.confirm_edit.setEchoMode(mode)
        self.show_pw_btn.setText("Hide password" if checked else "Show password")

    def _submit(self) -> None:
        pw = self.password_edit.text()
        if len(pw) < 8:
            self._show_error("Password must be at least 8 characters.")
            return
        if self.is_new and self.confirm_edit is not None:
            if pw != self.confirm_edit.text():
                self._show_error("Passwords do not match.")
                return
        self.accept()

    def _show_error(self, message: str) -> None:
        self.error_banner.setText(f"  {message}  ")
        self.error_banner.show()
        QTimer.singleShot(4000, self.error_banner.hide)

    def done(self, result: int) -> None:
        unregister_theme_listener(self._on_theme_changed)
        super().done(result)

    def closeEvent(self, event) -> None:
        unregister_theme_listener(self._on_theme_changed)
        super().closeEvent(event)
