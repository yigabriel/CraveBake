import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { useErrorMessage } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { Button, Field, Icon, Input } from "../components/ui";

export const passwordRules = (password: string) => [
  { key: "auth.rules.length", ok: password.length >= 8 },
  { key: "auth.rules.letter", ok: /[A-Za-z]/.test(password) },
  { key: "auth.rules.number", ok: /\d/.test(password) },
];

export function PasswordRules({ password }: { password: string }) {
  const { t } = useTranslation();
  return (
    <ul className="flex flex-wrap gap-x-md gap-y-xs">
      {passwordRules(password).map((rule) => (
        <li key={rule.key} className={`flex items-center gap-xs text-label-sm ${rule.ok ? "text-tertiary" : "text-on-surface-variant"}`}>
          <Icon name={rule.ok ? "check_circle" : "radio_button_unchecked"} className="text-[16px]" />
          {t(rule.key)}
        </li>
      ))}
    </ul>
  );
}

function AuthLayout({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background">
      <div className="relative hidden flex-1 items-end overflow-hidden bg-gradient-to-br from-primary to-primary-container p-xl lg:flex">
        <Icon name="bakery_dining" className="absolute -right-lg -top-lg text-[420px] text-on-primary/10" />
        <div className="relative max-w-md text-on-primary">
          <p className="text-label-sm uppercase">Crave Bake</p>
          <p className="mt-sm text-display-lg">{subtitle}</p>
        </div>
      </div>
      <div className="flex flex-1 items-center justify-center px-margin-mobile py-lg">
        <div className="w-full max-w-sm">
          <div className="mb-lg flex items-center gap-xs">
            <Icon name="bakery_dining" className="text-[32px] text-primary" />
            <span className="text-title-lg text-primary">Crave Bake</span>
          </div>
          <h1 className="mb-md text-display-sm">{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const errorMessage = useErrorMessage();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [lockedFor, setLockedFor] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (lockedFor <= 0) return;
    const timer = setTimeout(() => setLockedFor((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [lockedFor]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      // Back to where the 401 interrupted the user.
      navigate(params.get("next") || "/", { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 429) setLockedFor(caught.retryAfterSeconds ?? 900);
      else if (caught instanceof ApiError && caught.status === 401)
        setError(caught.message.includes("inactive") ? t("auth.inactive") : t("auth.badCredentials"));
      else setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  };

  const minutes = Math.ceil(lockedFor / 60);
  return (
    <AuthLayout title={t("auth.loginTitle")} subtitle={t("auth.tagline")}>
      <form onSubmit={submit} className="flex flex-col gap-md">
        <Field label={t("auth.email")}>
          <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label={t("auth.password")}>
          <Input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {/* No "forgot password" link: the API has no password recovery yet (§17). */}
        {error && <p className="rounded bg-error-container px-sm py-xs text-label-md text-on-error-container">{error}</p>}
        {lockedFor > 0 && (
          <p className="rounded bg-error-container px-sm py-xs text-label-md text-on-error-container">
            {t("auth.locked", { count: minutes })}
          </p>
        )}
        <Button type="submit" loading={submitting} disabled={lockedFor > 0}>
          {t("auth.login")}
        </Button>
      </form>
      <p className="mt-md text-center text-label-md text-on-surface-variant">
        {t("auth.noAccount")}{" "}
        <Link to="/register" className="font-semibold text-primary">
          {t("auth.register")}
        </Link>
      </p>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const { t } = useTranslation();
  const { register } = useAuth();
  const navigate = useNavigate();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const valid = passwordRules(form.password).every((rule) => rule.ok);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setErrors({});
    try {
      await register(form.email, form.password, form.full_name);
      // Suggested onboarding: tell us what is in your kitchen.
      navigate("/profile/kitchen?welcome=1", { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) setErrors({ email: t("auth.emailTaken") });
      else if (caught instanceof ApiError && Object.keys(caught.fieldErrors).length) setErrors(caught.fieldErrors);
      else setErrors({ form: errorMessage(caught) });
    } finally {
      setSubmitting(false);
    }
  };

  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [key]: event.target.value }));

  return (
    <AuthLayout title={t("auth.registerTitle")} subtitle={t("auth.tagline")}>
      <form onSubmit={submit} className="flex flex-col gap-md">
        <Field label={t("auth.fullName")} error={errors.full_name}>
          <Input required maxLength={255} autoComplete="name" value={form.full_name} onChange={set("full_name")} />
        </Field>
        <Field label={t("auth.email")} error={errors.email}>
          <Input type="email" required autoComplete="email" value={form.email} onChange={set("email")} />
        </Field>
        <Field label={t("auth.password")} error={errors.password} hint={<PasswordRules password={form.password} />}>
          <Input type="password" required autoComplete="new-password" value={form.password} onChange={set("password")} />
        </Field>
        {errors.form && <p className="rounded bg-error-container px-sm py-xs text-label-md text-on-error-container">{errors.form}</p>}
        <Button type="submit" loading={submitting} disabled={!valid}>
          {t("auth.createAccount")}
        </Button>
      </form>
      <p className="mt-md text-center text-label-md text-on-surface-variant">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-semibold text-primary">
          {t("auth.login")}
        </Link>
      </p>
    </AuthLayout>
  );
}
