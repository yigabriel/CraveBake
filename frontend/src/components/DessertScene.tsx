import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";

/**
 * The interactive pastry table behind sign in / sign up.
 *
 * public/images/auth-scene holds the background and each dessert cropped to its
 * visible pixels (from the 2736x1536 layers in design-sources/auth_page). BOXES says
 * where each dessert sat on that canvas, in percent, so the layers recompose
 * exactly at any size. Pointing at a dessert (hover, focus or tap) zooms it 10%,
 * blurs everything behind it and shows its review on a liquid-glass card.
 */

export const DESSERTS = ["cheesecake", "bread", "apple-pie", "cookies", "flan", "croissant", "macarons"] as const;
export type Dessert = (typeof DESSERTS)[number];

type Box = { x: number; y: number; w: number; h: number };

/**
 * x/y/w/h: the image, cropped around every visible pixel (soft shadow included,
 * +24px) in percent of the 2736x1536 canvas. `hit`: the solid dessert only
 * (alpha > 200), in percent of that image — what reacts to the pointer, so the
 * large, overlapping shadow boxes never steal the hover from a neighbour.
 */
const BOXES: Record<Dessert, Box & { hit: Box }> = {
  "apple-pie": { x: 58.662, y: 17.253, w: 21.053, h: 36.654, hit: { x: 5.903, y: 18.117, w: 74.479, h: 73.712 } },
  bread: { x: 70.98, y: 0, w: 24.123, h: 41.862, hit: { x: 7.576, y: 6.221, w: 70.606, h: 84.603 } },
  cheesecake: { x: 54.788, y: 0, w: 21.016, h: 27.995, hit: { x: 7.13, y: 0, w: 73.043, h: 86.512 } },
  cookies: { x: 64.766, y: 43.229, w: 20.395, h: 31.25, hit: { x: 9.677, y: 10, w: 66.487, h: 70.208 } },
  croissant: { x: 60.307, y: 61.784, w: 21.784, h: 33.984, hit: { x: 7.047, y: 7.471, w: 71.644, h: 70.69 } },
  flan: { x: 78.984, y: 31.315, w: 21.016, h: 36.068, hit: { x: 11.13, y: 12.455, w: 73.391, h: 74.007 } },
  macarons: { x: 75.146, y: 63.216, w: 24.854, h: 36.784, hit: { x: 11.471, y: 6.195, w: 76.029, h: 81.416 } },
};
const percent = (box: Box): CSSProperties => ({ left: `${box.x}%`, top: `${box.y}%`, width: `${box.w}%`, height: `${box.h}%` });
const RATIO = "2736 / 1536";
const SRC = "/images/auth-scene";
const BLUR = "blur(6px) saturate(0.9) brightness(0.97)";

function Stars() {
  return (
    <span aria-hidden className="flex gap-[2px] text-[#E9A84C]">
      {Array.from({ length: 5 }, (_, i) => (
        <svg key={i} viewBox="0 0 20 20" className="h-4 w-4 fill-current">
          <path d="M10 1.6l2.6 5.3 5.8.8-4.2 4.1 1 5.8L10 14.9 4.8 17.6l1-5.8L1.6 7.7l5.8-.8z" />
        </svg>
      ))}
    </span>
  );
}

/** Translucent "liquid glass": blurred backdrop, specular highlight, soft inner edges. */
export function ReviewCard({ dessert, style, compact = false }: { dessert: Dessert; style?: CSSProperties; compact?: boolean }) {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-live="polite"
      style={style}
      className={`liquid-glass pointer-events-none animate-liquid-in ${compact ? "p-sm" : "w-[min(340px,calc(100vw-32px))] p-md"}`}
    >
      <div className="relative flex items-center justify-between gap-sm">
        <Stars />
        <span className="text-label-sm text-[#3A1F14]/60">10/10</span>
      </div>
      <p
        key={dessert}
        className={`relative mt-xs font-serif font-semibold italic leading-none text-primary animate-craving ${compact ? "text-[28px]" : "text-[38px]"}`}
      >
        {t(`auth.desserts.${dessert}.name`)}
      </p>
      <p className={`relative mt-sm text-[#3A1F14] ${compact ? "text-label-md" : "text-body-md"}`}>
        “{t(`auth.desserts.${dessert}.review`)}”
      </p>
      <p className="relative mt-sm text-label-sm text-[#3A1F14]/70">— {t(`auth.desserts.${dessert}.author`)}</p>
    </div>
  );
}

function Stage({ className, style, children }: { className?: string; style: CSSProperties; children: React.ReactNode }) {
  return (
    <div className={`absolute ${className ?? ""}`} style={{ aspectRatio: RATIO, ...style }}>
      {children}
    </div>
  );
}

/**
 * `variant="cover"`: fills its (fixed, full-screen) parent like object-fit: cover,
 * anchored right, where the desserts are. `variant="banner"`: fills a short
 * mobile banner by height, anchored right.
 */
export function DessertScene({
  active,
  onActive,
  variant,
}: {
  active: Dessert | null;
  onActive: (dessert: Dessert | null) => void;
  variant: "cover" | "banner";
}) {
  const { t } = useTranslation();
  const buttons = useRef<Partial<Record<Dessert, HTMLButtonElement | null>>>({});
  const [card, setCard] = useState<CSSProperties | null>(null);

  const geometry: CSSProperties =
    variant === "cover"
      ? { right: 0, top: "50%", transform: "translateY(-50%)", width: "max(100vw, calc(100vh * 2736 / 1536))" }
      : // The desserts sit around x = 78% of the canvas: center that point in the banner
        // (0.78 * 2736 / 1536 = 1.3894), but never leave a gap at the right edge.
        // The banner's height (--scene-h) is set by the parent.
        {
          left: "max(calc(100% - 1.78125 * var(--scene-h)), calc(50% - 1.3894 * var(--scene-h)))",
          top: 0,
          height: "100%",
        };

  // Place the card beside the dessert, on the side with room, kept inside the viewport.
  const place = useCallback(() => {
    if (variant !== "cover" || !active) return setCard(null);
    const box = buttons.current[active]?.getBoundingClientRect();
    if (!box) return;
    const width = Math.min(340, window.innerWidth - 32);
    const height = 260;
    const gap = 24;
    const right = box.right + gap + width <= window.innerWidth - 16;
    const left = right ? box.right + gap : Math.max(16, box.left - gap - width);
    const top = Math.min(Math.max(16, box.top + box.height / 2 - height / 2), window.innerHeight - height - 16);
    setCard({ position: "fixed", left, top, zIndex: 40 });
  }, [active, variant]);

  useLayoutEffect(place, [place]);
  useEffect(() => {
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [place]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onActive(null);
    // A tap anywhere but on a dessert closes the review (touch screens never "leave").
    const onPointerDown = (event: PointerEvent) =>
      !(event.target as HTMLElement).closest("[data-dessert]") && onActive(null);
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointerDown);
    };
  }, [onActive]);

  const blurred = (dessert: Dessert | null) => (active && dessert !== active ? BLUR : "none");

  return (
    <>
      <Stage style={geometry} className="pointer-events-none">
        <img
          src={`${SRC}/background.webp`}
          alt=""
          className="h-full w-full object-cover transition-[filter] duration-500"
          style={{ filter: blurred(null) }}
        />
      </Stage>
      {/* The cream fade that keeps the form legible sits between the table and the desserts. */}
      {variant === "cover" && (
        <div
          className="pointer-events-none absolute inset-y-0 left-0 w-[58%]"
          style={{ background: "linear-gradient(90deg, #FBF6EE 50%, #FBF6EEcc 72%, transparent)" }}
        />
      )}
      <Stage style={geometry} className="pointer-events-none">
        {DESSERTS.map((dessert) => {
          const box = BOXES[dessert];
          const isActive = active === dessert;
          return (
            <div
              key={dessert}
              className="absolute transition-[transform,filter] duration-500 ease-[cubic-bezier(.2,.8,.2,1)] motion-reduce:transition-none"
              style={{
                ...percent(box),
                transform: isActive ? "scale(1.1)" : "none",
                filter: isActive ? "drop-shadow(0 18px 28px rgba(58,31,20,.22))" : blurred(dessert),
                zIndex: isActive ? 20 : 10,
              }}
            >
              <img src={`${SRC}/${dessert}.webp`} alt="" draggable={false} className="h-full w-full select-none object-contain" />
              <button
                ref={(element) => {
                  buttons.current[dessert] = element;
                }}
                type="button"
                aria-label={t(`auth.desserts.${dessert}.name`)}
                aria-pressed={isActive}
                onPointerEnter={(event) => event.pointerType === "mouse" && onActive(dessert)}
                onPointerLeave={(event) => event.pointerType === "mouse" && onActive(null)}
                onFocus={() => onActive(dessert)}
                onBlur={() => onActive(null)}
                // Touch and pen have no hover: a tap toggles (a mouse click must not undo its hover).
                onPointerUp={(event) => event.pointerType !== "mouse" && onActive(isActive ? null : dessert)}
                // Keyboard Enter/Space (detail 0) toggles too.
                onClick={(event) => event.detail === 0 && onActive(isActive ? null : dessert)}
                data-dessert
                className="pointer-events-auto absolute rounded-full outline-none focus-visible:ring-4 focus-visible:ring-primary/40"
                style={percent(box.hit)}
              />
            </div>
          );
        })}
      </Stage>
      {variant === "cover" && active && card && <ReviewCard dessert={active} style={card} />}
    </>
  );
}
