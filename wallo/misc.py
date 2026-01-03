""" Misc. functions that do not require an instance """
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
from PySide6.QtGui import QColor, QIcon, QPixmap, QImage  # pylint: disable=no-name-in-module

ACCENT_COLOR = "#b4421f"

def invertIcon(icon: QIcon, size: int = 24) -> QIcon:
    """Return a new QIcon with all non-transparent pixels set to the matplotlib 'C0' blue.
    Args:
        icon (QIcon): The icon to be inverted.
        size (int): The size of the icon.
    Returns:
        QIcon: The inverted icon.
    """
    pix = icon.pixmap(size, size)
    img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    blue = QColor(ACCENT_COLOR)
    for y in range(img.height()):
        for x in range(img.width()):
            col = img.pixelColor(x, y)
            if col.alpha() == 0:
                continue  # keep fully transparent pixels transparent
            # preserve alpha, replace RGB with C0 blue
            newcol = QColor(blue.red(), blue.green(), blue.blue(), col.alpha())
            img.setPixelColor(x, y, newcol)
    return QIcon(QPixmap.fromImage(img))


class PushToTalkRecorder:
    """ Push to talk recorder, saving temporary data in temp-folder"""
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.frames = []
        self.stream = None

    def start(self):
        """ Start recording """
        self.frames = []
        self.stream = sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback)
        self.stream.start()

    def stop(self):
        """ Stop recording """
        self.stream.stop()
        self.stream.close()
        audio = np.concatenate(self.frames, axis=0)
        fd, path = tempfile.mkstemp(suffix='.wav')
        sf.write(path, audio, self.samplerate)
        return path

    def _callback(self, indata, frames, time, status):
        """ This is called (from a separate thread) for each audio block.
        Args:
            indata (numpy.ndarray): The audio data.
            frames (int): The number of frames.
            time (float): The time.
            status (int): The status.
        """
        self.frames.append(indata.copy())