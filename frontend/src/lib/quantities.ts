import Decimal from "decimal.js";
import type { Language } from "../api/types";

/**
 * Quantities arrive as decimal strings ("2.50"). Scaling and rounding use
 * decimal.js so 0.1 + 0.2 never shows up in a recipe.
 */

const FRACTIONS: Record<string, string> = { "0.25": "¼", "0.5": "½", "0.75": "¾" };
const SPOON_UNITS = new Set(["cup", "tbsp", "tsp"]);

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

/** "1 ½", "250", "2,5" (es) / "2.5" (en). */
export function formatQuantity(quantity: Decimal.Value, unit: string | null | undefined, language: Language): string {
  const value = roundForUnit(quantity, unit);
  if (unit && SPOON_UNITS.has(unit)) {
    const whole = value.floor();
    const fraction = FRACTIONS[value.minus(whole).toString()];
    if (fraction) return whole.isZero() ? fraction : `${whole.toString()} ${fraction}`;
  }
  return new Intl.NumberFormat(language, { maximumFractionDigits: 2 }).format(value.toNumber());
}

const UNIT_LABELS: Record<Language, Record<string, string>> = {
  es: { cup: "taza", tbsp: "cda", tsp: "cdta", u: "u" },
  en: {},
};

/** The API's abbreviations are English (cup, tbsp); Spanish UIs show taza / cda / cdta. */
export function unitLabel(abbreviation: string | null | undefined, language: Language): string {
  if (!abbreviation) return "";
  return UNIT_LABELS[language][abbreviation] ?? abbreviation;
}

/** Non-integer counts ("1.5 huevos") deserve a hint: the user has to decide. */
export function isFractionalCount(quantity: Decimal.Value, unit: string | null | undefined): boolean {
  return unit === "u" && !roundForUnit(quantity, unit).isInteger();
}

/** Unit pickers: the catalog name is Spanish ("taza"), so Spanish shows it alone; English shows the abbreviation. */
export function unitOptionLabel(unit: { name: string; abbreviation: string }, language: Language): string {
  return language === "es" ? unit.name : `${unit.abbreviation} (${unit.name})`;
}
