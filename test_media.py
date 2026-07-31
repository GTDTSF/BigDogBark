from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
player = QMediaPlayer()
audio_output = QAudioOutput()
player.setAudioOutput(audio_output)
print("QMediaPlayer available")
