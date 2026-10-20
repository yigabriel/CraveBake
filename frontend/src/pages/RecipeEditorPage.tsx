import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { recipesApi } from "../api/endpoints";
import { useDifficulties, useErrorMessage, useRecipeCategories, useTags, useUnits } from "../api/queries";
import type { RecipeBasics, RecipeDetail, RecipePhoto, RecipeStepInput } from "../api/types";
import { EquipmentPicker, IngredientPicker } from "../components/Pickers";
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
  Switch,
} from "../components/ui";
import { EquipmentIcon } from "../lib/equipment";
import { ImageUploadButton } from "../components/ImageUploadButton";

const MAX_TAGS = 10;
const MAX_COVERS = 3;

interface IngredientRow {
  key: string;
  ingredient_id: string;
  name: string;
  quantity: string;
  unit_id: string;
  notes: string;
}
interface EquipmentRow {
  key: string;
  equipment_id: string;
  name: string;
  notes: string;
}
interface StepRow {
  key: string;
  id?: string;
  title: string;
  instructions: string;
  timerMinutes: string;
  hasPhoto: boolean;
}
interface Draft {
  basics: RecipeBasics;
  ingredients: IngredientRow[];
  equipment: EquipmentRow[];
  steps: StepRow[];
  tagIds: string[];
}

let counter = 0;
const newKey = () => `row-${++counter}`;

const emptyDraft = (): Draft => ({
  basics: {
    title: "",
    description: null,
    video_url: null,
    category_id: null,
    difficulty_id: null,
    prep_time_minutes: null,
    servings: null,
    is_public: false,
  },
  ingredients: [],
  equipment: [],
  steps: [{ key: newKey(), title: "", instructions: "", timerMinutes: "", hasPhoto: false }],
  tagIds: [],
});

function draftFrom(recipe: RecipeDetail): Draft {
  return {
    basics: {
      title: recipe.title,
      description: recipe.description,
      video_url: recipe.video_url,
      category_id: recipe.category?.id ?? null,
      difficulty_id: recipe.difficulty?.id ?? null,
      prep_time_minutes: recipe.prep_time_minutes,
      servings: recipe.servings,
      is_public: recipe.is_public,
    },
    // Always the as-written quantity/unit_id, never display_*.
    ingredients: recipe.ingredients.map((line) => ({
      key: newKey(),
      ingredient_id: line.ingredient_id,
      name: line.ingredient_name ?? "?",
      quantity: String(Number(line.quantity)),
      unit_id: line.unit_id,
      notes: line.notes ?? "",
    })),
    equipment: recipe.equipment.map((item) => ({
      key: newKey(),
      equipment_id: item.equipment_id,
      name: item.equipment_name ?? "?",
      notes: item.notes ?? "",
    })),
    steps: recipe.steps.map((step) => ({
      key: newKey(),
      id: step.id,
      title: step.title ?? "",
      instructions: step.instructions,
      timerMinutes: step.timer_seconds ? String(step.timer_seconds / 60) : "",
      hasPhoto: !!step.photo,
    })),
    tagIds: recipe.tags.map((tag) => tag.id),
  };
}

// --- Validation (mirrors the API rules, §8) ------------------------------------------------

type Errors = Record<string, string>;

function validateBasics(basics: RecipeBasics, t: (key: string) => string): Errors {
  const errors: Errors = {};
  if (!basics.title.trim()) errors.title = t("editor.errors.titleRequired");
  if (basics.video_url && !/^https?:\/\//.test(basics.video_url)) errors.video_url = t("editor.errors.videoUrl");
  if (basics.prep_time_minutes !== null && !(basics.prep_time_minutes > 0)) errors.prep_time_minutes = t("editor.errors.positive");
  if (basics.servings !== null && !(basics.servings > 0)) errors.servings = t("editor.errors.positive");
  return errors;
}

function validateIngredients(rows: IngredientRow[], t: (key: string) => string): Errors {
  const errors: Errors = {};
  rows.forEach((row) => {
    if (!(Number(row.quantity) > 0)) errors[row.key] = t("editor.errors.quantity");
    else if (!row.unit_id) errors[row.key] = t("editor.errors.unit");
  });
  return errors;
}

function validateSteps(rows: StepRow[], t: (key: string) => string): Errors {
  const errors: Errors = {};
  rows.forEach((row) => {
    if (!row.instructions.trim()) errors[row.key] = t("editor.errors.instructions");
    else if (row.timerMinutes && !(Number(row.timerMinutes) > 0)) errors[row.key] = t("editor.errors.timer");
  });
  return errors;
}

const ingredientInputs = (rows: IngredientRow[]) =>
  rows.map((row) => ({ ingredient_id: row.ingredient_id, quantity: row.quantity, unit_id: row.unit_id, notes: row.notes.trim() || null }));
const equipmentInputs = (rows: EquipmentRow[]) => rows.map((row) => ({ equipment_id: row.equipment_id, notes: row.notes.trim() || null }));
const stepInputs = (rows: StepRow[]): RecipeStepInput[] =>
  rows.map((row) => ({
    // Keeping the id keeps the step's photo (§8).
    id: row.id ?? null,
    instructions: row.instructions.trim(),
    title: row.title.trim() || null,
    timer_seconds: row.timerMinutes ? Math.round(Number(row.timerMinutes) * 60) : null,
  }));

function move<T>(list: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= list.length) return list;
  const next = [...list];
  [next[index], next[target]] = [next[target], next[index]];
  return next;
}

function RowControls({ index, length, onMove, onRemove }: { index: number; length: number; onMove: (delta: number) => void; onRemove: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex shrink-0 items-center">
      <IconButton icon="arrow_upward" label={t("editor.moveUp")} disabled={index === 0} onClick={() => onMove(-1)} className="h-8 w-8" />
      <IconButton icon="arrow_downward" label={t("editor.moveDown")} disabled={index === length - 1} onClick={() => onMove(1)} className="h-8 w-8" />
      <IconButton icon="delete" label={t("common.delete")} onClick={onRemove} className="h-8 w-8 text-error" />
    </div>
  );
}

// --- Sections ---------------------------------------------------------------------------

function BasicsSection({
  basics,
  onChange,
  errors,
  isPersonalization,
}: {
  basics: RecipeBasics;
  onChange: (basics: RecipeBasics) => void;
  errors: Errors;
  isPersonalization: boolean;
}) {
  const { t } = useTranslation();
  const categories = useRecipeCategories();
  const difficulties = useDifficulties();
  const set = <K extends keyof RecipeBasics>(key: K, value: RecipeBasics[K]) => onChange({ ...basics, [key]: value });
  const int = (value: string) => (value === "" ? null : Math.floor(Number(value)));
  return (
    <div className="flex flex-col gap-md">
      <Field label={t("editor.title")} error={errors.title}>
        <Input value={basics.title} maxLength={200} onChange={(e) => set("title", e.target.value)} />
      </Field>
      <Field label={t("editor.description")}>
        <textarea rows={4} value={basics.description ?? ""} onChange={(e) => set("description", e.target.value || null)} className={inputClass} />
      </Field>
      <div className="grid gap-md sm:grid-cols-2">
        <Field label={t("recipe.category")}>
          <select value={basics.category_id ?? ""} onChange={(e) => set("category_id", e.target.value || null)} className={inputClass}>
            <option value="">—</option>
            {categories.data?.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("recipe.difficulty")}>
          <select value={basics.difficulty_id ?? ""} onChange={(e) => set("difficulty_id", e.target.value || null)} className={inputClass}>
            <option value="">—</option>
            {difficulties.data?.map((difficulty) => (
              <option key={difficulty.id} value={difficulty.id}>
                {difficulty.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("editor.prepMinutes")} error={errors.prep_time_minutes}>
          <Input type="number" min={1} value={basics.prep_time_minutes ?? ""} onChange={(e) => set("prep_time_minutes", int(e.target.value))} />
        </Field>
        <Field label={t("recipe.servings")} error={errors.servings} hint={t("editor.servingsHint")}>
          <Input type="number" min={1} value={basics.servings ?? ""} onChange={(e) => set("servings", int(e.target.value))} />
        </Field>
      </div>
      <Field label={t("editor.videoUrl")} error={errors.video_url} hint={t("editor.videoHint")}>
        <Input type="url" placeholder="https://" value={basics.video_url ?? ""} onChange={(e) => set("video_url", e.target.value.trim() || null)} />
      </Field>
      {isPersonalization ? (
        <p className="flex items-center gap-xs rounded bg-surface-container-low p-sm text-label-md text-on-surface-variant">
          <Icon name="lock" className="text-[18px]" /> {t("editor.personalizationPrivate")}
        </p>
      ) : (
        <div
          className={`flex items-center justify-between gap-md rounded-xl border-2 p-sm transition-colors ${
            basics.is_public ? "border-tertiary/40 bg-tertiary-fixed/40" : "border-outline-variant/60 bg-surface-container-low"
          }`}
        >
          <span className="flex items-center gap-sm">
            <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${basics.is_public ? "bg-tertiary text-on-tertiary" : "bg-surface-container-high text-outline"}`}>
              <Icon name={basics.is_public ? "public" : "lock"} className="text-[20px]" />
            </span>
            <span>
              <span className="block text-label-md font-semibold">{basics.is_public ? t("editor.public") : t("editor.private")}</span>
              <span className="text-label-sm font-normal text-on-surface-variant">{basics.is_public ? t("editor.publicHint") : t("editor.privateHint")}</span>
            </span>
          </span>
          <Switch checked={basics.is_public} onChange={(value) => set("is_public", value)} label={t("editor.public")} />
        </div>
      )}
    </div>
  );
}

function IngredientsSection({ rows, onChange, errors }: { rows: IngredientRow[]; onChange: (rows: IngredientRow[]) => void; errors: Errors }) {
  const { t } = useTranslation();
  const units = useUnits();
  const update = (key: string, changes: Partial<IngredientRow>) => onChange(rows.map((row) => (row.key === key ? { ...row, ...changes } : row)));
  return (
    <div className="flex flex-col gap-sm">
      {/* The same ingredient may appear twice (dough + dusting): no exclusion here. */}
      <IngredientPicker
        allowCreate
        placeholder={t("editor.addIngredient")}
        onPick={(ingredient) =>
          onChange([...rows, { key: newKey(), ingredient_id: ingredient.id, name: ingredient.name, quantity: "", unit_id: "", notes: "" }])
        }
      />
      {rows.length === 0 && <p className="text-label-md text-on-surface-variant">{t("editor.noIngredients")}</p>}
      {rows.map((row, index) => (
        <Card key={row.key} className={`flex flex-col gap-xs p-sm ${errors[row.key] ? "ring-1 ring-error" : ""}`}>
          <div className="flex items-center gap-xs">
            <span className="flex-1 text-label-md font-semibold">
              {index + 1}. {row.name}
            </span>
            <RowControls index={index} length={rows.length} onMove={(delta) => onChange(move(rows, index, delta))} onRemove={() => onChange(rows.filter((r) => r.key !== row.key))} />
          </div>
          <div className="grid grid-cols-[100px_1fr] gap-xs sm:grid-cols-[100px_160px_1fr]">
            <Input type="number" min="0" step="any" inputMode="decimal" aria-label={t("pantry.quantity")} placeholder={t("pantry.quantity")} value={row.quantity} onChange={(e) => update(row.key, { quantity: e.target.value })} />
            <select aria-label={t("pantry.unit")} value={row.unit_id} onChange={(e) => update(row.key, { unit_id: e.target.value })} className={inputClass}>
              <option value="">{t("pantry.unit")}</option>
              {units.data?.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unit.name}
                </option>
              ))}
            </select>
            <Input className="col-span-2 sm:col-span-1" maxLength={500} placeholder={t("editor.notesPlaceholder")} value={row.notes} onChange={(e) => update(row.key, { notes: e.target.value })} />
          </div>
          {errors[row.key] && <span className="text-label-sm font-normal text-error">{errors[row.key]}</span>}
        </Card>
      ))}
    </div>
  );
}

function EquipmentSection({ rows, onChange }: { rows: EquipmentRow[]; onChange: (rows: EquipmentRow[]) => void }) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-sm">
      {/* The same equipment cannot be repeated: picked ones are excluded. */}
      <EquipmentPicker
        allowCreateAs="utensilio"
        placeholder={t("editor.addEquipment")}
        excludeIds={rows.map((row) => row.equipment_id)}
        onPick={(equipment) => onChange([...rows, { key: newKey(), equipment_id: equipment.id, name: equipment.name, notes: "" }])}
      />
      {rows.length === 0 && <p className="text-label-md text-on-surface-variant">{t("editor.noEquipment")}</p>}
      {rows.map((row, index) => (
        <Card key={row.key} className="flex items-center gap-sm p-sm">
          <EquipmentIcon name={row.name} className="text-[22px] text-secondary" />
          <span className="w-40 shrink-0 text-label-md font-semibold">{row.name}</span>
          <Input maxLength={500} placeholder={t("editor.notesPlaceholder")} value={row.notes} onChange={(e) => onChange(rows.map((r) => (r.key === row.key ? { ...r, notes: e.target.value } : r)))} />
          <RowControls index={index} length={rows.length} onMove={(delta) => onChange(move(rows, index, delta))} onRemove={() => onChange(rows.filter((r) => r.key !== row.key))} />
        </Card>
      ))}
    </div>
  );
}

/**
 * The photo of ONE step, shown inside that step's card so the link is obvious.
 * Saved immediately (its own endpoint); the step must exist (have an id) first.
 */
function StepPhotoSlot({ recipeId, stepId, photo }: { recipeId: string; stepId: string; photo: RecipePhoto | null }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] }),
    onError: (error) => toast(errorMessage(error), "error"),
  });

  if (photo)
    return (
      <div className="flex items-center gap-sm rounded-lg bg-surface-container-low p-xs">
        <img src={photo.photo_url} alt="" className="h-16 w-16 rounded object-cover" />
        <span className="flex-1 text-label-md text-tertiary">
          <Icon name="check_circle" className="mr-xs align-middle text-[16px]" />
          {t("editor.stepHasPhoto")}
        </span>
        {/* One photo per step (409 otherwise): replacing = delete, then add. */}
        <Button variant="ghost" icon="delete" className="px-sm py-xs text-error" loading={run.isPending} onClick={() => run.mutate(() => recipesApi.removePhoto(recipeId, photo.id))}>
          {t("editor.removePhoto")}
        </Button>
      </div>
    );

  return (
    <div className="flex items-center gap-sm rounded-lg border border-dashed border-outline-variant p-xs">
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded bg-surface-container-high text-outline">
        <Icon name="add_photo_alternate" className="text-[22px]" />
      </span>
      <span className="flex-1 text-label-md text-on-surface-variant">{t("editor.stepPhotoHint")}</span>
      <ImageUploadButton
        purpose="recipe"
        className="shrink-0 px-sm py-xs"
        onUploaded={(url) =>
          run.mutateAsync(() => recipesApi.addPhoto(recipeId, { photo_type: "step", photo_url: url, step_id: stepId }))
        }
      />
    </div>
  );
}

function StepsSection({
  rows,
  onChange,
  errors,
  recipe,
}: {
  rows: StepRow[];
  onChange: (rows: StepRow[]) => void;
  errors: Errors;
  /** Present when editing: steps that are saved can get their photo right here. */
  recipe?: RecipeDetail;
}) {
  const { t } = useTranslation();
  const [confirmRemove, setConfirmRemove] = useState<StepRow | null>(null);
  const update = (key: string, changes: Partial<StepRow>) => onChange(rows.map((row) => (row.key === key ? { ...row, ...changes } : row)));
  const remove = (row: StepRow) => onChange(rows.filter((r) => r.key !== row.key));
  const photoOf = (row: StepRow) => recipe?.steps.find((step) => step.id === row.id)?.photo ?? null;
  return (
    <div className="flex flex-col gap-sm">
      {!recipe && (
        <p className="flex items-start gap-xs rounded bg-secondary-container/50 p-sm text-label-md">
          <Icon name="photo_camera" className="text-[18px]" /> {t("editor.stepPhotosLater")}
        </p>
      )}
      {rows.map((row, index) => (
        <Card key={row.key} className={`flex flex-col gap-xs p-sm ${errors[row.key] ? "ring-1 ring-error" : ""}`}>
          <div className="flex items-center gap-xs">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-container text-label-md text-on-primary">{index + 1}</span>
            <Input className="flex-1" maxLength={200} placeholder={t("editor.stepTitle")} value={row.title} onChange={(e) => update(row.key, { title: e.target.value })} />
            {/* A step that is not sent is deleted along with its photo: ask first (§8). */}
            <RowControls index={index} length={rows.length} onMove={(delta) => onChange(move(rows, index, delta))} onRemove={() => (photoOf(row) || row.hasPhoto ? setConfirmRemove(row) : remove(row))} />
          </div>
          <textarea rows={3} placeholder={t("editor.instructions")} value={row.instructions} onChange={(e) => update(row.key, { instructions: e.target.value })} className={inputClass} />
          <label className="flex items-center gap-xs text-label-md text-on-surface-variant">
            <Icon name="timer" className="text-[18px]" /> {t("editor.timer")}
            <span className="w-24">
              <Input type="number" min="0" step="any" value={row.timerMinutes} onChange={(e) => update(row.key, { timerMinutes: e.target.value })} />
            </span>
            {t("editor.minutes")}
          </label>
          {recipe &&
            (row.id ? (
              <StepPhotoSlot recipeId={recipe.id} stepId={row.id} photo={photoOf(row)} />
            ) : (
              <p className="flex items-center gap-xs text-label-sm font-normal text-on-surface-variant">
                <Icon name="photo_camera" className="text-[16px]" /> {t("editor.saveStepForPhoto")}
              </p>
            ))}
          {errors[row.key] && <span className="text-label-sm font-normal text-error">{errors[row.key]}</span>}
        </Card>
      ))}
      <Button variant="secondary" icon="add" onClick={() => onChange([...rows, { key: newKey(), title: "", instructions: "", timerMinutes: "", hasPhoto: false }])}>
        {t("editor.addStep")}
      </Button>
      <Modal
        open={!!confirmRemove}
        onClose={() => setConfirmRemove(null)}
        title={t("editor.removeStepTitle")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmRemove(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (confirmRemove) remove(confirmRemove);
                setConfirmRemove(null);
              }}
            >
              {t("common.delete")}
            </Button>
          </>
        }
      >
        <p>{t("editor.removeStepText")}</p>
      </Modal>
    </div>
  );
}

function TagsSection({ selected, onChange }: { selected: string[]; onChange: (ids: string[]) => void }) {
  const { t } = useTranslation();
  const tags = useTags();
  const groups = [...new Set(tags.data?.map((tag) => tag.group))];
  return (
    <div className="flex flex-col gap-md">
      <p className="text-label-md text-on-surface-variant">{t("editor.tagsHint", { count: selected.length, max: MAX_TAGS })}</p>
      {groups.map((group) => {
        const list = tags.data?.filter((tag) => tag.group === group) ?? [];
        return (
          <div key={group}>
            <h3 className="mb-xs text-label-sm uppercase text-on-surface-variant">{list[0]?.group_name}</h3>
            <div className="flex flex-wrap gap-xs">
              {list.map((tag) => {
                const on = selected.includes(tag.id);
                return (
                  <Chip
                    key={tag.id}
                    active={on}
                    onClick={() => onChange(on ? selected.filter((id) => id !== tag.id) : selected.length < MAX_TAGS ? [...selected, tag.id] : selected)}
                  >
                    {tag.name}
                  </Chip>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PhotosSection({ recipe }: { recipe: RecipeDetail }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["recipe", recipe.id] });
  const run = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
    onSuccess: refresh,
    onError: (error) => toast(errorMessage(error), "error"),
  });
  const covers = recipe.cover_photos;

  return (
    <div className="flex flex-col gap-md">
      {/* No uploads yet (§17): photos are registered by URL. */}
      <p className="flex items-start gap-xs rounded bg-secondary-container/50 p-sm text-label-md">
        <Icon name="info" className="text-[18px]" /> {t("editor.photosHint")}
      </p>
      <section>
        <h3 className="mb-xs text-title-lg">
          {t("editor.covers")} ({covers.length}/{MAX_COVERS})
        </h3>
        <div className="mb-sm grid grid-cols-3 gap-sm">
          {covers.map((photo, index) => (
            <div key={photo.id} className="relative overflow-hidden rounded-lg">
              <img src={photo.photo_url} alt="" className="aspect-square w-full object-cover" />
              <div className="absolute inset-x-0 bottom-0 flex justify-center gap-xs bg-inverse-surface/60 p-xs">
                <IconButton
                  icon="arrow_back"
                  label={t("editor.moveUp")}
                  disabled={index === 0 || run.isPending}
                  className="h-8 w-8 text-inverse-on-surface"
                  // Reorder sends every cover, each once.
                  onClick={() => run.mutate(() => recipesApi.reorderCovers(recipe.id, move(covers, index, -1).map((p) => p.id)))}
                />
                <IconButton icon="delete" label={t("common.delete")} disabled={run.isPending} className="h-8 w-8 text-inverse-on-surface" onClick={() => run.mutate(() => recipesApi.removePhoto(recipe.id, photo.id))} />
                <IconButton
                  icon="arrow_forward"
                  label={t("editor.moveDown")}
                  disabled={index === covers.length - 1 || run.isPending}
                  className="h-8 w-8 text-inverse-on-surface"
                  onClick={() => run.mutate(() => recipesApi.reorderCovers(recipe.id, move(covers, index, 1).map((p) => p.id)))}
                />
              </div>
            </div>
          ))}
        </div>
        {covers.length < MAX_COVERS ? (
          <ImageUploadButton
            purpose="recipe"
            label={t("editor.addCover")}
            onUploaded={(url) => run.mutateAsync(() => recipesApi.addPhoto(recipe.id, { photo_type: "cover", photo_url: url }))}
          />
        ) : (
          <p className="text-label-md text-on-surface-variant">{t("editor.coversFull")}</p>
        )}
      </section>
      <section className="flex flex-col gap-sm">
        <h3 className="text-title-lg">{t("editor.stepPhotos")}</h3>
        <p className="text-label-md text-on-surface-variant">{t("editor.stepPhotosHint")}</p>
        {recipe.steps.map((step) => (
          <Card key={step.id} className="flex flex-col gap-xs p-sm">
            <div className="flex items-start gap-xs">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-container text-label-md text-on-primary">{step.step_number}</span>
              <div className="min-w-0">
                <p className="text-label-md font-semibold">{step.title || t("cook.step", { n: step.step_number })}</p>
                <p className="line-clamp-1 text-label-sm font-normal text-on-surface-variant">{step.instructions}</p>
              </div>
            </div>
            <StepPhotoSlot recipeId={recipe.id} stepId={step.id} photo={step.photo} />
          </Card>
        ))}
        {recipe.steps.length === 0 && <p className="text-label-md text-on-surface-variant">{t("recipe.noSteps")}</p>}
      </section>
    </div>
  );
}

// --- Page -------------------------------------------------------------------------------

type Section = "basics" | "ingredients" | "equipment" | "steps" | "tags" | "photos";
const SECTIONS: { key: Section; icon: string }[] = [
  { key: "basics", icon: "edit_note" },
  { key: "ingredients", icon: "grocery" },
  { key: "equipment", icon: "kitchen" },
  { key: "steps", icon: "format_list_numbered" },
  { key: "tags", icon: "sell" },
  { key: "photos", icon: "photo_library" },
];

function SectionShell({ title, children, footer }: { title: string; children: ReactNode; footer: ReactNode }) {
  return (
    <Card className="p-md">
      <h2 className="mb-md text-headline-md">{title}</h2>
      {children}
      <div className="mt-md flex flex-wrap justify-end gap-sm border-t border-outline-variant/50 pt-md">{footer}</div>
    </Card>
  );
}

export function RecipeEditorPage() {
  const { id } = useParams();
  const editing = !!id;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const section = (params.get("section") as Section) ?? "basics";
  const setSection = (next: Section) => setParams({ section: next }, { replace: true });
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [errors, setErrors] = useState<Errors>({});

  const recipe = useQuery({ queryKey: ["recipe", id, "original"], queryFn: () => recipesApi.get(id!, "original"), enabled: editing });
  // Load the draft once: later responses only refresh the section that was saved,
  // so unsaved edits in other sections survive.
  const loaded = useRef(false);
  useEffect(() => {
    if (recipe.data && !loaded.current) {
      loaded.current = true;
      setDraft(draftFrom(recipe.data));
    }
  }, [recipe.data]);

  const afterSave = (detail: RecipeDetail) => {
    queryClient.setQueryData(["recipe", detail.id, "original"], detail);
    void queryClient.invalidateQueries({ queryKey: ["recipe", detail.id] });
    void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    void queryClient.invalidateQueries({ queryKey: ["recipes"] });
  };
  const failed = (error: unknown) => {
    // A 404 names the unknown id (ingredient, unit, tag...); field errors map to inputs.
    if (error instanceof ApiError && Object.keys(error.fieldErrors).length) setErrors(error.fieldErrors);
    toast(errorMessage(error), "error");
  };

  const create = useMutation({
    mutationFn: () =>
      recipesApi.create({
        ...draft.basics,
        title: draft.basics.title.trim(),
        ingredients: ingredientInputs(draft.ingredients),
        equipment: equipmentInputs(draft.equipment),
        tag_ids: draft.tagIds,
        steps: stepInputs(draft.steps.filter((step) => step.instructions.trim())),
      }),
    onSuccess: (detail) => {
      afterSave(detail);
      toast(t("editor.created"));
      // Photos need the recipe (and its step ids) to exist: continue in edit mode.
      navigate(`/recipes/${detail.id}/edit?section=photos`, { replace: true });
    },
    onError: failed,
  });

  const save = useMutation({
    mutationFn: async (which: Section): Promise<RecipeDetail> => {
      const original = recipe.data!;
      switch (which) {
        case "basics": {
          // PATCH only what changed; null clears a field (§8).
          const before = draftFrom(original).basics;
          const changes = Object.fromEntries(
            Object.entries(draft.basics).filter(([key, value]) => before[key as keyof RecipeBasics] !== value),
          ) as Partial<RecipeBasics>;
          if (changes.title !== undefined) changes.title = changes.title.trim();
          return Object.keys(changes).length ? recipesApi.update(original.id, changes) : original;
        }
        case "ingredients":
          return recipesApi.replaceIngredients(original.id, ingredientInputs(draft.ingredients));
        case "equipment":
          return recipesApi.replaceEquipment(original.id, equipmentInputs(draft.equipment));
        case "steps":
          return recipesApi.replaceSteps(original.id, stepInputs(draft.steps));
        case "tags":
          return recipesApi.replaceTags(original.id, draft.tagIds);
        default:
          return original;
      }
    },
    onSuccess: (detail, which) => {
      afterSave(detail);
      // New steps get their ids here; without them a second save would recreate them.
      const fresh = draftFrom(detail);
      const field = which === "tags" ? "tagIds" : which;
      if (field !== "photos") setDraft((current) => ({ ...current, [field]: fresh[field] }));
      toast(t("editor.saved"));
    },
    onError: failed,
  });

  const validate = (which: Section): boolean => {
    const found =
      which === "basics"
        ? validateBasics(draft.basics, t)
        : which === "ingredients"
          ? validateIngredients(draft.ingredients, t)
          : which === "steps"
            ? validateSteps(editing ? draft.steps : draft.steps.filter((s) => s.instructions.trim() || s.title.trim()), t)
            : {};
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  if (editing && recipe.isLoading) return <Skeleton className="h-[60vh]" />;
  if (editing && recipe.isError) return <ErrorState message={errorMessage(recipe.error)} onRetry={() => void recipe.refetch()} />;
  if (editing && recipe.data && !recipe.data.is_owner)
    return <EmptyState icon="lock" title={t("editor.notOwner")} action={<Link to={`/recipes/${id}`}><Button>{t("explore.viewRecipe")}</Button></Link>} />;

  const isPersonalization = recipe.data?.is_personalization ?? false;
  const sections = editing ? SECTIONS : SECTIONS.filter((s) => s.key !== "photos");
  const index = sections.findIndex((s) => s.key === section);
  const last = index === sections.length - 1;

  const body = {
    basics: <BasicsSection basics={draft.basics} onChange={(basics) => setDraft({ ...draft, basics })} errors={errors} isPersonalization={isPersonalization} />,
    ingredients: <IngredientsSection rows={draft.ingredients} onChange={(ingredients) => setDraft({ ...draft, ingredients })} errors={errors} />,
    equipment: <EquipmentSection rows={draft.equipment} onChange={(equipment) => setDraft({ ...draft, equipment })} />,
    steps: <StepsSection rows={draft.steps} onChange={(steps) => setDraft({ ...draft, steps })} errors={errors} recipe={recipe.data} />,
    tags: <TagsSection selected={draft.tagIds} onChange={(tagIds) => setDraft({ ...draft, tagIds })} />,
    photos: recipe.data ? <PhotosSection recipe={recipe.data} /> : null,
  }[section];

  const footer = editing ? (
    <>
      <Link to={`/recipes/${id}`}>
        <Button variant="ghost">{t("editor.viewRecipe")}</Button>
      </Link>
      {section !== "photos" && (
        <Button icon="save" loading={save.isPending} onClick={() => validate(section) && save.mutate(section)}>
          {t("editor.saveSection")}
        </Button>
      )}
    </>
  ) : (
    <>
      {index > 0 && (
        <Button variant="ghost" icon="arrow_back" onClick={() => setSection(sections[index - 1].key)}>
          {t("common.previous")}
        </Button>
      )}
      {last ? (
        <Button
          icon="check"
          loading={create.isPending}
          onClick={() => {
            const steps = draft.steps.filter((s) => s.instructions.trim() || s.title.trim());
            for (const [key, check] of [
              ["basics", () => validateBasics(draft.basics, t)],
              ["ingredients", () => validateIngredients(draft.ingredients, t)],
              ["steps", () => validateSteps(steps, t)],
            ] as const) {
              const found = check();
              if (Object.keys(found).length) {
                setErrors(found);
                setSection(key);
                return;
              }
            }
            create.mutate();
          }}
        >
          {t("editor.create")}
        </Button>
      ) : (
        <Button icon="arrow_forward" className="flex-row-reverse" onClick={() => validate(section) && setSection(sections[index + 1].key)}>
          {t("common.next")}
        </Button>
      )}
    </>
  );

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title={editing ? t("editor.editTitle") : t("editor.newTitle")}
        subtitle={editing ? recipe.data?.title : t("editor.newSubtitle")}
      />
      <nav className="-mx-margin-mobile mb-md flex gap-xs overflow-x-auto px-margin-mobile pb-xs lg:mx-0 lg:px-0">
        {sections.map((item, i) => (
          <button
            key={item.key}
            type="button"
            onClick={() => (editing || i <= index ? setSection(item.key) : undefined)}
            aria-current={section === item.key ? "step" : undefined}
            className={`flex shrink-0 items-center gap-xs rounded-full px-sm py-xs text-label-md transition-colors ${
              section === item.key
                ? "bg-primary text-on-primary"
                : editing || i < index
                  ? "bg-surface-container-high text-on-surface"
                  : "bg-surface-container-low text-on-surface-variant opacity-60"
            }`}
          >
            <Icon name={item.icon} className="text-[18px]" />
            {!editing && `${i + 1}. `}
            {t(`editor.sections.${item.key}`)}
          </button>
        ))}
      </nav>
      <SectionShell title={t(`editor.sections.${section}`)} footer={footer}>
        {body}
      </SectionShell>
    </div>
  );
}
