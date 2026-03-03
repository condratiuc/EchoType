"""Generate icon.ico for the application."""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QImage
from PyQt5.QtCore import Qt

app = QApplication(sys.argv)

sizes = [16, 32, 48, 64, 128, 256]
images = []

for size in sizes:
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)

    scale = size / 64.0
    pen = QPen(QColor('#60a5fa'))
    pen.setWidthF(3 * scale)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    # mic body
    p.drawRoundedRect(
        int(22 * scale), int(8 * scale),
        int(20 * scale), int(28 * scale),
        int(10 * scale), int(10 * scale),
    )
    # arc
    p.drawArc(
        int(14 * scale), int(18 * scale),
        int(36 * scale), int(28 * scale),
        0, -180 * 16,
    )
    # stand
    cx = int(32 * scale)
    p.drawLine(cx, int(46 * scale), cx, int(54 * scale))
    p.drawLine(int(22 * scale), int(54 * scale), int(42 * scale), int(54 * scale))

    p.end()
    images.append(px.toImage())

# Save the largest as .ico (Qt on Windows supports ICO write for single image)
# For a proper multi-size ICO, save the 256px version
images[-1].save('icon.ico', 'ICO')
# Also save PNG for reference
images[-1].save('icon.png', 'PNG')

print('Generated icon.ico and icon.png')
sys.exit(0)
