""" Misc. functions that do not require an instance """
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from PySide6.QtGui import QColor, QIcon, QPixmap, QImage  # pylint: disable=no-name-in-module

ACCENT_COLOR = '#b4421f'

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
    def __init__(self, samplerate:int=16000, channels:int=1):
        self.samplerate = samplerate
        self.channels = channels
        self.frames:list[np.ndarray] = []
        self.stream:sd.InputStream | None = None


    def start(self) -> None:
        """ Start recording """
        self.frames = []
        self.stream = sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback)
        self.stream.start()


    def stop(self) -> str:
        """ Stop recording
        Returns:
            str: The path to the saved audio file.
        """
        if self.stream is None:
            return ''
        self.stream.stop()
        self.stream.close()
        audio = np.concatenate(self.frames, axis=0)
        _, path = tempfile.mkstemp(suffix='.wav')
        sf.write(path, audio, self.samplerate)
        return path


    def _callback(self, indata:np.ndarray, _frames:int, _timeInfo:float, _status:int) -> None:
        """ This is called (from a separate thread) for each audio block.
        Args:
            indata (numpy.ndarray): The audio data.
            _frames (int): The number of frames.
            _timeInfo (float): The time.
            _status (int): The status.
        """
        self.frames.append(indata.copy())


helpText = """
# WALLO — Writing Assistance by Large Language Model

- Document structure: A document is a sequence of exchanges. Each exchange contains a task history and the LLM's reply.
- User workflow: Users enter or edit the task history, request the LLM to perform a task, and receive an editable reply. Both the task history and the
  LLM reply can always be modified. While the LLM is running, users may edit other exchanges.
- Tools and shortcuts:
  - Nine tools are arranged in a numeric-pad layout to support the user:
    - First row: task-history tools
    - Second row: LLM tools
    - Third row: miscellaneous tools
  - A drop-down menu provides access to all LLM prompts.
  - Keyboard shortcuts: Ctrl+1 … Ctrl+9 trigger LLM prompts; Alt+1 … Alt+9
    activate the corresponding tools.
"""