from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import QApplication
import sys
import os

app = QApplication(sys.argv)
player = QMediaPlayer()
audio_output = QAudioOutput()
player.setAudioOutput(audio_output)
player.audio_output_ref = audio_output

mp3_path = os.path.abspath("大狗.mp3")
print("Trying to play:", mp3_path)
if not os.path.exists(mp3_path):
    print("File does not exist!")
else:
    player.setSource(QUrl.fromLocalFile(mp3_path))
    player.play()

    def on_status_changed(status):
        print("Status:", status)

    player.mediaStatusChanged.connect(on_status_changed)

QTimer.singleShot(3000, app.quit)
app.exec()