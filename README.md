# cooked.exe

Real-time local computer vision distraction detector. The app watches a webcam feed locally, estimates attention with MediaPipe facial landmarks and OpenCV heuristics, and triggers unserious workplace interventions when distraction persists.

## Features

- FastAPI backend with WebSocket telemetry
- OpenCV webcam capture and MJPEG preview
- MediaPipe Face Mesh landmark tracking
- Heuristic head yaw, head pitch, face visibility, and mouth openness signals
- EMA-smoothed attention score
- Finite state machine for sustained distraction detection
- Browser dashboard with threshold, delay, and sound controls
- Local-only operation with no database, accounts, cloud APIs, or image upload

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

## Project Structure

```text
cooked.exe/
  app.py
  config.py
  requirements.txt
  backend/
    app.py
    camera.py
    mediapipe_tracker.py
    feature_extractor.py
    attention_engine.py
    state_machine.py
    intervention.py
    websocket_manager.py
    config.py
  frontend/
    index.html
    styles.css
    script.js
    overlay.js
  assets/
    images/
    sounds/
```

## Configuration

Runtime defaults live in `config.py`. The dashboard can update intervention delay, sound, and attention threshold while the app is running.
