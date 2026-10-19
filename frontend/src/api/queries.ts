import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "./client";
import { catalogApi, portfolioApi } from "./endpoints";
import type { FavoriteStatus } from "./types";

// Seeded by migrations, practically fixed: load once per session (§16).
const forever = { staleTime: Infinity, gcTime: Infinity } as const;

export const useUnits = () => useQuery({ queryKey: ["units"], queryFn: catalogApi.units, ...forever });
// The API orders by the name as originally written (Spanish); sort by what this user reads.
export const useRecipeCategories = () =>
  useQuery({
    queryKey: ["recipe-categories"],
    queryFn: async () => (await catalogApi.recipeCategories()).sort((a, b) => a.name.localeCompare(b.name)),
    ...forever,
  });
export const useDifficulties = () =>
  useQuery({
    queryKey: ["difficulties"],
    queryFn: async () => (await catalogApi.difficulties()).sort((a, b) => a.level_order - b.level_order),
    ...forever,
  });
export const useTags = () => useQuery({ queryKey: ["recipe-tags"], queryFn: catalogApi.tags, ...forever });

/** Hearts for a page of cards, in one request. */
export function useFavoriteStatus(recipeIds: string[]) {
  const ids = [...recipeIds].sort();
  return useQuery({
    queryKey: ["favorites", "status", ids],
    queryFn: async () => {
      const statuses = await portfolioApi.favoriteStatus(ids);
      return Object.fromEntries(statuses.map((item: FavoriteStatus) => [item.recipe_id, item.is_saved]));
    },
    enabled: ids.length > 0,
  });
}

/** Optimistic heart: paint now, roll back if the API says no. Both calls are idempotent. */
export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ recipeId, saved }: { recipeId: string; saved: boolean }): Promise<void> => {
      if (saved) await portfolioApi.save(recipeId);
      else await portfolioApi.unsave(recipeId);
    },
    onMutate: async ({ recipeId, saved }) => {
      await queryClient.cancelQueries({ queryKey: ["favorites", "status"] });
      const previous = queryClient.getQueriesData<Record<string, boolean>>({ queryKey: ["favorites", "status"] });
      queryClient.setQueriesData<Record<string, boolean>>({ queryKey: ["favorites", "status"] }, (old) =>
        old && recipeId in old ? { ...old, [recipeId]: saved } : old,
      );
      return { previous };
    },
    onError: (_error, _vars, context) => {
      context?.previous.forEach(([key, data]) => queryClient.setQueryData(key, data));
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["favorites"] });
      void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}

/** Errors are translated by `code`; the API's English `detail` is only a fallback. */
export function useErrorMessage() {
  const { t } = useTranslation();
  return (error: unknown): string => {
    if (!(error instanceof ApiError)) return t("errors.internal_error");
    const key = `errors.${error.code}`;
    const translated = t(key);
    return translated === key ? error.message : translated;
  };
}
