from __future__ import annotations

import threading
import webbrowser

import uvicorn

from config import settings


def open_browser() -> None:
    webbrowser.open(f"http://{settings.host}:{settings.port}")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
