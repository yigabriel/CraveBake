import { useEffect, type CSSProperties } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Logo, LogoMark } from "../components/Logo";
import { Button } from "../components/ui";

const SCENE = "/images/auth-scene";

// The same bakery as the sign-in scene, scattered around the empty plate.
const DESSERTS = [
  { name: "macarons", className: "-left-8 top-24 w-28 sm:left-[5%] sm:top-[16%] sm:w-36 lg:w-44", delay: 0 },
  { name: "croissant", className: "-right-10 top-20 w-32 sm:right-[6%] sm:top-[12%] sm:w-44 lg:w-52", delay: 0.2 },
  { name: "apple-pie", className: "-left-10 bottom-8 w-36 sm:left-[7%] sm:bottom-[8%] sm:w-48 lg:w-56", delay: 0.4 },
  { name: "flan", className: "-right-6 bottom-12 w-28 sm:right-[8%] sm:bottom-[10%] sm:w-36 lg:w-44", delay: 0.6 },
];

// Crumbs falling from the bite: fixed positions, so the scene is the same on every render.
const CRUMBS = [
  { x: 72, size: 10, delay: 0, drift: 18 },
  { x: 80, size: 7, delay: 0.5, drift: -10 },
  { x: 66, size: 6, delay: 1.1, drift: 26 },
  { x: 76, size: 9, delay: 1.6, drift: 6 },
  { x: 84, size: 5, delay: 2.2, drift: -18 },
];

/** Robots should not index a page that does not exist. */
function useNoIndex(title: string) {
  useEffect(() => {
    const previousTitle = document.title;
    const robots = document.createElement("meta");
    robots.name = "robots";
    robots.content = "noindex";
    document.head.appendChild(robots);
    document.title = title;
    return () => {
      robots.remove();
      document.title = previousTitle;
    };
  }, [title]);
}

/**
 * Any address that matches no page. The "0" of 404 is the bitten cookie of the logo, still
 * dropping crumbs: someone ate this page.
 */
export function NotFoundPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  useNoIndex(t("notFound.documentTitle"));

  return (
    <div className="fixed inset-0 overflow-hidden bg-[#F6E7DA]">
      <img src={`${SCENE}/background.webp`} alt="" className="absolute inset-0 h-full w-full scale-105 object-cover blur-[3px]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(255,248,240,0.7),rgba(246,231,218,0.9))]" />

      {DESSERTS.map((dessert) => (
        <div key={dessert.name} aria-hidden className={`absolute animate-pop-in ${dessert.className}`} style={{ animationDelay: `${dessert.delay}s` }}>
          <img
            src={`${SCENE}/${dessert.name}.webp`}
            alt=""
            className="w-full animate-bob drop-shadow-[0_18px_24px_rgba(58,31,20,0.25)]"
            style={{ animationDelay: `${dessert.delay * 2}s` }}
          />
        </div>
      ))}

      <header className="absolute inset-x-0 top-0 z-20 flex items-center px-margin-mobile py-md lg:px-margin-desktop">
        <Link to="/" aria-label="Crave Bake">
          <Logo size={32} />
        </Link>
      </header>

      <main className="relative z-10 flex h-full flex-col items-center justify-center overflow-y-auto px-margin-mobile py-[88px] text-center">
        
        {/* 4 [cookie] 4 — the digits are text, so screen readers still read "404". */}
        <h1 className="mt-sm flex items-center justify-center gap-[2vw] font-serif text-[clamp(96px,22vw,220px)] font-extrabold leading-none text-[#2d1810]">
          <span>4</span>
          <span className="relative inline-block">
            <span className="sr-only">0</span>
            <span aria-hidden className="block h-[0.82em] w-[0.82em] animate-wobble">
              <LogoMark size={200} className="h-full w-full drop-shadow-[0_14px_20px_rgba(58,31,20,0.25)]" />
            </span>
            {CRUMBS.map((crumb, index) => (
              <span
                key={index}
                aria-hidden
                className="crumb absolute top-[45%] rounded-full bg-[#E9A84C]"
                style={{ left: `${crumb.x}%`, width: crumb.size, height: crumb.size, "--drift": `${crumb.drift}px`, animationDelay: `${crumb.delay}s` } as CSSProperties}
              />
            ))}
          </span>
          <span>4</span>
        </h1>

        <section className="liquid-glass mt-md w-[min(460px,100%)] animate-liquid-in px-md py-md sm:px-lg">
          <h2 className="relative font-serif text-[28px] font-extrabold leading-tight text-[#2d1810] sm:text-[34px]">
            {t("notFound.lead")} <em className="italic text-[#9c3b24]">{t("notFound.accent")}</em>
          </h2>
          <p className="relative mt-sm text-body-md text-[#3A1F14]/80">{t("notFound.text")}</p>
          <div className="relative mt-md flex flex-col gap-xs sm:flex-row sm:justify-center">
            <Link to="/" className="sm:flex-1">
              <Button icon="home" className="w-full">
                {t("notFound.home")}
              </Button>
            </Link>
            <Button variant="secondary" icon="arrow_back" className="bg-white/60 sm:flex-1" onClick={() => navigate(-1)}>
              {t("notFound.back")}
            </Button>
          </div>
        </section>
      </main>
    </div>
  );
}
