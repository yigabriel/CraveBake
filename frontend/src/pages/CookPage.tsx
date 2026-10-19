import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { preparationApi } from "../api/endpoints";
import { useErrorMessage } from "../api/queries";
import type { DisplayUnitSystem, Language, PreparationDetail, PreparedStep } from "../api/types";
import { useUser } from "../auth/AuthContext";
import { useToast } from "../components/Toast";
import { Button, ErrorState, Icon, IconButton, Modal, Skeleton } from "../components/ui";
import { askNotificationPermission, keepScreenOn, ringAlarm } from "../lib/alarm";
import { formatQuantity, scale, unitLabel } from "../lib/quantities";
import { formatClock, formatDate } from "../lib/time";
import { UnitSystemToggle } from "./RecipeDetailPage";

/**
 * Seconds left per running timer, ticking locally once a second (never polling the API).
 * Anchored to `timer_remaining_seconds` at the moment the response arrived, so a skewed
 * device clock does not matter; reloading recomputes from the API, so timers survive.
 */
function useCountdowns(preparation: PreparationDetail | undefined, receivedAt: number) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const left: Record<number, number> = {};
  for (const step of preparation?.steps ?? []) {
    if (step.timer_remaining_seconds !== null && step.timer_started_at)
      left[step.step_number] = Math.max(0, step.timer_remaining_seconds - (now - receivedAt) / 1000);
  }
  return left;
}

function TimerRing({ total, left }: { total: number; left: number | undefined }) {
  const running = left !== undefined && left > 0;
  const progress = left === undefined ? 1 : left / total;
  const circumference = 2 * Math.PI * 90;
  return (
    <div className="relative mx-auto h-56 w-56">
      <svg viewBox="0 0 200 200" className="h-full w-full -rotate-90">
        <circle cx="100" cy="100" r="90" fill="none" strokeWidth="10" className="stroke-surface-container-high" />
        <circle
          cx="100"
          cy="100"
          r="90"
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - progress)}
          className={`stroke-tertiary-container transition-[stroke-dashoffset] duration-1000 ${left === 0 ? "stroke-error" : ""}`}
        />
      </svg>
      <span
        className={`absolute inset-0 flex items-center justify-center text-[44px] font-bold tabular-nums ${left === 0 ? "text-error" : ""}`}
        aria-live={running ? "off" : "polite"}
      >
        {formatClock(left ?? total)}
      </span>
    </div>
  );
}

function IngredientsPanel({
  preparation,
  units,
  onUnits,
  servings,
  onServings,
  language,
}: {
  preparation: PreparationDetail;
  units: DisplayUnitSystem;
  onUnits: (value: DisplayUnitSystem) => void;
  servings: number;
  onServings: (value: number) => void;
  language: Language;
}) {
  const { t } = useTranslation();
  // "Already used" checks are local (§14): the API does not store them.
  const [used, setUsed] = useState<Set<number>>(new Set());
  return (
    <div className="flex flex-col gap-sm">
      <UnitSystemToggle value={units} onChange={onUnits} />
      {preparation.servings && (
        <div className="flex items-center justify-between rounded-lg bg-surface-container-low p-sm">
          <span className="text-label-md">{t("recipe.servings")}</span>
          <div className="flex items-center gap-xs">
            <IconButton icon="remove" label={t("recipe.fewer")} disabled={servings <= 1} onClick={() => onServings(servings - 1)} />
            <span className="w-8 text-center text-title-lg">{servings}</span>
            <IconButton icon="add" label={t("recipe.more")} onClick={() => onServings(servings + 1)} />
          </div>
        </div>
      )}
      <ul className="flex flex-col gap-xs">
        {preparation.ingredients.map((line, index) => {
          const quantity = scale(line.quantity, preparation.servings, servings);
          const done = used.has(index);
          return (
            <li key={`${line.ingredient_id}-${index}`}>
              <label className={`flex items-start gap-sm rounded-lg bg-surface-container-lowest p-sm text-body-lg ${done ? "opacity-50" : ""}`}>
                <input
                  type="checkbox"
                  checked={done}
                  onChange={() =>
                    setUsed((current) => {
                      const next = new Set(current);
                      if (next.has(index)) next.delete(index);
                      else next.add(index);
                      return next;
                    })
                  }
                  className="mt-1 h-6 w-6 accent-primary"
                />
                <span className={done ? "line-through" : ""}>
                  <strong className="text-primary">
                    {formatQuantity(quantity, line.unit_abbreviation, language)} {unitLabel(line.unit_abbreviation, language)}
                  </strong>{" "}
                  {line.ingredient_name}
                  {line.converted && (
                    <span className="ml-xs text-label-md text-on-surface-variant">
                      · {formatQuantity(scale(line.original_quantity, preparation.servings, servings), line.original_unit_abbreviation, language)}{" "}
                      {unitLabel(line.original_unit_abbreviation, language)}
                    </span>
                  )}
                  {line.notes && <span className="block text-label-md italic text-on-surface-variant">{line.notes}</span>}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function FinishedView({ preparation }: { preparation: PreparationDetail }) {
  const { t, i18n } = useTranslation();
  const completed = preparation.status === "completed";
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-md py-lg text-center">
      <span className={`flex h-24 w-24 items-center justify-center rounded-full ${completed ? "bg-tertiary-fixed" : "bg-surface-container-high"}`}>
        <Icon name={completed ? "celebration" : "do_not_disturb_on"} className={`text-[48px] ${completed ? "text-tertiary" : "text-on-surface-variant"}`} />
      </span>
      <h1 className="text-display-sm">{completed ? t("cook.doneTitle") : t("cook.abandonedTitle")}</h1>
      <p className="text-body-lg text-on-surface-variant">
        {preparation.recipe_title} · {t("cook.progress", { done: preparation.completed_steps, total: preparation.total_steps })}
        {preparation.finished_at && ` · ${formatDate(preparation.finished_at, i18n.language as Language)}`}
      </p>
      <div className="flex flex-wrap justify-center gap-sm">
        <Link to={`/recipes/${preparation.recipe_id}`}>
          <Button variant="secondary" icon="menu_book">
            {t("explore.viewRecipe")}
          </Button>
        </Link>
        <Link to="/profile/history">
          <Button icon="history">{t("history.title")}</Button>
        </Link>
      </div>
    </div>
  );
}

export function CookPage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const user = useUser();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [units, setUnits] = useState<DisplayUnitSystem>(user.preferred_unit_system);
  const [servings, setServings] = useState<number | null>(null);
  const [panel, setPanel] = useState<"ingredients" | "steps" | null>(null);
  const [confirm, setConfirm] = useState<"finish" | "abandon" | null>(null);
  const receivedAt = useRef(Date.now());
  const alarmed = useRef(new Set<string>());

  const key = ["preparation", id, units];
  const query = useQuery({
    queryKey: key,
    queryFn: async () => {
      const detail = await preparationApi.get(id, units);
      receivedAt.current = Date.now();
      return detail;
    },
    placeholderData: keepPreviousData,
  });
  const preparation = query.data;
  const left = useCountdowns(preparation, receivedAt.current);

  // Every action returns the whole updated preparation: render straight from it (§14).
  const act = useMutation({
    mutationFn: (run: () => Promise<PreparationDetail>) => run(),
    onSuccess: (detail) => {
      receivedAt.current = Date.now();
      queryClient.setQueryData(key, detail);
      void queryClient.invalidateQueries({ queryKey: ["preparations"] });
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });

  const active = preparation?.status === "in_progress";
  useEffect(() => (active ? keepScreenOn() : undefined), [active]);

  // Ring once per timer run, for any step (not only the one on screen).
  useEffect(() => {
    if (!preparation || !active) return;
    for (const step of preparation.steps) {
      const runId = `${step.step_number}@${step.timer_started_at}`;
      if (left[step.step_number] === 0 && step.timer_started_at && !alarmed.current.has(runId)) {
        alarmed.current.add(runId);
        // Timers that had already ended before opening the page do not ring.
        if (step.timer_remaining_seconds !== 0) ringAlarm(t("cook.timerDoneTitle"), t("cook.timerDoneBody", { n: step.step_number, title: step.title ?? "" }));
      }
    }
  });

  if (query.isLoading) return <Skeleton className="h-[70vh]" />;
  if (query.isError || !preparation) return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  if (!active) return <FinishedView preparation={preparation} />;

  const total = preparation.total_steps;
  // When every step is done the API has no current step: stay on the last one.
  const shownNumber = preparation.current_step_number ?? total;
  const step: PreparedStep | undefined = preparation.steps.find((s) => s.step_number === shownNumber);
  const percent = total ? Math.round((preparation.completed_steps / total) * 100) : 0;
  const shownServings = servings ?? preparation.servings ?? 1;

  const goTo = (n: number) => {
    act.mutate(() => preparationApi.goTo(id, n, units));
  };
  const startTimer = async (n: number) => {
    await askNotificationPermission();
    act.mutate(() => preparationApi.startTimer(id, n, units));
  };
  const exit = () => {
    toast(t("cook.savedForLater"), "info");
    navigate(`/recipes/${preparation.recipe_id}`);
  };

  return (
    <div className="fixed inset-0 z-[55] flex flex-col bg-surface">
      <header className="flex items-center gap-sm border-b border-outline-variant/40 px-margin-mobile py-sm lg:px-margin-desktop">
        <IconButton icon="close" label={t("cook.exit")} onClick={exit} />
        <div className="flex-1">
          <div className="flex justify-between text-label-md">
            <span>{t("cook.stepOf", { n: shownNumber, total })}</span>
            <span className="text-primary">{percent}%</span>
          </div>
          <div className="mt-xs h-2 overflow-hidden rounded-full bg-surface-container-high">
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${percent}%` }} />
          </div>
        </div>
        <IconButton icon="format_list_numbered" label={t("recipe.steps")} onClick={() => setPanel("steps")} />
        <IconButton icon="grocery" label={t("recipe.ingredients")} onClick={() => setPanel("ingredients")} className="lg:hidden" />
      </header>

      <div className="flex min-h-0 flex-1">
        <main className="flex-1 overflow-y-auto px-margin-mobile py-md lg:px-margin-desktop">
          {step ? (
            <div className="mx-auto flex max-w-2xl flex-col gap-md text-center">
              {step.photo_url && <img src={step.photo_url} alt="" className="max-h-72 w-full rounded-xl object-cover shadow-card" />}
              <div>
                <p className="text-label-sm uppercase text-primary">{t("cook.step", { n: step.step_number })}</p>
                {step.title && <h1 className="text-display-sm">{step.title}</h1>}
              </div>
              <p className="whitespace-pre-line text-left text-body-lg sm:text-center lg:text-[22px] lg:leading-9">{step.instructions}</p>

              {step.timer_seconds && (
                <div className="flex flex-col items-center gap-sm">
                  <TimerRing total={step.timer_seconds} left={left[step.step_number]} />
                  {/* No pause / +5 min: the API only starts or restarts a fixed-length timer. */}
                  <Button
                    variant={left[step.step_number] === undefined ? "primary" : "secondary"}
                    icon={left[step.step_number] === undefined ? "play_arrow" : "restart_alt"}
                    loading={act.isPending}
                    onClick={() => void startTimer(step.step_number)}
                  >
                    {left[step.step_number] === undefined ? t("cook.startTimer") : t("cook.restartTimer")}
                  </Button>
                </div>
              )}

              <label className="mx-auto flex cursor-pointer items-center gap-sm rounded-full bg-surface-container-low px-md py-sm text-body-md">
                <input
                  type="checkbox"
                  checked={step.is_completed}
                  disabled={act.isPending}
                  onChange={() =>
                    act.mutate(() =>
                      step.is_completed ? preparationApi.uncomplete(id, step.step_number, units) : preparationApi.complete(id, step.step_number, units),
                    )
                  }
                  className="h-6 w-6 accent-tertiary"
                />
                {t("cook.markDone")}
              </label>
            </div>
          ) : (
            <p className="text-center text-body-lg text-on-surface-variant">{t("recipe.noSteps")}</p>
          )}
        </main>

        <aside className="hidden w-96 overflow-y-auto border-l border-outline-variant/40 bg-surface-container-low p-md lg:block">
          <h2 className="mb-sm text-headline-md">{t("recipe.ingredients")}</h2>
          <IngredientsPanel
            preparation={preparation}
            units={units}
            onUnits={setUnits}
            servings={shownServings}
            onServings={setServings}
            language={language}
          />
        </aside>
      </div>

      <footer className="flex items-center gap-sm border-t border-outline-variant/40 px-margin-mobile py-sm lg:px-margin-desktop">
        <Button variant="secondary" icon="arrow_back" disabled={shownNumber <= 1 || act.isPending} onClick={() => goTo(shownNumber - 1)} className="py-md">
          <span className="hidden sm:inline">{t("common.previous")}</span>
        </Button>
        <span className="flex-1" />
        {shownNumber < total ? (
          <Button icon="arrow_forward" disabled={act.isPending} onClick={() => goTo(shownNumber + 1)} className="flex-row-reverse py-md">
            {t("common.next")}
          </Button>
        ) : (
          <Button variant="tertiary" icon="check" onClick={() => setConfirm("finish")} className="py-md">
            {t("cook.finish")}
          </Button>
        )}
      </footer>

      <Modal open={panel === "ingredients"} onClose={() => setPanel(null)} title={t("recipe.ingredients")}>
        <IngredientsPanel
          preparation={preparation}
          units={units}
          onUnits={setUnits}
          servings={shownServings}
          onServings={setServings}
          language={language}
        />
      </Modal>

      <Modal open={panel === "steps"} onClose={() => setPanel(null)} title={t("recipe.steps")}>
        <ol className="flex flex-col gap-xs">
          {preparation.steps.map((s) => (
            <li key={s.step_number}>
              <button
                type="button"
                onClick={() => {
                  setPanel(null);
                  goTo(s.step_number);
                }}
                className={`flex w-full items-center gap-sm rounded-lg p-sm text-left ${s.is_current ? "bg-primary-fixed" : "hover:bg-surface-container-high"}`}
              >
                <Icon name={s.is_completed ? "check_circle" : "radio_button_unchecked"} filled={s.is_completed} className={s.is_completed ? "text-tertiary" : "text-outline"} />
                <span className="flex-1 text-body-md">
                  {s.step_number}. {s.title ?? s.instructions.slice(0, 60)}
                </span>
                {left[s.step_number] !== undefined && (
                  <span className={`text-label-md tabular-nums ${left[s.step_number] === 0 ? "text-error" : "text-tertiary"}`}>
                    {formatClock(left[s.step_number])}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ol>
        <div className="mt-md flex flex-col gap-xs border-t border-outline-variant/50 pt-md">
          <Button variant="tertiary" icon="check" onClick={() => setConfirm("finish")}>
            {t("cook.finish")}
          </Button>
          <Button variant="ghost" icon="do_not_disturb_on" className="text-error" onClick={() => setConfirm("abandon")}>
            {t("cook.abandon")}
          </Button>
        </div>
      </Modal>

      <Modal
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm === "abandon" ? t("cook.abandonTitle") : t("cook.finishTitle")}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirm(null)}>
              {t("common.cancel")}
            </Button>
            <Button
              variant={confirm === "abandon" ? "danger" : "tertiary"}
              loading={act.isPending}
              onClick={() => {
                const run = confirm === "abandon" ? () => preparationApi.abandon(id, units) : () => preparationApi.finish(id, units);
                setConfirm(null);
                setPanel(null);
                act.mutate(run);
              }}
            >
              {confirm === "abandon" ? t("cook.abandon") : t("cook.finish")}
            </Button>
          </>
        }
      >
        <p className="text-body-md">
          {confirm === "abandon"
            ? t("cook.abandonText")
            : preparation.completed_steps < total
              ? t("cook.finishPending", { count: total - preparation.completed_steps })
              : t("cook.finishText")}
        </p>
      </Modal>
    </div>
  );
}
