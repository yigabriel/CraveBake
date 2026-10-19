import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { preparationApi } from "../api/endpoints";
import { useErrorMessage } from "../api/queries";
import { useToast } from "./Toast";
import { Button } from "./ui";

/** Starts cooking mode, or resumes the preparation already in progress for this recipe (200). */
export function useStartCooking() {
  const navigate = useNavigate();
  const toast = useToast();
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  return useMutation({
    mutationFn: (recipeId: string) => preparationApi.start(recipeId),
    onSuccess: ({ detail, resumed }) => {
      if (resumed) toast(t("cook.resuming"), "info");
      navigate(`/cook/${detail.id}`);
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });
}

export function CookButton({ recipeId, short = false, className = "" }: { recipeId: string; short?: boolean; className?: string }) {
  const { t } = useTranslation();
  const start = useStartCooking();
  return (
    <Button icon="soup_kitchen" loading={start.isPending} onClick={() => start.mutate(recipeId)} className={className}>
      {short ? t("recipe.cookShort") : t("recipe.cook")}
    </Button>
  );
}
