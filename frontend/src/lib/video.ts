/** YouTube / Vimeo links become embeddable URLs; anything else is just linked (§5). */
export function embedUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\.|^m\./, "");
    if (host === "youtube.com" && parsed.searchParams.get("v"))
      return `https://www.youtube-nocookie.com/embed/${parsed.searchParams.get("v")}`;
    if (host === "youtube.com" && parsed.pathname.startsWith("/shorts/"))
      return `https://www.youtube-nocookie.com/embed/${parsed.pathname.split("/")[2]}`;
    if (host === "youtu.be") return `https://www.youtube-nocookie.com/embed${parsed.pathname}`;
    if (host === "vimeo.com" && /^\/\d+/.test(parsed.pathname))
      return `https://player.vimeo.com/video${parsed.pathname.match(/^\/\d+/)![0]}`;
  } catch {
    return null;
  }
  return null;
}
