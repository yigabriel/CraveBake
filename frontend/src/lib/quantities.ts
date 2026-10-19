import Decimal from "decimal.js";
import type { Language } from "../api/types";

/**
 * Quantities arrive as decimal strings ("2.50"). Scaling and rounding use
 * decimal.js so 0.1 + 0.2 never shows up in a recipe.
 *
 * US volumes come from the API with two decimals (0.80 cup): they are turned
 * into what a US measuring set can actually measure *here*, after scaling,
 * so rounding never compounds.
 */

const GLYPHS: Record<string, string> = {
  "0.125": "⅛",
  "0.25": "¼",
  "0.333": "⅓",
  "0.5": "½",
  "0.667": "⅔",
  "0.75": "¾",
};
const glyph = (fraction: number) => GLYPHS[String(Math.round(fraction * 1000) / 1000)] ?? "";

// Measures in a standard US set: cups ¼ ⅓ ½ ⅔ ¾ 1, tablespoon ½ 1, teaspoon ⅛ ¼ ½ 1.
const CUP_FRACTIONS = [0, 1 / 4, 1 / 3, 1 / 2, 2 / 3, 3 / 4, 1];
const TBSP_FRACTIONS = [0, 1 / 2, 1];
const TSP_FRACTIONS = [0, 1 / 8, 1 / 4, 1 / 2, 3 / 4, 1];
const TBSP_PER_CUP = 16;
const TSP_PER_TBSP = 3;

/** Rounds to something you can measure in a real kitchen (docs/FRONTEND_FEATURES.md §6). */
export function roundForUnit(quantity: Decimal.Value, unit: string | null | undefined): Decimal {
  const value = new Decimal(quantity);
  switch (unit) {
    case "u":
      return value.mul(2).toDecimalPlaces(0, Decimal.ROUND_HALF_UP).div(2);
    case "g":
    case "ml":
      return value.lt(10) ? value.toDecimalPlaces(1) : value.toDecimalPlaces(0);
    case "kg":
    case "l":
      return value.toDecimalPlaces(2);
    case "oz":
      return value.toDecimalPlaces(1);
    case "cup":
    case "tbsp":
    case "tsp": {
      const quarters = value.mul(4).toDecimalPlaces(0, Decimal.ROUND_HALF_UP).div(4);
      // Never round a real amount down to nothing.
      return quarters.isZero() && value.gt(0) ? new Decimal(0.25) : quarters;
    }
    default:
      return value.toDecimalPlaces(2);
  }
}

export function scale(quantity: Decimal.Value, baseServings: number | null, servings: number): Decimal {
  if (!baseServings) return new Decimal(quantity);
  return new Decimal(quantity).mul(servings).div(baseServings);
}

/** "2,5" (es) / "2.5" (en) — plain numbers, no fractions. */
export function formatQuantity(quantity: Decimal.Value, unit: string | null | undefined, language: Language): string {
  return new Intl.NumberFormat(language, { maximumFractionDigits: 2 }).format(roundForUnit(quantity, unit).toNumber());
}

const UNIT_LABELS: Record<Language, Record<string, [string, string]>> = {
  es: { cup: ["taza", "tazas"], tbsp: ["cda", "cdas"], tsp: ["cdta", "cdtas"] },
  en: { cup: ["cup", "cups"] },
};

/** The API's abbreviations are English (cup, tbsp): Spanish shows taza / cda / cdta, plural when > 1. */
export function unitLabel(abbreviation: string | null | undefined, language: Language, amount = 1): string {
  if (!abbreviation) return "";
  const forms = UNIT_LABELS[language][abbreviation];
  if (!forms) return abbreviation;
  return amount > 1 ? forms[1] : forms[0];
}

/** "1 ⅓", "⅔", "2". */
function mixed(whole: number, fraction: number, language: Language): string {
  const number = new Intl.NumberFormat(language).format(whole);
  if (!fraction) return number;
  return whole ? `${number} ${glyph(fraction)}` : glyph(fraction);
}

/** Closest measurable amount: whole part + the nearest fraction of the set. */
function nearest(value: number, fractions: number[]): { whole: number; fraction: number } {
  const whole = Math.floor(value);
  const rest = value - whole;
  const best = fractions.reduce((a, b) => (Math.abs(b - rest) < Math.abs(a - rest) ? b : a));
  return best === 1 ? { whole: whole + 1, fraction: 0 } : { whole, fraction: best };
}

function teaspoons(value: number, language: Language): string {
  if (value >= TSP_PER_TBSP) return tablespoons(value / TSP_PER_TBSP, language);
  const { whole, fraction } = nearest(Math.max(value, 1 / 8), TSP_FRACTIONS);
  return `${mixed(whole, fraction, language)} ${unitLabel("tsp", language, whole + fraction)}`;
}

function tablespoons(value: number, language: Language): string {
  if (value < 1) return teaspoons(value * TSP_PER_TBSP, language);
  if (value >= 4) return cups(value / TBSP_PER_CUP, language);
  const { whole, fraction } = nearest(value, TBSP_FRACTIONS);
  return `${mixed(whole, fraction, language)} ${unitLabel("tbsp", language, whole + fraction)}`;
}

/**
 * Cups the way a US measuring set measures them. If the nearest cup fraction is
 * off by half a tablespoon or more, the rest is added in tablespoons:
 * 0.8 cup -> "¾ cup + 1 tbsp" instead of rounding 6 g of flour away.
 */
function cups(value: number, language: Language): string {
  if (value < 1 / 4) return tablespoons(value * TBSP_PER_CUP, language);
  const close = nearest(value, CUP_FRACTIONS);
  const offTbsp = (value - (close.whole + close.fraction)) * TBSP_PER_CUP;
  const label = (amount: number) => unitLabel("cup", language, amount);
  if (Math.abs(offTbsp) < 0.5) return `${mixed(close.whole, close.fraction, language)} ${label(close.whole + close.fraction)}`;

  // Take the biggest cup measure that fits and top up with spoons.
  const whole = Math.floor(value);
  const fraction = Math.max(...CUP_FRACTIONS.filter((f) => f < 1 && whole + f <= value + 1e-9));
  const restTbsp = Math.round((value - whole - fraction) * TBSP_PER_CUP * 2) / 2;
  const base = `${mixed(whole, fraction, language)} ${label(whole + fraction)}`;
  if (!restTbsp) return base;
  if (!whole && !fraction) return tablespoons(restTbsp, language);
  return `${base} + ${tablespoons(restTbsp, language)}`;
}

/**
 * The full text of an amount, unit included: "¾ taza + 1 cda", "250 g", "1,5 u".
 * Use this (not formatQuantity + unitLabel) wherever an ingredient amount is shown.
 */
export function formatMeasure(quantity: Decimal.Value, unit: string | null | undefined, language: Language): string {
  const value = new Decimal(quantity).toNumber();
  if (unit === "cup") return cups(value, language);
  if (unit === "tbsp") return tablespoons(value, language);
  if (unit === "tsp") return teaspoons(value, language);
  const amount = roundForUnit(quantity, unit);
  const number = new Intl.NumberFormat(language, { maximumFractionDigits: 2 }).format(amount.toNumber());
  return unit ? `${number} ${unitLabel(unit, language, amount.toNumber())}` : number;
}

/** Non-integer counts ("1.5 huevos") deserve a hint: the user has to decide. */
export function isFractionalCount(quantity: Decimal.Value, unit: string | null | undefined): boolean {
  return unit === "u" && !roundForUnit(quantity, unit).isInteger();
}

