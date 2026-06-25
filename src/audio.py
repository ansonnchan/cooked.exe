from __future__ import annotations

import platform
import subprocess
import threading
from pathlib import Path


class LoopingAudioPlayer:
    def __init__(self, sound_path: Path) -> None:
        self._sound_path = sound_path
        self._lock = threading.RLock()
        self._playing = False
        self._monitor_thread: threading.Thread | None = None
        self._process: subprocess.Popen | None = None

    def play(self) -> None:
        with self._lock:
            if self._playing or not self._sound_path.exists() or platform.system() != "Darwin":
                return

            self._playing = True
            self._start_process()
            self._monitor_thread = threading.Thread(
                target=self._monitor,
                name="audio-loop",
                daemon=True,
            )
            self._monitor_thread.start()

    def stop(self) -> None:
        with self._lock:
            self._playing = False
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()
            self._process = None

    def _monitor(self) -> None:
        while True:
            with self._lock:
                process = self._process
                playing = self._playing
            if not playing or process is None:
                return

            process.wait()

            with self._lock:
                if not self._playing:
                    self._process = None
                    return
                self._start_process()

    def _start_process(self) -> None:
        self._process = subprocess.Popen(
            ["afplay", str(self._sound_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
