# cooked.exe

Local native desktop distraction detector. The app opens a PySide6/Qt window, fills it with the live webcam feed, estimates attention locally with MediaPipe facial landmarks and OpenCV heuristics, and slides in an employment form when the user becomes distracted.

## Features

- Native desktop window launched with `python app.py`
- Full-window webcam feed with live attention metrics overlay
- OpenCV webcam capture on a background thread
- MediaPipe Face Mesh landmark tracking
- Heuristic head yaw, head pitch, face visibility, and mouth openness signals
- EMA-smoothed attention score
- Immediate distracted-state intervention
- Sliding left-side PDF employment form overlay
- Looping local McDonald's sound while distracted
- Local-only operation with no browser UI, server, database, cloud APIs, or image upload

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows, activate the virtual environment with:

```bash
.venv\Scripts\activate
```

## Project Structure

```text
cooked.exe/
  app.py
  config.py
  requirements.txt
  backend/
    audio.py
    camera.py
    desktop_ui.py
    mediapipe_tracker.py
    feature_extractor.py
    attention_engine.py
    state_machine.py
    intervention.py
    config.py
  assets/
    images/
      employment-form.pdf
    sounds/
      mcdonalds-beeping-sound.mp3
```

## Configuration

Runtime defaults live in `config.py`.
