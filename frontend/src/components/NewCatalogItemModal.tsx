import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { translationApi } from "../api/endpoints";
import { ApiError } from "../api/client";
import { useErrorMessage } from "../api/queries";
import type { Language } from "../api/types";
import { useToast } from "./Toast";
import { Button, Field, Icon, Input, Modal } from "./ui";

const LANGUAGES: Language[] = ["es", "en"];

type Suggestion = "idle" | "loading" | "suggested" | "unavailable" | "limited" | "failed";

/**
 * Review step before adding an ingredient or equipment to the shared catalog.
 *
 * The name is translated into the other languages by the API (a suggestion, nothing is
 * saved yet). The person checks the name and every translation, sees how each language
 * will read it, and only then confirms. If the suggestion is not available they can type
 * the translation themselves or leave it empty (it then shows as written).
 */
export function NewCatalogItemModal({
  open,
  kind,
  name: typed,
  onClose,
  onConfirm,
}: {
  open: boolean;
  kind: "ingredient" | "equipment";
  /** What was typed in the search box. */
  name: string;
  onClose: () => void;
  onConfirm: (name: string, translations: Record<string, string>) => Promise<unknown>;
}) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const source = i18n.language as Language;
  const others = LANGUAGES.filter((language) => language !== source);

  const [name, setName] = useState(typed);
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<Suggestion>("idle");
  const [saving, setSaving] = useState(false);
  // The API refused it: another item already has this name or one of these translations.
  const [exists, setExists] = useState(false);
  // The name a suggestion was made for: a different name makes the suggestion stale.
  const [suggestedFor, setSuggestedFor] = useState("");
  const latest = useRef(0);

  const suggest = useCallback(
    async (text: string) => {
      const request = ++latest.current;
      setStatus("loading");
      try {
        const { translations: suggested } = await translationApi.suggest({ text, source });
        if (request !== latest.current) return; // a newer request replaced this one
        setTranslations((current) => ({ ...current, ...suggested }));
        setSuggestedFor(text);
        setStatus("suggested");
      } catch (error) {
        if (request !== latest.current) return;
        setStatus(error instanceof ApiError && error.status === 503 ? "unavailable" : error instanceof ApiError && error.status === 429 ? "limited" : "failed");
      }
    },
    [source],
  );

  // Every time the dialog opens: start from what was typed and ask for the suggestion.
  useEffect(() => {
    if (!open) {
      latest.current++; // ignore anything still in flight
      return;
    }
    setName(typed);
    setTranslations({});
    setSuggestedFor("");
    setSaving(false);
    setExists(false);
    void suggest(typed.trim());
  }, [open, typed, suggest]);

  const trimmed = name.trim();
  const stale = status === "suggested" && trimmed !== suggestedFor;
  const loading = status === "loading";

  const confirm = async () => {
    setSaving(true);
    setExists(false);
    try {
      await onConfirm(trimmed, Object.fromEntries(others.map((language) => [language, (translations[language] ?? "").trim()])));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) setExists(true);
      else toast(errorMessage(error), "error");
      setSaving(false);
    }
  };

  const hint = {
    idle: null,
    loading: t("newItem.translating"),
    suggested: stale ? t("newItem.stale") : t("newItem.suggested"),
    unavailable: t("newItem.unavailable"),
    limited: t("newItem.limited"),
    failed: t("newItem.failed"),
  }[status];

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t(`newItem.title.${kind}`)}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            {t("common.cancel")}
          </Button>
          <Button icon="check" loading={saving} disabled={!trimmed || loading} onClick={() => void confirm()}>
            {t("newItem.confirm")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-md">
        <p className="text-body-md text-on-surface-variant">{t("newItem.intro")}</p>

        <Field label={t("newItem.nameIn", { language: t(`newItem.languages.${source}`) })}>
          <Input value={name} maxLength={kind === "equipment" ? 150 : 255} onChange={(event) => {
              setName(event.target.value);
              setExists(false);
            }}
          />
        </Field>

        {others.map((language) => (
          <Field key={language} label={t("newItem.translationTo", { language: t(`newItem.languages.${language}`) })} hint={hint}>
            <div className="flex items-center gap-xs">
              <Input
                value={translations[language] ?? ""}
                maxLength={kind === "equipment" ? 150 : 255}
                disabled={loading}
                placeholder={loading ? t("newItem.translating") : t("newItem.emptyPlaceholder")}
                onChange={(event) => {
                  setTranslations((current) => ({ ...current, [language]: event.target.value }));
                  setExists(false);
                }}
              />
              <Button
                type="button"
                variant="secondary"
                icon={loading ? "progress_activity" : "translate"}
                className="shrink-0 px-sm"
                disabled={!trimmed || loading}
                onClick={() => void suggest(trimmed)}
              >
                <span className="sr-only sm:not-sr-only">{t("newItem.translateAgain")}</span>
              </Button>
            </div>
          </Field>
        ))}

        {exists && (
          <p role="alert" className="flex items-start gap-xs rounded-lg bg-error-container p-sm text-label-md text-on-error-container">
            <Icon name="error" className="text-[18px]" /> {t(`newItem.exists.${kind}`)}
          </p>
        )}

        <section aria-label={t("newItem.preview")} className="rounded-lg bg-surface-container-low p-sm">
          <h3 className="mb-xs flex items-center gap-xs text-label-md font-semibold">
            <Icon name="visibility" className="text-[18px] text-primary" /> {t("newItem.preview")}
          </h3>
          <ul className="flex flex-col gap-xs">
            {[source, ...others].map((language) => {
              const text = language === source ? trimmed : (translations[language] ?? "").trim();
              return (
                <li key={language} className="flex items-baseline gap-sm text-body-md">
                  <span className="w-20 shrink-0 text-label-sm uppercase text-on-surface-variant">{t(`newItem.languages.${language}`)}</span>
                  {text ? (
                    <strong>{text}</strong>
                  ) : (
                    <span className="text-on-surface-variant">
                      {trimmed || "—"} <em className="text-label-sm">({t("newItem.asWritten")})</em>
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </Modal>
  );
}
