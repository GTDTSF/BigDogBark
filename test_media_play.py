from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import QApplication
import sys
import os

app = QApplication(sys.argv)
player = QMediaPlayer()
audio_output = QAudioOutput()
player.setAudioOutput(audio_output)
player.setSource(QUrl.fromLocalFile(os.path.abspath("dog.mp4")))
player.play()

def on_status_changed(status):
    print("Status:", status)

player.mediaStatusChanged.connect(on_status_changed)

QTimer.singleShot(2000, app.quit)
app.exec()
