import { describe, expect, it } from "vitest";
import type { RecipeDetail, RecipeIngredient, RecipeStep } from "../api/types";
import { diffRecipes, isEmptyDiff } from "./recipeDiff";

const line = (ingredient_id: string, name: string, quantity: string, unit = "g"): RecipeIngredient => ({
  id: `${ingredient_id}-${quantity}`,
  ingredient_id,
  ingredient_name: name,
  quantity,
  unit_id: unit,
  unit_abbreviation: unit,
  notes: null,
  position: 0,
  // Converted values must never leak into the comparison.
  display_quantity: "999",
  display_unit_abbreviation: "oz",
  converted: true,
});

const step = (n: number, instructions: string): RecipeStep => ({
  id: `s${n}`,
  step_number: n,
  title: null,
  instructions,
  timer_seconds: null,
  photo: null,
});

const recipe = (overrides: Partial<RecipeDetail>): RecipeDetail =>
  ({ title: "Brownies", servings: 4, prep_time_minutes: 30, ingredients: [], steps: [], ...overrides }) as RecipeDetail;

describe("diffRecipes", () => {
  it("finds no change between equal recipes", () => {
    const base = recipe({ ingredients: [line("flour", "Harina", "250")], steps: [step(1, "Mezclar")] });
    expect(isEmptyDiff(diffRecipes(base, { ...base }))).toBe(true);
  });

  it("reports added, removed and changed ingredients by ingredient", () => {
    const original = recipe({ ingredients: [line("flour", "Harina", "250"), line("salt", "Sal", "5")] });
    const mine = recipe({ ingredients: [line("flour", "Harina", "300"), line("honey", "Miel", "15")] });

    expect(diffRecipes(original, mine).ingredients).toEqual([
      { name: "Harina", kind: "changed", original: "250 g", mine: "300 g" },
      { name: "Miel", kind: "added", mine: "15 g" },
      { name: "Sal", kind: "removed", original: "5 g" },
    ]);
  });

  it("compares steps by position and basic fields", () => {
    const original = recipe({ steps: [step(1, "Mezclar"), step(2, "Hornear")] });
    const mine = recipe({ servings: 8, steps: [step(1, "Mezclar bien")] });
    const diff = diffRecipes(original, mine);

    expect(diff.fields).toEqual([{ field: "servings", original: "4", mine: "8" }]);
    expect(diff.steps.map((s) => [s.stepNumber, s.kind])).toEqual([
      [1, "changed"],
      [2, "removed"],
    ]);
  });
});
