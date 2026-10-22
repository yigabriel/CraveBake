import { describe, expect, it } from "vitest";
import { fold, isSameName } from "./text";

describe("fold", () => {
  it("ignores accents, case and surrounding spaces", () => {
    expect(fold("  AZÚCAR ")).toBe("azucar");
    expect(fold("Piña colada")).toBe("pina colada");
    expect(fold("Crème brûlée")).toBe("creme brulee");
  });

  it("makes both spellings equal", () => {
    expect(fold("azucar")).toBe(fold("Azúcar"));
  });
});

describe("isSameName", () => {
  it("recognises any synonym of a name", () => {
    expect(isSameName("Mantequilla / Manteca", "manteca")).toBe(true);
    expect(isSameName("Mantequilla / Manteca", "MANTEQUILLA")).toBe(true);
    expect(isSameName("Mantequilla / Manteca", "Mantequilla / manteca")).toBe(true);
  });

  it("does not take a longer name for a synonym", () => {
    expect(isSameName("Mantequilla de maní", "mantequilla")).toBe(false);
    expect(isSameName("Mantequilla / Manteca", "manteca de cerdo")).toBe(false);
  });
});
