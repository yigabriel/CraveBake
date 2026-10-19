import { describe, expect, it } from "vitest";
import { formatQuantity, isFractionalCount, roundForUnit, scale, unitLabel } from "./quantities";

describe("roundForUnit", () => {
  it("rounds counts to halves", () => {
    expect(roundForUnit("1.3", "u").toString()).toBe("1.5");
    expect(roundForUnit("1.2", "u").toString()).toBe("1");
  });

  it("keeps one decimal for small grams and none above 10", () => {
    expect(roundForUnit("2.46", "g").toString()).toBe("2.5");
    expect(roundForUnit("123.6", "g").toString()).toBe("124");
  });

  it("rounds cups and spoons to quarters, never to zero", () => {
    expect(roundForUnit("1.3", "cup").toString()).toBe("1.25");
    expect(roundForUnit("0.05", "tsp").toString()).toBe("0.25");
  });

  it("keeps two decimals for kg and l", () => {
    expect(roundForUnit("1.23456", "kg").toString()).toBe("1.23");
  });
});

describe("scale", () => {
  it("multiplies by desired / original servings without float noise", () => {
    expect(scale("0.1", 3, 6).plus("0.2").toString()).toBe("0.4");
    expect(scale("250", 4, 6).toString()).toBe("375");
  });

  it("leaves the quantity alone without base servings", () => {
    expect(scale("250", null, 6).toString()).toBe("250");
  });
});

describe("formatQuantity", () => {
  it("shows spoon fractions as glyphs", () => {
    expect(formatQuantity("1.5", "cup", "es")).toBe("1 ½");
    expect(formatQuantity("0.75", "tbsp", "en")).toBe("¾");
  });

  it("uses the language's decimal separator", () => {
    expect(formatQuantity("2.5", "g", "es")).toBe("2,5");
    expect(formatQuantity("2.5", "g", "en")).toBe("2.5");
  });
});

describe("units", () => {
  it("translates US abbreviations for Spanish", () => {
    expect(unitLabel("cup", "es")).toBe("taza");
    expect(unitLabel("cup", "en")).toBe("cup");
    expect(unitLabel("g", "es")).toBe("g");
  });

  it("flags half eggs", () => {
    expect(isFractionalCount("1.5", "u")).toBe(true);
    expect(isFractionalCount("2", "u")).toBe(false);
  });
});
