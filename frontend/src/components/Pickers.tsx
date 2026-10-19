import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { catalogApi } from "../api/endpoints";
import { useErrorMessage } from "../api/queries";
import type { Equipment, EquipmentType, Ingredient } from "../api/types";
import { useToast } from "./Toast";
import { Icon, inputClass } from "./ui";

function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export { useDebounced };

interface Option {
  id: string;
  name: string;
  /** Shown instead of `name` (e.g. a translated catalog name). */
  label?: string;
  hint?: string | null;
}

function SearchPicker<T extends Option>({
  placeholder,
  queryKey,
  search,
  onPick,
  onCreate,
  excludeIds = [],
  autoFocus,
}: {
  placeholder: string;
  queryKey: string;
  search: (q: string) => Promise<T[]>;
  onPick: (item: T) => void;
  onCreate?: (name: string) => Promise<T>;
  excludeIds?: string[];
  autoFocus?: boolean;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const q = useDebounced(text.trim());
  const results = useQuery({ queryKey: [queryKey, "search", q], queryFn: () => search(q), enabled: open });
  // While the debounced search catches up with what is typed, old results would be
  // clickable and "Create" would use the previous text: show neither until it settles.
  const settled = text.trim() === q;
  const options = settled ? (results.data ?? []).filter((item) => !excludeIds.includes(item.id)) : [];
  const exact = settled && results.data?.some((item) => item.name.toLowerCase() === q.toLowerCase());
  const loading = results.isLoading || !settled;

  const pick = (item: T) => {
    onPick(item);
    setText("");
    setOpen(false);
  };

  return (
    <div className="relative">
      <Icon name="search" className="pointer-events-none absolute left-sm top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant" />
      <input
        value={text}
        autoFocus={autoFocus}
        onChange={(event) => {
          setText(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        aria-label={placeholder}
        className={`${inputClass} pl-[40px]`}
      />
      {open && (
        <ul className="absolute z-30 mt-xs max-h-72 w-full overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-lowest py-xs shadow-lift">
          {loading && <li className="px-sm py-xs text-label-md text-on-surface-variant">{t("common.loading")}</li>}
          {options.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => pick(item)}
                className="flex w-full items-center justify-between gap-sm px-sm py-xs text-left text-body-md hover:bg-surface-container-high"
              >
                {item.label ?? item.name}
                {item.hint && <span className="text-label-sm text-on-surface-variant">{item.hint}</span>}
              </button>
            </li>
          ))}
          {!loading && options.length === 0 && !onCreate && (
            <li className="px-sm py-xs text-label-md text-on-surface-variant">{t("common.noResults")}</li>
          )}
          {onCreate && !loading && q && !exact && (
            <li>
              <button
                type="button"
                disabled={creating}
                onMouseDown={(event) => event.preventDefault()}
                onClick={async () => {
                  setCreating(true);
                  try {
                    pick(await onCreate(q));
                  } catch (error) {
                    toast(errorMessage(error), "error");
                  } finally {
                    setCreating(false);
                  }
                }}
                className="flex w-full items-center gap-xs px-sm py-xs text-left text-label-md text-primary hover:bg-surface-container-high"
              >
                <Icon name="add_circle" className="text-[18px]" /> {t("common.createNamed", { name: q })}
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

export function IngredientPicker({
  onPick,
  excludeIds,
  allowCreate = false,
  placeholder,
  autoFocus,
}: {
  onPick: (ingredient: Ingredient) => void;
  excludeIds?: string[];
  allowCreate?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <SearchPicker<Ingredient & Option>
      placeholder={placeholder ?? t("ingredients.searchPlaceholder")}
      queryKey="ingredients"
      search={async (q) =>
        (await catalogApi.searchIngredients(q, 10)).items.map((item) => ({ ...item, hint: item.category_name }))
      }
      onPick={onPick}
      onCreate={allowCreate ? (name) => catalogApi.createIngredient({ name }) : undefined}
      excludeIds={excludeIds}
      autoFocus={autoFocus}
    />
  );
}

export function EquipmentPicker({
  onPick,
  excludeIds,
  allowCreateAs,
  placeholder,
}: {
  onPick: (equipment: Equipment) => void;
  excludeIds?: string[];
  /** Type given to equipment created from here; undefined disables creation. */
  allowCreateAs?: EquipmentType;
  placeholder?: string;
}) {
  const { t } = useTranslation();
  return (
    <SearchPicker<Equipment & Option>
      placeholder={placeholder ?? t("kitchen.searchPlaceholder")}
      queryKey="equipment"
      search={async (q) =>
        (await catalogApi.searchEquipment(q)).items.map((item) => ({
          ...item,
          hint: t(`kitchen.types.${item.equipment_type}`),
        }))
      }
      onPick={onPick}
      onCreate={allowCreateAs ? (name) => catalogApi.createEquipment({ name, equipment_type: allowCreateAs }) : undefined}
      excludeIds={excludeIds}
    />
  );
}
