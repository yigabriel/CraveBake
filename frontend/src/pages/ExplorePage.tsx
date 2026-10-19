import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useInfiniteQuery, useQueries, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { catalogApi, preparationApi, recipesApi, type RecipeSearch } from "../api/endpoints";
import { useDifficulties, useErrorMessage, useFavoriteStatus, useRecipeCategories, useTags } from "../api/queries";
import type { RecipeSummary, RecipeTag } from "../api/types";
import { useUser } from "../auth/AuthContext";
import { useDebounced, IngredientPicker } from "../components/Pickers";
import { cardFromSummary, FavoriteButton, RecipeCard } from "../components/RecipeCard";
import {
  Button,
  CardGridSkeleton,
  Chip,
  Cover,
  EmptyState,
  ErrorState,
  Icon,
  inputClass,
  Modal,
  Segmented,
} from "../components/ui";
import { formatMinutes } from "../lib/time";

const PAGE_SIZE = 12;
const TIME_OPTIONS = [15, 30, 60, 120, 240];
const TAG_GROUPS = ["sabor", "dieta", "tecnica", "tiempo", "celebraciones"] as const;

/** Filters live in the URL so a search can be shared and survives "back" (§4). */
function useFilters() {
  const [params, setParams] = useSearchParams();
  const filters: RecipeSearch = {
    q: params.get("q") ?? undefined,
    category_id: params.get("category_id") ?? undefined,
    difficulty_id: params.get("difficulty_id") ?? undefined,
    max_prep_time: params.get("max_prep_time") ? Number(params.get("max_prep_time")) : undefined,
    tag_ids: params.getAll("tag_ids"),
    ingredient_ids: params.getAll("ingredient_ids"),
  };
  const update = (changes: Partial<RecipeSearch>) => {
    const next = { ...filters, ...changes };
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(next)) {
      if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
      else if (value !== undefined && value !== "") search.set(key, String(value));
    }
    setParams(search, { replace: true });
  };
  const active =
    !!filters.q ||
    !!filters.category_id ||
    !!filters.difficulty_id ||
    !!filters.max_prep_time ||
    !!filters.tag_ids?.length ||
    !!filters.ingredient_ids?.length;
  return { filters, update, active, clear: () => setParams(new URLSearchParams(), { replace: true }) };
}

function InProgressBanner() {
  const { t } = useTranslation();
  const inProgress = useQuery({
    queryKey: ["preparations", "in_progress", "banner"],
    queryFn: () => preparationApi.list({ status: "in_progress", limit: 1 }),
  });
  const current = inProgress.data?.items[0];
  if (!current) return null;
  return (
    <Link
      to={`/cook/${current.id}`}
      className="mb-md flex items-center gap-sm rounded-lg bg-tertiary-fixed p-sm text-on-tertiary-fixed-variant shadow-card transition-shadow hover:shadow-lift"
    >
      <Cover url={current.cover_photo_url} alt="" className="h-14 w-14 shrink-0 rounded" />
      <div className="min-w-0 flex-1">
        <p className="text-label-sm uppercase">{t("cook.inProgressBanner")}</p>
        <p className="truncate text-title-lg">{current.recipe_title}</p>
        <p className="text-label-md">{t("cook.progress", { done: current.completed_steps, total: current.total_steps })}</p>
      </div>
      <span className="flex items-center gap-xs rounded-full bg-tertiary px-sm py-xs text-label-md text-on-tertiary">
        {t("cook.resume")} <Icon name="arrow_forward" className="text-[18px]" />
      </span>
    </Link>
  );
}

function Hero({ recipe, saved, isOwn }: { recipe: RecipeSummary; saved: boolean | undefined; isOwn: boolean }) {
  const { t } = useTranslation();
  return (
    <section className="mb-lg grid overflow-hidden rounded-xl bg-surface-container-low shadow-card lg:grid-cols-[1.4fr_1fr]">
      <Link to={`/recipes/${recipe.id}`} className="relative block aspect-[16/10] lg:aspect-auto">
        <Cover url={recipe.cover_photo_url} alt={recipe.title} className="h-full w-full" />
        <span className="absolute left-sm top-sm rounded-full bg-surface/90 px-sm py-[2px] text-label-sm uppercase text-primary">
          {t("explore.newest")}
        </span>
      </Link>
      <div className="flex flex-col justify-center gap-sm p-md lg:p-lg">
        <div className="flex flex-wrap gap-xs">
          {recipe.difficulty && <Chip tone="accent">{recipe.difficulty.name}</Chip>}
          {recipe.prep_time_minutes && (
            <Chip tone="accent" icon="schedule">
              {formatMinutes(recipe.prep_time_minutes)}
            </Chip>
          )}
        </div>
        <h2 className="text-display-sm lg:text-display-lg">{recipe.title}</h2>
        {recipe.description && <p className="line-clamp-3 text-body-lg text-on-surface-variant">{recipe.description}</p>}
        <div className="mt-sm flex items-center gap-sm">
          {!isOwn && saved !== undefined && <FavoriteButton recipeId={recipe.id} saved={saved} />}
          <Link to={`/recipes/${recipe.id}`}>
            <Button icon="menu_book">{t("explore.viewRecipe")}</Button>
          </Link>
        </div>
      </div>
    </section>
  );
}

function TagsModal({
  open,
  onClose,
  selected,
  onChange,
}: {
  open: boolean;
  onClose: () => void;
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  const { t } = useTranslation();
  const tags = useTags();
  const byGroup = useMemo(() => {
    const groups: Record<string, RecipeTag[]> = {};
    for (const tag of tags.data ?? []) (groups[tag.group] ??= []).push(tag);
    return groups;
  }, [tags.data]);
  const toggle = (id: string) => onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  return (
    <Modal open={open} onClose={onClose} title={t("explore.tags")} footer={<Button onClick={onClose}>{t("common.apply")}</Button>}>
      <div className="flex flex-col gap-md">
        {TAG_GROUPS.filter((group) => byGroup[group]).map((group) => (
          <div key={group}>
            <h3 className="mb-xs text-label-sm uppercase text-on-surface-variant">{byGroup[group][0].group_name}</h3>
            <div className="flex flex-wrap gap-xs">
              {byGroup[group].map((tag) => (
                <Chip key={tag.id} active={selected.includes(tag.id)} onClick={() => toggle(tag.id)}>
                  {tag.name}
                </Chip>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}

export function ExplorePage() {
  const { t } = useTranslation();
  const user = useUser();
  const errorMessage = useErrorMessage();
  const { filters, update, active, clear } = useFilters();
  const categories = useRecipeCategories();
  const difficulties = useDifficulties();
  const tags = useTags();
  const [text, setText] = useState(filters.q ?? "");
  const [tagsOpen, setTagsOpen] = useState(false);
  const debounced = useDebounced(text.trim());

  useEffect(() => {
    if (debounced !== (filters.q ?? "")) update({ q: debounced || undefined });
  }, [debounced]);
  // The header search writes ?q= directly.
  useEffect(() => setText(filters.q ?? ""), [filters.q]);

  const results = useInfiniteQuery({
    queryKey: ["recipes", "search", filters],
    queryFn: ({ pageParam }) => recipesApi.search({ ...filters, limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined),
  });
  const recipes = results.data?.pages.flatMap((page) => page.items) ?? [];
  const total = results.data?.pages[0]?.total ?? 0;
  const favorites = useFavoriteStatus(recipes.filter((r) => r.created_by_user_id !== user.id).map((r) => r.id));
  const savedOf = (recipe: RecipeSummary) =>
    recipe.created_by_user_id === user.id ? undefined : favorites.data?.[recipe.id] ?? false;

  const ingredientNames = useQueries({
    queries: (filters.ingredient_ids ?? []).map((id) => ({
      queryKey: ["ingredient", id],
      queryFn: () => catalogApi.getIngredient(id),
      staleTime: Infinity,
    })),
  });
  const tagName = (id: string) => tags.data?.find((tag) => tag.id === id)?.name ?? "…";

  const [hero, ...rest] = recipes;
  const showHero = !active && hero;

  return (
    <div>
      <InProgressBanner />
      {results.isLoading && !active && <div className="mb-lg h-72 animate-pulse rounded-xl bg-surface-container-high" />}
      {showHero && <Hero recipe={hero} saved={savedOf(hero)} isOwn={hero.created_by_user_id === user.id} />}

      <div className="-mx-margin-mobile mb-sm flex gap-xs overflow-x-auto px-margin-mobile pb-xs lg:mx-0 lg:px-0">
        <Chip active={!filters.category_id} onClick={() => update({ category_id: undefined })}>
          {t("explore.allRecipes")}
        </Chip>
        {categories.data?.map((category) => (
          <Chip key={category.id} active={filters.category_id === category.id} onClick={() => update({ category_id: category.id })}>
            {category.name}
          </Chip>
        ))}
      </div>

      <section className="mb-md flex flex-col gap-sm rounded-xl bg-surface-container-low p-sm lg:p-md">
        <div className="flex flex-col gap-sm lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Icon name="search" className="pointer-events-none absolute left-sm top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant" />
            <input
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={t("explore.searchPlaceholder")}
              aria-label={t("explore.searchPlaceholder")}
              className={`${inputClass} bg-surface-container-lowest pl-[40px]`}
            />
          </div>
          <div className="lg:w-72">
            <IngredientPicker
              placeholder={t("explore.withIngredient")}
              excludeIds={filters.ingredient_ids}
              onPick={(ingredient) => update({ ingredient_ids: [...(filters.ingredient_ids ?? []), ingredient.id] })}
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-sm">
          <span className="text-label-sm uppercase text-on-surface-variant">{t("explore.maxTime")}</span>
          <div className="flex flex-wrap gap-xs">
            {TIME_OPTIONS.map((minutes) => (
              <Chip
                key={minutes}
                active={filters.max_prep_time === minutes}
                onClick={() => update({ max_prep_time: filters.max_prep_time === minutes ? undefined : minutes })}
              >
                ≤ {formatMinutes(minutes)}
              </Chip>
            ))}
          </div>
          {difficulties.data && (
            <Segmented
              label={t("explore.difficulty")}
              value={filters.difficulty_id ?? ""}
              onChange={(value) => update({ difficulty_id: value || undefined })}
              options={[{ value: "", label: t("common.all") }, ...difficulties.data.map((d) => ({ value: d.id, label: d.name }))]}
            />
          )}
          <Button variant="secondary" icon="tune" onClick={() => setTagsOpen(true)} className="py-xs">
            {t("explore.tags")} {filters.tag_ids?.length ? `(${filters.tag_ids.length})` : ""}
          </Button>
          {active && (
            <Button variant="ghost" icon="restart_alt" onClick={clear} className="py-xs">
              {t("common.clear")}
            </Button>
          )}
        </div>
        {(!!filters.tag_ids?.length || !!filters.ingredient_ids?.length) && (
          <div className="flex flex-wrap gap-xs">
            {filters.ingredient_ids?.map((id, index) => (
              <Chip
                key={id}
                tone="success"
                icon="nutrition"
                onRemove={() => update({ ingredient_ids: filters.ingredient_ids?.filter((x) => x !== id) })}
              >
                {ingredientNames[index]?.data?.name ?? "…"}
              </Chip>
            ))}
            {filters.tag_ids?.map((id) => (
              <Chip key={id} tone="accent" onRemove={() => update({ tag_ids: filters.tag_ids?.filter((x) => x !== id) })}>
                {tagName(id)}
              </Chip>
            ))}
          </div>
        )}
      </section>

      <div className="mb-sm flex items-baseline justify-between">
        <h2 className="text-headline-md">{active ? t("explore.results") : t("explore.latest")}</h2>
        {results.data && <span className="text-label-md text-on-surface-variant">{t("explore.showing", { shown: recipes.length, total })}</span>}
      </div>

      {results.isLoading ? (
        <CardGridSkeleton />
      ) : results.isError ? (
        <ErrorState message={errorMessage(results.error)} onRetry={() => void results.refetch()} />
      ) : recipes.length === 0 ? (
        <EmptyState
          icon="search_off"
          title={t("explore.emptyTitle")}
          text={active ? t("explore.emptyFiltered") : t("explore.emptyAll")}
          action={
            active ? (
              <Button variant="secondary" onClick={clear}>
                {t("common.clear")}
              </Button>
            ) : (
              <Link to="/recipes/new">
                <Button icon="add">{t("portfolio.createRecipe")}</Button>
              </Link>
            )
          }
        />
      ) : (
        <>
          <div className="grid gap-gutter sm:grid-cols-2 lg:grid-cols-3">
            {(showHero ? rest : recipes).map((recipe) => (
              <RecipeCard key={recipe.id} recipe={cardFromSummary(recipe)} saved={savedOf(recipe)} />
            ))}
          </div>
          {results.hasNextPage && (
            <div className="mt-md flex justify-center">
              <Button variant="secondary" icon="autorenew" loading={results.isFetchingNextPage} onClick={() => void results.fetchNextPage()}>
                {t("explore.loadMore")}
              </Button>
            </div>
          )}
        </>
      )}

      <TagsModal open={tagsOpen} onClose={() => setTagsOpen(false)} selected={filters.tag_ids ?? []} onChange={(tag_ids) => update({ tag_ids })} />
    </div>
  );
}
