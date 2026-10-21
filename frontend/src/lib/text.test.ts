import { describe, expect, it } from "vitest";
import { fold } from "./text";

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
