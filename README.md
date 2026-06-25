# cooked.exe 🍚

A desktop attention detector that uses your webcam to notice when you stop paying attention.

**Inspired by r/csMajors.**

According to extensive, peer-unreviewed research, this app exists to prevent **Anson Chan's Law of Unemployment**:

_P(unemployed)_ = min(0.01%, ((Age - 18) × π × DoomscrollMultiplier × CSMajorFactor) ÷ (1 + GrassTouchedThisWeek))

Where:

* `π` = vibes constant
* `DoomscrollMultiplier` = minutes lost to scrolling (we take the limit as it approaches ∞)
* `CSMajorFactor` = 1.8 (changes every week depending on the r/csMajors subreddit weekly doom and gloom level)
* `GrassTouchedThisWeek` = estimated to be 0


Everything runs locally on your machine. There is no cloud service, database, browser UI, account system, or external API.

## Features

- Native Desktop App: Opens its own desktop window with `python app.py`
- Live Webcam Feed: Uses the entire main window as the camera preview
- Attention Metrics Overlay: Displays attention score, current status, head yaw, head pitch, and face detection state
- MediaPipe Face Tracking: Uses Face Mesh landmarks to estimate face presence and head movement
- Attention Scoring: Combines face visibility, head yaw, head pitch, and mouth openness into a smoothed attention score
- Immediate Intervention: Triggers as soon as the attention engine marks the user as distracted
- Employment Form Overlay: Job employment form pops up while user is distracted
- Looping Audio: Plays the McDonald's beeping sound while user is distracted 


## Requirements

- Python 3.8+
- Webcam access
- macOS, Windows, or Linux desktop environment capable of running Qt

## Dependencies

Core dependencies:

```text
opencv-python==4.11.0.86
mediapipe==0.10.21
numpy>=1.26.4,<2
PySide6>=6.7.0
```

These are installed from `requirements.txt`.

## Installation

Clone the repository:

```bash
git clone https://github.com/ansonnchan/cooked.exe
cd cooked.exe
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the desktop app:

```bash
python app.py
```

The app will open a native desktop window. The webcam feed fills the window, and live metrics appear in the top corner.

## App Flow

1. Start the app with `python app.py`.
2. Grant camera permission if your operating system asks for it.
3. Stay focused and visible to the webcam.
4. If your attention score drops into the distracted state, the employment form slides in from the left.
5. While distracted, the McDonald's sound loops.
6. When you return to focused, the employment form hides and the sound stops.

## Configuration

Runtime defaults live in `config.py`.

Common settings:

```text
camera_index                  Webcam device index
fps                           Camera processing rate
jpeg_quality                  Preview encoding quality
ema_alpha                     Attention-score smoothing factor
attention_threshold           Score below which distraction begins
recovery_threshold            Score required to recover from intervention
intervention_delay_seconds    Delay before intervention, currently 0.0
head_yaw_threshold            Side-to-side head angle threshold
head_pitch_threshold          Downward head angle threshold
mouth_open_threshold          Mouth openness threshold
sound_enabled                 Enables local alert sound
mirror_preview                Mirrors the camera preview
```

## Project Structure

```text
cooked.exe/
  app.py
  config.py
  requirements.txt
  src/
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

## Troubleshooting

- No Camera Feed: Check webcam permissions and make sure another app is not using the camera.
- Wrong Camera Opens: Change `camera_index` in `config.py`.
- Face Not Detected: Improve lighting and keep your face in frame.
- Audio Does Not Play: Check system output volume and confirm the MP3 exists at `assets/sounds/mcdonalds-beeping-sound.mp3`.
- PDF Does Not Show: Confirm the employment form exists at `assets/images/employment-form.pdf`.
- App Does Not Launch: Reinstall dependencies with `pip install -r requirements.txt`.


