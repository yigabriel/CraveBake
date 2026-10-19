import Decimal from "decimal.js";
import type { RecipeDetail } from "../api/types";

/**
 * "Compare with the original" (Stitch's compare modal), computed client-side:
 * the API only says *that* the original changed (source_updated_since_personalized).
 * Uses the as-written quantity/unit fields, never display_*, so both sides compare
 * in the units their authors chose.
 */

export interface IngredientChange {
  name: string;
  kind: "added" | "removed" | "changed";
  original?: string;
  mine?: string;
}

export interface StepChange {
  stepNumber: number;
  kind: "added" | "removed" | "changed";
  original?: string;
  mine?: string;
}

export interface FieldChange {
  field: "title" | "servings" | "prep_time_minutes";
  original: string;
  mine: string;
}

export interface RecipeDiff {
  fields: FieldChange[];
  ingredients: IngredientChange[];
  steps: StepChange[];
}

const amount = (line: RecipeDetail["ingredients"][number]) =>
  `${new Decimal(line.quantity).toString()} ${line.unit_abbreviation ?? ""}`.trim();

const stepText = (step: RecipeDetail["steps"][number]) =>
  [step.title, step.instructions].filter(Boolean).join(" — ") + (step.timer_seconds ? ` (${step.timer_seconds}s)` : "");

/** Lines grouped by ingredient; the same ingredient may appear twice (dough + dusting). */
function byIngredient(recipe: RecipeDetail) {
  const map = new Map<string, { name: string; amounts: string[] }>();
  for (const line of recipe.ingredients) {
    const entry = map.get(line.ingredient_id) ?? { name: line.ingredient_name ?? "?", amounts: [] };
    entry.amounts.push(amount(line));
    map.set(line.ingredient_id, entry);
  }
  return map;
}

export function diffRecipes(original: RecipeDetail, mine: RecipeDetail): RecipeDiff {
  const fields: FieldChange[] = [];
  for (const field of ["title", "servings", "prep_time_minutes"] as const) {
    if (original[field] !== mine[field])
      fields.push({ field, original: String(original[field] ?? "—"), mine: String(mine[field] ?? "—") });
  }

  const ingredients: IngredientChange[] = [];
  const before = byIngredient(original);
  const after = byIngredient(mine);
  for (const [id, entry] of after) {
    const old = before.get(id);
    if (!old) ingredients.push({ name: entry.name, kind: "added", mine: entry.amounts.join(" + ") });
    else if (old.amounts.join("|") !== entry.amounts.join("|"))
      ingredients.push({ name: entry.name, kind: "changed", original: old.amounts.join(" + "), mine: entry.amounts.join(" + ") });
  }
  for (const [id, entry] of before) {
    if (!after.has(id)) ingredients.push({ name: entry.name, kind: "removed", original: entry.amounts.join(" + ") });
  }

  const steps: StepChange[] = [];
  const count = Math.max(original.steps.length, mine.steps.length);
  for (let i = 0; i < count; i++) {
    const a = original.steps[i];
    const b = mine.steps[i];
    if (a && !b) steps.push({ stepNumber: i + 1, kind: "removed", original: stepText(a) });
    else if (!a && b) steps.push({ stepNumber: i + 1, kind: "added", mine: stepText(b) });
    else if (a && b && stepText(a) !== stepText(b))
      steps.push({ stepNumber: i + 1, kind: "changed", original: stepText(a), mine: stepText(b) });
  }

  return { fields, ingredients, steps };
}

export const isEmptyDiff = (diff: RecipeDiff) => !diff.fields.length && !diff.ingredients.length && !diff.steps.length;
