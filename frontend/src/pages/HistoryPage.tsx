import { Link, useSearchParams } from "react-router-dom";
import { useInfiniteQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { preparationApi } from "../api/endpoints";
import { useErrorMessage } from "../api/queries";
import type { Language, PreparationStatus } from "../api/types";
import { Button, Card, Cover, EmptyState, ErrorState, Icon, PageHeader, Skeleton } from "../components/ui";
import { formatDate, timeAgo } from "../lib/time";

const TABS: PreparationStatus[] = ["in_progress", "completed", "abandoned"];

export function HistoryPage() {
  const { t, i18n } = useTranslation();
  const language = i18n.language as Language;
  const errorMessage = useErrorMessage();
  const [params, setParams] = useSearchParams();
  const status = (params.get("status") as PreparationStatus) ?? "in_progress";
  const list = useInfiniteQuery({
    queryKey: ["preparations", "history", status],
    queryFn: ({ pageParam }) => preparationApi.list({ status, limit: 20, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined),
  });
  const items = list.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/profile" className="mb-sm inline-flex items-center gap-xs text-label-md text-primary">
        <Icon name="arrow_back" className="text-[18px]" /> {t("profile.title")}
      </Link>
      <PageHeader title={t("history.title")} />
      <div role="tablist" className="mb-md flex gap-xs border-b border-outline-variant/50">
        {TABS.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={status === tab}
            onClick={() => setParams({ status: tab }, { replace: true })}
            className={`border-b-2 px-sm py-sm text-label-md ${status === tab ? "border-primary font-semibold text-primary" : "border-transparent text-on-surface-variant"}`}
          >
            {t(`history.tabs.${tab}`)}
          </button>
        ))}
      </div>
      {list.isLoading ? (
        <Skeleton className="h-48" />
      ) : list.isError ? (
        <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState
          icon="history_edu"
          title={t(`history.empty.${status}`)}
          action={
            <Link to="/">
              <Button icon="explore">{t("nav.explore")}</Button>
            </Link>
          }
        />
      ) : (
        <ul className="flex flex-col gap-sm">
          {items.map((item) => (
            <li key={item.id}>
              <Link to={item.status === "in_progress" ? `/cook/${item.id}` : `/recipes/${item.recipe_id}`}>
                <Card className="flex items-center gap-sm p-sm transition-shadow hover:shadow-lift">
                  <Cover url={item.cover_photo_url} alt="" className="h-20 w-20 shrink-0 rounded" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-title-lg">{item.recipe_title}</p>
                    <p className="text-label-md text-on-surface-variant">
                      {t("cook.progress", { done: item.completed_steps, total: item.total_steps })}
                    </p>
                    <div className="mt-xs h-1.5 overflow-hidden rounded-full bg-surface-container-high">
                      <div
                        className={`h-full rounded-full ${item.status === "completed" ? "bg-tertiary" : "bg-primary"}`}
                        style={{ width: `${item.total_steps ? (item.completed_steps / item.total_steps) * 100 : 0}%` }}
                      />
                    </div>
                    <p className="mt-xs text-label-sm font-normal text-on-surface-variant">
                      {item.finished_at
                        ? t("history.finishedOn", { date: formatDate(item.finished_at, language) })
                        : t("history.startedAgo", { when: timeAgo(item.started_at, language) })}
                    </p>
                  </div>
                  {item.status === "in_progress" ? (
                    <span className="flex items-center gap-xs rounded-full bg-tertiary px-sm py-xs text-label-md text-on-tertiary">
                      {t("cook.resume")}
                    </span>
                  ) : (
                    <Icon name="chevron_right" className="text-on-surface-variant" />
                  )}
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {list.hasNextPage && (
        <div className="mt-md flex justify-center">
          <Button variant="secondary" loading={list.isFetchingNextPage} onClick={() => void list.fetchNextPage()}>
            {t("explore.loadMore")}
          </Button>
        </div>
      )}
    </div>
  );
}
