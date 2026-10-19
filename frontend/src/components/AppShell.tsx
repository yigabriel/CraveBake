import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, NavLink, Outlet, useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { Logo, LogoMark } from "./Logo";
import { Icon } from "./ui";

const NAV = [
  { to: "/", key: "nav.explore", icon: "explore", end: true },
  { to: "/discover", key: "nav.discover", icon: "style" },
  { to: "/portfolio", key: "nav.portfolio", icon: "menu_book" },
  { to: "/tools/converter", key: "nav.converter", icon: "calculate" },
  { to: "/profile", key: "nav.profile", icon: "person" },
] as const;

export function Avatar({ size = 32 }: { size?: number }) {
  const { user } = useAuth();
  const initials = (user?.full_name ?? "?")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  if (user?.avatar_url)
    return <img src={user.avatar_url} alt="" style={{ width: size, height: size }} className="rounded-full object-cover" />;
  return (
    <span
      style={{ width: size, height: size, fontSize: size * 0.4 }}
      className="flex items-center justify-center rounded-full bg-primary font-semibold text-on-primary"
    >
      {initials}
    </span>
  );
}

function HeaderSearch() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [value, setValue] = useState(params.get("q") ?? "");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        input.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    navigate(value.trim() ? `/?q=${encodeURIComponent(value.trim())}` : "/");
  };

  return (
    <form onSubmit={submit} role="search" className="relative hidden items-center sm:flex">
      <Icon name="search" className="pointer-events-none absolute left-sm text-[18px] text-on-surface-variant" />
      <input
        ref={input}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder={t("nav.searchPlaceholder")}
        aria-label={t("nav.searchPlaceholder")}
        className="w-72 rounded bg-surface-container-low py-xs pl-[40px] pr-sm text-label-md outline-none transition-all focus:bg-surface-container focus:ring-1 focus:ring-primary-container"
      />
    </form>
  );
}

export function AppShell() {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-50 bg-surface/90 shadow-[0_1px_8px_rgba(0,0,0,0.04)] backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-gutter px-margin-mobile lg:h-20 lg:px-margin-desktop">
          <div className="flex items-center gap-lg">
            <Link to="/" aria-label="Crave Bake">
              <Logo size={36} />
            </Link>
            <nav className="hidden items-center gap-xs lg:flex">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={"end" in item}
                  className={({ isActive }) =>
                    `rounded px-sm py-xs text-label-md transition-all ${
                      isActive
                        ? "bg-surface-container-high font-semibold text-on-surface"
                        : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                    }`
                  }
                >
                  {t(item.key)}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-md">
            <HeaderSearch />
            <Link to="/profile" aria-label={t("nav.profile")} className="transition-transform hover:scale-105">
              <Avatar />
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1440px] flex-1 px-margin-mobile pb-[120px] pt-md lg:px-margin-desktop lg:pb-xl">
        <Outlet />
      </main>

      <footer className="hidden border-t border-outline-variant/40 bg-surface-container-low lg:block">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between px-margin-desktop py-md text-label-md text-on-surface-variant">
          <span className="flex items-center gap-xs">
            <LogoMark size={22} /> Crave Bake — {t("nav.tagline")}
          </span>
          <span className="flex gap-md">
            <Link to="/">{t("nav.explore")}</Link>
            <Link to="/tools/converter">{t("nav.converter")}</Link>
          </span>
        </div>
      </footer>

      <BottomNav />
    </div>
  );
}

function BottomNav() {
  const { t } = useTranslation();
  const items = [NAV[0], NAV[2], NAV[1], NAV[3], NAV[4]];
  return (
    <nav className="fixed inset-x-margin-mobile bottom-sm z-50 flex items-end justify-around rounded-full border border-outline-variant/60 bg-surface-container-low/95 px-xs py-xs shadow-lift backdrop-blur lg:hidden">
      {items.map((item) =>
        item.to === "/discover" ? (
          <NavLink
            key={item.to}
            to={item.to}
            className="-mt-md flex h-16 w-16 flex-col items-center justify-center rounded-full border-4 border-surface bg-primary-container text-on-primary shadow-lift"
          >
            <Icon name="style" filled className="text-[26px]" />
            <span className="text-[10px] font-semibold">Swipe</span>
          </NavLink>
        ) : (
          <NavLink
            key={item.to}
            to={item.to}
            end={"end" in item}
            className={({ isActive }) =>
              `flex min-w-[56px] flex-col items-center gap-[2px] rounded-full px-xs py-[6px] text-[11px] ${
                isActive ? "font-semibold text-primary" : "text-on-surface-variant"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon name={item.icon} filled={isActive} className="text-[24px]" />
                {t(item.key === "nav.converter" ? "nav.converterShort" : item.key)}
              </>
            )}
          </NavLink>
        ),
      )}
    </nav>
  );
}
