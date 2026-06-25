from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class LoopingAudioPlayer:
    def __init__(self, sound_path: Path, volume: float = 0.65) -> None:
        self._sound_path = sound_path
        self._audio_output = QAudioOutput()
        self._audio_output.setVolume(volume)

        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio_output)
        self._player.setSource(QUrl.fromLocalFile(str(sound_path)))
        self._player.setLoops(QMediaPlayer.Loops.Infinite)

    def play(self) -> None:
        if not self._sound_path.exists():
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return
        self._player.play()

    def stop(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            return
        self._player.stop()
