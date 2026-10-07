"""
ui/qr_overlay.py — Fullscreen overlay để user chọn vùng QR trên màn hình.

Cách dùng:
  overlay = QRSelectorOverlay()
  region = overlay.select_region()  # blocking call, returns QRect or None
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QRect, QPoint, QEventLoop
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QGuiApplication
from PyQt6.QtWidgets import QWidget

from ui.theme import COLORS, FONTS


class QRSelectorOverlay(QWidget):
    """Fullscreen semi-transparent overlay. User drags để chọn region.

    Esc = cancel
    Click+drag = select region (must be > 20x20 px)
    Release = confirm
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Allow truly transparent background where we don't paint
        # Without this, unpainted areas show widget's opaque default bg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Cover all monitors
        all_screens = QGuiApplication.screens()
        if all_screens:
            combined = all_screens[0].geometry()
            for screen in all_screens[1:]:
                combined = combined.united(screen.geometry())
            self.setGeometry(combined)
        else:
            self.setGeometry(QGuiApplication.primaryScreen().geometry())

        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

        self._start: Optional[QPoint] = None
        self._end: Optional[QPoint] = None
        self._selection = QRect()

        self._loop: Optional[QEventLoop] = None
        self._result: Optional[QRect] = None
        self._cancelled = False

        self._hint_text = (
            "Click and drag to select the QR code area. Press Esc to cancel."
        )

    def select_region(self) -> Optional[QRect]:
        """Show overlay, block until user selects hoặc cancels.

        Returns:
            QRect in screen coordinates, or None if cancelled.
        """
        self._result = None
        self._cancelled = False
        self._start = None
        self._end = None
        self._selection = QRect()

        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        # Event loop blocks until quit() is called
        self._loop = QEventLoop()
        self._loop.exec()

        self.hide()
        return self._result

    def _finish(self, result: Optional[QRect], cancelled: bool = False) -> None:
        """Stop the event loop with result."""
        self._result = result
        self._cancelled = cancelled
        if self._loop:
            self._loop.quit()

    # ---------- Mouse events ----------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self._update_selection()
            self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._start is not None:
            self._end = event.position().toPoint()
            self._update_selection()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._start is not None:
            self._end = event.position().toPoint()
            self._update_selection()
            if self._selection.width() > 20 and self._selection.height() > 20:
                self._finish(self._selection)
            else:
                # Too small - reset and let user try again
                self._start = None
                self._end = None
                self._selection = QRect()
                self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._finish(None, cancelled=True)

    # ---------- Paint ----------

    def paintEvent(self, _event) -> None:
        p = QPainter(self)

        if self._selection.isNull() or self._selection.width() == 0:
            # No selection yet - dark everywhere
            p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        else:
            # Draw 4 dark rectangles AROUND the selection
            # This way the selection area shows the desktop through (no clear needed)
            sel = self._selection
            overlay_color = QColor(0, 0, 0, 140)

            # Top region
            if sel.top() > 0:
                p.fillRect(0, 0, self.width(), sel.top(), overlay_color)
            # Bottom region
            if sel.bottom() < self.height():
                p.fillRect(0, sel.bottom(), self.width(),
                           self.height() - sel.bottom(), overlay_color)
            # Left region (within selection height range)
            if sel.left() > 0:
                p.fillRect(0, sel.top(), sel.left(), sel.height(), overlay_color)
            # Right region
            if sel.right() < self.width():
                p.fillRect(sel.right(), sel.top(),
                           self.width() - sel.right(), sel.height(), overlay_color)

            # Selection border
            pen = QPen(QColor(COLORS["primary"]), 2, Qt.PenStyle.SolidLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self._selection)

            # Crosshair in center
            cx = self._selection.center().x()
            cy = self._selection.center().y()
            p.setPen(QPen(QColor(COLORS["primary"]), 1))
            p.drawLine(cx - 12, cy, cx + 12, cy)
            p.drawLine(cx, cy - 12, cx, cy + 12)

            # Size label above selection
            label = f"{self._selection.width()} x {self._selection.height()}"
            font = QFont(*FONTS["body"])
            font.setBold(True)
            p.setFont(font)
            metrics = p.fontMetrics()
            label_w = metrics.horizontalAdvance(label) + 16
            label_h = metrics.height() + 8
            label_x = self._selection.x()
            label_y = max(0, self._selection.y() - label_h - 4)
            p.setBrush(QBrush(QColor(COLORS["primary"])))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(label_x, label_y, label_w, label_h, 4, 4)
            p.setPen(QColor("white"))
            p.drawText(label_x + 8, label_y + metrics.ascent() + 4, label)

        # Hint text at top center
        p.setPen(QColor("white"))
        font = QFont(*FONTS["body"])
        p.setFont(font)
        metrics = p.fontMetrics()
        text_w = metrics.horizontalAdvance(self._hint_text) + 32
        text_h = metrics.height() + 16
        p.setBrush(QBrush(QColor(0, 0, 0, 180)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(
            (self.width() - text_w) // 2, 20,
            text_w, text_h, 8, 8
        )
        p.setPen(QColor("white"))
        p.drawText(
            (self.width() - text_w) // 2 + 16,
            20 + metrics.ascent() + 8,
            self._hint_text
        )

    # ---------- Helpers ----------

    def _update_selection(self) -> None:
        if self._start is None or self._end is None:
            self._selection = QRect()
            return
        self._selection = QRect(self._start, self._end).normalized()
