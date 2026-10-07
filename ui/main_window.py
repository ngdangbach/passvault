"""
ui/main_window.py — Modern vault browser với card list, sidebar, hero detail và theme engine.
"""

from __future__ import annotations

import datetime
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QGuiApplication, QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
    QPushButton, QScrollArea, QSplitter, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from core.password_gen import entropy_bits
from core.totp import generate_code
from core.vault import Vault
from ui.theme import (
    COLORS, FONTS, RADIUS, SPACE, get_all_themes, get_current_theme,
    get_current_theme_id, register_theme_listener, set_theme,
    unregister_theme_listener,
)
from ui.unlock_dialog import make_logo_icon
from ui.widgets import (
    Avatar, Card, ItemCard, PasswordGeneratorDialog, PasswordStrengthBar,
    ThemeSelectorDialog, Toast, TotpRing,
)


CATEGORIES = [
    ("all",    "All Items"),
    ("fav",    "Favorites"),
    ("recent", "Recent"),
    ("2fa",    "2FA Enabled"),
    ("weak",   "Weak Passwords"),
]


class SidebarButton(QPushButton):
    """Modern sidebar button with clean typography and count badge."""

    def __init__(self, label: str, count: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(38)
        self._label = label
        self._count = count
        self._apply_style()

    def set_count(self, count: int) -> None:
        self._count = count
        self._refresh_text()

    def _refresh_text(self) -> None:
        if self._count > 0:
            self.setText(f"  {self._label}   ({self._count})")
        else:
            self.setText(f"  {self._label}")

    def _apply_style(self) -> None:
        self._refresh_text()
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['primary']};
                    color: {COLORS['primary_fg']};
                    border: 0;
                    border-radius: {RADIUS['sm']}px;
                    text-align: left;
                    padding: 8px 14px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['text_secondary']};
                    border: 0;
                    border-radius: {RADIUS['sm']}px;
                    text-align: left;
                    padding: 8px 14px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background: {COLORS['surface_hover']};
                    color: {COLORS['text']};
                }}
            """)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._apply_style()

    def enterEvent(self, event) -> None:
        if not self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['surface_hover']};
                    color: {COLORS['text']};
                    border: 0;
                    border-radius: {RADIUS['sm']}px;
                    text-align: left;
                    padding: 8px 14px;
                    font-size: 11px;
                }}
            """)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._apply_style()
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    """Modern PassVault main interface with sidebar, card list, details, and theme engine."""

    def __init__(self, vault: Vault, on_lock) -> None:
        super().__init__()
        self.vault = vault
        self._on_lock = on_lock
        self._current_item_id: Optional[str] = None
        self._current_category = "all"
        self._all_items_meta: list = []
        self._item_cards: dict[str, ItemCard] = {}

        self.setWindowTitle("PassVault — Secure Local Vault")
        self.setMinimumSize(980, 680)
        self.resize(1150, 750)
        self.setWindowIcon(QIcon(make_logo_icon(64)))

        self._build_ui()
        self.refresh()

        # TOTP countdown timer
        self._totp_timer = QTimer(self)
        self._totp_timer.timeout.connect(self._update_totp)
        self._totp_timer.start(1000)

        # Clipboard auto-clear timer (30s)
        self._clipboard_clear_timer = QTimer(self)
        self._clipboard_clear_timer.setSingleShot(True)
        self._clipboard_clear_timer.timeout.connect(self._clear_clipboard)

        register_theme_listener(self._on_theme_changed)

        self._really_quit = False
        self._setup_tray()

    # ==========================================================================
    # UI CONSTRUCTION
    # ==========================================================================

    def _build_ui(self) -> None:
        self.central_widget = QWidget()
        root = QVBoxLayout(self.central_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top Header Bar
        self.header = self._build_header()
        root.addWidget(self.header)

        # Body Layout
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Left: Sidebar
        self.sidebar = self._build_sidebar()
        body.addWidget(self.sidebar)

        # Splitter: List & Detail
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)

        # Middle: Item List Pane
        self.list_pane = self._build_list_pane()
        self.splitter.addWidget(self.list_pane)

        # Right: Detail Pane
        self.detail_pane = self._build_detail_pane()
        self.splitter.addWidget(self.detail_pane)

        self.splitter.setSizes([380, 560])
        body.addWidget(self.splitter, stretch=1)

        body_widget = QWidget()
        body_widget.setLayout(body)
        root.addWidget(body_widget, stretch=1)

        self.toast = Toast(self)
        self.setCentralWidget(self.central_widget)

        # Apply initial styling across all components
        self._apply_theme()

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setFixedHeight(58)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(SPACE["lg"], 0, SPACE["lg"], 0)
        h_layout.setSpacing(SPACE["md"])

        # Brand Logo + Title
        self.logo_lbl = QLabel()
        self.logo_lbl.setPixmap(make_logo_icon(32))
        h_layout.addWidget(self.logo_lbl)

        self.title_lbl = QLabel("PassVault")
        self.title_lbl.setFont(QFont(*FONTS["h3"]))
        h_layout.addWidget(self.title_lbl)

        # Security Status Pill
        self.status_pill = QLabel("AES-256 GCM")
        h_layout.addWidget(self.status_pill)

        h_layout.addStretch()

        # Action: New Item
        self.add_btn = QPushButton("+ New Item")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setShortcut("Ctrl+N")
        self.add_btn.setToolTip("Add new item (Ctrl+N)")
        self.add_btn.clicked.connect(self._on_add)
        h_layout.addWidget(self.add_btn)

        # Action: Password Generator
        self.gen_btn = QPushButton("Generator")
        self.gen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_btn.setShortcut("Ctrl+G")
        self.gen_btn.setToolTip("Open Password Generator (Ctrl+G)")
        self.gen_btn.clicked.connect(self._open_generator)
        h_layout.addWidget(self.gen_btn)

        # Action: Theme Switcher
        self.theme_btn = QPushButton("Theme")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setToolTip("Change UI Theme")
        self.theme_btn.clicked.connect(self._open_theme_selector)
        h_layout.addWidget(self.theme_btn)

        # Action: Change Password
        self.ch_pw_btn = QPushButton("Change Password")
        self.ch_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ch_pw_btn.setShortcut("Ctrl+P")
        self.ch_pw_btn.clicked.connect(self._on_change_password)
        h_layout.addWidget(self.ch_pw_btn)

        # Action: Lock Vault
        self.lock_btn = QPushButton("Lock Vault")
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setShortcut("Ctrl+L")
        self.lock_btn.setToolTip("Run in background / Minimize to tray (Ctrl+L)")
        self.lock_btn.clicked.connect(self._lock)
        h_layout.addWidget(self.lock_btn)

        return header

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(SPACE["md"], SPACE["lg"], SPACE["md"], SPACE["lg"])
        layout.setSpacing(SPACE["xs"])

        # Category label
        self.cat_lbl = QLabel("CATEGORIES")
        self.cat_lbl.setFont(QFont(*FONTS["caption"]))
        layout.addWidget(self.cat_lbl)

        self.category_buttons: dict[str, SidebarButton] = {}
        for cat_id, label in CATEGORIES:
            btn = SidebarButton(label, count=0)
            btn.clicked.connect(lambda _c, cid=cat_id: self._set_category(cid))
            self.category_buttons[cat_id] = btn
            layout.addWidget(btn)

        layout.addSpacing(SPACE["md"])

        # Vault Security Health Card
        self.health_card = Card()
        health_layout = QVBoxLayout(self.health_card)
        health_layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        health_layout.setSpacing(4)

        self.health_title = QLabel("VAULT HEALTH")
        self.health_title.setFont(QFont(*FONTS["caption"]))
        health_layout.addWidget(self.health_title)

        self.health_stat_lbl = QLabel("")
        self.health_stat_lbl.setFont(QFont(*FONTS["small"]))
        health_layout.addWidget(self.health_stat_lbl)

        layout.addWidget(self.health_card)

        layout.addStretch()

        # Keyboard shortcuts hint
        self.shortcuts_lbl = QLabel("Ctrl+F Search  •  Ctrl+N New\nCtrl+G Generator  •  Ctrl+L Lock")
        self.shortcuts_lbl.setFont(QFont(*FONTS["caption"]))
        layout.addWidget(self.shortcuts_lbl)

        self.category_buttons["all"].setChecked(True)
        return sidebar

    def _build_list_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["md"], SPACE["lg"])
        layout.setSpacing(SPACE["md"])

        # Search Bar
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search logins (Ctrl+F)...")
        self.search_edit.setFixedHeight(38)
        self.search_edit.textChanged.connect(self.refresh)
        layout.addWidget(self.search_edit)

        # Filter info header
        info_row = QHBoxLayout()
        self.count_info_lbl = QLabel("0 items")
        self.count_info_lbl.setFont(QFont(*FONTS["caption"]))
        info_row.addWidget(self.count_info_lbl)
        info_row.addStretch()
        layout.addLayout(info_row)

        # Card container inside scroll area
        self.card_container = QWidget()
        self.card_container.setStyleSheet("background: transparent;")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(SPACE["sm"])
        self.card_layout.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.card_container)
        self.scroll.setWidgetResizable(True)
        # CRITICAL: Disable horizontal scrollbar completely so it never covers bottom cards
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.scroll, stretch=1)

        return pane

    def _build_detail_pane(self) -> QWidget:
        pane = QWidget()
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        layout.setSpacing(SPACE["md"])

        # Empty State
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(SPACE["md"])

        self.empty_shield_icon = QLabel()
        self.empty_shield_icon.setPixmap(make_logo_icon(64))
        self.empty_shield_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_shield_icon)

        self.empty_title = QLabel("Select a login to view credentials")
        self.empty_title.setFont(QFont(*FONTS["h3"]))
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title)

        self.empty_desc = QLabel("Encrypted and decrypted exclusively in-memory.")
        self.empty_desc.setFont(QFont(*FONTS["body"]))
        self.empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_desc)

        layout.addWidget(self.empty_state)

        # Detail Content (Visible when an item is selected)
        self.detail_content = QWidget()
        self.detail_content.setVisible(False)
        self.detail_content.setStyleSheet("background: transparent;")
        dlayout = QVBoxLayout(self.detail_content)
        dlayout.setContentsMargins(0, 0, 0, 0)
        dlayout.setSpacing(SPACE["md"])

        # Hero Header Card
        self.hero_card = Card()
        hero_layout = QHBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        hero_layout.setSpacing(SPACE["lg"])

        self.detail_avatar = Avatar("", size=56)
        hero_layout.addWidget(self.detail_avatar)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(2)
        hero_text.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.detail_name = QLabel("")
        self.detail_name.setFont(QFont(*FONTS["h2"]))
        hero_text.addWidget(self.detail_name)

        self.detail_url = QLabel("")
        self.detail_url.setFont(QFont(*FONTS["body"]))
        self.detail_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hero_text.addWidget(self.detail_url)

        hero_layout.addLayout(hero_text, stretch=1)

        # Hero Actions (Open, Edit, Delete)
        act_col = QHBoxLayout()
        act_col.setSpacing(SPACE["sm"])

        self.open_url_btn = QPushButton("Open")
        self.open_url_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_url_btn.clicked.connect(self._open_url)
        act_col.addWidget(self.open_url_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self._on_edit)
        act_col.addWidget(self.edit_btn)

        self.del_btn = QPushButton("Delete")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(self._on_delete)
        act_col.addWidget(self.del_btn)

        hero_layout.addLayout(act_col)
        dlayout.addWidget(self.hero_card)

        # Credentials Card (Username & Password)
        self.cred_card = Card()
        cred_layout = QVBoxLayout(self.cred_card)
        cred_layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        cred_layout.setSpacing(SPACE["md"])

        # Username Field
        self.lbl_user_title = QLabel("USERNAME / EMAIL")
        self.lbl_user_title.setFont(QFont(*FONTS["caption"]))
        cred_layout.addWidget(self.lbl_user_title)

        user_row = QHBoxLayout()
        self.user_value = QLabel("(none)")
        self.user_value.setFont(QFont(*FONTS["body"]))
        self.user_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        user_row.addWidget(self.user_value, stretch=1)

        self.copy_user_btn = QPushButton("Copy")
        self.copy_user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_user_btn.clicked.connect(self._copy_username)
        user_row.addWidget(self.copy_user_btn)
        cred_layout.addLayout(user_row)

        cred_layout.addSpacing(SPACE["xs"])

        # Password Field
        self.lbl_pw_title = QLabel("PASSWORD")
        self.lbl_pw_title.setFont(QFont(*FONTS["caption"]))
        cred_layout.addWidget(self.lbl_pw_title)

        pw_row = QHBoxLayout()
        self.pw_value = QLabel("••••••••••••")
        self.pw_value.setFont(QFont(*FONTS["mono_lg"]))
        self.pw_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        pw_row.addWidget(self.pw_value, stretch=1)

        self.show_pw_btn = QPushButton("Show")
        self.show_pw_btn.setCheckable(True)
        self.show_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.show_pw_btn.toggled.connect(self._toggle_pw)
        pw_row.addWidget(self.show_pw_btn)

        self.copy_pw_btn = QPushButton("Copy Password")
        self.copy_pw_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_pw_btn.clicked.connect(self._copy_password)
        pw_row.addWidget(self.copy_pw_btn)
        cred_layout.addLayout(pw_row)

        # Password Strength Bar
        self.detail_strength_bar = PasswordStrengthBar()
        cred_layout.addWidget(self.detail_strength_bar)

        dlayout.addWidget(self.cred_card)

        # TOTP 2FA Card
        self.totp_card = Card()
        totp_layout = QHBoxLayout(self.totp_card)
        totp_layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        totp_layout.setSpacing(SPACE["lg"])

        self.totp_ring = TotpRing()
        self.totp_ring.clicked.connect(self._copy_totp)
        totp_layout.addWidget(self.totp_ring)

        totp_info = QVBoxLayout()
        totp_info.setSpacing(4)
        totp_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.totp_title = QLabel("TWO-FACTOR AUTHENTICATION")
        self.totp_title.setFont(QFont(*FONTS["caption"]))
        totp_info.addWidget(self.totp_title)

        self.totp_hint = QLabel("Click code or ring to copy. Rotates every 30s.")
        self.totp_hint.setFont(QFont(*FONTS["small"]))
        totp_info.addWidget(self.totp_hint)

        self.copy_totp_btn = QPushButton("Copy TOTP Code")
        self.copy_totp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_totp_btn.clicked.connect(self._copy_totp)
        totp_info.addWidget(self.copy_totp_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        totp_layout.addLayout(totp_info, stretch=1)
        dlayout.addWidget(self.totp_card)

        # Notes Card
        self.notes_card = Card()
        notes_layout = QVBoxLayout(self.notes_card)
        notes_layout.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        notes_layout.setSpacing(4)

        self.notes_title = QLabel("NOTES")
        self.notes_title.setFont(QFont(*FONTS["caption"]))
        notes_layout.addWidget(self.notes_title)

        self.notes_label = QLabel("No notes")
        self.notes_label.setFont(QFont(*FONTS["body"]))
        self.notes_label.setWordWrap(True)
        self.notes_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        notes_layout.addWidget(self.notes_label)

        dlayout.addWidget(self.notes_card)

        # Footer Timestamps
        self.audit_lbl = QLabel("")
        self.audit_lbl.setFont(QFont(*FONTS["caption"]))
        dlayout.addWidget(self.audit_lbl)

        dlayout.addStretch()
        layout.addWidget(self.detail_content)
        layout.addStretch()

        return pane

    # ==========================================================================
    # COMPREHENSIVE DYNAMIC RE-THEMING (PREVENTS COLOR MISMATCHES)
    # ==========================================================================

    def _apply_theme(self) -> None:
        """Thoroughly updates every widget with the current active theme tokens."""
        cur_theme = get_current_theme()

        # Backgrounds
        self.setStyleSheet(f"QMainWindow {{ background: {COLORS['bg']}; }}")
        self.central_widget.setStyleSheet(f"background: {COLORS['bg']};")
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background: {COLORS['border']}; }}")

        # Header
        self.header.setStyleSheet(f"""
            background: {COLORS['surface']};
            border-bottom: 1px solid {COLORS['border']};
        """)
        self.logo_lbl.setPixmap(make_logo_icon(32))
        self.title_lbl.setStyleSheet(f"color: {COLORS['text']}; background: transparent; font-weight: bold;")
        self.status_pill.setStyleSheet(f"""
            background: {COLORS['bg_alt']};
            color: {COLORS['success']};
            border: 1px solid {COLORS['border']};
            border-radius: {RADIUS['pill']}px;
            padding: 3px 10px;
            font-size: 10px;
            font-weight: bold;
        """)

        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                padding: 7px 16px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
        """)

        ghost_style = f"""
            QPushButton {{
                background: {COLORS['surface_hover']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {RADIUS['sm']}px;
                padding: 7px 13px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_press']};
                color: {COLORS['text']};
            }}
        """
        self.gen_btn.setStyleSheet(ghost_style)
        self.theme_btn.setStyleSheet(ghost_style)
        self.theme_btn.setText("Theme")
        self.ch_pw_btn.setStyleSheet(ghost_style)

        self.lock_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['danger']};
                border: 1px solid {COLORS['danger']};
                border-radius: {RADIUS['sm']}px;
                padding: 7px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']};
                color: #ffffff;
            }}
        """)

        # Sidebar
        self.sidebar.setStyleSheet(f"""
            background: {COLORS['surface']};
            border-right: 1px solid {COLORS['border']};
        """)
        self.cat_lbl.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            background: transparent;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 4px 10px;
        """)
        for btn in self.category_buttons.values():
            btn._apply_style()

        self.health_card.apply_theme()
        self.health_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; letter-spacing: 1px;")
        self.health_stat_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; line-height: 1.4;")
        self.shortcuts_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 6px 8px; line-height: 1.3;")

        # List pane
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                background: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['md']}px;
                padding: 8px 14px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {COLORS['primary']};
            }}
        """)
        self.count_info_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold;")
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: 0; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border_strong']};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['primary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        # Empty state
        self.empty_shield_icon.setPixmap(make_logo_icon(64))
        self.empty_title.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.empty_desc.setStyleSheet(f"color: {COLORS['text_muted']};")

        # Detail pane
        self.hero_card.apply_theme()
        self.detail_avatar.update()
        self.detail_name.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        self.detail_url.setStyleSheet(f"color: {COLORS['primary']};")

        small_ghost = f"""
            QPushButton {{
                background: {COLORS['surface_hover']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border_strong']};
                border-radius: {RADIUS['sm']}px;
                padding: 6px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_press']};
                color: {COLORS['text']};
            }}
        """
        self.open_url_btn.setStyleSheet(small_ghost)
        self.edit_btn.setStyleSheet(small_ghost)
        self.del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['danger']};
                border: 1px solid {COLORS['danger']};
                border-radius: {RADIUS['sm']}px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']};
                color: #ffffff;
            }}
        """)

        # Credentials card
        self.cred_card.apply_theme()
        self.lbl_user_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; letter-spacing: 1px;")
        self.user_value.setStyleSheet(f"color: {COLORS['text']};")
        self.copy_user_btn.setStyleSheet(small_ghost)

        self.lbl_pw_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; letter-spacing: 1px;")
        self.pw_value.setStyleSheet(f"color: {COLORS['text']}; letter-spacing: 1.5px;")
        self.show_pw_btn.setStyleSheet(small_ghost)
        self.copy_pw_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: {COLORS['primary_fg']};
                border: 0;
                border-radius: {RADIUS['sm']}px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {COLORS['primary_hover']}; }}
        """)
        self.detail_strength_bar.update()

        # TOTP card
        self.totp_card.apply_theme()
        self.totp_ring.update()
        self.totp_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; letter-spacing: 1px;")
        self.totp_hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.copy_totp_btn.setStyleSheet(small_ghost)

        # Notes card
        self.notes_card.apply_theme()
        self.notes_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-weight: bold; letter-spacing: 1px;")
        self.notes_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.audit_lbl.setStyleSheet(f"color: {COLORS['text_muted']};")

        # Toast
        self.toast.apply_theme()

        # Re-apply styles to all existing cards in the list
        for card in self._item_cards.values():
            card.apply_style()

        # Update System Tray icon & styling
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.setIcon(QIcon(make_logo_icon(64)))
        self._update_tray_menu_style()

    # ==========================================================================
    # DATA & LOGIC
    # ==========================================================================

    def refresh(self) -> None:
        all_items = self.vault.list_items()
        self._all_items_meta = all_items

        # Calculate counts & audit weak passwords
        weak_count = 0
        totp_count = 0
        items_with_pw = []

        for it in all_items:
            full = self.vault.get_item(it["id"])
            if full:
                pw = full.password
                if it["has_totp"]:
                    totp_count += 1
                if pw and (len(pw) < 8 or entropy_bits(pw, 94) < 36):
                    weak_count += 1
                it_dict = dict(it)
                it_dict["password"] = pw
                items_with_pw.append(it_dict)
            else:
                items_with_pw.append(dict(it))

        counts = {
            "all":    len(all_items),
            "fav":    sum(1 for it in all_items if it.get("is_pinned")),
            "recent": min(10, len(all_items)),
            "2fa":    totp_count,
            "weak":   weak_count,
        }

        for cat_id, btn in self.category_buttons.items():
            btn.set_count(counts.get(cat_id, 0))

        # Health card stats
        pct_2fa = int((totp_count / max(1, len(all_items))) * 100)
        self.health_stat_lbl.setText(
            f"• {counts['all']} Total Logins\n"
            f"• {totp_count} Protected with 2FA ({pct_2fa}%)\n"
            f"• {weak_count} Weak Passwords"
        )

        # Apply category filter
        items = self._filter_items(items_with_pw)

        # Apply search filter
        query = self.search_edit.text().lower().strip()
        if query:
            items = [
                it for it in items
                if query in it["name"].lower()
                or query in it.get("url", "").lower()
                or query in it.get("username", "").lower()
            ]

        self.count_info_lbl.setText(f"{len(items)} items matching")
        self._rebuild_card_list(items)

        # Preserve selection if item still exists
        if self._current_item_id:
            for it in items:
                if it["id"] == self._current_item_id:
                    self._show_detail(self._current_item_id)
                    return
        self._clear_detail()

    def _filter_items(self, items: list) -> list:
        if self._current_category == "fav":
            return [it for it in items if it.get("is_pinned")]
        if self._current_category == "recent":
            return items[:10]
        if self._current_category == "2fa":
            return [it for it in items if it["has_totp"]]
        if self._current_category == "weak":
            return [
                it for it in items
                if it.get("password") and (len(it["password"]) < 8 or entropy_bits(it["password"], 94) < 36)
            ]
        return items

    def _set_category(self, cat_id: str) -> None:
        for cid, btn in self.category_buttons.items():
            btn.setChecked(cid == cat_id)
        self._current_category = cat_id
        self.refresh()

    def _rebuild_card_list(self, items: list) -> None:
        while self.card_layout.count() > 1:
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._item_cards.clear()

        if not items:
            empty = QLabel("No logins found")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 40px; font-size: 12px;")
            self.card_layout.insertWidget(0, empty)
            return

        for it in items:
            is_sel = (it["id"] == self._current_item_id)
            card = ItemCard(it, is_selected=is_sel)
            card.clicked.connect(self._on_card_clicked)
            self._item_cards[it["id"]] = card
            self.card_layout.insertWidget(self.card_layout.count() - 1, card)

    def _on_card_clicked(self, item_id: str) -> None:
        self._current_item_id = item_id
        for cid, card in self._item_cards.items():
            card.set_selected(cid == item_id)
        self._show_detail(item_id)

    def _show_detail(self, item_id: str) -> None:
        item = self.vault.get_item(item_id)
        if not item:
            return

        self.empty_state.setVisible(False)
        self.detail_content.setVisible(True)

        self.detail_avatar.set_name(item.name)
        self.detail_name.setText(item.name)
        self.detail_url.setText(item.url or "(no url)")

        self.user_value.setText(item.username or "(no username)")
        self.notes_label.setText(item.notes or "No notes")

        self._cached_username = item.username
        self._cached_url = item.url
        self._cached_password = item.password
        self._cached_totp = item.totp_secret

        # Password mask & strength bar
        self._pw_visible = False
        self.show_pw_btn.setChecked(False)
        self.show_pw_btn.setText("Show")
        self.pw_value.setText("••••••••••••" if item.password else "(none)")
        self.detail_strength_bar.set_password(item.password)

        # TOTP
        if item.totp_secret:
            self.totp_card.setVisible(True)
            self.totp_ring.set_secret(item.totp_secret)
        else:
            self.totp_ring.clear()
            self.totp_card.setVisible(False)

        # Audit dates
        up_date = datetime.datetime.fromtimestamp(item.updated_at).strftime("%Y-%m-%d %H:%M")
        self.audit_lbl.setText(f"Last updated: {up_date}")

    def _clear_detail(self) -> None:
        self.empty_state.setVisible(True)
        self.detail_content.setVisible(False)
        self._current_item_id = None
        self.totp_ring.clear()
        self._cached_username = ""
        self._cached_url = ""
        self._cached_password = ""
        self._cached_totp = ""

    def _toggle_pw(self, checked: bool) -> None:
        self._pw_visible = checked
        if checked:
            self.pw_value.setText(self._cached_password or "(empty)")
            self.show_pw_btn.setText("Hide")
        else:
            self.pw_value.setText("••••••••••••" if self._cached_password else "(none)")
            self.show_pw_btn.setText("Show")

    def _update_totp(self) -> None:
        totp_secret = getattr(self, "_cached_totp", "")
        if not totp_secret:
            self.totp_ring.clear()
            return
        try:
            code, remaining = generate_code(totp_secret)
            formatted = f"{code[:3]} {code[3:]}"
            self.totp_ring.update_state(formatted, remaining, total=30)
        except Exception:
            self.totp_ring.update_state("ERR", 0)

    # ==========================================================================
    # ACTIONS
    # ==========================================================================

    def _copy_username(self) -> None:
        v = getattr(self, "_cached_username", "")
        if v:
            QGuiApplication.clipboard().setText(v)
            self.toast.show_message(f"Copied username: {v}")

    def _copy_url(self) -> None:
        v = getattr(self, "_cached_url", "")
        if v:
            QGuiApplication.clipboard().setText(v)
            self.toast.show_message(f"Copied URL: {v}")

    def _open_url(self) -> None:
        import webbrowser
        url = getattr(self, "_cached_url", "")
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            webbrowser.open(url)
            self.toast.show_message(f"Opened {url}")
        except Exception as e:
            self.toast.show_message(f"Cannot open: {e}")

    def _copy_password(self) -> None:
        pw = getattr(self, "_cached_password", "")
        if not pw:
            return
        QGuiApplication.clipboard().setText(pw)
        self._clipboard_clear_timer.start(30_000)
        self.toast.show_message("Password copied — auto-clears in 30s")

    def _copy_totp(self) -> None:
        totp_secret = getattr(self, "_cached_totp", "")
        if not totp_secret:
            return
        try:
            code, _ = generate_code(totp_secret)
            QGuiApplication.clipboard().setText(code)
            self.toast.show_message(f"TOTP copied: {code}")
        except Exception:
            pass

    def _clear_clipboard(self) -> None:
        QGuiApplication.clipboard().clear()
        self.toast.show_message("Clipboard cleared for security")

    def _on_add(self) -> None:
        from ui.item_dialog import ItemDialog
        dlg = ItemDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            self.vault.add_item(**data)
            self.refresh()
            self.toast.show_message(f"Added {data['name']}")

    def _on_edit(self) -> None:
        if not self._current_item_id:
            return
        item = self.vault.get_item(self._current_item_id)
        if not item:
            return
        from ui.item_dialog import ItemDialog
        existing = {
            "id": item.id, "name": item.name, "url": item.url,
            "username": item.username, "password": item.password,
            "totp_secret": item.totp_secret, "notes": item.notes,
        }
        dlg = ItemDialog(self, existing=existing)
        if dlg.exec():
            data = dlg.get_data()
            self.vault.update_item(self._current_item_id, **data)
            self.refresh()
            self._show_detail(self._current_item_id)
            self.toast.show_message(f"Updated {data['name']}")

    def _on_delete(self) -> None:
        if not self._current_item_id:
            return
        item = self.vault.get_item(self._current_item_id)
        if not item:
            return
        reply = QMessageBox.warning(
            self, "Confirm Delete",
            f"Are you sure you want to delete '{item.name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.vault.delete_item(self._current_item_id)
            self._current_item_id = None
            self.refresh()
            self.toast.show_message("Item deleted")

    def _open_generator(self) -> None:
        dlg = PasswordGeneratorDialog(self)
        if dlg.exec():
            self.toast.show_message("Generated password copied to clipboard")

    def _open_theme_selector(self) -> None:
        dlg = ThemeSelectorDialog(self)
        dlg.exec()

    def _on_change_password(self) -> None:
        from core.vault import change_master_password
        from ui.change_password_dialog import ChangePasswordDialog

        dlg = ChangePasswordDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        passwords = dlg.get_passwords()
        if not passwords:
            return
        old_pw, new_pw = passwords
        new_vault = change_master_password(self.vault.db, old_pw, new_pw)
        if new_vault is None:
            QMessageBox.warning(self, "Failed", "Incorrect master password.")
            return

        self.vault = new_vault
        self.toast.show_message("Master password updated successfully")

    # ==========================================================================
    # SYSTEM TRAY & BACKGROUND RUNTIME
    # ==========================================================================

    def _setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(make_logo_icon(64)))
        self.tray_icon.setToolTip("PassVault — Secure Password Manager")
        self.tray_icon.activated.connect(self._on_tray_activated)

        self.tray_menu = QMenu()
        self._update_tray_menu_style()

        act_open = self.tray_menu.addAction("Open PassVault")
        act_open.setFont(QFont(*FONTS["ui_bold"]))
        act_open.triggered.connect(self._restore_from_tray)

        act_new = self.tray_menu.addAction("New Item")
        act_new.triggered.connect(self._on_tray_new_item)

        self.tray_menu.addSeparator()

        act_exit = self.tray_menu.addAction("Exit PassVault")
        act_exit.triggered.connect(self._quit_application)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()

    def _update_tray_menu_style(self) -> None:
        if hasattr(self, "tray_menu") and self.tray_menu:
            self.tray_menu.setStyleSheet(f"""
                QMenu {{
                    background: {COLORS['surface']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    border-radius: {RADIUS['sm']}px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 16px;
                    border-radius: {RADIUS['xs']}px;
                    font-size: 11px;
                }}
                QMenu::item:selected {{
                    background: {COLORS['primary']};
                    color: {COLORS['primary_fg']};
                }}
                QMenu::separator {{
                    height: 1px;
                    background: {COLORS['border']};
                    margin: 4px 8px;
                }}
            """)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.isVisible() and not self.isMinimized():
                self._minimize_to_tray()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _minimize_to_tray(self) -> None:
        self.hide()
        if not getattr(self, "_has_notified_tray", False):
            self._has_notified_tray = True
            if self.tray_icon.isSystemTrayAvailable():
                self.tray_icon.showMessage(
                    "PassVault",
                    "PassVault is running in background. Click icon to reopen without master password.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2500,
                )

    def _on_tray_new_item(self) -> None:
        self._restore_from_tray()
        self._on_add()

    def _quit_application(self) -> None:
        self._really_quit = True
        self.close()

    def _lock(self) -> None:
        self._minimize_to_tray()

    def _on_theme_changed(self, theme_data: dict) -> None:
        self._apply_theme()
        self.refresh()

    def closeEvent(self, event) -> None:
        if getattr(self, "_really_quit", False):
            self._clear_clipboard()
            unregister_theme_listener(self._on_theme_changed)
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.hide()
            self._on_lock()
            event.accept()
        else:
            event.ignore()
            self._minimize_to_tray()
