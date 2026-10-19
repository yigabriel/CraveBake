import { useEffect, useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
import { Link, NavLink, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { useErrorMessage } from "../api/queries";
import { useAuth } from "../auth/AuthContext";
import { Logo } from "../components/Logo";
import { Button, Icon } from "../components/ui";

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

const CREAM = "#FBF6EE";

/** The craving in the headline changes every couple of seconds (still for reduced motion). */
function CravingWord() {
  const { t } = useTranslation();
  const words = t("auth.cravings", { returnObjects: true }) as string[];
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = setInterval(() => setIndex((i) => (i + 1) % words.length), 2400);
    return () => clearInterval(timer);
  }, [words.length]);
  return (
    <span className="relative inline-block font-serif font-semibold italic text-primary">
      <span key={index} className="inline-block animate-craving">
        {words[index]}
      </span>
      {/* A crumb trail under the word, drawn like the logo's crumbs. */}
      <svg aria-hidden viewBox="0 0 120 10" className="absolute -bottom-1 left-0 h-2.5 w-full" preserveAspectRatio="none">
        <path d="M2 6c18-5 38 3 58-1s40-3 58 1" fill="none" stroke="#E9A84C" strokeWidth="3" strokeLinecap="round" />
      </svg>
    </span>
  );
}

function AuthField({ label, error, hint, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: ReactNode }) {
  return (
    <label className="flex flex-col gap-xs">
      <span className="text-label-md font-semibold text-[#3A1F14]">{label}</span>
      <input
        {...props}
        className={`w-full rounded-xl border bg-white/80 px-md py-sm text-body-md text-[#3A1F14] shadow-[0_1px_0_rgba(58,31,20,0.04)] outline-none backdrop-blur transition-colors placeholder:text-[#3A1F14]/35 focus:border-primary focus:bg-white ${
          error ? "border-error" : "border-[#3A1F14]/15"
        }`}
      />
      {hint && !error && <span className="text-label-sm font-normal">{hint}</span>}
      {error && <span className="text-label-sm font-normal text-error">{error}</span>}
    </label>
  );
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-xs rounded-xl bg-error-container/90 px-sm py-xs text-label-md text-on-error-container">
      <Icon name="error" className="text-[18px]" /> {children}
    </p>
  );
}

function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const tab = ({ isActive }: { isActive: boolean }) =>
    `relative pb-xs text-label-md transition-colors ${
      isActive ? "font-semibold text-[#3A1F14] after:absolute after:inset-x-0 after:-bottom-px after:h-0.5 after:rounded-full after:bg-primary" : "text-[#3A1F14]/55 hover:text-[#3A1F14]"
    }`;
  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: CREAM }}>
      {/* Desktop: the photo fills the screen; the form lives on its empty cream side. */}
      <img src="/images/auth-bakery.webp" alt="" className="absolute inset-0 hidden h-full w-full object-cover object-right lg:block" />
      <div
        className="absolute inset-y-0 left-0 hidden w-[62%] lg:block"
        style={{ background: `linear-gradient(90deg, ${CREAM} 55%, ${CREAM}cc 75%, transparent)` }}
      />
      {/* Mobile: the photo is a banner that melts into the cream. */}
      <div className="relative h-60 lg:hidden">
        <img src="/images/auth-bakery.webp" alt="" className="h-full w-full object-cover object-[78%_50%]" />
        <div className="absolute inset-0" style={{ background: `linear-gradient(180deg, transparent 35%, ${CREAM})` }} />
      </div>

      <div className="relative z-10 -mt-xl flex min-h-[calc(100vh-15rem)] flex-col px-margin-mobile pb-md lg:mt-0 lg:min-h-screen lg:px-xl lg:py-lg">
        <Link to="/login" aria-label="Crave Bake" className="mb-md self-start">
          <Logo size={40} />
        </Link>

        <main className="flex w-full max-w-[440px] flex-1 flex-col justify-center">
          <h1 className="text-[38px] font-bold leading-[1.08] tracking-tight text-[#3A1F14] lg:text-[60px]">
            {t("auth.headline")}
            <br />
            <CravingWord />
          </h1>
          <p className="mb-lg mt-md max-w-sm text-body-lg text-[#3A1F14]/70">{t("auth.subtitle")}</p>

          <nav className="mb-md flex gap-md border-b border-[#3A1F14]/10">
            <NavLink to="/login" className={tab}>
              {t("auth.login")}
            </NavLink>
            <NavLink to="/register" className={tab}>
              {t("auth.createAccount")}
            </NavLink>
          </nav>
          {children}
        </main>

        <p className="mt-lg text-label-sm font-normal text-[#3A1F14]/50">© Crave Bake · {t("auth.footer")}</p>
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

  return (
    <AuthLayout>
      <form onSubmit={submit} className="flex flex-col gap-md">
        <AuthField label={t("auth.email")} type="email" autoComplete="email" required placeholder="tu@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        <AuthField label={t("auth.password")} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        {/* No "forgot password" link: the API has no password recovery yet (§17). */}
        {error && <Notice>{error}</Notice>}
        {lockedFor > 0 && <Notice>{t("auth.locked", { count: Math.ceil(lockedFor / 60) })}</Notice>}
        <Button type="submit" icon="arrow_forward" loading={submitting} disabled={lockedFor > 0} className="flex-row-reverse rounded-xl py-sm text-body-md">
          {t("auth.login")}
        </Button>
      </form>
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
    <AuthLayout>
      <form onSubmit={submit} className="flex flex-col gap-md">
        <AuthField label={t("auth.fullName")} error={errors.full_name} required maxLength={255} autoComplete="name" value={form.full_name} onChange={set("full_name")} />
        <AuthField label={t("auth.email")} error={errors.email} type="email" required autoComplete="email" placeholder="tu@email.com" value={form.email} onChange={set("email")} />
        <AuthField
          label={t("auth.password")}
          error={errors.password}
          hint={<PasswordRules password={form.password} />}
          type="password"
          required
          autoComplete="new-password"
          value={form.password}
          onChange={set("password")}
        />
        {errors.form && <Notice>{errors.form}</Notice>}
        <Button type="submit" icon="arrow_forward" loading={submitting} disabled={!valid} className="flex-row-reverse rounded-xl py-sm text-body-md">
          {t("auth.createAccount")}
        </Button>
      </form>
    </AuthLayout>
  );
}
