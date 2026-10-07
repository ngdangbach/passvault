"""
ui/change_password_dialog.py — Modern change master password dialog.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from ui.theme import (
    COLORS, FONTS, RADIUS, SPACE, register_theme_listener, unregister_theme_listener,
)
from ui.widgets import Card, PasswordStrengthBar


class ChangePasswordDialog(QDialog):
    """Change master password dialog with real-time strength meter."""

    def __init__(self, parent: Optional[QWidget]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Change Master Password — PassVault")
        self.setModal(True)
        self.setFixedSize(460, 560)
        self._build_ui()
        register_theme_listener(self._on_theme_changed)

    def _build_ui(self) -> None:
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["xl"])
        root.setSpacing(SPACE["lg"])

        title = QLabel("Change Master Password")
        title.setFont(QFont(*FONTS["h2"]))
        title.setStyleSheet(f"color: {COLORS['text']};")
        root.addWidget(title)

        subtitle = QLabel("Re-encrypts your master vault key with a new Argon2id password.")
        subtitle.setFont(QFont(*FONTS["body"]))
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']};")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        # Form card
        self.card = Card()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        card_layout.setSpacing(SPACE["sm"])

        lbl_old = QLabel("Current Master Password")
        lbl_old.setFont(QFont(*FONTS["small"]))
        lbl_old.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        card_layout.addWidget(lbl_old)

        self.old_pw_edit = self._make_input("Enter current password")
        card_layout.addWidget(self.old_pw_edit)

        card_layout.addSpacing(SPACE["sm"])

        lbl_new = QLabel("New Master Password (≥ 8 chars)")
        lbl_new.setFont(QFont(*FONTS["small"]))
        lbl_new.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        card_layout.addWidget(lbl_new)

        self.new_pw_edit = self._make_input("Enter new strong password")
        card_layout.addWidget(self.new_pw_edit)

        self.strength_bar = PasswordStrengthBar()
        self.new_pw_edit.textChanged.connect(self.strength_bar.set_password)
        card_layout.addWidget(self.strength_bar)

        card_layout.addSpacing(SPACE["sm"])

        lbl_confirm = QLabel("Confirm New Password")
        lbl_confirm.setFont(QFont(*FONTS["small"]))
        lbl_confirm.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        card_layout.addWidget(lbl_confirm)

        self.confirm_pw_edit = self._make_input("Retype new password")
        card_layout.addWidget(self.confirm_pw_edit)

        # Visibility toggle
        self.show_pw_btn = QPushButton("Show passwords")
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pw_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_secondary']};
                border: 0;
                text-align: left;
                padding: 4px 0;
                font-size: 11px;
            }}
            QPushButton:hover {{ color: {COLORS['primary']}; }}
        """)
        self.show_pw_btn.toggled.connect(self._toggle_visibility)
        card_layout.addWidget(self.show_pw_btn)

        root.addWidget(self.card)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {RADIUS['sm']}px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: {COLORS['surface_hover']}; color: {COLORS['text']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        self.submit_btn = QPushButton("Change Password")
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
        """)
        self.submit_btn.clicked.connect(self._submit)
        btn_box.addWidget(self.submit_btn)

        root.addLayout(btn_box)

    def _input_style(self) -> str:
        return f"""
            QLineEdit {{
                background: {COLORS['bg_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['sm']}px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {COLORS['primary']};
            }}
        """

    def _make_input(self, placeholder: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(40)
        edit.setStyleSheet(self._input_style())
        return edit

    def _toggle_visibility(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.old_pw_edit.setEchoMode(mode)
        self.new_pw_edit.setEchoMode(mode)
        self.confirm_pw_edit.setEchoMode(mode)
        self.show_pw_btn.setText("Hide passwords" if checked else "Show passwords")

    def _submit(self) -> None:
        old_pw = self.old_pw_edit.text()
        new_pw = self.new_pw_edit.text()
        confirm_pw = self.confirm_pw_edit.text()

        if not old_pw:
            QMessageBox.warning(self, "Missing password", "Please enter your current master password.")
            return
        if len(new_pw) < 8:
            QMessageBox.warning(self, "Weak password", "New password must be at least 8 characters.")
            return
        if new_pw != confirm_pw:
            QMessageBox.warning(self, "Mismatch", "New password and confirmation do not match.")
            return
        if old_pw == new_pw:
            QMessageBox.warning(self, "Same password", "New password must be different from current password.")
            return

        self.accept()

    def get_passwords(self) -> Optional[Tuple[str, str]]:
        if self.result() == QDialog.DialogCode.Accepted:
            return self.old_pw_edit.text(), self.new_pw_edit.text()
        return None

    def _on_theme_changed(self, _theme_data: dict) -> None:
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")
        self.card.apply_theme()
        for e in [self.old_pw_edit, self.new_pw_edit, self.confirm_pw_edit]:
            e.setStyleSheet(self._input_style())

    def done(self, result: int) -> None:
        unregister_theme_listener(self._on_theme_changed)
        super().done(result)

    def closeEvent(self, event) -> None:
        unregister_theme_listener(self._on_theme_changed)
        super().closeEvent(event)
