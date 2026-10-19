import type { Language } from "../api/types";

/** 90 -> "1 h 30 min", 45 -> "45 min". */
export function formatMinutes(minutes: number | null | undefined): string {
  if (!minutes) return "";
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest} min`;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function formatSeconds(seconds: number | null | undefined): string {
  if (!seconds) return "";
  return seconds < 60 ? `${seconds} s` : formatMinutes(Math.round(seconds / 60));
}

/** Countdown clock: 3725 -> "1:02:05", 900 -> "15:00". */
export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

/** "hace 3 días" / "3 days ago". */
export function timeAgo(iso: string, language: Language, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const format = new Intl.RelativeTimeFormat(language, { numeric: "auto" });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31536000],
    ["month", 2592000],
    ["week", 604800],
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return format.format(Math.round(seconds / size), unit);
  }
  return format.format(0, "minute");
}

export function formatDate(iso: string, language: Language): string {
  return new Intl.DateTimeFormat(language, { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso));
}
