/** Timer finished: sound + vibration + notification (§14). Each part fails silently. */

export async function askNotificationPermission() {
  if (typeof Notification !== "undefined" && Notification.permission === "default") {
    await Notification.requestPermission().catch(() => {});
  }
}

function beep() {
  try {
    const AudioCtx = window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    const context = new AudioCtx();
    [0, 0.4, 0.8].forEach((offset) => {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(0.3, context.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + offset + 0.3);
      oscillator.connect(gain).connect(context.destination);
      oscillator.start(context.currentTime + offset);
      oscillator.stop(context.currentTime + offset + 0.3);
    });
  } catch {
    // No audio available.
  }
}

export function ringAlarm(title: string, body: string) {
  beep();
  navigator.vibrate?.([400, 200, 400, 200, 400]);
  if (typeof Notification !== "undefined" && Notification.permission === "granted" && document.hidden) {
    try {
      new Notification(title, { body, tag: "cravebake-timer" });
    } catch {
      // Some mobile browsers only allow notifications from a service worker.
    }
  }
}

/** Keeps the screen on while cooking; re-acquired when the tab becomes visible again. */
export function keepScreenOn(): () => void {
  let lock: WakeLockSentinel | null = null;
  let released = false;
  const acquire = async () => {
    try {
      if (!released && document.visibilityState === "visible" && "wakeLock" in navigator) {
        lock = await navigator.wakeLock.request("screen");
      }
    } catch {
      // Denied or unsupported (e.g. battery saver).
    }
  };
  void acquire();
  document.addEventListener("visibilitychange", acquire);
  return () => {
    released = true;
    document.removeEventListener("visibilitychange", acquire);
    void lock?.release().catch(() => {});
  };
}
