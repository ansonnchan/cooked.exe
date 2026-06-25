const els = {
  connectionLabel: document.querySelector("#connectionLabel"),
  connectionDot: document.querySelector("#connectionDot"),
  stateBadge: document.querySelector("#stateBadge"),
  scoreMeter: document.querySelector("#scoreMeter"),
  attentionScore: document.querySelector("#attentionScore"),
  reasonLine: document.querySelector("#reasonLine"),
  distractionTimer: document.querySelector("#distractionTimer"),
  yawValue: document.querySelector("#yawValue"),
  pitchValue: document.querySelector("#pitchValue"),
  mouthValue: document.querySelector("#mouthValue"),
  faceValue: document.querySelector("#faceValue"),
  cameraError: document.querySelector("#cameraError"),
  thresholdSlider: document.querySelector("#thresholdSlider"),
  thresholdOutput: document.querySelector("#thresholdOutput"),
  delaySlider: document.querySelector("#delaySlider"),
  delayOutput: document.querySelector("#delayOutput"),
  soundToggle: document.querySelector("#soundToggle"),
  overlay: document.querySelector("#interventionOverlay"),
  interventionTitle: document.querySelector("#interventionTitle"),
  interventionBody: document.querySelector("#interventionBody"),
  dismissIntervention: document.querySelector("#dismissIntervention"),
};

let socket = null;
let settings = {
  attention_threshold: 50,
  intervention_delay_seconds: 5,
  sound_enabled: true,
};
let activeInterventionId = null;
let settingsPatchTimer = null;
let pendingSettingsPatch = {};

const stateLabels = {
  starting: "Starting",
  camera_unavailable: "Camera Unavailable",
  focused: "Focused",
  face_missing: "Face Missing",
  possibly_distracted: "Possibly Distracted",
  distracted: "Distracted",
  intervening: "Intervening",
};

async function loadSettings() {
  const response = await fetch("/api/settings");
  settings = await response.json();
  syncSettingsControls();
}

function syncSettingsControls() {
  els.thresholdSlider.value = settings.attention_threshold;
  els.thresholdOutput.value = settings.attention_threshold;
  els.delaySlider.value = settings.intervention_delay_seconds;
  els.delayOutput.value = `${Number(settings.intervention_delay_seconds).toFixed(1)}s`;
  els.soundToggle.checked = settings.sound_enabled;
}

function patchSettings(changes) {
  settings = { ...settings, ...changes };
  pendingSettingsPatch = { ...pendingSettingsPatch, ...changes };
  syncSettingsControls();
  clearTimeout(settingsPatchTimer);
  settingsPatchTimer = setTimeout(async () => {
    const payload = { ...pendingSettingsPatch };
    pendingSettingsPatch = {};
    const response = await fetch("/api/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    settings = await response.json();
    syncSettingsControls();
  }, 160);
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

  socket.addEventListener("open", () => {
    els.connectionLabel.textContent = "Live";
    els.connectionDot.className = "dot live";
  });

  socket.addEventListener("message", (event) => {
    updateTelemetry(JSON.parse(event.data));
  });

  socket.addEventListener("close", () => {
    els.connectionLabel.textContent = "Reconnecting";
    els.connectionDot.className = "dot offline";
    setTimeout(connectWebSocket, 800);
  });
}

function updateTelemetry(data) {
  const score = clamp(Number(data.attention_score || 0), 0, 100);
  els.scoreMeter.style.setProperty("--score", score);
  els.attentionScore.textContent = score;
  els.stateBadge.textContent = stateLabels[data.state] || data.state || "Unknown";
  els.distractionTimer.textContent = `${Number(data.distraction_seconds || 0).toFixed(1)}s`;
  els.yawValue.textContent = Number(data.head_yaw || 0).toFixed(1);
  els.pitchValue.textContent = Number(data.head_pitch || 0).toFixed(1);
  els.mouthValue.textContent = data.mouth_open ? "Open" : "Closed";
  els.faceValue.textContent = data.face_detected ? "Yes" : "No";
  els.reasonLine.textContent = data.reasons?.length ? data.reasons.join(", ") : "No active penalties";

  if (data.camera_error) {
    els.cameraError.hidden = false;
    els.cameraError.textContent = data.camera_error;
  } else {
    els.cameraError.hidden = true;
    els.cameraError.textContent = "";
  }

  updateScoreColor(score);
  updateOverlay(data);
}

function updateScoreColor(score) {
  let color = "var(--green)";
  if (score < settings.attention_threshold) {
    color = "var(--red)";
  } else if (score < settings.attention_threshold + 18) {
    color = "var(--amber)";
  }
  els.scoreMeter.style.background = `radial-gradient(circle at center, var(--panel) 58%, transparent 60%), conic-gradient(${color} ${score}%, #3a3435 0)`;
}

function updateOverlay(data) {
  if (!data.intervention_active || !data.intervention) {
    els.overlay.hidden = true;
    activeInterventionId = null;
    return;
  }

  els.overlay.hidden = false;
  els.interventionTitle.textContent = data.intervention.title;
  els.interventionBody.textContent = data.intervention.body;
  els.dismissIntervention.textContent = data.intervention.action_label || "Apply Now";

  if (
    settings.sound_enabled &&
    data.intervention.sound_enabled &&
    activeInterventionId !== data.intervention.id
  ) {
    try {
      window.cookedOverlayAudio.play();
    } catch (_error) {
      // Some browsers require a user gesture before audio can start.
    }
  }
  activeInterventionId = data.intervention.id;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

els.thresholdSlider.addEventListener("input", (event) => {
  patchSettings({ attention_threshold: Number(event.target.value) });
});

els.delaySlider.addEventListener("input", (event) => {
  patchSettings({ intervention_delay_seconds: Number(event.target.value) });
});

els.soundToggle.addEventListener("change", (event) => {
  patchSettings({ sound_enabled: event.target.checked });
});

els.dismissIntervention.addEventListener("click", async () => {
  await fetch("/api/intervention/dismiss", { method: "POST" });
  els.overlay.hidden = true;
});

loadSettings()
  .catch(() => {
    els.connectionLabel.textContent = "Settings unavailable";
  })
  .finally(connectWebSocket);
