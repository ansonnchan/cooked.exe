function createWarningSound() {
  let audioContext = null;
  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;

  function tone(frequency, start, duration, gainValue) {
    const oscillator = audioContext.createOscillator();
    const gain = audioContext.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0, audioContext.currentTime + start);
    gain.gain.linearRampToValueAtTime(gainValue, audioContext.currentTime + start + 0.01);
    gain.gain.linearRampToValueAtTime(0, audioContext.currentTime + start + duration);
    oscillator.connect(gain);
    gain.connect(audioContext.destination);
    oscillator.start(audioContext.currentTime + start);
    oscillator.stop(audioContext.currentTime + start + duration + 0.02);
  }

  return {
    play() {
      if (!AudioContextConstructor) {
        return;
      }

      audioContext = audioContext || new AudioContextConstructor();
      if (audioContext.state === "suspended") {
        audioContext.resume();
      }
      tone(220, 0, 0.18, 0.12);
      tone(175, 0.22, 0.2, 0.11);
      tone(140, 0.48, 0.26, 0.1);
    },
  };
}

window.cookedOverlayAudio = createWarningSound();
