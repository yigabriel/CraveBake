import { describe, expect, it } from "vitest";
import { formatMeasure, formatQuantity, isFractionalCount, roundForUnit, scale, unitLabel } from "./quantities";

describe("roundForUnit", () => {
  it("rounds counts to halves", () => {
    expect(roundForUnit("1.3", "u").toString()).toBe("1.5");
    expect(roundForUnit("1.2", "u").toString()).toBe("1");
  });

  it("keeps one decimal for small grams and none above 10", () => {
    expect(roundForUnit("2.46", "g").toString()).toBe("2.5");
    expect(roundForUnit("123.6", "g").toString()).toBe("124");
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

describe("formatMeasure: US cups and spoons", () => {
  it("uses thirds, which US measuring cups have", () => {
    expect(formatMeasure("0.33", "cup", "en")).toBe("⅓ cup");
    expect(formatMeasure("1.67", "cup", "en")).toBe("1 ⅔ cups");
  });

  it("tops up with tablespoons instead of rounding flour away", () => {
    // 100 g of all-purpose flour at 125 g/cup.
    expect(formatMeasure("0.80", "cup", "es")).toBe("¾ taza + 1 cda");
    expect(formatMeasure("0.80", "cup", "en")).toBe("¾ cup + 1 tbsp");
  });

  it("does not add spoons when a cup fraction is close enough", () => {
    expect(formatMeasure("1.01", "cup", "es")).toBe("1 taza");
    expect(formatMeasure("2", "cup", "es")).toBe("2 tazas");
  });

  it("moves to a smaller or bigger measure when the amount calls for it", () => {
    expect(formatMeasure("0.125", "cup", "en")).toBe("2 tbsp");
    expect(formatMeasure("0.5", "tbsp", "es")).toBe("1 ½ cdtas");
    expect(formatMeasure("6", "tsp", "en")).toBe("2 tbsp");
    expect(formatMeasure("0.05", "tsp", "en")).toBe("⅛ tsp");
  });

  it("keeps metric amounts as plain numbers", () => {
    expect(formatMeasure("2.5", "g", "es")).toBe("2,5 g");
    expect(formatMeasure("250", "g", "en")).toBe("250 g");
  });
});

describe("formatQuantity", () => {
  it("uses the language's decimal separator", () => {
    expect(formatQuantity("2.5", "g", "es")).toBe("2,5");
    expect(formatQuantity("2.5", "g", "en")).toBe("2.5");
  });
});

describe("units", () => {
  it("translates US abbreviations for Spanish, with plurals", () => {
    expect(unitLabel("cup", "es")).toBe("taza");
    expect(unitLabel("cup", "es", 2)).toBe("tazas");
    expect(unitLabel("cup", "en")).toBe("cup");
    expect(unitLabel("g", "es")).toBe("g");
  });

  it("flags half eggs", () => {
    expect(isFractionalCount("1.5", "u")).toBe(true);
    expect(isFractionalCount("2", "u")).toBe(false);
  });
});
