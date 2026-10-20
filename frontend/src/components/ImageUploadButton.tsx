import { useRef, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useErrorMessage } from "../api/queries";
import { UploadError, uploadImage, type UploadPurpose } from "../lib/imageUpload";
import { useToast } from "./Toast";
import { Button, Icon, IconButton, Input } from "./ui";

const MAX_URL = 1024;

/** True when the URL points to something the browser can show as an image. */
function loadsAsImage(url: string, timeoutMs = 8000): Promise<boolean> {
  return new Promise((resolve) => {
    const image = new Image();
    const timer = setTimeout(() => resolve(false), timeoutMs);
    image.onload = () => {
      clearTimeout(timer);
      resolve(image.naturalWidth > 0);
    };
    image.onerror = () => {
      clearTimeout(timer);
      resolve(false);
    };
    image.src = url;
  });
}

/**
 * "Choose photo": opens the file picker (camera or gallery on phones), shrinks,
 * uploads with progress, then hands the public URL to `onUploaded`, which
 * registers it (cover, step, avatar). The link button next to it takes an image
 * URL instead, which skips our storage entirely.
 */
export function ImageUploadButton({
  purpose,
  onUploaded,
  label,
  variant = "secondary",
  className = "",
  disabled = false,
}: {
  purpose: UploadPurpose;
  onUploaded: (url: string) => Promise<unknown> | void;
  label?: string;
  variant?: "primary" | "secondary" | "ghost";
  className?: string;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const input = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [linking, setLinking] = useState(false);
  const [link, setLink] = useState("");
  const [checking, setChecking] = useState(false);

  const upload = async (file: File) => {
    setProgress(0);
    try {
      const url = await uploadImage(file, purpose, setProgress);
      setProgress(1);
      await onUploaded(url);
    } catch (error) {
      toast(error instanceof UploadError ? t(`upload.errors.${error.reason}`) : errorMessage(error), "error");
    } finally {
      setProgress(null);
      // Let the same file be picked again after an error.
      if (input.current) input.current.value = "";
    }
  };

  const url = link.trim();
  const validUrl = /^https?:\/\/\S+$/.test(url) && url.length <= MAX_URL;
  const addLink = async (event: FormEvent) => {
    event.preventDefault();
    if (!validUrl) return;
    setChecking(true);
    try {
      // Catch typos and page links (not images) before saving a broken photo.
      if (!(await loadsAsImage(url))) {
        toast(t("upload.errors.badUrl"), "error");
        return;
      }
      await onUploaded(url);
      setLink("");
      setLinking(false);
    } catch (error) {
      toast(errorMessage(error), "error");
    } finally {
      setChecking(false);
    }
  };

  if (linking)
    return (
      <form onSubmit={(event) => void addLink(event)} className="flex min-w-[220px] flex-1 items-center gap-xs">
        <Input
          type="url"
          autoFocus
          maxLength={MAX_URL}
          placeholder="https://…/foto.jpg"
          aria-label={t("upload.urlLabel")}
          value={link}
          onChange={(event) => setLink(event.target.value)}
          onKeyDown={(event) => event.key === "Escape" && setLinking(false)}
        />
        <Button type="submit" icon="check" className="shrink-0 px-sm py-xs" disabled={!validUrl || disabled} loading={checking}>
          <span className="sr-only sm:not-sr-only">{t("common.add")}</span>
        </Button>
        <IconButton type="button" icon="close" label={t("common.cancel")} onClick={() => setLinking(false)} className="h-9 w-9 shrink-0" />
      </form>
    );

  const busy = progress !== null;
  return (
    <div className="flex shrink-0 items-center gap-xs">
      <input
        ref={input}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void upload(file);
        }}
      />
      <Button
        type="button"
        variant={variant}
        icon={busy ? undefined : "add_a_photo"}
        disabled={disabled || busy}
        onClick={() => input.current?.click()}
        className={`relative overflow-hidden ${className}`}
      >
        {busy && (
          <span
            aria-hidden
            className="absolute inset-y-0 left-0 bg-primary/15 transition-[width] duration-200"
            style={{ width: `${Math.round((progress ?? 0) * 100)}%` }}
          />
        )}
        {busy && <Icon name="progress_activity" className="relative animate-spin text-[18px]" />}
        <span className="relative">
          {busy ? t("upload.uploading", { percent: Math.round((progress ?? 0) * 100) }) : label ?? t("upload.choose")}
        </span>
      </Button>
      <IconButton
        type="button"
        icon="link"
        label={t("upload.useUrl")}
        disabled={disabled || busy}
        onClick={() => setLinking(true)}
        className="h-9 w-9 border border-outline-variant"
      />
    </div>
  );
}
