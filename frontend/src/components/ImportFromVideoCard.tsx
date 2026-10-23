import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { recipeImportApi } from "../api/endpoints";
import type { RecipeDraft } from "../api/types";
import { videoPlatform } from "../lib/videoLink";
import { useToast } from "./Toast";
import { Button, Card, Icon, Input } from "./ui";

/**
 * "Saw it on a Reel?": paste the link and the recipe editor fills in. The person reviews
 * everything and saves it as usual; nothing is created until then.
 */
export function ImportFromVideoCard({ onImported }: { onImported: (draft: RecipeDraft) => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [link, setLink] = useState("");
  const platform = videoPlatform(link);
  const showLinkError = link.trim() !== "" && !platform;

  const importIt = useMutation({
    mutationFn: () => recipeImportApi.fromVideo(link.trim()),
    onSuccess: onImported,
    onError: (error) => {
      const status = error instanceof ApiError ? error.status : 0;
      const key = status === 429 ? "limited" : status === 404 ? "unavailableVideo" : status === 503 ? "unavailable" : status === 400 ? "nothingFound" : "failed";
      toast(t(`import.errors.${key}`), "error");
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (platform && !importIt.isPending) importIt.mutate();
  };

  return (
    <Card className="mb-md border border-primary/20 bg-primary-fixed/30 p-md">
      <form onSubmit={submit} className="flex flex-col gap-sm">
        <div className="flex items-start gap-sm">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-container text-on-primary">
            <Icon name="smart_display" className="text-[22px]" />
          </span>
          <div>
            <h2 className="text-title-lg">{t("import.title")}</h2>
            <p className="text-label-md font-normal text-on-surface-variant">{t("import.hint")}</p>
          </div>
        </div>
        <div className="flex flex-col gap-xs sm:flex-row">
          <Input
            type="url"
            inputMode="url"
            aria-label={t("import.placeholder")}
            placeholder={t("import.placeholder")}
            value={link}
            disabled={importIt.isPending}
            onChange={(event) => setLink(event.target.value)}
          />
          <Button type="submit" icon="auto_awesome" loading={importIt.isPending} disabled={!platform} className="shrink-0">
            {importIt.isPending ? t("import.reading") : t("import.button")}
          </Button>
        </div>
        {showLinkError && <p className="text-label-sm font-normal text-error">{t("import.errors.badLink")}</p>}
        {importIt.isPending && <p className="text-label-sm font-normal text-on-surface-variant">{t("import.wait")}</p>}
      </form>
    </Card>
  );
}

/** What the import read and what is left to check, shown while the person reviews the draft. */
export function ImportReport({
  platform,
  author,
  read,
  picked,
  unmatched,
  cover,
  onDropCover,
}: {
  platform: RecipeDraft["platform"];
  author: string | null;
  read: RecipeDraft["read"];
  /** What was chosen from the catalogs, so the person knows to check it. */
  picked: { category: string | null; difficulty: string | null; equipment: number };
  unmatched: number;
  /** The video's cover frame that will become the recipe's cover, if any. */
  cover: string | null;
  onDropCover: () => void;
}) {
  const { t } = useTranslation();
  const seen = (label: string, ok: boolean) => (
    <span key={label} className={`inline-flex items-center gap-[2px] ${ok ? "text-tertiary" : "text-on-surface-variant line-through"}`}>
      <Icon name={ok ? "check_circle" : "cancel"} className="text-[16px]" /> {label}
    </span>
  );
  return (
    <div role="status">
    <Card className="mb-md flex flex-col gap-xs border border-tertiary/30 bg-tertiary-fixed/30 p-sm">
      <p className="flex items-center gap-xs text-label-md font-semibold">
        <Icon name="fact_check" className="text-[18px] text-tertiary" />
        {t("import.report.title", { platform: t(`import.platforms.${platform}`), author: author ?? "—" })}
      </p>
      <p className="flex flex-wrap gap-x-sm text-label-sm font-normal">
        {t("import.report.read")}
        {seen(t("import.report.fields.title"), read.title)}
        {seen(t("import.report.fields.description"), read.description)}
        {seen(t("import.report.fields.transcript"), read.transcript)}
      </p>
      <p className="text-label-sm font-normal">
        {t("import.report.picked", { category: picked.category ?? "—", difficulty: picked.difficulty ?? "—", count: picked.equipment })}
      </p>
      {!read.transcript && <p className="text-label-sm font-normal text-on-surface-variant">{t("import.report.noCaptions")}</p>}
      {unmatched > 0 && <p className="text-label-sm font-semibold text-primary">{t("import.report.unmatched", { count: unmatched })}</p>}
      {cover && (
        <div className="flex items-center gap-sm rounded-lg bg-white/60 p-xs">
          <img src={cover} alt={t("import.report.coverAlt")} className="h-16 w-16 shrink-0 rounded object-cover" />
          <p className="flex-1 text-label-sm font-normal">{t("import.report.cover")}</p>
          <Button variant="ghost" icon="hide_image" className="shrink-0 px-sm py-xs" onClick={onDropCover}>
            {t("import.report.dropCover")}
          </Button>
        </div>
      )}
      <p className="text-label-sm font-normal text-on-surface-variant">{t("import.report.review")}</p>
    </Card>
    </div>
  );
}
