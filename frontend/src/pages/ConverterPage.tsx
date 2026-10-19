import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { catalogApi } from "../api/endpoints";
import { useErrorMessage, useUnits } from "../api/queries";
import type { Ingredient, Language, Unit } from "../api/types";
import { IngredientPicker, useDebounced } from "../components/Pickers";
import { useToast } from "../components/Toast";
import { Card, Chip, Field, Icon, IconButton, Input, inputClass, PageHeader, Skeleton } from "../components/ui";
import { formatMeasure } from "../lib/quantities";

export function ConverterPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const units = useUnits();
  const [quantity, setQuantity] = useState("1");
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [ingredient, setIngredient] = useState<Ingredient | null>(null);

  const list = units.data ?? [];
  const from = list.find((unit) => unit.id === fromId) ?? list.find((unit) => unit.abbreviation === "cup");
  const to = list.find((unit) => unit.id === toId) ?? list.find((unit) => unit.abbreviation === "g");
  // Volume <-> weight depends on density: only then is the ingredient needed (§7a).
  const crossing = !!from && !!to && from.unit_type !== to.unit_type && from.unit_type !== "count" && to.unit_type !== "count";
  const countMismatch = !!from && !!to && from.unit_type !== to.unit_type && (from.unit_type === "count" || to.unit_type === "count");
  const amount = useDebounced(quantity, 250);
  const ready = !!from && !!to && Number(amount) > 0 && !countMismatch && (!crossing || !!ingredient);

  const result = useQuery({
    queryKey: ["convert", amount, from?.id, to?.id, crossing ? ingredient?.id : null],
    queryFn: () =>
      catalogApi.convert({ quantity: amount, from_unit_id: from!.id, to_unit_id: to!.id, ingredient_id: crossing ? ingredient!.id : null }),
    enabled: ready,
    retry: false,
  });

  const unitOption = (unit: Unit) => (
    <option key={unit.id} value={unit.id}>
      {unit.name}
    </option>
  );
  const grouped = (["weight", "volume", "count"] as const).map((type) => (
    <optgroup key={type} label={t(`converter.types.${type}`)}>
      {list.filter((unit) => unit.unit_type === type).map(unitOption)}
    </optgroup>
  ));
  const noDensity = result.error instanceof ApiError && result.error.status === 400;
  const shown = result.data ? formatMeasure(result.data.converted_quantity, to?.abbreviation, language) : null;

  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title={t("converter.title")} subtitle={t("converter.subtitle")} />
      {units.isLoading ? (
        <Skeleton className="h-96" />
      ) : (
        <Card className="flex flex-col gap-md p-md">
          <Field
            label={crossing ? t("converter.ingredientRequired") : t("converter.ingredientOptional")}
            hint={crossing ? t("converter.densityHint") : undefined}
          >
            {ingredient ? (
              <div>
                <Chip tone="success" icon="nutrition" onRemove={() => setIngredient(null)}>
                  {ingredient.name}
                </Chip>
              </div>
            ) : (
              <IngredientPicker onPick={setIngredient} />
            )}
          </Field>
          <Field label={t("converter.amount")}>
            <Input type="number" inputMode="decimal" min="0" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="text-title-lg" />
          </Field>
          <div className="grid grid-cols-[1fr_auto_1fr] items-end gap-sm">
            <Field label={t("converter.from")}>
              <select value={from?.id ?? ""} onChange={(e) => setFromId(e.target.value)} className={inputClass}>
                {grouped}
              </select>
            </Field>
            <IconButton
              icon="swap_horiz"
              label={t("converter.swap")}
              className="mb-[2px] bg-surface-container-high"
              onClick={() => {
                setFromId(to?.id ?? "");
                setToId(from?.id ?? "");
              }}
            />
            <Field label={t("converter.to")}>
              <select value={to?.id ?? ""} onChange={(e) => setToId(e.target.value)} className={inputClass}>
                {grouped}
              </select>
            </Field>
          </div>

          <div className="flex items-center justify-between gap-sm rounded-xl bg-primary-fixed/60 p-md">
            <div>
              <p className="text-label-sm uppercase text-primary">{t("converter.result")}</p>
              {countMismatch ? (
                <p className="text-body-md text-on-surface-variant">{t("converter.countNotConvertible")}</p>
              ) : crossing && !ingredient ? (
                <p className="text-body-md text-on-surface-variant">{t("converter.pickIngredient")}</p>
              ) : noDensity ? (
                <p className="text-body-md text-on-surface-variant">{t("converter.noDensity")}</p>
              ) : result.isError ? (
                <p className="text-body-md text-error">{errorMessage(result.error)}</p>
              ) : (
                <p className="text-display-sm text-on-primary-container" aria-live="polite">
                  {result.isFetching && !shown ? "…" : shown ?? "—"}
                </p>
              )}
            </div>
            {shown && (
              <IconButton
                icon="content_copy"
                label={t("converter.copy")}
                onClick={() => {
                  void navigator.clipboard.writeText(shown);
                  toast(t("converter.copied"));
                }}
              />
            )}
          </div>
          {result.data && ingredient && crossing && (
            <p className="flex items-center gap-xs text-label-sm font-normal text-on-surface-variant">
              <Icon name="info" className="text-[16px]" /> {t("converter.basedOn", { name: ingredient.name })}
            </p>
          )}
        </Card>
      )}
    </div>
  );
}
