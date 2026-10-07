"""
ui/item_dialog.py — Modern Add/Edit vault item dialog.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication, QImage
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)
from PIL import Image

from core.password_gen import PasswordConfig, entropy_bits, generate
from core.qr_scanner import (
    capture_region, decode_qr_codes, extract_otpauth_from_string,
)
from core.totp import normalize_secret
from ui.theme import (
    COLORS, FONTS, RADIUS, SPACE, register_theme_listener, unregister_theme_listener,
)
from ui.widgets import Card, PasswordGeneratorDialog, PasswordStrengthBar


class ItemDialog(QDialog):
    """Add/Edit vault item modal with integrated generator & QR code scanner."""

    def __init__(
        self,
        parent: Optional[QWidget],
        existing: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self.is_edit = existing is not None
        self.setWindowTitle("Edit Item" if self.is_edit else "Add New Login")
        self.setModal(True)
        self.setMinimumWidth(560)
        self._build_ui()
        if existing:
            self._fill_existing(existing)
        register_theme_listener(self._on_theme_changed)

    def _build_ui(self) -> None:
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["xl"])
        root.setSpacing(SPACE["lg"])

        # Title
        title_lbl = QLabel("Edit Login Credentials" if self.is_edit else "New Login Credentials")
        title_lbl.setFont(QFont(*FONTS["h2"]))
        title_lbl.setStyleSheet(f"color: {COLORS['text']};")
        root.addWidget(title_lbl)

        # Card container
        self.card = Card()
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        card_layout.setSpacing(SPACE["md"])

        form = QFormLayout()
        form.setVerticalSpacing(SPACE["md"])
        form.setHorizontalSpacing(SPACE["lg"])

        # Inputs
        self.name_edit = self._make_input("e.g. GitHub, Google, Work Email...")
        self.url_edit = self._make_input("https://...")
        self.username_edit = self._make_input("Email or username")
        self.password_edit = self._make_input("Password", password=True)
        self.totp_edit = self._make_input("Base32 TOTP secret key")
        self.notes_edit = self._make_input("Additional notes (optional)")

        # Password Row (input + Show + Generate)
        pw_row = QHBoxLayout()
        pw_row.setSpacing(SPACE["sm"])
        pw_row.addWidget(self.password_edit, stretch=1)

        self.show_pw_btn = QPushButton("Show")
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pw_btn.setStyleSheet(self._secondary_btn_style())
        self.show_pw_btn.toggled.connect(self._toggle_pw)
        pw_row.addWidget(self.show_pw_btn)

        gen_btn = QPushButton("Generate")
        gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        gen_btn.setStyleSheet(self._secondary_btn_style())
        gen_btn.clicked.connect(self._on_generate)
        pw_row.addWidget(gen_btn)

        # Strength Bar
        self.strength_bar = PasswordStrengthBar()
        self.password_edit.textChanged.connect(self.strength_bar.set_password)

        pw_col = QVBoxLayout()
        pw_col.setSpacing(SPACE["xs"])
        pw_col.addLayout(pw_row)
        pw_col.addWidget(self.strength_bar)

        # TOTP Row (input + Scan QR menu)
        totp_row = QHBoxLayout()
        totp_row.setSpacing(SPACE["sm"])
        totp_row.addWidget(self.totp_edit, stretch=1)

        self.scan_btn = QPushButton("Scan QR")
        self.scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_btn.setStyleSheet(self._primary_btn_style())
        self.scan_btn.clicked.connect(self._on_scan_menu)
        totp_row.addWidget(self.scan_btn)

        # Add to form
        form.addRow(self._make_label("Service / Name:"), self.name_edit)
        form.addRow(self._make_label("Website URL:"), self.url_edit)
        form.addRow(self._make_label("Username:"), self.username_edit)
        form.addRow(self._make_label("Password:"), pw_col)
        form.addRow(self._make_label("2FA Secret:"), totp_row)
        form.addRow(self._make_label("Notes:"), self.notes_edit)

        card_layout.addLayout(form)
        root.addWidget(self.card)

        # Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(self._secondary_btn_style())
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Login")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(self._primary_btn_style())
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._submit)
        btn_box.addWidget(save_btn)

        root.addLayout(btn_box)

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont(*FONTS["body"]))
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent; font-weight: bold;")
        return lbl

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

    def _primary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
            QPushButton:pressed {{ background: {COLORS['primary_press']}; }}
        """

    def _secondary_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {RADIUS['sm']}px;
                padding: 8px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
                color: {COLORS['text']};
            }}
        """

    def _make_input(self, placeholder: str, password: bool = False) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(self._input_style())
        if password:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        return edit

    def _toggle_pw(self, checked: bool) -> None:
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.show_pw_btn.setText("Hide" if checked else "Show")

    def _fill_existing(self, data: dict) -> None:
        self.name_edit.setText(data.get("name", ""))
        self.url_edit.setText(data.get("url", ""))
        self.username_edit.setText(data.get("username", ""))
        self.password_edit.setText(data.get("password", ""))
        self.totp_edit.setText(data.get("totp_secret", ""))
        self.notes_edit.setText(data.get("notes", ""))
        self.strength_bar.set_password(data.get("password", ""))

    def _on_generate(self) -> None:
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pw = dlg.get_password()
            if pw:
                self.password_edit.setText(pw)
                self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
                self.show_pw_btn.setChecked(True)

    def _on_scan_menu(self) -> None:
        menu = QMenu(self)
        act_screen = menu.addAction("Capture from screen...")
        act_paste = menu.addAction("Paste image from clipboard")
        act_file = menu.addAction("Open QR image file...")

        has_img = QGuiApplication.clipboard().mimeData().hasImage()
        act_paste.setEnabled(has_img)

        act_screen.triggered.connect(self._scan_from_screen)
        act_paste.triggered.connect(self._paste_from_clipboard)
        act_file.triggered.connect(self._open_file)

        btn = self.sender()
        if isinstance(btn, QWidget):
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _scan_from_screen(self) -> None:
        from ui.qr_overlay import QRSelectorOverlay
        self.hide()
        overlay = QRSelectorOverlay()
        region = overlay.select_region()
        self.show()
        self.raise_()
        self.activateWindow()

        if region is None:
            return

        try:
            img = capture_region(region.x(), region.y(), region.width(), region.height())
            self._process_qr_image(img)
        except Exception as e:
            QMessageBox.warning(self, "Capture failed", f"Could not capture screen: {e}")

    def _paste_from_clipboard(self) -> None:
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if not mime.hasImage():
            QMessageBox.warning(self, "No image", "Clipboard does not contain an image.")
            return
        img = clipboard.image()
        if img.isNull():
            return
        pil_img = self._qimage_to_pil(img)
        self._process_qr_image(pil_img)

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open QR image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if not path:
            return
        try:
            img = Image.open(path)
            self._process_qr_image(img)
        except Exception as e:
            QMessageBox.warning(self, "Cannot open file", f"Error: {e}")

    def _process_qr_image(self, img) -> None:
        if img is None:
            return
        results = decode_qr_codes(img)
        if not results:
            QMessageBox.warning(
                self, "No QR detected",
                "Could not find a valid QR code in the image."
            )
            return
        self._apply_otpauth_data(results[0])

    def _apply_otpauth_data(self, data: str) -> None:
        parsed = extract_otpauth_from_string(data)
        if not parsed:
            QMessageBox.warning(self, "Invalid TOTP", "Data is not a valid TOTP key.")
            return

        secret = parsed.get("secret", "")
        if not secret:
            QMessageBox.warning(self, "No secret", "QR does not contain a secret.")
            return

        self.totp_edit.setText(secret)
        issuer = parsed.get("issuer", "").strip()
        account = parsed.get("account", "").strip()

        if issuer and not self.name_edit.text().strip():
            self.name_edit.setText(issuer)
        if account and not self.username_edit.text().strip():
            self.username_edit.setText(account)

        QMessageBox.information(
            self, "QR Loaded",
            f"TOTP configured successfully for {issuer or account or 'Account'}!"
        )

    @staticmethod
    def _qimage_to_pil(qimg) -> Image.Image:
        qimg = qimg.convertToFormat(QImage.Format.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        ptr.setsize(w * h * 4)
        return Image.frombytes("RGBA", (w, h), bytes(ptr))

    def _submit(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Missing field", "Service name is required.")
            return
        if not self.password_edit.text():
            QMessageBox.warning(self, "Missing field", "Password is required.")
            return
        if self.totp_edit.text().strip():
            self.totp_edit.setText(normalize_secret(self.totp_edit.text()))
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "url": self.url_edit.text().strip(),
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text(),
            "totp_secret": self.totp_edit.text().strip(),
            "notes": self.notes_edit.text(),
        }

    def _on_theme_changed(self, _theme_data: dict) -> None:
        self.setStyleSheet(f"QDialog {{ background: {COLORS['bg']}; }}")
        self.card.apply_theme()
        for edit in [
            self.name_edit, self.url_edit, self.username_edit,
            self.password_edit, self.totp_edit, self.notes_edit
        ]:
            edit.setStyleSheet(self._input_style())

    def done(self, result: int) -> None:
        unregister_theme_listener(self._on_theme_changed)
        super().done(result)

    def closeEvent(self, event) -> None:
        unregister_theme_listener(self._on_theme_changed)
        super().closeEvent(event)
