import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { pantryApi } from "../api/endpoints";
import { useErrorMessage, useUnits } from "../api/queries";
import type { Ingredient, Language, PantryItem } from "../api/types";
import { IngredientPicker } from "../components/Pickers";
import { useToast } from "../components/Toast";
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  Field,
  Icon,
  IconButton,
  Input,
  inputClass,
  Modal,
  PageHeader,
  Skeleton,
} from "../components/ui";
import { formatMeasure } from "../lib/quantities";

const OTHER = "__other__";

function EditModal({ item, onClose }: { item: PantryItem | null; onClose: () => void }) {
  const { t } = useTranslation();
  const units = useUnits();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [quantity, setQuantity] = useState(item?.quantity ? String(Number(item.quantity)) : "");
  const [unitId, setUnitId] = useState(item?.unit?.id ?? "");
  const save = useMutation({
    // PUT replaces quantity AND unit: always send both, or a stored amount is lost.
    mutationFn: () =>
      pantryApi.upsert({ ingredient_id: item!.ingredient.id, quantity: quantity || null, unit_id: quantity ? unitId || null : null }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["pantry"] });
      toast(t("pantry.updated"));
      onClose();
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });
  const invalid = quantity !== "" && !(Number(quantity) > 0);
  return (
    <Modal
      open={!!item}
      onClose={onClose}
      title={item?.ingredient.name ?? ""}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button loading={save.isPending} disabled={invalid} onClick={() => save.mutate()}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <p className="mb-md text-label-md font-normal text-on-surface-variant">{t("pantry.quantityOptional")}</p>
      <div className="grid grid-cols-2 gap-sm">
        <Field label={t("pantry.quantity")} error={invalid ? t("pantry.quantityPositive") : undefined}>
          <Input type="number" min="0" step="any" inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
        </Field>
        <Field label={t("pantry.unit")}>
          <select value={unitId} onChange={(e) => setUnitId(e.target.value)} disabled={!quantity} className={inputClass}>
            <option value="">—</option>
            {units.data?.map((unit) => (
              <option key={unit.id} value={unit.id}>
                {unit.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </Modal>
  );
}

export function PantryPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [category, setCategory] = useState<string | null>(null);
  const [editing, setEditing] = useState<PantryItem | null>(null);
  const pantry = useQuery({ queryKey: ["pantry"], queryFn: pantryApi.list });

  // Optimistic: the list changes at once, the request runs behind it; a failure puts it back.
  const add = useMutation({
    mutationFn: (ingredient: Ingredient) => pantryApi.upsert({ ingredient_id: ingredient.id }),
    onMutate: async (ingredient) => {
      await queryClient.cancelQueries({ queryKey: ["pantry"] });
      const previous = queryClient.getQueryData<PantryItem[]>(["pantry"]);
      const optimistic: PantryItem = { id: `optimistic-${ingredient.id}`, ingredient, quantity: null, unit: null, updated_at: new Date().toISOString() };
      queryClient.setQueryData<PantryItem[]>(["pantry"], (list = []) => [...list, optimistic]);
      toast(t("pantry.added", { name: ingredient.name }));
      return { previous };
    },
    onSuccess: (saved) =>
      queryClient.setQueryData<PantryItem[]>(["pantry"], (list = []) =>
        list.map((item) => (item.ingredient.id === saved.ingredient.id ? saved : item)),
      ),
    onError: (error, _ingredient, context) => {
      queryClient.setQueryData(["pantry"], context?.previous);
      toast(errorMessage(error), "error");
    },
  });
  const remove = useMutation({
    mutationFn: (ingredientId: string) => pantryApi.remove(ingredientId),
    onMutate: async (ingredientId) => {
      await queryClient.cancelQueries({ queryKey: ["pantry"] });
      const previous = queryClient.getQueryData<PantryItem[]>(["pantry"]);
      queryClient.setQueryData<PantryItem[]>(["pantry"], (list = []) => list.filter((item) => item.ingredient.id !== ingredientId));
      return { previous };
    },
    onError: (error, _id, context) => {
      queryClient.setQueryData(["pantry"], context?.previous);
      toast(errorMessage(error), "error");
    },
  });

  const items = pantry.data ?? [];
  const groups = useMemo(() => {
    const map = new Map<string, PantryItem[]>();
    for (const item of [...items].sort((a, b) => a.ingredient.name.localeCompare(b.ingredient.name))) {
      const key = item.ingredient.default_category ?? OTHER;
      map.set(key, [...(map.get(key) ?? []), item]);
    }
    return [...map.entries()].sort(([a], [b]) => (a === OTHER ? 1 : b === OTHER ? -1 : a.localeCompare(b)));
  }, [items]);
  const categoryNames = new Map(items.map((item) => [item.ingredient.default_category ?? OTHER, item.ingredient.category_name]));
  const label = (key: string) => (key === OTHER ? t("pantry.otherCategory") : categoryNames.get(key) ?? key);
  const shown = category ? groups.filter(([key]) => key === category) : groups;

  return (
    <div className="mx-auto max-w-4xl">
      <Link to="/profile" className="mb-sm inline-flex items-center gap-xs text-label-md text-primary">
        <Icon name="arrow_back" className="text-[18px]" /> {t("profile.title")}
      </Link>
      <PageHeader title={t("pantry.title")} subtitle={t("pantry.subtitle")} />

      <Card className="mb-md p-sm">
        <IngredientPicker
          allowCreate
          placeholder={t("pantry.addPlaceholder")}
          excludeIds={items.map((item) => item.ingredient.id)}
          onPick={(ingredient) => add.mutate(ingredient)}
        />
      </Card>

      {pantry.isLoading ? (
        <Skeleton className="h-64" />
      ) : pantry.isError ? (
        <ErrorState message={errorMessage(pantry.error)} onRetry={() => void pantry.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState icon="kitchen" title={t("pantry.emptyTitle")} text={t("pantry.emptyText")} />
      ) : (
        <>
          <div className="-mx-margin-mobile mb-md flex gap-xs overflow-x-auto px-margin-mobile pb-xs lg:mx-0 lg:flex-wrap lg:px-0">
            <Chip active={!category} onClick={() => setCategory(null)}>
              {t("common.all")} ({items.length})
            </Chip>
            {groups.map(([key, list]) => (
              <Chip key={key} active={category === key} onClick={() => setCategory(key)}>
                {label(key)} ({list.length})
              </Chip>
            ))}
          </div>
          <div className="flex flex-col gap-md">
            {shown.map(([key, list]) => (
              <section key={key}>
                <h2 className="mb-xs text-label-sm uppercase text-on-surface-variant">{label(key)}</h2>
                <Card className="divide-y divide-outline-variant/40">
                  {list.map((item) => (
                    <div key={item.id} className="flex items-center gap-sm px-sm py-sm">
                      <Icon name="nutrition" className="text-secondary" />
                      <span className="flex-1 text-body-md">{item.ingredient.name}</span>
                      <span className="text-label-md text-on-surface-variant">
                        {item.quantity
                          ? formatMeasure(item.quantity, item.unit?.abbreviation, language)
                          : t("pantry.inStock")}
                      </span>
                      <IconButton icon="edit" label={t("common.edit")} onClick={() => setEditing(item)} />
                      <IconButton
                        icon="delete"
                        label={t("common.delete")}
                        onClick={() => remove.mutate(item.ingredient.id)}
                        className="text-error"
                      />
                    </div>
                  ))}
                </Card>
              </section>
            ))}
          </div>
          <p className="mt-md text-center text-label-sm text-on-surface-variant">{t("pantry.usedFor")}</p>
        </>
      )}
      <EditModal key={editing?.id ?? "none"} item={editing} onClose={() => setEditing(null)} />
    </div>
  );
}
