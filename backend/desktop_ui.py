from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from .audio import LoopingAudioPlayer
from .camera import CameraService
from .config import settings


class CookedWindow(QMainWindow):
    def __init__(self, camera_service: CameraService, base_dir: Path) -> None:
        super().__init__()
        self._camera_service = camera_service
        self._employment_form_path = base_dir / "assets" / "images" / "employment-form.pdf"
        self._sound_path = base_dir / "assets" / "sounds" / "mcdonalds-beeping-sound.mp3"
        self._intervention_visible = False
        self._last_pixmap: QPixmap | None = None

        self.setWindowTitle("cooked.exe")
        self.resize(1280, 720)
        self.setMinimumSize(860, 520)

        self._root = QWidget(self)
        self._root.setStyleSheet("background: #050505;")
        self.setCentralWidget(self._root)

        self._video_label = QLabel(self._root)
        self._video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_label.setStyleSheet("background: #050505;")
        self._video_label.setScaledContents(False)

        self._metrics_label = QLabel(self._root)
        self._metrics_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._metrics_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._metrics_label.setStyleSheet(
            """
            QLabel {
                background: rgba(0, 0, 0, 155);
                color: #f7f7f2;
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 8px;
                font: 600 14px "Arial";
                padding: 10px 12px;
            }
            """
        )

        self._pdf_panel = QWidget(self._root)
        self._pdf_panel.setStyleSheet(
            """
            QWidget {
                background: rgba(246, 246, 239, 245);
                border-right: 1px solid rgba(0, 0, 0, 80);
            }
            """
        )
        self._pdf_panel.hide()

        self._pdf_view = QPdfView(self._pdf_panel)
        self._pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self._pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._pdf_document = QPdfDocument(self)
        self._pdf_document.load(str(self._employment_form_path))
        self._pdf_view.setDocument(self._pdf_document)

        panel_layout = QVBoxLayout(self._pdf_panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.addWidget(self._pdf_view)

        self._audio = LoopingAudioPlayer(self._sound_path)

        self._animation = QPropertyAnimation(self._pdf_panel, b"geometry", self)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(max(1, int(1000 / max(1, settings.fps))))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_children()
        self._render_video()

    def closeEvent(self, event) -> None:
        self._audio.stop()
        self._camera_service.stop()
        super().closeEvent(event)

    def _refresh(self) -> None:
        image_data = self._camera_service.current_jpeg()
        if image_data:
            image = QImage.fromData(image_data, "JPG")
            if not image.isNull():
                self._last_pixmap = QPixmap.fromImage(image)
                self._render_video()

        telemetry = self._camera_service.telemetry()
        self._metrics_label.setText(self._metrics_text(telemetry))
        self._metrics_label.adjustSize()
        self._position_metrics()
        self._sync_intervention(telemetry)

    def _render_video(self) -> None:
        if self._last_pixmap is None:
            return

        scaled = self._last_pixmap.scaled(
            self._video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._video_label.setPixmap(scaled)

    def _layout_children(self) -> None:
        self._video_label.setGeometry(self._root.rect())
        self._position_metrics()

        panel_width = self._panel_width()
        target_x = 0 if self._intervention_visible else -panel_width
        self._pdf_panel.setGeometry(target_x, 0, panel_width, self._root.height())
        self._pdf_panel.raise_()
        self._metrics_label.raise_()

    def _position_metrics(self) -> None:
        margin = 16
        x = self._root.width() - self._metrics_label.width() - margin
        self._metrics_label.move(max(margin, x), margin)

    def _sync_intervention(self, telemetry: dict[str, Any]) -> None:
        distracted = telemetry.get("intervention_active") or telemetry.get("state") in {
            "distracted",
            "intervening",
        }
        if distracted and not self._intervention_visible:
            self._show_intervention()
        elif not distracted and self._intervention_visible:
            self._hide_intervention()

        if distracted:
            self._audio.play()
        else:
            self._audio.stop()

    def _show_intervention(self) -> None:
        self._intervention_visible = True
        panel_width = self._panel_width()
        self._pdf_panel.show()
        self._animate_panel(
            QRect(-panel_width, 0, panel_width, self._root.height()),
            QRect(0, 0, panel_width, self._root.height()),
        )

    def _hide_intervention(self) -> None:
        self._intervention_visible = False
        panel_width = self._panel_width()
        self._animate_panel(
            QRect(0, 0, panel_width, self._root.height()),
            QRect(-panel_width, 0, panel_width, self._root.height()),
            hide_when_done=True,
        )

    def _animate_panel(self, start: QRect, end: QRect, hide_when_done: bool = False) -> None:
        try:
            self._animation.finished.disconnect()
        except RuntimeError:
            pass

        if hide_when_done:
            self._animation.finished.connect(self._pdf_panel.hide)

        self._pdf_panel.raise_()
        self._metrics_label.raise_()
        self._animation.stop()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def _panel_width(self) -> int:
        return max(340, min(560, int(self._root.width() * 0.42)))

    def _metrics_text(self, telemetry: dict[str, Any]) -> str:
        face_status = "Detected" if telemetry.get("face_detected") else "Missing"
        return "\n".join(
            [
                f"Attention Score: {telemetry.get('attention_score', 0)}",
                f"Current Status: {telemetry.get('state', 'unknown')}",
                f"Head Yaw: {telemetry.get('head_yaw', 0.0)}",
                f"Head Pitch: {telemetry.get('head_pitch', 0.0)}",
                f"Face: {face_status}",
            ]
        )


def run_desktop_app() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    camera_service = CameraService()
    camera_service.start()

    app = QApplication.instance() or QApplication([])
    window = CookedWindow(camera_service, base_dir)
    window.show()
    return app.exec()
