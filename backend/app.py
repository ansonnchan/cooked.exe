from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .camera import CameraService
from .config import get_settings, settings, update_settings
from .websocket_manager import WebSocketManager

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

camera_service = CameraService()
websockets = WebSocketManager()


class SettingsPatch(BaseModel):
    attention_threshold: int | None = Field(default=None, ge=1, le=99)
    intervention_delay_seconds: float | None = Field(default=None, ge=1.0, le=30.0)
    sound_enabled: bool | None = None
    ema_alpha: float | None = Field(default=None, ge=0.05, le=1.0)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    camera_service.start()
    telemetry_task = asyncio.create_task(_broadcast_telemetry())
    try:
        yield
    finally:
        telemetry_task.cancel()
        try:
            await telemetry_task
        except asyncio.CancelledError:
            pass
        camera_service.stop()


app = FastAPI(title="cooked.exe", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/video_feed")
async def video_feed() -> StreamingResponse:
    return StreamingResponse(
        camera_service.frame_stream(),
        media_type=f"multipart/x-mixed-replace; boundary={settings.frame_boundary}",
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websockets.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await websockets.disconnect(websocket)


@app.get("/api/settings")
async def read_settings() -> dict[str, Any]:
    return get_settings()


@app.patch("/api/settings")
async def patch_settings(patch: SettingsPatch) -> dict[str, Any]:
    return update_settings(**patch.model_dump(exclude_unset=True))


@app.post("/api/intervention/dismiss")
async def dismiss_intervention() -> dict[str, Any]:
    return camera_service.dismiss_intervention()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _broadcast_telemetry() -> None:
    while True:
        await websockets.broadcast(camera_service.telemetry())
        await asyncio.sleep(1.0 / max(1, settings.websocket_hz))
