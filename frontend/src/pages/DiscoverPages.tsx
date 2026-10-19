import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { discoveryApi, pantryApi, recipesApi } from "../api/endpoints";
import { useErrorMessage, useRecipeCategories, useTags } from "../api/queries";
import type { DiscoverySession, Ingredient, Recommendation, SwipeAction } from "../api/types";
import { useStartCooking } from "../components/CookButton";
import { LogoMark } from "../components/Logo";
import { IngredientPicker } from "../components/Pickers";
import { useToast } from "../components/Toast";
import {
  Button,
  Card,
  Chip,
  Cover,
  EmptyState,
  ErrorState,
  Icon,
  Modal,
  PageHeader,
  Skeleton,
} from "../components/ui";
import { formatMinutes } from "../lib/time";

const INTRO_KEY = "cravebake.discover.introSeen";
const MAX_TAGS = 10;

function readIntroSeen() {
  try {
    return localStorage.getItem(INTRO_KEY) === "1";
  } catch {
    return false;
  }
}

function Intro({ onStart }: { onStart: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-md py-lg text-center">
      <span className="flex h-28 w-28 items-center justify-center rounded-full bg-secondary-container shadow-lift">
        <LogoMark size={76} />
      </span>
      <h1 className="text-display-sm">{t("discover.introTitle")}</h1>
      <p className="text-body-lg text-on-surface-variant">{t("discover.introText")}</p>
      <div className="grid w-full grid-cols-3 gap-sm text-label-sm text-on-surface-variant">
        {[
          ["arrow_back", "discover.gestureDiscard"],
          ["arrow_upward", "discover.gestureCook"],
          ["arrow_forward", "discover.gestureSave"],
        ].map(([icon, key]) => (
          <span key={key} className="flex flex-col items-center gap-xs rounded-lg bg-surface-container-low p-sm">
            <Icon name={icon} className="text-primary" /> {t(key)}
          </span>
        ))}
      </div>
      <Button icon="arrow_forward" onClick={onStart} className="w-full">
        {t("discover.introStart")}
      </Button>
    </div>
  );
}

/** Step 1: what do I have? (pantry or a temporary selection) + filters. */
export function DiscoverStartPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const errorMessage = useErrorMessage();
  const [introSeen, setIntroSeen] = useState(readIntroSeen);
  const [source, setSource] = useState<"pantry" | "selection">("pantry");
  const [picked, setPicked] = useState<Ingredient[]>([]);
  const [minScore, setMinScore] = useState(50);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [tagIds, setTagIds] = useState<string[]>([]);
  const [pantryEmpty, setPantryEmpty] = useState(false);
  const pantry = useQuery({ queryKey: ["pantry"], queryFn: pantryApi.list });
  const categories = useRecipeCategories();
  const tags = useTags();

  const start = useMutation({
    mutationFn: () =>
      discoveryApi.start({
        // Empty = use the pantry. A selection is temporary: never stored in the pantry.
        ingredient_ids: source === "selection" ? picked.map((item) => item.id) : [],
        min_score: minScore / 100,
        category_id: categoryId,
        tag_ids: tagIds,
      }),
    onSuccess: (session) => navigate(`/discover/${session.id}`),
    onError: (error) => {
      if (error instanceof ApiError && error.status === 400 && source === "pantry") setPantryEmpty(true);
    },
  });

  if (!introSeen)
    return (
      <Intro
        onStart={() => {
          try {
            localStorage.setItem(INTRO_KEY, "1");
          } catch {
            // Shown again next time; harmless.
          }
          setIntroSeen(true);
        }}
      />
    );

  if (pantryEmpty)
    return (
      <EmptyState
        icon="kitchen"
        title={t("discover.noIngredientsTitle")}
        text={t("discover.noIngredientsText")}
        action={
          <>
            <Button
              icon="checklist"
              onClick={() => {
                setPantryEmpty(false);
                setSource("selection");
              }}
            >
              {t("discover.pickIngredients")}
            </Button>
            <Link to="/profile/pantry">
              <Button variant="secondary" icon="kitchen">
                {t("discover.fillPantry")}
              </Button>
            </Link>
          </>
        }
      />
    );

  const pantryItems = pantry.data ?? [];
  const canStart = source === "pantry" || picked.length > 0;

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title={t("discover.title")} subtitle={t("discover.subtitle")} />
      <div className="flex flex-col gap-md">
        <Card className="p-md">
          <h2 className="mb-sm text-title-lg">{t("discover.whatDoYouHave")}</h2>
          <div className="mb-sm grid grid-cols-2 gap-sm">
            {(["pantry", "selection"] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={source === option}
                onClick={() => setSource(option)}
                className={`flex flex-col items-start gap-xs rounded-lg border-2 p-sm text-left transition-colors ${
                  source === option ? "border-primary bg-primary-fixed/40" : "border-outline-variant"
                }`}
              >
                <Icon name={option === "pantry" ? "kitchen" : "checklist"} className="text-primary" />
                <span className="text-label-md font-semibold">{t(`discover.source.${option}`)}</span>
                <span className="text-label-sm font-normal text-on-surface-variant">{t(`discover.source.${option}Hint`)}</span>
              </button>
            ))}
          </div>
          {source === "pantry" ? (
            pantry.isLoading ? (
              <Skeleton className="h-10" />
            ) : pantryItems.length ? (
              <div className="flex flex-wrap items-center gap-xs">
                {pantryItems.map((item) => (
                  <Chip key={item.id} tone="success">
                    {item.ingredient.name}
                  </Chip>
                ))}
                <Link to="/profile/pantry" className="text-label-md text-primary">
                  {t("discover.managePantry")}
                </Link>
              </div>
            ) : (
              <p className="text-label-md text-on-surface-variant">
                {t("discover.pantryEmptyHint")}{" "}
                <Link to="/profile/pantry" className="text-primary">
                  {t("discover.fillPantry")}
                </Link>
              </p>
            )
          ) : (
            <div className="flex flex-col gap-sm">
              <IngredientPicker
                excludeIds={picked.map((item) => item.id)}
                onPick={(ingredient) => setPicked((current) => [...current, ingredient])}
              />
              <div className="flex flex-wrap gap-xs">
                {picked.map((item) => (
                  <Chip key={item.id} tone="success" onRemove={() => setPicked((current) => current.filter((x) => x.id !== item.id))}>
                    {item.name}
                  </Chip>
                ))}
              </div>
              <p className="text-label-sm font-normal text-on-surface-variant">{t("discover.selectionTemporary")}</p>
            </div>
          )}
        </Card>

        <Card className="p-md">
          <label className="flex flex-col gap-sm">
            <span className="flex justify-between text-title-lg">
              {t("discover.minScore")} <span className="text-primary">{minScore}%</span>
            </span>
            <input type="range" min={0} max={100} step={10} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} className="accent-primary" />
            <span className="text-label-md font-normal text-on-surface-variant">{t("discover.minScoreHint", { value: minScore })}</span>
          </label>
        </Card>

        <Card className="flex flex-col gap-sm p-md">
          <h2 className="text-title-lg">{t("discover.filters")}</h2>
          <div className="flex flex-wrap gap-xs">
            <Chip active={!categoryId} onClick={() => setCategoryId(null)}>
              {t("explore.allRecipes")}
            </Chip>
            {categories.data?.map((category) => (
              <Chip key={category.id} active={categoryId === category.id} onClick={() => setCategoryId(category.id)}>
                {category.name}
              </Chip>
            ))}
          </div>
          <div className="flex flex-wrap gap-xs">
            {tags.data?.map((tag) => {
              const selected = tagIds.includes(tag.id);
              return (
                <Chip
                  key={tag.id}
                  active={selected}
                  onClick={() =>
                    setTagIds((current) =>
                      selected ? current.filter((x) => x !== tag.id) : current.length < MAX_TAGS ? [...current, tag.id] : current,
                    )
                  }
                >
                  {tag.name}
                </Chip>
              );
            })}
          </div>
        </Card>

        {start.isError && !pantryEmpty && <p className="text-label-md text-error">{errorMessage(start.error)}</p>}
        <Button icon="style" disabled={!canStart} loading={start.isPending} onClick={() => start.mutate()} className="py-md text-body-md">
          {t("discover.start")}
        </Button>
      </div>
    </div>
  );
}

function CompatibilityRing({ score }: { score: number }) {
  const percent = Math.round(score * 100);
  const circumference = 2 * Math.PI * 18;
  return (
    <svg viewBox="0 0 44 44" className="h-12 w-12" role="img" aria-label={`${percent}%`}>
      <circle cx="22" cy="22" r="18" fill="none" strokeWidth="4" className="stroke-surface-container-high" />
      <circle
        cx="22"
        cy="22"
        r="18"
        fill="none"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - score)}
        transform="rotate(-90 22 22)"
        className="stroke-tertiary"
      />
      <text x="22" y="26" textAnchor="middle" className="fill-on-surface text-[11px] font-bold">
        {percent}%
      </text>
    </svg>
  );
}

function SwipeCard({ card, onSwipe }: { card: Recommendation; onSwipe: (action: SwipeAction) => void }) {
  const { t } = useTranslation();
  const [drag, setDrag] = useState({ x: 0, y: 0, active: false });
  const origin = useRef({ x: 0, y: 0 });
  const THRESHOLD = 110;

  const onDown = (event: ReactPointerEvent) => {
    // Let buttons and links inside the card work normally.
    if ((event.target as HTMLElement).closest("a,button")) return;
    origin.current = { x: event.clientX, y: event.clientY };
    setDrag({ x: 0, y: 0, active: true });
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  };
  const onMove = (event: ReactPointerEvent) => {
    if (!drag.active) return;
    setDrag({ x: event.clientX - origin.current.x, y: event.clientY - origin.current.y, active: true });
  };
  const onUp = () => {
    if (!drag.active) return;
    const { x, y } = drag;
    setDrag({ x: 0, y: 0, active: false });
    if (y < -THRESHOLD && Math.abs(y) > Math.abs(x)) onSwipe("selected");
    else if (x > THRESHOLD && !card.is_own) onSwipe("saved");
    else if (x < -THRESHOLD) onSwipe("discarded");
  };
  const hint = drag.y < -60 && Math.abs(drag.y) > Math.abs(drag.x) ? "selected" : drag.x > 60 && !card.is_own ? "saved" : drag.x < -60 ? "discarded" : null;

  return (
    <article
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      style={{
        transform: `translate(${drag.x}px, ${drag.y}px) rotate(${drag.x / 20}deg)`,
        transition: drag.active ? "none" : "transform 250ms ease",
        touchAction: "none",
      }}
      className="relative cursor-grab select-none overflow-hidden rounded-xl bg-surface-container-lowest shadow-lift active:cursor-grabbing"
    >
      {hint && (
        <span
          className={`absolute left-1/2 top-md z-10 -translate-x-1/2 rounded-full px-md py-xs text-label-md font-bold uppercase text-on-primary ${
            hint === "saved" ? "bg-primary" : hint === "selected" ? "bg-tertiary" : "bg-inverse-surface"
          }`}
        >
          {t(`discover.actions.${hint}`)}
        </span>
      )}
      <div className="relative aspect-[4/3]">
        <Cover url={card.cover_photo_url} alt={card.title} className="pointer-events-none h-full w-full" />
        <div className="absolute inset-0 bg-gradient-to-t from-inverse-surface/80 via-transparent to-transparent" />
        {card.is_personalization && (
          <span className="absolute left-sm top-sm flex items-center gap-xs rounded-full bg-primary-container px-sm py-xs text-label-sm text-on-primary">
            <Icon name="auto_awesome" className="text-[14px]" /> {t("discover.yourVersion")}
          </span>
        )}
        <div className="absolute right-sm top-sm flex items-center gap-xs rounded-full bg-surface/95 py-[2px] pl-[2px] pr-sm">
          <CompatibilityRing score={card.compatibility_score} />
          <span className="text-label-sm uppercase text-tertiary">{t("discover.compatible")}</span>
        </div>
        <div className="absolute bottom-sm left-sm right-sm text-inverse-on-surface">
          <h2 className="text-headline-md">{card.title}</h2>
          <p className="flex flex-wrap gap-sm text-label-md">
            {card.prep_time_minutes && (
              <span className="flex items-center gap-xs">
                <Icon name="schedule" className="text-[16px]" /> {formatMinutes(card.prep_time_minutes)}
              </span>
            )}
            {card.difficulty_name && (
              <span className="flex items-center gap-xs">
                <Icon name="signal_cellular_alt" className="text-[16px]" /> {card.difficulty_name}
              </span>
            )}
            {card.is_saved && (
              <span className="flex items-center gap-xs">
                <Icon name="favorite" filled className="text-[16px]" /> {t("discover.alreadySaved")}
              </span>
            )}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-sm p-sm">
        {card.description && <p className="line-clamp-2 text-body-md text-on-surface-variant">{card.description}</p>}
        <div className="rounded-lg bg-surface-container-low p-sm">
          <p className="flex items-center gap-xs text-label-md font-semibold text-tertiary">
            <Icon name="check_circle" className="text-[18px]" /> {t("discover.have", { count: card.matched_ingredients.length })}
          </p>
          <p className="text-label-md font-normal">{card.matched_ingredients.map((item) => item.name).join(", ") || "—"}</p>
        </div>
        {!!card.missing_ingredients.length && (
          <div className="rounded-lg border border-error/30 bg-error-container/40 p-sm">
            <p className="flex items-center gap-xs text-label-md font-semibold text-error">
              <Icon name="cancel" className="text-[18px]" /> {t("discover.missing", { count: card.missing_ingredients.length })}
            </p>
            <p className="text-label-md font-normal">{card.missing_ingredients.map((item) => item.name).join(", ")}</p>
          </div>
        )}
        <p className="flex items-center gap-xs border-t border-outline-variant/50 pt-sm text-label-md">
          <Icon name="inventory_2" className="text-[18px] text-on-surface-variant" />
          {card.has_all_equipment ? (
            <span className="text-tertiary">{t("discover.allEquipment")}</span>
          ) : (
            <span className="text-secondary">{t("discover.needEquipment", { list: card.missing_equipment.map((item) => item.name).join(", ") })}</span>
          )}
        </p>
        <Link to={`/recipes/${card.recipe_id}`} className="self-start text-label-md text-primary">
          {t("explore.viewRecipe")} →
        </Link>
      </div>
    </article>
  );
}

function SessionSummary({ session }: { session: DiscoverySession }) {
  const { t } = useTranslation();
  return (
    <div className="mb-md flex flex-col gap-sm">
      <div className="flex items-start justify-between gap-sm">
        <div className="min-w-0">
          <h1 className="flex flex-wrap items-center gap-x-sm text-headline-md">
            {t("discover.today")}
            <span className="flex items-center gap-xs rounded-full bg-tertiary-fixed px-sm py-[2px] text-label-sm text-on-tertiary-fixed-variant">
              <span className="h-2 w-2 rounded-full bg-tertiary" /> {t("discover.active")}
            </span>
          </h1>
          <p className="text-label-md text-on-surface-variant">
            {t("discover.searchingWith")} <strong className="text-primary">{session.ingredients.map((item) => item.name).join(", ")}</strong>
            {session.ingredient_source === "pantry" && ` (${t("discover.usingPantry")})`}
          </p>
        </div>
        <Link to="/discover/new" aria-label={t("discover.newSearch")}>
          <Button variant="secondary" icon="tune" className="px-sm py-xs">
            <span className="hidden sm:inline">{t("discover.newSearch")}</span>
          </Button>
        </Link>
      </div>
      <div className="flex flex-wrap gap-xs">
        <Chip icon="filter_alt">≥ {Math.round(session.min_score * 100)}%</Chip>
        {session.category && <Chip tone="accent">{session.category.name}</Chip>}
        {session.tags.map((tag) => (
          <Chip key={tag.id} tone="accent">
            {tag.name}
          </Chip>
        ))}
        <Link to={`/discover/${session.id}/results`} className="ml-auto flex items-center gap-xs text-label-md text-primary">
          <Icon name="checklist" className="text-[16px]" /> {t("discover.chosen", { count: session.selected_count })}
        </Link>
      </div>
    </div>
  );
}

/** Step 2: the deck. */
export function DeckPage() {
  const { sessionId = "" } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const startCooking = useStartCooking();
  const [swiped, setSwiped] = useState<Set<string>>(new Set());
  const [chosen, setChosen] = useState<Recommendation | null>(null);

  const session = useQuery({ queryKey: ["discovery", sessionId], queryFn: () => discoveryApi.get(sessionId) });
  // Swiped cards leave the deck server-side: always ask from offset 0 (§13).
  const deck = useQuery({ queryKey: ["discovery", sessionId, "deck"], queryFn: () => discoveryApi.deck(sessionId, 10) });
  const cards = useMemo(() => (deck.data?.items ?? []).filter((card) => !swiped.has(card.recipe_id)), [deck.data, swiped]);
  const current = cards[0];

  useEffect(() => {
    // Preload when ~3 cards are left.
    if (deck.data && cards.length <= 3 && deck.data.total > deck.data.items.length && !deck.isFetching) void deck.refetch();
  }, [cards.length, deck]);

  const swipe = useMutation({
    mutationFn: ({ card, action }: { card: Recommendation; action: SwipeAction }) => discoveryApi.swipe(sessionId, card.recipe_id, action),
    onSuccess: (_result, { action }) => {
      void queryClient.invalidateQueries({ queryKey: ["discovery", sessionId], exact: true });
      if (action === "saved") {
        toast(t("favorites.saved"));
        void queryClient.invalidateQueries({ queryKey: ["portfolio"] });
        void queryClient.invalidateQueries({ queryKey: ["favorites"] });
      }
    },
    onError: (error, { card }) => {
      // 409 = already swiped in this session: it is gone either way.
      if (!(error instanceof ApiError && error.status === 409)) {
        setSwiped((current) => {
          const next = new Set(current);
          next.delete(card.recipe_id);
          return next;
        });
        toast(errorMessage(error), "error");
      }
    },
  });

  const act = (action: SwipeAction) => {
    if (!current || (action === "saved" && current.is_own)) return;
    setSwiped((previous) => new Set(previous).add(current.recipe_id));
    swipe.mutate({ card: current, action });
    if (action === "selected") setChosen(current);
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (chosen || (event.target as HTMLElement).tagName === "INPUT") return;
      if (event.key === "ArrowLeft") act("discarded");
      if (event.key === "ArrowRight") act("saved");
      if (event.key === "ArrowUp") act("selected");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const retryLower = useMutation({
    mutationFn: (s: DiscoverySession) =>
      discoveryApi.start({
        ingredient_ids: s.ingredient_source === "selection" ? s.ingredients.map((item) => item.id) : [],
        min_score: Math.max(0, Math.round((s.min_score - 0.2) * 10) / 10),
        category_id: s.category?.id ?? null,
        tag_ids: s.tags.map((tag) => tag.id),
      }),
    onSuccess: (next) => {
      setSwiped(new Set());
      navigate(`/discover/${next.id}`, { replace: true });
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });

  if (session.isError || deck.isError)
    return <ErrorState message={errorMessage(session.error ?? deck.error)} onRetry={() => void deck.refetch()} />;

  return (
    <div className="mx-auto max-w-xl">
      {session.data ? <SessionSummary session={session.data} /> : <Skeleton className="mb-md h-16" />}
      {deck.isLoading ? (
        <Skeleton className="aspect-[3/4]" />
      ) : !current ? (
        deck.isFetching ? (
          <Skeleton className="aspect-[3/4]" />
        ) : (
          <EmptyState
            icon="search_off"
            title={t("discover.deckEmptyTitle")}
            text={t("discover.deckEmptyText")}
            action={
              <>
                <Link to="/discover/new">
                  <Button icon="checklist">{t("discover.tryOtherIngredients")}</Button>
                </Link>
                {session.data && session.data.min_score > 0 && (
                  <Button variant="secondary" icon="trending_down" loading={retryLower.isPending} onClick={() => retryLower.mutate(session.data!)}>
                    {t("discover.lowerScore")}
                  </Button>
                )}
              </>
            }
          />
        )
      ) : (
        <>
          <div className="relative">
            {cards[1] && <div className="absolute inset-x-sm -bottom-sm top-sm -z-10 rounded-xl bg-surface-container-high shadow-card" />}
            <SwipeCard key={current.recipe_id} card={current} onSwipe={act} />
          </div>
          {/* Sticky above the mobile bottom bar so the actions never fall below the fold. */}
          <div className="sticky bottom-[100px] z-20 mt-md flex items-center justify-center gap-md lg:static">
            <button
              type="button"
              onClick={() => act("discarded")}
              aria-label={t("discover.actions.discarded")}
              className="flex h-14 w-14 items-center justify-center rounded-full bg-surface-container-lowest text-on-surface-variant shadow-card transition-transform hover:scale-105"
            >
              <Icon name="close" className="text-[28px]" />
            </button>
            {!current.is_own && (
              <button
                type="button"
                onClick={() => act("saved")}
                aria-label={t("discover.actions.saved")}
                className="flex h-20 w-20 items-center justify-center rounded-full bg-primary text-on-primary shadow-lift transition-transform hover:scale-105"
              >
                <Icon name="favorite" filled className="text-[36px]" />
              </button>
            )}
            <button
              type="button"
              onClick={() => act("selected")}
              aria-label={t("discover.actions.selected")}
              className="flex h-16 w-16 flex-col items-center justify-center rounded-full bg-tertiary text-on-tertiary shadow-lift transition-transform hover:scale-105"
            >
              <Icon name="soup_kitchen" className="text-[24px]" />
              <span className="text-[10px] font-bold uppercase">{t("recipe.cookShort")}</span>
            </button>
          </div>
          <p className="mt-sm hidden text-center text-label-sm text-on-surface-variant lg:block">{t("discover.keyboardHint")}</p>
        </>
      )}

      <Modal open={!!chosen} onClose={() => setChosen(null)} title={t("discover.chosenTitle")}>
        {chosen && (
          <div className="flex flex-col gap-sm">
            <p className="text-body-lg">{chosen.title}</p>
            <Button icon="soup_kitchen" loading={startCooking.isPending} onClick={() => startCooking.mutate(chosen.recipe_id)}>
              {t("discover.cookNow")}
            </Button>
            <Link to={`/recipes/${chosen.recipe_id}`}>
              <Button variant="secondary" icon="menu_book" className="w-full">
                {t("explore.viewRecipe")}
              </Button>
            </Link>
            <Button variant="ghost" onClick={() => setChosen(null)}>
              {t("discover.keepSwiping")}
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
}

/** Step 3: what I chose in this session. */
export function DiscoverResultsPage() {
  const { sessionId = "" } = useParams();
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [action, setAction] = useState<SwipeAction>("selected");
  const swipes = useQuery({ queryKey: ["discovery", sessionId, "swipes", action], queryFn: () => discoveryApi.swipes(sessionId, action) });
  const recipes = useQueries({
    queries: (swipes.data?.items ?? []).map((swipe) => ({
      queryKey: ["recipe", swipe.recipe_id, "original"],
      queryFn: () => recipesApi.get(swipe.recipe_id, "original"),
      retry: false,
    })),
  });

  return (
    <div className="mx-auto max-w-2xl">
      <Link to={`/discover/${sessionId}`} className="mb-sm inline-flex items-center gap-xs text-label-md text-primary">
        <Icon name="arrow_back" className="text-[18px]" /> {t("discover.backToDeck")}
      </Link>
      <PageHeader title={t("discover.resultsTitle")} />
      <div className="mb-md flex gap-xs">
        {(["selected", "saved", "discarded"] as const).map((item) => (
          <Chip key={item} active={action === item} onClick={() => setAction(item)}>
            {t(`discover.results.${item}`)}
          </Chip>
        ))}
      </div>
      {swipes.isLoading ? (
        <Skeleton className="h-40" />
      ) : swipes.isError ? (
        <ErrorState message={errorMessage(swipes.error)} onRetry={() => void swipes.refetch()} />
      ) : !swipes.data?.items.length ? (
        <EmptyState icon="style" title={t("discover.resultsEmpty")} />
      ) : (
        <ul className="flex flex-col gap-sm">
          {swipes.data.items.map((swipe, index) => {
            const recipe = recipes[index]?.data;
            return (
              <li key={swipe.id}>
                <Link to={`/recipes/${swipe.recipe_id}`}>
                  <Card className="flex items-center gap-sm p-sm transition-shadow hover:shadow-lift">
                    <Cover url={recipe?.cover_photos[0]?.photo_url} alt="" className="h-16 w-16 shrink-0 rounded" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-title-lg">{recipe?.title ?? (recipes[index]?.isError ? t("recipe.notFound") : "…")}</p>
                      <p className="text-label-md text-tertiary">
                        {Math.round(swipe.compatibility_score * 100)}% {t("discover.compatible").toLowerCase()}
                      </p>
                    </div>
                    <Icon name="chevron_right" className="text-on-surface-variant" />
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
