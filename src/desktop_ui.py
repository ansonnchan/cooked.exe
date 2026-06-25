from __future__ import annotations

import base64
import tkinter as tk
from pathlib import Path
from typing import Any

from .audio import LoopingAudioPlayer
from .camera import CameraService
from .config import settings

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import fitz
except ImportError:
    fitz = None


class CookedWindow:
    def __init__(self, root: tk.Tk, camera_service: CameraService, base_dir: Path) -> None:
        self._root = root
        self._camera_service = camera_service
        self._employment_form_path = base_dir / "assets" / "images" / "employment-form.pdf"
        self._sound_path = base_dir / "assets" / "sounds" / "mcdonalds-beeping-sound.mp3"
        self._audio = LoopingAudioPlayer(self._sound_path)

        self._root.title("cooked.exe")
        self._root.geometry("1280x720")
        self._root.minsize(860, 520)
        self._root.configure(background="#050505")
        self._root.protocol("WM_DELETE_WINDOW", self.close)

        self._canvas = tk.Canvas(self._root, background="#050505", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._video_image: tk.PhotoImage | None = None
        self._pdf_image: tk.PhotoImage | None = None
        self._last_pdf_width = 0
        self._panel_x = 0
        self._panel_target_x = 0
        self._intervention_visible = False

        self._root.after(self._interval_ms(), self._refresh)

    def close(self) -> None:
        self._audio.stop()
        self._camera_service.stop()
        self._root.destroy()

    def _refresh(self) -> None:
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        telemetry = self._camera_service.telemetry()

        self._draw_video(width, height)
        self._sync_intervention(telemetry, width)
        self._animate_panel(width)
        self._draw_metrics(telemetry, width)

        self._root.after(self._interval_ms(), self._refresh)

    def _draw_video(self, width: int, height: int) -> None:
        self._canvas.delete("video")
        image_data = self._camera_service.current_jpeg()
        if image_data is None or cv2 is None:
            self._draw_placeholder(width, height)
            return

        frame = cv2.imdecode(self._bytes_to_array(image_data), cv2.IMREAD_COLOR)
        if frame is None:
            self._draw_placeholder(width, height)
            return

        frame_height, frame_width = frame.shape[:2]
        scale = max(width / frame_width, height / frame_height)
        resized_width = max(1, int(frame_width * scale))
        resized_height = max(1, int(frame_height * scale))
        resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)

        x0 = max(0, (resized_width - width) // 2)
        y0 = max(0, (resized_height - height) // 2)
        cropped = resized[y0 : y0 + height, x0 : x0 + width]
        ok, encoded = cv2.imencode(".png", cropped)
        if not ok:
            self._draw_placeholder(width, height)
            return

        self._video_image = tk.PhotoImage(data=base64.b64encode(encoded.tobytes()))
        self._canvas.create_image(0, 0, image=self._video_image, anchor=tk.NW, tags="video")
        self._canvas.tag_lower("video")

    def _draw_placeholder(self, width: int, height: int) -> None:
        self._canvas.create_rectangle(0, 0, width, height, fill="#111114", outline="", tags="video")
        self._canvas.create_text(
            width // 2,
            height // 2,
            text="Starting camera...",
            fill="#f4f4f0",
            font=("Arial", 26, "bold"),
            tags="video",
        )

    def _sync_intervention(self, telemetry: dict[str, Any], width: int) -> None:
        distracted = telemetry.get("intervention_active") or telemetry.get("state") in {
            "distracted",
            "intervening",
        }
        panel_width = self._panel_width(width)
        self._panel_target_x = 0 if distracted else -panel_width

        if distracted and not self._intervention_visible:
            self._intervention_visible = True
        elif not distracted and self._intervention_visible:
            self._intervention_visible = False

        if distracted:
            self._audio.play()
        else:
            self._audio.stop()

    def _animate_panel(self, width: int) -> None:
        panel_width = self._panel_width(width)
        if self._panel_x == 0 and not self._intervention_visible:
            self._panel_x = -panel_width

        step = max(18, panel_width // 8)
        if self._panel_x < self._panel_target_x:
            self._panel_x = min(self._panel_target_x, self._panel_x + step)
        elif self._panel_x > self._panel_target_x:
            self._panel_x = max(self._panel_target_x, self._panel_x - step)

        self._draw_panel(panel_width)

    def _draw_panel(self, panel_width: int) -> None:
        self._canvas.delete("panel")
        if self._panel_x <= -panel_width:
            return

        height = max(1, self._canvas.winfo_height())
        x = self._panel_x
        self._canvas.create_rectangle(
            x,
            0,
            x + panel_width,
            height,
            fill="#f4f1e8",
            outline="#2b2b2b",
            tags="panel",
        )

        self._ensure_pdf_image(panel_width, height)
        if self._pdf_image is not None:
            self._canvas.create_image(x + 12, 12, image=self._pdf_image, anchor=tk.NW, tags="panel")
        else:
            self._canvas.create_text(
                x + panel_width // 2,
                92,
                text="Employment Form",
                fill="#1f1f1f",
                font=("Arial", 24, "bold"),
                tags="panel",
            )
            self._canvas.create_text(
                x + 24,
                150,
                text=str(self._employment_form_path),
                fill="#444444",
                font=("Arial", 13),
                width=panel_width - 48,
                anchor=tk.NW,
                tags="panel",
            )

    def _ensure_pdf_image(self, panel_width: int, height: int) -> None:
        if self._pdf_image is not None and self._last_pdf_width == panel_width:
            return
        self._last_pdf_width = panel_width
        self._pdf_image = None

        if fitz is None or not self._employment_form_path.exists():
            return

        document = fitz.open(self._employment_form_path)
        try:
            page = document[0]
            available_width = max(1, panel_width - 24)
            scale = available_width / page.rect.width
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            png_bytes = pixmap.tobytes("png")
            self._pdf_image = tk.PhotoImage(data=base64.b64encode(png_bytes))
        finally:
            document.close()

    def _draw_metrics(self, telemetry: dict[str, Any], width: int) -> None:
        self._canvas.delete("metrics")
        face_status = "Detected" if telemetry.get("face_detected") else "Missing"
        lines = [
            f"Attention Score: {telemetry.get('attention_score', 0)}",
            f"Current Status: {telemetry.get('state', 'unknown')}",
            f"Head Yaw: {telemetry.get('head_yaw', 0.0)}",
            f"Head Pitch: {telemetry.get('head_pitch', 0.0)}",
            f"Face: {face_status}",
        ]
        text = "\n".join(lines)
        box_width = 250
        x = max(16, width - box_width - 16)
        y = 16
        self._canvas.create_rectangle(
            x,
            y,
            x + box_width,
            y + 112,
            fill="#000000",
            stipple="gray50",
            outline="#777777",
            tags="metrics",
        )
        self._canvas.create_text(
            x + 12,
            y + 10,
            text=text,
            fill="#f7f7f2",
            font=("Arial", 14, "bold"),
            anchor=tk.NW,
            tags="metrics",
        )

    def _panel_width(self, width: int) -> int:
        return max(340, min(560, int(width * 0.42)))

    def _interval_ms(self) -> int:
        return max(1, int(1000 / max(1, settings.fps)))

    def _bytes_to_array(self, data: bytes):
        import numpy as np

        return np.frombuffer(data, dtype=np.uint8)


def run_desktop_app() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    camera_service = CameraService()
    camera_service.start()

    root = tk.Tk()
    CookedWindow(root, camera_service, base_dir)
    root.mainloop()
    return 0
