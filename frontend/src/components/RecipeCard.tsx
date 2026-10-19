import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useToggleFavorite, useErrorMessage } from "../api/queries";
import type { PortfolioItem, RecipeSummary } from "../api/types";
import { formatMinutes } from "../lib/time";
import { useToast } from "./Toast";
import { Chip, Cover, Icon } from "./ui";

export interface CardData {
  id: string;
  title: string;
  description: string | null;
  cover_photo_url: string | null;
  category_name: string | null;
  difficulty_name: string | null;
  tags: string[];
  prep_time_minutes: number | null;
  servings: number | null;
  is_personalization: boolean;
  source_recipe_title: string | null;
}

export function cardFromSummary(recipe: RecipeSummary): CardData {
  return {
    ...recipe,
    category_name: recipe.category?.name ?? null,
    difficulty_name: recipe.difficulty?.name ?? null,
    tags: recipe.tags.map((tag) => tag.name),
  };
}

export function cardFromPortfolio(item: PortfolioItem): CardData {
  return { ...item, id: item.recipe_id, is_personalization: item.kind === "personalized" };
}

export function FavoriteButton({ recipeId, saved, className = "" }: { recipeId: string; saved: boolean; className?: string }) {
  const { t } = useTranslation();
  const toggle = useToggleFavorite();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  return (
    <button
      type="button"
      aria-pressed={saved}
      aria-label={saved ? t("favorites.remove") : t("favorites.save")}
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        toggle.mutate(
          { recipeId, saved: !saved },
          {
            onSuccess: () => toast(saved ? t("favorites.removed") : t("favorites.saved")),
            onError: (error) => toast(errorMessage(error), "error"),
          },
        );
      }}
      className={`flex h-9 w-9 items-center justify-center rounded-full bg-surface/90 text-primary shadow-card backdrop-blur transition-transform hover:scale-110 ${className}`}
    >
      <Icon name="favorite" filled={saved} className="text-[20px]" />
    </button>
  );
}

/** Reusable recipe card (§4 "Tarjeta de receta"). No author or ratings: the API has neither. */
export function RecipeCard({
  recipe,
  saved,
  footer,
  badge,
}: {
  recipe: CardData;
  /** undefined hides the heart (own recipes cannot be saved). */
  saved?: boolean;
  footer?: ReactNode;
  badge?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <article className="group flex flex-col overflow-hidden rounded-lg bg-surface-container-lowest shadow-card transition-shadow hover:shadow-lift">
      <Link to={`/recipes/${recipe.id}`} className="relative block aspect-[4/3] overflow-hidden">
        <Cover url={recipe.cover_photo_url} alt={recipe.title} className="h-full w-full transition-transform duration-500 group-hover:scale-105" />
        <div className="absolute left-sm top-sm flex flex-wrap gap-xs">
          {recipe.category_name && (
            <span className="rounded-full bg-surface/90 px-sm py-[2px] text-label-sm text-on-surface backdrop-blur">
              {recipe.category_name}
            </span>
          )}
          {badge}
        </div>
        {saved !== undefined && <FavoriteButton recipeId={recipe.id} saved={saved} className="absolute right-sm top-sm" />}
        {recipe.prep_time_minutes && (
          <span className="absolute bottom-sm left-sm flex items-center gap-xs rounded-full bg-inverse-surface/80 px-sm py-[2px] text-label-sm text-inverse-on-surface">
            <Icon name="schedule" className="text-[14px]" /> {formatMinutes(recipe.prep_time_minutes)}
          </span>
        )}
      </Link>
      <div className="flex flex-1 flex-col gap-xs p-sm">
        {recipe.is_personalization && (
          <span className="flex items-center gap-xs text-label-sm text-primary">
            <Icon name="fork_right" className="text-[16px]" />
            {recipe.source_recipe_title
              ? t("recipe.yourVersionOf", { title: recipe.source_recipe_title })
              : t("recipe.yourVersion")}
          </span>
        )}
        <Link to={`/recipes/${recipe.id}`} className="text-title-lg leading-snug hover:text-primary">
          {recipe.title}
        </Link>
        {recipe.description && <p className="line-clamp-2 text-label-md font-normal text-on-surface-variant">{recipe.description}</p>}
        <div className="mt-auto flex flex-wrap items-center gap-xs pt-xs text-label-sm text-on-surface-variant">
          {recipe.difficulty_name && (
            <span className="flex items-center gap-[2px]">
              <Icon name="signal_cellular_alt" className="text-[14px]" /> {recipe.difficulty_name}
            </span>
          )}
          {recipe.servings && (
            <span className="flex items-center gap-[2px]">
              <Icon name="pie_chart" className="text-[14px]" /> {t("recipe.servingsShort", { count: recipe.servings })}
            </span>
          )}
          {recipe.tags.slice(0, 2).map((tag) => (
            <Chip key={tag} tone="accent">
              {tag}
            </Chip>
          ))}
        </div>
        {footer && <div className="mt-xs border-t border-outline-variant/40 pt-sm">{footer}</div>}
      </div>
    </article>
  );
}
