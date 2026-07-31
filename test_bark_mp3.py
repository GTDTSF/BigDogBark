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

mp3_path = os.path.abspath("叫.mp3")
player.setSource(QUrl.fromLocalFile(mp3_path))

rate_changed = False

def on_pos_changed(pos):
    global rate_changed
    if pos > 200 and not rate_changed:
        rate_changed = True
        print("Changing rate at pos", pos)
        player.setPlaybackRate(0.2)

player.positionChanged.connect(on_pos_changed)
player.play()

QTimer.singleShot(4000, app.quit)
app.exec()