import { useEffect, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { LogoMark } from "./Logo";

export function Icon({ name, filled = false, className = "" }: { name: string; filled?: boolean; className?: string }) {
  return (
    <span
      aria-hidden
      className={`material-symbols-outlined select-none leading-none ${className}`}
      style={filled ? { fontVariationSettings: "'FILL' 1" } : undefined}
    >
      {name}
    </span>
  );
}

type Variant = "primary" | "secondary" | "ghost" | "tertiary" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary text-on-primary hover:shadow-lift",
  secondary: "border border-secondary/60 text-secondary hover:bg-surface-container-high",
  ghost: "text-on-surface-variant hover:bg-surface-container-high",
  tertiary: "bg-tertiary text-on-tertiary hover:shadow-lift",
  danger: "bg-error text-on-error hover:shadow-lift",
};

export function Button({
  variant = "primary",
  icon,
  loading = false,
  className = "",
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: string; loading?: boolean }) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-base rounded px-md py-sm text-label-md font-semibold transition-all disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    >
      {loading ? <Icon name="progress_activity" className="animate-spin text-[18px]" /> : icon && <Icon name={icon} className="text-[18px]" />}
      {children}
    </button>
  );
}

export function IconButton({
  icon,
  label,
  filled,
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { icon: string; label: string; filled?: boolean }) {
  return (
    <button
      {...props}
      aria-label={label}
      title={label}
      className={`inline-flex h-10 w-10 items-center justify-center rounded-full transition-colors hover:bg-surface-container-high disabled:opacity-40 ${className}`}
    >
      <Icon name={icon} filled={filled} className="text-[22px]" />
    </button>
  );
}

export function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-xs">
      <span className="text-label-md text-on-surface-variant">{label}</span>
      {children}
      {hint && !error && <span className="text-label-sm font-normal text-on-surface-variant">{hint}</span>}
      {error && <span className="text-label-sm font-normal text-error">{error}</span>}
    </label>
  );
}

export const inputClass =
  "w-full rounded border border-secondary/20 bg-surface px-sm py-[10px] text-body-md text-on-surface outline-none transition-colors placeholder:text-on-surface-variant/60 focus:border-primary";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputClass} ${props.className ?? ""}`} />;
}

export function Chip({
  children,
  active = false,
  onClick,
  onRemove,
  tone = "default",
  icon,
}: {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
  onRemove?: () => void;
  tone?: "default" | "success" | "accent";
  icon?: string;
}) {
  const tones = {
    default: active
      ? "bg-primary text-on-primary"
      : "bg-surface-container-lowest text-on-surface-variant border border-outline-variant hover:bg-surface-container-high",
    success: "bg-tertiary-fixed text-on-tertiary-fixed-variant",
    accent: "bg-secondary-container text-on-secondary-fixed-variant",
  };
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      aria-pressed={onClick ? active : undefined}
      className={`inline-flex shrink-0 items-center gap-xs whitespace-nowrap rounded-full px-sm py-[6px] text-label-md transition-colors ${tones[tone]}`}
    >
      {icon && <Icon name={icon} className="text-[16px]" />}
      {children}
      {onRemove && (
        <button type="button" onClick={onRemove} aria-label="×" className="-mr-xs rounded-full hover:opacity-70">
          <Icon name="close" className="text-[16px]" />
        </button>
      )}
    </Tag>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-full bg-surface-container-high p-xs">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          onClick={() => onChange(option.value)}
          className={`rounded-full px-sm py-[6px] text-label-md transition-all ${
            value === option.value ? "bg-surface-container-lowest text-primary shadow-card" : "text-on-surface-variant"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-lg bg-surface-container-lowest shadow-card ${className}`}>{children}</div>;
}

// --- Screen states (§1: loading, empty, error, content) ----------------------------------

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-surface-container-high ${className}`} />;
}

export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-gutter sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className="h-72" />
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  text,
  action,
}: {
  icon: string;
  title: string;
  text?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-sm rounded-xl bg-surface-container-low px-md py-lg text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-full bg-secondary-container">
        <Icon name={icon} className="text-[32px] text-primary" />
      </span>
      <h3 className="text-title-lg">{title}</h3>
      {text && <p className="max-w-md text-body-md text-on-surface-variant">{text}</p>}
      {action && <div className="mt-xs flex flex-wrap justify-center gap-sm">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <EmptyState
      icon="cloud_off"
      title={t("common.errorTitle")}
      text={message}
      action={
        onRetry && (
          <Button variant="secondary" icon="refresh" onClick={onRetry}>
            {t("common.retry")}
          </Button>
        )
      }
    />
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const { t } = useTranslation();
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-inverse-surface/40 backdrop-blur-[8px] sm:items-center" onClick={onClose}>
      <div
        role="dialog"
        aria-modal
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        className="flex max-h-[90vh] w-full flex-col rounded-t-xl bg-surface shadow-lift sm:max-w-lg sm:rounded-xl"
      >
        <div className="flex items-center justify-between border-b border-outline-variant/50 px-md py-sm">
          <h2 className="text-title-lg">{title}</h2>
          <IconButton icon="close" label={t("common.close")} onClick={onClose} />
        </div>
        <div className="overflow-y-auto px-md py-md">{children}</div>
        {footer && <div className="flex justify-end gap-sm border-t border-outline-variant/50 px-md py-sm">{footer}</div>}
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-md flex flex-wrap items-end justify-between gap-sm">
      <div>
        <h1 className="text-display-sm lg:text-display-lg">{title}</h1>
        {subtitle && <p className="mt-xs text-body-md text-on-surface-variant">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-sm">{actions}</div>}
    </div>
  );
}

export function Placeholder({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center justify-center bg-gradient-to-br from-secondary-container to-primary-fixed ${className}`}>
      <LogoMark size={56} className="opacity-50" />
    </div>
  );
}

export function Cover({ url, alt, className = "" }: { url: string | null | undefined; alt: string; className?: string }) {
  if (!url) return <Placeholder className={className} />;
  return <img src={url} alt={alt} loading="lazy" className={`object-cover ${className}`} />;
}

/** On/off switch (role="switch"), for settings that apply at once or on save. */
export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-8 w-14 shrink-0 items-center rounded-full transition-colors duration-200 ${
        checked ? "bg-tertiary" : "bg-outline-variant"
      }`}
    >
      <span
        className={`flex h-6 w-6 items-center justify-center rounded-full bg-surface-container-lowest shadow-card transition-transform duration-200 ${
          checked ? "translate-x-7" : "translate-x-1"
        }`}
      >
        <Icon name={checked ? "public" : "lock"} className={`text-[14px] ${checked ? "text-tertiary" : "text-outline"}`} />
      </span>
    </button>
  );
}
