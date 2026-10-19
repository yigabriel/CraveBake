import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { portfolioApi, recipesApi } from "../api/endpoints";
import { useErrorMessage, useRecipeCategories, useTags } from "../api/queries";
import type { Language, PortfolioItem, PortfolioKind } from "../api/types";
import { useDebounced } from "../components/Pickers";
import { cardFromPortfolio, FavoriteButton, RecipeCard } from "../components/RecipeCard";
import { useToast } from "../components/Toast";
import {
  Button,
  Card,
  CardGridSkeleton,
  Chip,
  EmptyState,
  ErrorState,
  Icon,
  inputClass,
  PageHeader,
} from "../components/ui";
import { timeAgo } from "../lib/time";

const PAGE_SIZE = 12;
type Tab = PortfolioKind | "all";

function ItemActions({ item }: { item: PortfolioItem }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    void queryClient.invalidateQueries({ queryKey: ["recipe", item.recipe_id] });
  };
  const publish = useMutation({
    mutationFn: () => recipesApi.update(item.recipe_id, { is_public: !item.is_public }),
    onSuccess: () => {
      toast(item.is_public ? t("portfolio.madePrivate") : t("portfolio.madePublic"));
      refresh();
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });
  const personalize = useMutation({
    mutationFn: () => recipesApi.personalize(item.recipe_id),
    onSuccess: (copy) => {
      refresh();
      navigate(`/recipes/${copy.id}/edit`);
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });

  if (item.kind === "saved")
    return (
      <div className="flex items-center justify-between">
        <Button variant="ghost" icon="fork_right" className="px-0 py-xs text-primary" loading={personalize.isPending} onClick={() => personalize.mutate()}>
          {t("portfolio.createMyVersion")}
        </Button>
        <FavoriteButton recipeId={item.recipe_id} saved />
      </div>
    );

  return (
    <div className="flex flex-wrap items-center gap-xs">
      <Link to={`/recipes/${item.recipe_id}/edit`}>
        <Button variant="secondary" icon="edit" className="px-sm py-xs">
          {t("common.edit")}
        </Button>
      </Link>
      {item.kind === "original" && (
        // Personalizations are always private (§9): no publish switch for them.
        <Button variant="ghost" icon={item.is_public ? "lock" : "public"} className="px-sm py-xs" loading={publish.isPending} onClick={() => publish.mutate()}>
          {item.is_public ? t("portfolio.makePrivate") : t("portfolio.makePublic")}
        </Button>
      )}
      {item.kind === "personalized" && item.source_updated_since_personalized && item.source_recipe_title && (
        <Link to={`/recipes/${item.recipe_id}`} className="flex items-center gap-xs text-label-md text-secondary">
          <Icon name="sync_problem" className="text-[16px]" /> {t("portfolio.originalChanged")}
        </Link>
      )}
    </div>
  );
}

function KindBadge({ item }: { item: PortfolioItem }) {
  const { t } = useTranslation();
  if (item.kind === "saved")
    return (
      <span className="flex items-center gap-[2px] rounded-full bg-secondary-container px-sm py-[2px] text-label-sm text-on-secondary-container">
        <Icon name="bookmark" filled className="text-[12px]" /> {t("portfolio.kinds.saved")}
      </span>
    );
  return (
    <span className="flex items-center gap-[2px] rounded-full bg-surface/90 px-sm py-[2px] text-label-sm text-on-surface backdrop-blur">
      <Icon name={item.is_public ? "public" : "lock"} className="text-[12px]" /> {item.is_public ? t("recipe.public") : t("recipe.private")}
    </span>
  );
}

export function PortfolioPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const errorMessage = useErrorMessage();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) ?? "all";
  const [text, setText] = useState("");
  const [categoryId, setCategoryId] = useState<string>("");
  const [tagIds, setTagIds] = useState<string[]>([]);
  const q = useDebounced(text.trim());
  const categories = useRecipeCategories();
  const tags = useTags();

  const summary = useQuery({ queryKey: ["portfolio", "summary"], queryFn: portfolioApi.summary });
  const filters = { kind: tab === "all" ? undefined : tab, q: q || undefined, category_id: categoryId || undefined, tag_ids: tagIds };
  const list = useInfiniteQuery({
    queryKey: ["portfolio", "list", filters],
    queryFn: ({ pageParam }) => portfolioApi.list({ ...filters, limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined),
  });
  const items = list.data?.pages.flatMap((page) => page.items) ?? [];

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "all", label: t("portfolio.tabs.all"), count: summary.data?.total },
    { key: "original", label: t("portfolio.tabs.original"), count: summary.data?.original_count },
    { key: "personalized", label: t("portfolio.tabs.personalized"), count: summary.data?.personalized_count },
    { key: "saved", label: t("portfolio.tabs.saved"), count: summary.data?.saved_count },
  ];
  const stats = [
    { icon: "inventory_2", label: t("portfolio.stats.total"), value: summary.data?.total },
    { icon: "menu_book", label: t("portfolio.stats.original"), value: summary.data?.original_count },
    { icon: "fork_right", label: t("portfolio.stats.personalized"), value: summary.data?.personalized_count },
    { icon: "bookmark", label: t("portfolio.stats.saved"), value: summary.data?.saved_count },
  ];
  const filtered = !!q || !!categoryId || tagIds.length > 0;
  const toggleTag = (id: string) => setTagIds((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  return (
    <div>
      <PageHeader
        title={t("portfolio.title")}
        subtitle={summary.data ? t("portfolio.subtitle", { count: summary.data.total }) : undefined}
        actions={
          <Link to="/recipes/new">
            <Button icon="add">{t("portfolio.createRecipe")}</Button>
          </Link>
        }
      />

      <div className="mb-md hidden grid-cols-4 gap-gutter lg:grid">
        {stats.map((stat) => (
          <Card key={stat.label} className="flex items-center gap-sm p-md">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary-container">
              <Icon name={stat.icon} className="text-primary" />
            </span>
            <div>
              <p className="text-display-sm">{stat.value ?? "–"}</p>
              <p className="text-label-md text-on-surface-variant">{stat.label}</p>
            </div>
          </Card>
        ))}
      </div>

      <div role="tablist" className="-mx-margin-mobile mb-sm flex gap-xs overflow-x-auto border-b border-outline-variant/50 px-margin-mobile lg:mx-0 lg:px-0">
        {tabs.map((item) => (
          <button
            key={item.key}
            role="tab"
            aria-selected={tab === item.key}
            onClick={() => setParams(item.key === "all" ? {} : { tab: item.key }, { replace: true })}
            className={`flex shrink-0 items-center gap-xs border-b-2 px-sm py-sm text-label-md transition-colors ${
              tab === item.key ? "border-primary font-semibold text-primary" : "border-transparent text-on-surface-variant"
            }`}
          >
            {item.label}
            {item.count !== undefined && <span className="rounded-full bg-surface-container-high px-xs text-label-sm">{item.count}</span>}
          </button>
        ))}
      </div>

      <div className="mb-md flex flex-col gap-sm">
        <div className="flex flex-col gap-sm sm:flex-row">
          <div className="relative flex-1">
            <Icon name="search" className="pointer-events-none absolute left-sm top-1/2 -translate-y-1/2 text-[18px] text-on-surface-variant" />
            <input
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={t("portfolio.searchPlaceholder")}
              aria-label={t("portfolio.searchPlaceholder")}
              className={`${inputClass} pl-[40px]`}
            />
          </div>
          <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} aria-label={t("recipe.category")} className={`${inputClass} sm:w-56`}>
            <option value="">{t("portfolio.allCategories")}</option>
            {categories.data?.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>
        <div className="-mx-margin-mobile flex gap-xs overflow-x-auto px-margin-mobile pb-xs lg:mx-0 lg:flex-wrap lg:px-0">
          <span className="flex shrink-0 items-center gap-xs text-label-sm uppercase text-on-surface-variant">
            <Icon name="sell" className="text-[16px]" /> {t("explore.tags")}
          </span>
          {tags.data?.map((tag) => (
            <Chip key={tag.id} active={tagIds.includes(tag.id)} onClick={() => toggleTag(tag.id)}>
              {tag.name}
            </Chip>
          ))}
        </div>
      </div>

      {list.isLoading ? (
        <CardGridSkeleton />
      ) : list.isError ? (
        <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={tab === "saved" ? "bookmark" : "menu_book"}
          title={filtered ? t("explore.emptyTitle") : t(`portfolio.empty.${tab}.title`)}
          text={filtered ? t("explore.emptyFiltered") : t(`portfolio.empty.${tab}.text`)}
          action={
            tab === "saved" || tab === "personalized" ? (
              <Link to="/">
                <Button icon="explore">{t("nav.explore")}</Button>
              </Link>
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
            {items.map((item) => (
              <div key={`${item.kind}-${item.recipe_id}`} className="flex flex-col">
                <RecipeCard
                  recipe={cardFromPortfolio(item)}
                  badge={<KindBadge item={item} />}
                  footer={
                    <div className="flex flex-col gap-xs">
                      <span className="flex items-center gap-xs text-label-sm font-normal text-on-surface-variant">
                        <Icon name="history" className="text-[14px]" />
                        {t(item.kind === "saved" ? "portfolio.savedAgo" : "portfolio.createdAgo", { when: timeAgo(item.added_at, language) })}
                      </span>
                      <ItemActions item={item} />
                    </div>
                  }
                />
              </div>
            ))}
          </div>
          {list.hasNextPage && (
            <div className="mt-md flex justify-center">
              <Button variant="secondary" icon="autorenew" loading={list.isFetchingNextPage} onClick={() => void list.fetchNextPage()}>
                {t("explore.loadMore")}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
