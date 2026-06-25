from __future__ import annotations

import platform
import subprocess
import threading
from pathlib import Path


class LoopingAudioPlayer:
    def __init__(self, sound_path: Path) -> None:
        self._sound_path = sound_path
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None

    def play(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        if not self._sound_path.exists():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, name="audio-loop", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
        self._process = None

    def _loop(self) -> None:
        if platform.system() != "Darwin":
            return

        while not self._stop_event.is_set():
            self._process = subprocess.Popen(
                ["afplay", str(self._sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process.wait()
            self._process = None
