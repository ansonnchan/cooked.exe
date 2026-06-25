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
        self._video_item: int | None = None
        self._status_item: int | None = None
        self._status_shadow_item: int | None = None
        self._pdf_image: tk.PhotoImage | None = None
        self._pdf_size: tuple[int, int] | None = None
        self._intervention_visible = False
        self._last_distracted = False
        self._last_panel_geometry: tuple[int, int, int, int] | None = None

        self._root.after(1, self._refresh)

    def close(self) -> None:
        self._audio.stop()
        self._camera_service.stop()
        self._root.destroy()

    def _refresh(self) -> None:
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        telemetry = self._camera_service.telemetry()
        distracted = self._is_distracted(telemetry)

        self._draw_video(width, height)
        self._sync_intervention(distracted, width, height)
        self._draw_status(distracted)

        self._root.after(self._interval_ms(), self._refresh)

    def _draw_video(self, width: int, height: int) -> None:
        frame = self._camera_service.current_frame()
        if frame is None or cv2 is None:
            self._draw_placeholder(width, height)
            return

        frame_height, frame_width = frame.shape[:2]
        scale = max(width / frame_width, height / frame_height)
        resized_width = max(1, int(frame_width * scale))
        resized_height = max(1, int(frame_height * scale))
        resized = cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)

        x0 = max(0, (resized_width - width) // 2)
        y0 = max(0, (resized_height - height) // 2)
        cropped = resized[y0 : y0 + height, x0 : x0 + width]
        rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        header = f"P6\n{width} {height}\n255\n".encode("ascii")
        self._video_image = tk.PhotoImage(data=header + rgb.tobytes(), format="PPM")

        if self._video_item is None:
            self._video_item = self._canvas.create_image(
                0,
                0,
                image=self._video_image,
                anchor=tk.NW,
                tags="video",
            )
            self._canvas.tag_lower(self._video_item)
        else:
            self._canvas.itemconfigure(self._video_item, image=self._video_image)

    def _draw_placeholder(self, width: int, height: int) -> None:
        self._canvas.delete("video")
        self._video_item = None
        self._canvas.create_rectangle(0, 0, width, height, fill="#111114", outline="", tags="video")
        self._canvas.create_text(
            width // 2,
            height // 2,
            text="Starting camera...",
            fill="#f4f4f0",
            font=("Arial", 26, "bold"),
            tags="video",
        )
        self._canvas.tag_lower("video")

    def _sync_intervention(self, distracted: bool, width: int, height: int) -> None:
        panel_geometry = self._panel_geometry(width, height)
        geometry_changed = panel_geometry != self._last_panel_geometry

        if distracted != self._last_distracted:
            self._last_distracted = distracted
            if distracted:
                self._audio.play()
            else:
                self._audio.stop()

        if distracted and (not self._intervention_visible or geometry_changed):
            self._draw_panel(panel_geometry)
            self._intervention_visible = True
        elif not distracted and self._intervention_visible:
            self._canvas.delete("panel")
            self._intervention_visible = False

        self._last_panel_geometry = panel_geometry

    def _draw_panel(self, geometry: tuple[int, int, int, int]) -> None:
        x, y, panel_width, panel_height = geometry
        self._canvas.delete("panel")
        self._canvas.create_rectangle(
            x,
            y,
            x + panel_width,
            y + panel_height,
            fill="#f4f1e8",
            outline="#2b2b2b",
            tags="panel",
        )

        self._ensure_pdf_image(panel_width, panel_height)
        if self._pdf_image is not None:
            self._canvas.create_image(x + 10, y + 10, image=self._pdf_image, anchor=tk.NW, tags="panel")
            return

        self._canvas.create_text(
            x + panel_width // 2,
            y + 76,
            text="Employment Form",
            fill="#1f1f1f",
            font=("Arial", 22, "bold"),
            tags="panel",
        )
        self._canvas.create_text(
            x + 24,
            y + 128,
            text=str(self._employment_form_path),
            fill="#444444",
            font=("Arial", 13),
            width=panel_width - 48,
            anchor=tk.NW,
            tags="panel",
        )

    def _ensure_pdf_image(self, panel_width: int, panel_height: int) -> None:
        target_size = (panel_width, panel_height)
        if self._pdf_image is not None and self._pdf_size == target_size:
            return

        self._pdf_image = None
        self._pdf_size = target_size
        if fitz is None or not self._employment_form_path.exists():
            return

        document = fitz.open(self._employment_form_path)
        try:
            page = document[0]
            max_width = max(1, panel_width - 20)
            max_height = max(1, panel_height - 20)
            scale = min(max_width / page.rect.width, max_height / page.rect.height)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            self._pdf_image = tk.PhotoImage(data=base64.b64encode(pixmap.tobytes("png")))
        finally:
            document.close()

    def _draw_status(self, distracted: bool) -> None:
        status = "DISTRACTED" if distracted else "FOCUSED"
        color = "#ff3b30" if distracted else "#34c759"
        x = 22
        y = 20
        font = ("Arial", 24, "bold")

        if self._status_shadow_item is None:
            self._status_shadow_item = self._canvas.create_text(
                x + 2,
                y + 2,
                text=status,
                fill="#111111",
                font=font,
                anchor=tk.NW,
                tags="status",
            )
            self._status_item = self._canvas.create_text(
                x,
                y,
                text=status,
                fill=color,
                font=font,
                anchor=tk.NW,
                tags="status",
            )
        else:
            self._canvas.itemconfigure(self._status_shadow_item, text=status)
            self._canvas.itemconfigure(self._status_item, text=status, fill=color)

        self._canvas.tag_raise("status")

    def _is_distracted(self, telemetry: dict[str, Any]) -> bool:
        return bool(telemetry.get("intervention_active")) or telemetry.get("state") in {
            "distracted",
            "intervening",
        }

    def _panel_geometry(self, width: int, height: int) -> tuple[int, int, int, int]:
        panel_width = max(280, min(430, int(width * 0.32)))
        panel_height = max(320, min(int(height * 0.82), height - 48))
        return 18, max(72, (height - panel_height) // 2), panel_width, panel_height

    def _interval_ms(self) -> int:
        return max(1, int(1000 / max(1, settings.fps)))


def run_desktop_app() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    camera_service = CameraService()
    camera_service.start()

    root = tk.Tk()
    CookedWindow(root, camera_service, base_dir)
    root.mainloop()
    return 0
