from PySide6.QtGui import QColor, QIcon, QPixmap, QImage  # pylint: disable=no-name-in-module

def invertIcon(self, icon: QIcon, size: int = 24) -> QIcon:
    """Return a new QIcon with all non-transparent pixels set to the matplotlib 'C0' blue."""
    pix = icon.pixmap(size, size)
    img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    # Matplotlib "C0" hex color
    blue = QColor('#1f77b4')
    for y in range(img.height()):
        for x in range(img.width()):
            col = img.pixelColor(x, y)
            if col.alpha() == 0:
                continue  # keep fully transparent pixels transparent
            # preserve alpha, replace RGB with C0 blue
            newcol = QColor(blue.red(), blue.green(), blue.blue(), col.alpha())
            img.setPixelColor(x, y, newcol)
    return QIcon(QPixmap.fromImage(img))

