from __future__ import annotations

from dataclasses import asdict, dataclass
from threading import RLock
from typing import Any


@dataclass
class Settings:
    camera_index: int = 0
    camera_width: int = 1280
    camera_height: int = 720
    fps: int = 20
    jpeg_quality: int = 82
    ema_alpha: float = 0.3
    attention_threshold: int = 50
    recovery_threshold: int = 62
    intervention_delay_seconds: float = 0.0
    head_yaw_threshold: float = 22.0
    head_pitch_threshold: float = 18.0
    mouth_open_threshold: float = 0.32
    sound_enabled: bool = True
    yaw_penalty: int = 35
    pitch_penalty: int = 20
    face_missing_penalty: int = 55
    mouth_open_penalty: int = 15
    max_faces: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    mirror_preview: bool = True
    frame_boundary: str = "frame"


settings = Settings()
_settings_lock = RLock()


def get_settings() -> dict[str, Any]:
    with _settings_lock:
        return asdict(settings)


def update_settings(**changes: Any) -> dict[str, Any]:
    with _settings_lock:
        for key, value in changes.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)
        return asdict(settings)
