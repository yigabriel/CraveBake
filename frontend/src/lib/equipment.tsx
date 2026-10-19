import type { EquipmentType } from "../api/types";
import { Icon } from "../components/ui";

// Line icons drawn for what Material Symbols lacks, in the same 24px / ~2px-stroke style.
const CUSTOM: Record<string, string> = {
  whisk: "M12 15C6.5 11 7 3.5 12 2c5 1.5 5.5 9 0 13M12 15c-2.5-4-2-11 0-13 2 2 2.5 9 0 13M10.5 15h3v7h-3z",
  rolling_pin: "M6.3 14.2l7.9-7.9a2.5 2.5 0 0 1 3.5 3.5l-7.9 7.9a2.5 2.5 0 0 1-3.5-3.5zM3 21l2.5-2.5M18.5 5.5L21 3",
  piping_bag: "M5 3h14l-5 13h-4zM10.5 16h3l-.6 3.5h-1.8zM8 3c1-1.5 7-1.5 8 0",
  sieve: "M3 10h14a7 7 0 0 1-14 0zM17 10h5M6.5 13h7M8.5 15.8h3",
  measuring_cup: "M5 5h10v12a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3zM15 8h1.5a2.5 2.5 0 0 1 2.5 2.5v1a2.5 2.5 0 0 1-2.5 2.5H15M8 9h3M8 12h2M8 15h3",
  spatula: "M12 2v11M8.5 13h7v4.5a3.5 3.5 0 0 1-7 0z",
  bowl: "M3 11h18a9 9 0 0 1-18 0zM8 20.5h8",
  cupcake: "M6 12h12l-1.6 8H7.6zM5 12a7 7 0 0 1 14 0M10 14.5v3.5M14 14.5v3.5M12 4.5V3",
  loaf_pan: "M2 8h20M3.5 8l1.8 11h13.4l1.8-11",
  rect_pan: "M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM6.5 8.5h11v7h-11z",
  tart: "M12 3l1.6 1.2 2-.3.8 1.8 1.9.8-.3 2 1.2 1.6-1.2 1.6.3 2-1.9.8-.8 1.8-2-.3L12 21l-1.6-1.2-2 .3-.8-1.8-1.9-.8.3-2L4.8 12l1.2-1.6-.3-2 1.9-.8.8-1.8 2 .3zM12 7.5a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9z",
  tray: "M2 15h20l-2 4H4zM5 12.5a2 2 0 0 1 4 0M10 12.5a2 2 0 0 1 4 0M15 12.5a2 2 0 0 1 4 0",
  hand_mixer: "M4 5h11a4 4 0 0 1 4 4v1a2 2 0 0 1-2 2H4zM8 12v5.5M12 12v5.5M7 17.5a1 1.5 0 0 0 2 0M11 17.5a1 1.5 0 0 0 2 0",
  stand_mixer: "M4 21h14M15 21V9M6 3h9a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2H6a3 3 0 0 1 0-6zM9 9v3M4.5 13h9l-1 6h-7z",
};

// First match wins; keywords are accent-free and lowercase, in Spanish and English.
const RULES: [string[], string][] = [
  [["planetaria", "stand mixer"], "stand_mixer"],
  [["batidora", "hand mixer", "mixer"], "hand_mixer"],
  [["batidor", "whisk"], "whisk"],
  [["procesadora", "licuadora", "blender", "processor"], "m:blender"],
  [["microondas", "microwave"], "m:microwave"],
  // Before "horno": a "bandeja para horno" is a tray, not an oven.
  [["bandeja", "placa", "tray", "sheet"], "tray"],
  [["horno", "oven"], "m:oven_gen"],
  [["balanza", "bascula", "scale"], "m:scale"],
  [["termometro", "thermometer"], "m:thermometer"],
  [["soplete", "torch"], "m:local_fire_department"],
  [["rejilla", "rack"], "m:grid_on"],
  [["bundt", "savarin"], "m:donut_large"],
  [["cupcake", "muffin"], "cupcake"],
  [["tarta", "tart", "pie"], "tart"],
  [["budin", "loaf", "pan de molde"], "loaf_pan"],
  [["redondo", "round", "springform"], "m:cake"],
  [["rectangular"], "rect_pan"],
  [["espatula", "spatula"], "spatula"],
  [["rodillo", "rolling"], "rolling_pin"],
  [["manga", "piping"], "piping_bag"],
  [["tamiz", "colador", "sieve", "sifter"], "sieve"],
  [["medidor", "taza", "measuring"], "measuring_cup"],
  [["bowl", "bol ", "recipiente"], "bowl"],
  [["cuchill", "lame", "knife"], "m:content_cut"],
  [["sarten", "olla", "skillet", "pot"], "m:skillet"],
  [["molde", "pan"], "m:cake"],
];
const BY_TYPE: Record<EquipmentType, string> = {
  molde: "m:cake",
  utensilio: "m:flatware",
  electrodomestico: "m:kitchen",
  otro: "m:category",
};

const normalize = (text: string) =>
  ` ${text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()} `;

export function equipmentIconKey(name: string | null | undefined, type?: EquipmentType): string {
  const text = normalize(name ?? "");
  const rule = RULES.find(([keywords]) => keywords.some((keyword) => text.includes(keyword)));
  return rule?.[1] ?? (type ? BY_TYPE[type] : "m:kitchen");
}

/** An icon that shows what the equipment is: a mixer for a mixer, an oven for an oven. */
export function EquipmentIcon({ name, type, className = "" }: { name: string | null | undefined; type?: EquipmentType; className?: string }) {
  const key = equipmentIconKey(name, type);
  if (key.startsWith("m:")) return <Icon name={key.slice(2)} className={className} />;
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden
      className={`inline-block h-[1em] w-[1em] ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={CUSTOM[key]} />
    </svg>
  );
}
