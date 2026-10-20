import { describe, expect, it } from "vitest";
import { fitWithin } from "./imageUpload";

describe("fitWithin", () => {
  it("shrinks the long side to the limit, keeping the aspect ratio", () => {
    expect(fitWithin(4000, 3000, 1600)).toEqual({ width: 1600, height: 1200 });
    expect(fitWithin(3000, 4000, 1600)).toEqual({ width: 1200, height: 1600 });
  });

  it("never enlarges a small photo", () => {
    expect(fitWithin(800, 600, 1600)).toEqual({ width: 800, height: 600 });
  });

  it("rounds to whole pixels", () => {
    expect(fitWithin(1000, 333, 512)).toEqual({ width: 512, height: 170 });
  });
});
