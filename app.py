from __future__ import annotations

import os
import sys

os.environ.setdefault("LANG", "en_US.UTF-8")
os.environ.setdefault("LC_ALL", "en_US.UTF-8")

from src.desktop_ui import run_desktop_app


if __name__ == "__main__":
    sys.exit(run_desktop_app())
