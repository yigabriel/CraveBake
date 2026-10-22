/**
 * Is this a link the recipe import accepts: a TikTok video or an Instagram Reel?
 * Mirrors `parse_source_url` in the API (which is the real check); this one only
 * saves a round trip and tells the person right away.
 */
const TIKTOK_HOSTS = new Set(["tiktok.com", "www.tiktok.com", "m.tiktok.com"]);
const TIKTOK_SHORT_HOSTS = new Set(["vm.tiktok.com", "vt.tiktok.com"]);
const INSTAGRAM_HOSTS = new Set(["instagram.com", "www.instagram.com"]);

const TIKTOK_VIDEO = /^(\/@[\w.-]+\/video\/\d+|\/v\/\d+(\.html)?|\/t\/[\w-]+\/?)$/;
const TIKTOK_SHORT = /^\/[\w-]{6,20}\/?$/;
const INSTAGRAM_VIDEO = /^(\/[\w.]+)?\/(reel|reels|p|tv)\/[\w-]+\/?$/;

export type VideoPlatform = "tiktok" | "instagram";

export function videoPlatform(raw: string): VideoPlatform | null {
  const text = raw.trim();
  if (!text || text.length > 500) return null;
  let url: URL;
  try {
    url = new URL(text.includes("://") ? text : `https://${text}`);
  } catch {
    return null;
  }
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || !["", "80", "443"].includes(url.port)) return null;
  const host = url.hostname.toLowerCase();
  if ((TIKTOK_HOSTS.has(host) && TIKTOK_VIDEO.test(url.pathname)) || (TIKTOK_SHORT_HOSTS.has(host) && TIKTOK_SHORT.test(url.pathname))) return "tiktok";
  if (INSTAGRAM_HOSTS.has(host) && INSTAGRAM_VIDEO.test(url.pathname)) return "instagram";
  return null;
}
