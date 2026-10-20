import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { Language, PreparationDetail } from "../api/types";
import { Logo, LogoMark } from "../components/Logo";
import { Button, Icon } from "../components/ui";
import { formatDate, formatMinutes } from "../lib/time";

const SCENE = "/images/auth-scene";
const SPRINKLE_COLORS = ["#9c3b24", "#E9A84C", "#F4C2C2", "#ffffff", "#7FA37A", "#C96F53"];
const SIGNOFFS = 4;

// Same bakery as the sign-in scene, now scattered around the finished bake.
const DESSERTS = [
  { name: "cookies", className: "-left-6 top-20 w-24 sm:left-[6%] sm:top-[14%] sm:w-32 lg:w-40", delay: 0 },
  { name: "macarons", className: "-right-6 top-16 w-24 sm:right-[6%] sm:top-[10%] sm:w-36 lg:w-40", delay: 0.25 },
  { name: "croissant", className: "-left-10 bottom-10 w-32 sm:left-[8%] sm:bottom-[8%] sm:w-44 lg:w-52", delay: 0.5 },
  { name: "apple-pie", className: "-right-10 bottom-6 w-36 sm:right-[4%] sm:bottom-[9%] sm:w-48 lg:w-56", delay: 0.75 },
  { name: "flan", className: "hidden xl:block right-[24%] bottom-[3%] w-32", delay: 1.25 },
];

/** Stable pseudo-random in [0, 1): the same confetti on every render. */
function noise(i: number, k: number) {
  const x = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

/** A one-off shower of sprinkles, like the ones on top of a cake. */
function Sprinkles({ count = 48 }: { count?: number }) {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 z-[5] overflow-hidden">
      {Array.from({ length: count }, (_, i) => {
        const dot = noise(i, 1) < 0.25;
        const style = {
          left: `${noise(i, 2) * 100}%`,
          background: SPRINKLE_COLORS[i % SPRINKLE_COLORS.length],
          width: dot ? 9 : 6,
          height: dot ? 9 : 16 + noise(i, 3) * 8,
          "--dx": `${(noise(i, 4) - 0.5) * 160}px`,
          "--r0": `${noise(i, 5) * 360}deg`,
          "--r1": `${noise(i, 6) * 900 - 450}deg`,
          "--dur": `${2.6 + noise(i, 7) * 2.2}s`,
          "--delay": `${noise(i, 8) * 1.4}s`,
        } as CSSProperties;
        return <span key={i} className="sprinkle" style={style} />;
      })}
    </div>
  );
}

function Stat({ icon, label, children }: { icon: string; label: string; children: string }) {
  return (
    <span
      title={label}
      className="flex items-center gap-[6px] rounded-full bg-white/70 px-sm py-[6px] text-label-md text-[#3A1F14] shadow-[inset_0_1px_0_rgba(255,255,255,0.9)]"
    >
      <Icon name={icon} className="text-[18px] text-primary" />
      <span className="sr-only">{label}: </span>
      {children}
    </span>
  );
}

/** Minutes from start to finish, or null when the dates are missing or nonsense. */
function totalMinutes(preparation: PreparationDetail): number | null {
  if (!preparation.finished_at) return null;
  const ms = new Date(preparation.finished_at).getTime() - new Date(preparation.started_at).getTime();
  return Number.isFinite(ms) && ms >= 0 ? Math.round(ms / 60000) : null;
}

/**
 * The screen after cooking: a celebration for a finished bake, a gentle
 * "maybe next time" for an abandoned one. Same bakery scene as sign-in.
 */
export function CookFinished({ preparation }: { preparation: PreparationDetail }) {
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const completed = preparation.status === "completed";
  const minutes = totalMinutes(preparation);
  // One sign-off per preparation, so it does not change on reload.
  const signoff = [...preparation.id].reduce((sum, c) => sum + c.charCodeAt(0), 0) % SIGNOFFS;
  const desserts = completed ? DESSERTS : DESSERTS.slice(0, 2);

  return (
    <div className="fixed inset-0 z-[55] overflow-hidden bg-[#F6E7DA]">
      <img
        src={`${SCENE}/background.webp`}
        alt=""
        className={`absolute inset-0 h-full w-full scale-105 object-cover blur-[3px] ${completed ? "" : "grayscale-[60%]"}`}
      />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,248,240,0.55),rgba(246,231,218,0.85))]" />

      {desserts.map((dessert) => (
        <div
          key={dessert.name}
          aria-hidden
          className={`absolute z-0 animate-pop-in ${dessert.className} ${completed ? "" : "opacity-60 grayscale-[50%]"}`}
          style={{ animationDelay: `${dessert.delay}s` }}
        >
          <img
            src={`${SCENE}/${dessert.name}.webp`}
            alt=""
            className="w-full animate-bob drop-shadow-[0_18px_24px_rgba(58,31,20,0.25)]"
            style={{ animationDelay: `${dessert.delay * 2}s` }}
          />
        </div>
      ))}

      {completed && <Sprinkles />}

      <header className="absolute inset-x-0 top-0 z-30 flex items-center px-margin-mobile py-md lg:px-margin-desktop">
        <Link to="/" aria-label="Crave Bake">
          <Logo size={32} />
        </Link>
      </header>

      <main className="relative z-10 flex h-full items-center justify-center overflow-y-auto px-margin-mobile py-[88px]">
        <section className="liquid-glass w-[min(440px,100%)] animate-liquid-in px-md pb-lg pt-xl text-center sm:px-lg">
          <div className="relative mx-auto mb-md h-28 w-28">
            {preparation.cover_photo_url ? (
              <img
                src={preparation.cover_photo_url}
                alt=""
                className={`h-full w-full rounded-full object-cover ring-4 ring-white shadow-[0_12px_30px_rgba(58,31,20,0.25)] ${completed ? "" : "grayscale"}`}
              />
            ) : (
              <span className="flex h-full w-full items-center justify-center rounded-full bg-[#FFF6EC] ring-4 ring-white shadow-[0_12px_30px_rgba(58,31,20,0.18)]">
                <LogoMark size={72} />
              </span>
            )}
            <span
              className={`absolute -bottom-1 -right-1 flex h-10 w-10 items-center justify-center rounded-full ring-4 ring-white ${
                completed ? "bg-[#9c3b24] text-white" : "bg-surface-container-high text-on-surface-variant"
              }`}
            >
              <Icon name={completed ? "check" : "hourglass_empty"} className="text-[22px]" />
            </span>
          </div>

          <p className="relative text-label-sm uppercase tracking-[0.18em] text-[#9c3b24]">
            {completed ? t("cook.finished.eyebrow") : t("cook.abandonedTitle")}
          </p>
          <h1 className="relative mt-xs font-serif text-[44px] font-extrabold leading-[1.05] text-[#2d1810] sm:text-[52px]">
            {completed ? t("cook.finished.lead") : t("cook.finished.abandonedLead")}
            <em className="italic text-[#9c3b24]">{completed ? t("cook.finished.accent") : t("cook.finished.abandonedAccent")}</em>
          </h1>
          <p className="relative mt-sm text-title-lg text-[#3A1F14]">{preparation.recipe_title}</p>

          <div className="relative mt-md flex flex-wrap justify-center gap-xs">
            <Stat icon="check_circle" label={t("recipe.steps")}>
              {t("cook.progress", { done: preparation.completed_steps, total: preparation.total_steps })}
            </Stat>
            {minutes !== null && (
              <Stat icon="schedule" label={t("cook.finished.duration")}>
                {minutes < 1 ? t("cook.finished.underMinute") : formatMinutes(minutes)}
              </Stat>
            )}
            {preparation.finished_at && (
              <Stat icon="event" label={t("cook.finished.date")}>
                {formatDate(preparation.finished_at, language)}
              </Stat>
            )}
          </div>

          <p className="relative mx-auto mt-md max-w-xs font-serif text-body-lg italic text-[#3A1F14]/80">
            {completed ? t(`cook.finished.signoff${signoff + 1}`) : t("cook.finished.abandonedText")}
          </p>

          <div className="relative mt-lg flex flex-col gap-xs sm:flex-row sm:justify-center">
            <Link to={`/recipes/${preparation.recipe_id}`} className="sm:flex-1">
              <Button icon="menu_book" className="w-full">
                {t("explore.viewRecipe")}
              </Button>
            </Link>
            <Link to="/profile/history" className="sm:flex-1">
              <Button variant="secondary" icon="history" className="w-full bg-white/60">
                {t("cook.finished.history")}
              </Button>
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
