import { describe, expect, it } from "vitest";
import { equipmentIconKey } from "./equipment";

// The 23 seeded names (backend/alembic/versions/0007) and the icon each one must get,
// in both languages: the API sends whichever the user reads.
const SEEDED: [string, string][] = [
  ["Molde redondo desmontable", "m:cake"],
  ["Molde rectangular", "rect_pan"],
  ["Molde para budín", "loaf_pan"],
  ["Molde para tarta", "tart"],
  ["Molde para cupcakes y muffins", "cupcake"],
  ["Molde bundt (savarín)", "m:donut_large"],
  ["Bandeja para horno", "tray"],
  ["Batidor de globo", "whisk"],
  ["Espátula de silicona", "spatula"],
  ["Rodillo", "rolling_pin"],
  ["Manga pastelera", "piping_bag"],
  ["Tamiz", "sieve"],
  ["Balanza de cocina", "m:scale"],
  ["Tazas y cucharas medidoras", "measuring_cup"],
  ["Rejilla de enfriado", "m:grid_on"],
  ["Bowl", "bowl"],
  ["Horno", "m:oven_gen"],
  ["Batidora de mano", "hand_mixer"],
  ["Batidora planetaria", "stand_mixer"],
  ["Procesadora de alimentos", "m:blender"],
  ["Microondas", "m:microwave"],
  ["Termómetro de cocina", "m:thermometer"],
  ["Soplete de cocina", "m:local_fire_department"],
];

// The same equipment as the API names it in English (migration 0017).
const SEEDED_EN: [string, string][] = [
  ["Springform pan", "m:cake"],
  ["Rectangular pan", "rect_pan"],
  ["Loaf pan", "loaf_pan"],
  ["Tart pan", "tart"],
  ["Muffin tin", "cupcake"],
  ["Bundt pan", "m:donut_large"],
  ["Baking sheet", "tray"],
  ["Balloon whisk", "whisk"],
  ["Silicone spatula", "spatula"],
  ["Rolling pin", "rolling_pin"],
  ["Piping bag", "piping_bag"],
  ["Sifter", "sieve"],
  ["Kitchen scale", "m:scale"],
  ["Measuring cups & spoons", "measuring_cup"],
  ["Cooling rack", "m:grid_on"],
  ["Mixing bowl", "bowl"],
  ["Oven", "m:oven_gen"],
  ["Hand mixer", "hand_mixer"],
  ["Stand mixer", "stand_mixer"],
  ["Food processor", "m:blender"],
  ["Microwave", "m:microwave"],
  ["Kitchen thermometer", "m:thermometer"],
  ["Kitchen torch", "m:local_fire_department"],
];

describe("equipment icons", () => {
  it.each([...SEEDED, ...SEEDED_EN])("%s -> %s", (name, key) => {
    expect(equipmentIconKey(name)).toBe(key);
  });

  it("falls back to the equipment type for unknown names", () => {
    expect(equipmentIconKey("Cosa rara", "electrodomestico")).toBe("m:kitchen");
  });
});

