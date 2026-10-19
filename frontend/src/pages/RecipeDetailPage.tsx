import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { recipesApi } from "../api/endpoints";
import { useErrorMessage, useFavoriteStatus } from "../api/queries";
import type { DisplayUnitSystem, Language, RecipeDetail } from "../api/types";
import { useUser } from "../auth/AuthContext";
import { CookButton } from "../components/CookButton";
import { FavoriteButton } from "../components/RecipeCard";
import { useToast } from "../components/Toast";
import {
  Button,
  Card,
  Chip,
  Cover,
  EmptyState,
  ErrorState,
  Field,
  Icon,
  IconButton,
  Input,
  Modal,
  Segmented,
  Skeleton,
} from "../components/ui";
import { formatMeasure, isFractionalCount, scale } from "../lib/quantities";
import { diffRecipes, isEmptyDiff } from "../lib/recipeDiff";
import { formatMinutes, formatSeconds } from "../lib/time";
import { embedUrl } from "../lib/video";
import { EquipmentIcon } from "../lib/equipment";

export function UnitSystemToggle({ value, onChange }: { value: DisplayUnitSystem; onChange: (value: DisplayUnitSystem) => void }) {
  const { t } = useTranslation();
  return (
    <Segmented
      label={t("units.system")}
      value={value}
      onChange={onChange}
      options={[
        { value: "metric", label: t("units.metric") },
        { value: "us", label: t("units.us") },
      ]}
    />
  );
}

function Carousel({ recipe, onVideo }: { recipe: RecipeDetail; onVideo: () => void }) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const photos = recipe.cover_photos;
  const current = photos[index];
  return (
    <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-surface-container-high shadow-card lg:aspect-[16/10]">
      <Cover url={current?.photo_url} alt={recipe.title} className="h-full w-full" />
      {recipe.video_url && (
        <button
          type="button"
          onClick={onVideo}
          className="absolute right-sm top-sm flex items-center gap-xs rounded-full bg-inverse-surface/80 px-sm py-xs text-label-md text-inverse-on-surface backdrop-blur"
        >
          <Icon name="play_circle" filled className="text-[20px]" /> {t("recipe.watchVideo")}
        </button>
      )}
      {photos.length > 1 && (
        <>
          <IconButton
            icon="chevron_left"
            label={t("common.previous")}
            onClick={() => setIndex((index - 1 + photos.length) % photos.length)}
            className="absolute left-sm top-1/2 -translate-y-1/2 bg-surface/80"
          />
          <IconButton
            icon="chevron_right"
            label={t("common.next")}
            onClick={() => setIndex((index + 1) % photos.length)}
            className="absolute right-sm top-1/2 -translate-y-1/2 bg-surface/80"
          />
          <div className="absolute bottom-sm left-1/2 flex -translate-x-1/2 gap-xs">
            {photos.map((photo, i) => (
              <button
                key={photo.id}
                type="button"
                aria-label={`${i + 1} / ${photos.length}`}
                onClick={() => setIndex(i)}
                className={`h-2 rounded-full transition-all ${i === index ? "w-6 bg-surface" : "w-2 bg-surface/60"}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function VideoModal({ url, open, onClose }: { url: string; open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const embed = embedUrl(url);
  return (
    <Modal open={open} onClose={onClose} title={t("recipe.video")}>
      {embed ? (
        <iframe
          src={embed}
          title={t("recipe.video")}
          className="aspect-video w-full rounded-lg"
          allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <a href={url} target="_blank" rel="noreferrer" className="flex items-center gap-xs text-primary underline">
          <Icon name="open_in_new" /> {url}
        </a>
      )}
    </Modal>
  );
}

function CompareModal({ recipe, open, onClose }: { recipe: RecipeDetail; open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const original = useQuery({
    queryKey: ["recipe", recipe.source_recipe_id, "original"],
    queryFn: () => recipesApi.get(recipe.source_recipe_id!, "original"),
    enabled: open && !!recipe.source_recipe_id,
  });
  const diff = original.data ? diffRecipes(original.data, recipe) : null;
  const kindStyle = { added: "text-tertiary", removed: "text-error line-through", changed: "text-primary" };
  return (
    <Modal open={open} onClose={onClose} title={t("compare.title")}>
      {original.isLoading && <Skeleton className="h-40" />}
      {original.isError && <ErrorState message={errorMessage(original.error)} />}
      {diff && isEmptyDiff(diff) && <p className="text-body-md text-on-surface-variant">{t("compare.noDifferences")}</p>}
      {diff && !isEmptyDiff(diff) && (
        <div className="flex flex-col gap-md text-body-md">
          <p className="text-label-md text-on-surface-variant">
            {t("compare.subtitle", { original: original.data?.title })}
          </p>
          {!!diff.fields.length && (
            <section>
              <h3 className="mb-xs text-label-sm uppercase text-on-surface-variant">{t("compare.basics")}</h3>
              {diff.fields.map((change) => (
                <p key={change.field}>
                  <strong>{t(`compare.fields.${change.field}`)}:</strong> {change.original} → <span className="text-primary">{change.mine}</span>
                </p>
              ))}
            </section>
          )}
          {!!diff.ingredients.length && (
            <section>
              <h3 className="mb-xs text-label-sm uppercase text-on-surface-variant">{t("recipe.ingredients")}</h3>
              <table className="w-full text-left text-label-md">
                <thead className="text-on-surface-variant">
                  <tr>
                    <th className="py-xs font-medium">{t("compare.ingredient")}</th>
                    <th className="py-xs font-medium">{t("compare.original")}</th>
                    <th className="py-xs font-medium">{t("compare.mine")}</th>
                  </tr>
                </thead>
                <tbody>
                  {diff.ingredients.map((change) => (
                    <tr key={change.name + change.kind} className="border-t border-outline-variant/40">
                      <td className={`py-xs ${kindStyle[change.kind]}`}>{change.name}</td>
                      <td className="py-xs">{change.original ?? "—"}</td>
                      <td className="py-xs">{change.mine ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
          {!!diff.steps.length && (
            <section className="flex flex-col gap-sm">
              <h3 className="text-label-sm uppercase text-on-surface-variant">{t("recipe.steps")}</h3>
              {diff.steps.map((change) => (
                <div key={change.stepNumber} className="rounded bg-surface-container-low p-sm text-label-md font-normal">
                  <p className={`mb-xs font-semibold ${kindStyle[change.kind]}`}>
                    {t("compare.step", { n: change.stepNumber })} · {t(`compare.kinds.${change.kind}`)}
                  </p>
                  {change.original && <p className="text-on-surface-variant">− {change.original}</p>}
                  {change.mine && <p>+ {change.mine}</p>}
                </div>
              ))}
            </section>
          )}
        </div>
      )}
    </Modal>
  );
}

function PersonalizeModal({ recipe, open, onClose }: { recipe: RecipeDetail; open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const personalize = useMutation({
    mutationFn: () => recipesApi.personalize(recipe.id, title.trim() || undefined),
    onSuccess: (copy) => {
      void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      toast(t("recipe.copyCreated"));
      // Straight to editing the copy (§9).
      navigate(`/recipes/${copy.id}/edit`);
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("recipe.personalizeTitle")}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button icon="fork_right" loading={personalize.isPending} onClick={() => personalize.mutate()}>
            {t("recipe.personalize")}
          </Button>
        </>
      }
    >
      <p className="mb-md text-body-md text-on-surface-variant">{t("recipe.personalizeText")}</p>
      <Field label={t("recipe.versionTitle")} hint={t("recipe.versionTitleHint")}>
        <Input value={title} maxLength={200} placeholder={recipe.title} onChange={(e) => setTitle(e.target.value)} />
      </Field>
    </Modal>
  );
}

function Ingredients({ recipe, servings, language }: { recipe: RecipeDetail; servings: number; language: Language }) {
  const { t } = useTranslation();
  // Local only: the API does not store mise-en-place checks.
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const toggle = (id: string) =>
    setChecked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const all = checked.size === recipe.ingredients.length;
  return (
    <section>
      <div className="mb-sm flex items-center justify-between gap-sm">
        <h2 className="flex items-center gap-sm text-headline-md">
          {t("recipe.ingredients")}
          <span className="rounded-full bg-secondary-container px-sm py-[2px] text-label-sm text-on-secondary-container">
            {t("recipe.ready", { done: checked.size, total: recipe.ingredients.length })}
          </span>
        </h2>
        <button
          type="button"
          onClick={() => setChecked(all ? new Set() : new Set(recipe.ingredients.map((line) => line.id)))}
          className="text-label-md text-primary"
        >
          {all ? t("recipe.uncheckAll") : t("recipe.checkAll")}
        </button>
      </div>
      <ul className="flex flex-col gap-xs">
        {recipe.ingredients.map((line) => {
          // Scale first, then show in the unit the API already converted to (§6).
          const quantity = scale(line.display_quantity, recipe.servings, servings);
          const unit = line.display_unit_abbreviation;
          const done = checked.has(line.id);
          return (
            <li key={line.id}>
              <label className={`flex cursor-pointer items-start gap-sm rounded-lg bg-surface-container-lowest p-sm shadow-card transition-opacity ${done ? "opacity-60" : ""}`}>
                <input type="checkbox" checked={done} onChange={() => toggle(line.id)} className="mt-1 h-5 w-5 accent-primary" />
                <span className="flex-1">
                  <span className={`text-body-md ${done ? "line-through" : ""}`}>
                    <strong className="text-primary">
                      {formatMeasure(quantity, unit, language)}
                    </strong>{" "}
                    {line.ingredient_name}
                  </span>
                  {line.converted && (
                    <span className="ml-xs text-label-md text-on-surface-variant">
                      · {formatMeasure(scale(line.quantity, recipe.servings, servings), line.unit_abbreviation, language)}
                    </span>
                  )}
                  {line.notes && <span className="block text-label-md font-normal italic text-on-surface-variant">{line.notes}</span>}
                  {isFractionalCount(quantity, unit) && (
                    <span className="block text-label-sm font-normal text-secondary">{t("recipe.fractionalCount")}</span>
                  )}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function ScalePanel({ base, servings, onChange }: { base: number; servings: number; onChange: (value: number) => void }) {
  const { t } = useTranslation();
  return (
    <Card className="p-sm">
      <div className="flex items-center justify-between gap-sm">
        <div>
          <p className="text-label-sm uppercase text-primary">{t("recipe.scale")}</p>
          <p className="text-label-md text-on-surface-variant">{t("recipe.baseServings", { count: base })}</p>
        </div>
        <div className="flex items-center gap-xs">
          <IconButton icon="remove" label={t("recipe.fewer")} disabled={servings <= 1} onClick={() => onChange(servings - 1)} className="bg-surface-container-high" />
          <span className="w-12 text-center text-title-lg" aria-live="polite">
            {servings}
          </span>
          <IconButton icon="add" label={t("recipe.more")} onClick={() => onChange(servings + 1)} className="bg-primary text-on-primary hover:bg-primary" />
        </div>
      </div>
      {servings !== base && (
        <button type="button" onClick={() => onChange(base)} className="mt-xs flex items-center gap-xs text-label-md text-primary">
          <Icon name="replay" className="text-[16px]" /> {t("common.reset")}
        </button>
      )}
      <p className="mt-xs flex items-start gap-xs rounded bg-surface-container-low p-xs text-label-sm font-normal text-on-surface-variant">
        <Icon name="info" className="text-[16px]" /> {t("recipe.timesDontScale")}
      </p>
    </Card>
  );
}

export function RecipeDetailPage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const user = useUser();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [unitSystem, setUnitSystem] = useState<DisplayUnitSystem>(user.preferred_unit_system);
  const [servings, setServings] = useState<number | null>(null);
  const [modal, setModal] = useState<"video" | "compare" | "personalize" | "delete" | null>(null);

  const query = useQuery({
    queryKey: ["recipe", id, unitSystem],
    queryFn: () => recipesApi.get(id, unitSystem),
    // Switching units keeps the page on screen while the new quantities load.
    placeholderData: keepPreviousData,
  });
  const recipe = query.data;
  const isOwn = recipe?.created_by_user_id === user.id;
  const favorite = useFavoriteStatus(recipe && !isOwn ? [recipe.id] : []);
  const versions = useQuery({
    queryKey: ["recipe", id, "personalizations"],
    queryFn: () => recipesApi.personalizations(id),
    enabled: !!recipe && !recipe.is_personalization,
  });
  const remove = useMutation({
    mutationFn: () => recipesApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
      void queryClient.invalidateQueries({ queryKey: ["recipes"] });
      toast(t("recipe.deleted"));
      navigate("/portfolio", { replace: true });
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });

  if (query.isLoading)
    return (
      <div className="grid gap-md lg:grid-cols-[1.5fr_1fr]">
        <Skeleton className="aspect-[4/3]" />
        <Skeleton className="h-96" />
      </div>
    );
  if (query.isError || !recipe) {
    const notFound = query.error instanceof ApiError && query.error.status === 404;
    return notFound ? (
      <EmptyState
        icon="visibility_off"
        title={t("recipe.notFound")}
        text={t("recipe.notFoundText")}
        action={<Button onClick={() => navigate("/")}>{t("nav.explore")}</Button>}
      />
    ) : (
      <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
    );
  }

  const shownServings = servings ?? recipe.servings ?? 1;
  const canPersonalize = !recipe.is_personalization;
  const share = async () => {
    const url = window.location.href;
    if (navigator.share) await navigator.share({ title: recipe.title, url }).catch(() => {});
    else {
      await navigator.clipboard.writeText(url);
      toast(t("recipe.linkCopied"));
    }
  };

  return (
    <div className="pb-[88px] lg:pb-0">
      <div className="mb-sm flex items-center justify-between gap-sm">
        <div className="flex min-w-0 items-center gap-xs text-label-md text-on-surface-variant">
          <IconButton icon="arrow_back" label={t("common.back")} onClick={() => navigate(-1)} />
          {recipe.category && (
            <Link to={`/?category_id=${recipe.category.id}`} className="truncate hover:text-primary">
              {recipe.category.name}
            </Link>
          )}
        </div>
        <div className="flex items-center gap-xs">
          {recipe.is_public && <IconButton icon="share" label={t("recipe.share")} onClick={() => void share()} />}
          <IconButton icon="print" label={t("recipe.print")} onClick={() => window.print()} className="hidden lg:inline-flex" />
          {!isOwn && <FavoriteButton recipeId={recipe.id} saved={favorite.data?.[recipe.id] ?? false} />}
        </div>
      </div>

      <div className="grid gap-lg lg:grid-cols-[1.5fr_1fr]">
        {/* DOM order top -> aside -> bottom: on mobile the ingredients come before the steps. */}
        <div className="flex flex-col gap-md lg:col-start-1">
          <Carousel recipe={recipe} onVideo={() => setModal("video")} />

          {recipe.is_personalization && (
            <div className="flex items-center justify-between gap-sm rounded-lg border border-primary/30 bg-primary-fixed/50 p-sm text-label-md">
              <span className="flex items-center gap-xs">
                <Icon name="auto_fix_high" className="text-primary" />
                {recipe.source_recipe_title ? t("recipe.yourVersionOf", { title: recipe.source_recipe_title }) : t("recipe.yourVersionOrphan")}
              </span>
              {/* A null title means the original was deleted or made private: never link it (§5). */}
              {recipe.source_recipe_title && recipe.source_recipe_id && (
                <Link to={`/recipes/${recipe.source_recipe_id}`} className="flex shrink-0 items-center gap-xs text-primary">
                  {t("recipe.viewOriginal")} <Icon name="arrow_forward" className="text-[16px]" />
                </Link>
              )}
            </div>
          )}
          {recipe.source_updated_since_personalized && recipe.source_recipe_title && (
            <div className="flex items-start gap-sm rounded-lg bg-secondary-container/60 p-sm text-label-md">
              <Icon name="sync_problem" className="text-secondary" />
              <div className="flex-1">
                <p className="font-semibold">{t("recipe.sourceChanged")}</p>
                <button type="button" onClick={() => setModal("compare")} className="mt-xs font-semibold text-primary underline">
                  {t("compare.open")}
                </button>
              </div>
            </div>
          )}

          <div>
            <div className="mb-xs flex flex-wrap gap-xs">
              {!recipe.is_public && (
                <Chip icon="lock" tone="accent">
                  {t("recipe.private")}
                </Chip>
              )}
              {recipe.tags.map((tag) => (
                <Chip key={tag.id} tone="accent">
                  {tag.name}
                </Chip>
              ))}
            </div>
            <h1 className="text-display-sm lg:text-display-lg">{recipe.title}</h1>
            {recipe.description && <p className="mt-sm whitespace-pre-line text-body-lg text-on-surface-variant">{recipe.description}</p>}
          </div>

          <div className="grid grid-cols-3 gap-sm">
            {[
              { icon: "timer", label: t("recipe.prepTime"), value: formatMinutes(recipe.prep_time_minutes) || "—" },
              { icon: "signal_cellular_alt", label: t("recipe.difficulty"), value: recipe.difficulty?.name ?? "—" },
              { icon: "restaurant", label: t("recipe.servings"), value: recipe.servings ?? "—" },
            ].map((meta) => (
              <Card key={meta.label} className="flex flex-col items-center gap-[2px] p-sm text-center">
                <Icon name={meta.icon} className="text-primary" />
                <span className="text-label-sm uppercase text-on-surface-variant">{meta.label}</span>
                <span className="text-label-md font-semibold">{meta.value}</span>
              </Card>
            ))}
          </div>
        </div>

        <aside className="flex flex-col gap-md lg:sticky lg:top-24 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:self-start">
          {recipe.servings ? <ScalePanel base={recipe.servings} servings={shownServings} onChange={setServings} /> : null}
          <div className="flex flex-wrap items-center justify-between gap-sm">
            <UnitSystemToggle value={unitSystem} onChange={setUnitSystem} />
            {query.isFetching && <Icon name="progress_activity" className="animate-spin text-primary" />}
          </div>
          {recipe.ingredients.length ? (
            <Ingredients recipe={recipe} servings={shownServings} language={language} />
          ) : (
            <p className="text-body-md text-on-surface-variant">{t("recipe.noIngredients")}</p>
          )}

          <div className="hidden flex-col gap-sm lg:flex">
            <CookButton recipeId={recipe.id} className="py-md text-body-md" />
            {canPersonalize && (
              <Button variant="secondary" icon="fork_right" onClick={() => setModal("personalize")}>
                {t("recipe.personalize")}
              </Button>
            )}
          </div>

          {recipe.is_owner && (
            <Card className="flex flex-col gap-xs p-sm">
              <p className="text-label-sm uppercase text-on-surface-variant">{t("recipe.ownerActions")}</p>
              <Link to={`/recipes/${recipe.id}/edit`}>
                <Button variant="secondary" icon="edit" className="w-full">
                  {t("common.edit")}
                </Button>
              </Link>
              <Button variant="ghost" icon="delete" className="text-error" onClick={() => setModal("delete")}>
                {t("common.delete")}
              </Button>
            </Card>
          )}

          {!!versions.data?.total && (
            <Card className="p-sm">
              <p className="mb-xs text-label-md font-semibold">{t("recipe.yourVersions", { count: versions.data.total })}</p>
              <ul className="flex flex-col gap-xs">
                {versions.data.items.map((version) => (
                  <li key={version.id}>
                    <Link to={`/recipes/${version.id}`} className="flex items-center gap-xs text-label-md text-primary">
                      <Icon name="fork_right" className="text-[16px]" /> {version.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </aside>

        <div className="flex flex-col gap-md lg:col-start-1">

          {!!recipe.equipment.length && (
            <section>
              <h2 className="mb-sm text-headline-md">{t("recipe.equipment")}</h2>
              <div className="grid grid-cols-2 gap-sm sm:grid-cols-3">
                {recipe.equipment.map((item) => (
                  <Card key={item.id} className="flex flex-col items-center gap-xs p-sm text-center">
                    <EquipmentIcon name={item.equipment_name} className="text-[30px] text-secondary" />
                    <span className="text-label-md font-semibold">{item.equipment_name}</span>
                    {item.notes && <span className="text-label-sm font-normal text-on-surface-variant">{item.notes}</span>}
                  </Card>
                ))}
              </div>
            </section>
          )}

          <section>
            <div className="mb-sm flex items-baseline justify-between">
              <h2 className="text-headline-md">{t("recipe.steps")}</h2>
              <span className="text-label-md text-on-surface-variant">{t("recipe.stepCount", { count: recipe.steps.length })}</span>
            </div>
            {recipe.steps.length === 0 ? (
              <p className="text-body-md text-on-surface-variant">{t("recipe.noSteps")}</p>
            ) : (
              <ol className="flex flex-col gap-sm">
                {recipe.steps.map((step) => (
                  <li key={step.id}>
                    <Card className="flex gap-sm p-sm">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-container text-label-md font-bold text-on-primary">
                        {step.step_number}
                      </span>
                      <div className="flex-1">
                        {step.title && <h3 className="text-title-lg">{step.title}</h3>}
                        {step.timer_seconds && (
                          <span className="my-xs inline-flex items-center gap-xs rounded-full bg-primary-fixed px-sm py-[2px] text-label-sm text-primary">
                            <Icon name="timer" className="text-[14px]" /> {formatSeconds(step.timer_seconds)}
                          </span>
                        )}
                        <p className="whitespace-pre-line text-body-md text-on-surface-variant">{step.instructions}</p>
                        {step.photo && <img src={step.photo.photo_url} alt="" loading="lazy" className="mt-sm max-h-64 rounded-lg object-cover" />}
                      </div>
                    </Card>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>

      {/* Mobile action bar, as in Stitch: Personalize + Cook. */}
      <div className="fixed inset-x-0 bottom-[92px] z-40 flex gap-sm px-margin-mobile lg:hidden">
        {canPersonalize && (
          <Button variant="secondary" icon="edit_note" className="bg-surface shadow-lift" onClick={() => setModal("personalize")}>
            {t("recipe.personalizeShort")}
          </Button>
        )}
        <CookButton recipeId={recipe.id} short className="flex-1 bg-primary-container shadow-lift" />
      </div>

      {recipe.video_url && <VideoModal url={recipe.video_url} open={modal === "video"} onClose={() => setModal(null)} />}
      <CompareModal recipe={recipe} open={modal === "compare"} onClose={() => setModal(null)} />
      <PersonalizeModal recipe={recipe} open={modal === "personalize"} onClose={() => setModal(null)} />
      <Modal
        open={modal === "delete"}
        onClose={() => setModal(null)}
        title={t("recipe.deleteTitle")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setModal(null)}>
              {t("common.cancel")}
            </Button>
            <Button variant="danger" icon="delete" loading={remove.isPending} onClick={() => remove.mutate()}>
              {t("common.delete")}
            </Button>
          </>
        }
      >
        <p className="text-body-md">{t("recipe.deleteText")}</p>
      </Modal>
    </div>
  );
}
