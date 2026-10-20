import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useErrorMessage } from "../api/queries";
import { UploadError, uploadImage, type UploadPurpose } from "../lib/imageUpload";
import { useToast } from "./Toast";
import { Button, Icon } from "./ui";

/**
 * "Choose photo": opens the file picker (camera or gallery on phones), shrinks,
 * uploads with progress, then hands the public URL to `onUploaded`, which
 * registers it (cover, step, avatar).
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

  const busy = progress !== null;
  return (
    <>
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
    </>
  );
}
