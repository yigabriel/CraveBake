import { describe, expect, it } from "vitest";
import { videoPlatform } from "./videoLink";

describe("videoPlatform", () => {
  it("recognises TikTok videos and Instagram Reels, with or without the scheme", () => {
    expect(videoPlatform("https://www.tiktok.com/@baker/video/7312345678901234567")).toBe("tiktok");
    expect(videoPlatform("tiktok.com/@baker.cakes/video/7312345678901234567?is_from_webapp=1")).toBe("tiktok");
    expect(videoPlatform("https://vm.tiktok.com/ZMabc12345/")).toBe("tiktok");
    expect(videoPlatform("https://www.instagram.com/reel/C9abcDEF123/?igsh=abc")).toBe("instagram");
    expect(videoPlatform("  https://instagram.com/baker/reels/C9abcDEF123  ")).toBe("instagram");
  });

  it("rejects everything else", () => {
    for (const link of [
      "",
      "not a link",
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "https://www.tiktok.com/@baker", // a profile
      "https://www.tiktok.com/discover",
      "https://www.instagram.com/baker/",
      "https://www.tiktok.com.evil.example/@a/video/1",
      "https://user:pass@www.tiktok.com/@a/video/1",
      "javascript:alert(1)",
    ])
      expect(videoPlatform(link), link).toBeNull();
  });
});
