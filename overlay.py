import logging
import time
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient

log = logging.getLogger('echotype.overlay')


NEON = QColor(0, 255, 65)
CYAN = QColor(0, 212, 255)
RED = QColor(255, 51, 68)
PURPLE = QColor(192, 132, 252)
BG = QColor(10, 14, 20, 240)
BORDER_COLOR = QColor(0, 255, 65, 80)
MONO = 'Consolas'


class RecordingOverlay(QWidget):
    """Floating overlay in the bottom-right corner — cyberpunk style."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._status = 'recording'
        self._dot_visible = True
        self._level_history = [0.0] * 24

        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._toggle_dot)
        self._dot_timer.setInterval(500)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self._error_text = ''
        self._tick = 0

        self.setFixedSize(320, 60)
        self._reposition()

    def _reposition(self):
        primary = QApplication.primaryScreen()
        if primary is None:
            log.warning('primaryScreen() returned None, skipping reposition')
            return
        screen = primary.availableGeometry()
        x = screen.right() - self.width() - 16
        y = screen.bottom() - self.height() - 16
        self.move(x, y)

    # --- public API ---

    def show_recording(self):
        self._status = 'recording'
        self._dot_visible = True
        self._level_history = [0.0] * 24
        self._tick = 0
        self._dot_timer.start()
        self._hide_timer.stop()
        self._reposition()
        self.show()
        self.update()

    def show_transcribing(self):
        self._status = 'transcribing'
        self._dot_timer.stop()
        self._level_history = [0.0] * 24
        self.update()

    def show_enhancing(self):
        self._status = 'enhancing'
        self._dot_timer.stop()
        self.update()

    def show_done(self):
        self._status = 'done'
        self._dot_timer.stop()
        self.update()
        self._hide_timer.start(2000)

    def show_error(self, text):
        self._status = 'error'
        self._error_text = text[:60]
        self._dot_timer.stop()
        self._reposition()
        self.show()
        self.update()
        self._hide_timer.start(6000)

    def update_level(self, level):
        self._level_history.pop(0)
        self._level_history.append(level)
        self._tick += 1
        self.update()

    # --- internals ---

    def _toggle_dot(self):
        self._dot_visible = not self._dot_visible
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        rect = QRectF(1, 1, w - 2, h - 2)

        # background
        p.setBrush(BG)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, 10, 10)

        # neon border
        if self._status == 'recording':
            border_c = QColor(RED)
            border_c.setAlpha(140)
        elif self._status == 'transcribing':
            border_c = QColor(CYAN)
            border_c.setAlpha(100)
        elif self._status == 'enhancing':
            border_c = QColor(PURPLE)
            border_c.setAlpha(120)
        elif self._status == 'done':
            border_c = QColor(NEON)
            border_c.setAlpha(140)
        else:
            border_c = QColor(RED)
            border_c.setAlpha(100)

        pen = QPen(border_c)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, 10, 10)

        # top scanline accent
        grad = QLinearGradient(0, 2, w, 2)
        grad.setColorAt(0, QColor(border_c.red(), border_c.green(), border_c.blue(), 0))
        grad.setColorAt(0.3, border_c)
        grad.setColorAt(0.7, border_c)
        grad.setColorAt(1, QColor(border_c.red(), border_c.green(), border_c.blue(), 0))
        p.setPen(QPen(grad, 1))
        p.drawLine(20, 2, w - 20, 2)

        # content
        if self._status == 'recording':
            self._paint_recording(p)
        elif self._status == 'transcribing':
            self._paint_transcribing(p)
        elif self._status == 'enhancing':
            self._paint_enhancing(p)
        elif self._status == 'done':
            self._paint_done(p)
        elif self._status == 'error':
            self._paint_error(p)

        p.end()

    def _paint_recording(self, p: QPainter):
        # pulsing red dot with glow
        if self._dot_visible:
            # glow
            glow = QColor(RED)
            glow.setAlpha(40)
            p.setBrush(glow)
            p.setPen(Qt.NoPen)
            p.drawEllipse(12, 19, 20, 20)
            # core dot
            p.setBrush(RED)
            p.drawEllipse(16, 23, 12, 12)

        # text
        p.setPen(QColor(RED))
        p.setFont(QFont(MONO, 10, QFont.Bold))
        p.drawText(40, 34, 'REC')

        # separator
        p.setPen(QColor(255, 255, 255, 30))
        p.drawLine(70, 16, 70, 44)

        # audio bars — neon green
        self._paint_bars(p, start_x=80)

    def _paint_bars(self, p: QPainter, start_x: int):
        bar_w = 3
        gap = 3
        max_h = 34
        cy = self.height() // 2

        for i, level in enumerate(self._level_history):
            x = start_x + i * (bar_w + gap)
            h = max(2, int(level * max_h))
            y = cy - h // 2

            # gradient from green to bright green with intensity
            intensity = min(255, int(100 + level * 155))
            color = QColor(0, intensity, int(40 + level * 25), 200)

            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, y, bar_w, h), 1.5, 1.5)

            # top glow pixel for tall bars
            if level > 0.5:
                glow = QColor(NEON)
                glow.setAlpha(int(level * 120))
                p.setBrush(glow)
                p.drawRect(QRectF(x, y - 1, bar_w, 2))

    def _paint_processing(self, p: QPainter, color: QColor, label: str, dot_x: int):
        """Shared painter for transcribing / enhancing states."""
        p.setPen(color)
        p.setFont(QFont(MONO, 10, QFont.Bold))
        p.drawText(20, 34, label)

        # animated dots with trailing effect
        phase = int(time.time() * 4) % 4
        for i in range(4):
            dist = (phase - i) % 4
            alpha = max(30, 220 - dist * 60)
            c = QColor(color)
            c.setAlpha(alpha)
            p.setBrush(c)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(dot_x + i * 18, 25, 10, 8), 3, 3)

    def _paint_transcribing(self, p: QPainter):
        self._paint_processing(p, CYAN, 'PROCESSING', 150)

    def _paint_enhancing(self, p: QPainter):
        self._paint_processing(p, PURPLE, 'ENHANCING PROMPT', 200)

    def _paint_done(self, p: QPainter):
        # green terminal checkmark
        p.setPen(Qt.NoPen)
        # glow
        glow = QColor(NEON)
        glow.setAlpha(30)
        p.setBrush(glow)
        p.drawEllipse(12, 17, 24, 24)
        # circle
        p.setBrush(QColor(0, 40, 15))
        pen = QPen(NEON)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.drawEllipse(15, 20, 18, 18)

        # checkmark
        pen = QPen(NEON)
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(20, 29, 23, 33)
        p.drawLine(23, 33, 30, 24)

        # text
        p.setPen(NEON)
        p.setFont(QFont(MONO, 10, QFont.Bold))
        p.drawText(42, 34, 'COPIED TO CLIPBOARD')

    def _paint_error(self, p: QPainter):
        # red X
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(40, 0, 5))
        pen = QPen(RED)
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.drawEllipse(15, 20, 18, 18)

        pen = QPen(RED)
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(21, 25, 27, 33)
        p.drawLine(27, 25, 21, 33)

        # text
        p.setPen(RED)
        p.setFont(QFont(MONO, 9))
        p.drawText(42, 34, self._error_text or 'ERROR')
