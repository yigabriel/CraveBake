import { useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { kitchenApi, pantryApi, portfolioApi, preparationApi, usersApi } from "../api/endpoints";
import { useErrorMessage } from "../api/queries";
import type { Language, UnitSystem } from "../api/types";
import { useAuth, useUser } from "../auth/AuthContext";
import { Avatar } from "../components/AppShell";
import { ImageUploadButton } from "../components/ImageUploadButton";
import { useToast } from "../components/Toast";
import { Button, Card, Field, Icon, Input, Modal, PageHeader, Segmented } from "../components/ui";
import { PasswordRules, passwordRules } from "./AuthPages";

function WorkshopCard({
  to,
  icon,
  title,
  count,
  preview,
  hint,
}: {
  to: string;
  icon: string;
  title: string;
  count: string;
  preview?: string;
  hint: string;
}) {
  return (
    <Link to={to} className="group">
      <Card className="flex h-full flex-col gap-xs p-md transition-shadow group-hover:shadow-lift">
        <div className="flex items-center justify-between">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-secondary-container">
            <Icon name={icon} className="text-primary" />
          </span>
          <Icon name="chevron_right" className="text-on-surface-variant transition-transform group-hover:translate-x-1" />
        </div>
        <h3 className="text-title-lg">{title}</h3>
        <p className="text-label-md text-primary">{count}</p>
        {preview && <p className="line-clamp-2 text-label-md font-normal text-on-surface-variant">{preview}</p>}
        <p className="mt-auto text-label-sm font-normal text-on-surface-variant">{hint}</p>
      </Card>
    </Link>
  );
}

function Section({ title, icon, children }: { title: string; icon: string; children: ReactNode }) {
  return (
    <Card className="p-md">
      <h2 className="mb-md flex items-center gap-sm text-title-lg">
        <Icon name={icon} className="text-primary" /> {title}
      </h2>
      {children}
    </Card>
  );
}

function EditProfileModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const user = useUser();
  const { setUser } = useAuth();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [fullName, setFullName] = useState(user.full_name);
  const [avatar, setAvatar] = useState<string | null>(user.avatar_url);
  const save = useMutation({
    // Send only what changed (§3).
    mutationFn: () =>
      usersApi.updateProfile({
        ...(fullName.trim() !== user.full_name ? { full_name: fullName.trim() } : {}),
        ...(avatar !== user.avatar_url ? { avatar_url: avatar } : {}),
      }),
    onSuccess: (updated) => {
      setUser(updated);
      toast(t("profile.saved"));
      onClose();
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("profile.edit")}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button loading={save.isPending} disabled={!fullName.trim()} onClick={() => save.mutate()}>
            {t("common.save")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-md">
        <Field label={t("auth.fullName")}>
          <Input value={fullName} maxLength={255} onChange={(e) => setFullName(e.target.value)} />
        </Field>
        {/* The photo is uploaded right away but only saved to the profile with "Save". */}
        <Field label={t("profile.avatar")}>
          <div className="flex items-center gap-md">
            {avatar ? (
              <img src={avatar} alt="" className="h-16 w-16 shrink-0 rounded-full bg-surface-container-high object-cover" />
            ) : (
              <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full bg-surface-container-high text-outline">
                <Icon name="person" className="text-[32px]" />
              </span>
            )}
            <ImageUploadButton purpose="avatar" onUploaded={setAvatar} />
            {avatar && (
              <Button variant="ghost" icon="delete" onClick={() => setAvatar(null)}>
                {t("editor.removePhoto")}
              </Button>
            )}
          </div>
        </Field>
      </div>
    </Modal>
  );
}

function ChangePasswordModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState<string | null>(null);
  const valid = passwordRules(next).every((rule) => rule.ok);
  const change = useMutation({
    mutationFn: () => usersApi.changePassword(current, next),
    onSuccess: () => {
      // The token stays valid after the change.
      toast(t("profile.passwordChanged"));
      setCurrent("");
      setNext("");
      onClose();
    },
    // 400, not 401: a wrong current password must not end the session.
    onError: (caught) =>
      setError(caught instanceof ApiError && caught.status === 400 && caught.message.includes("Current") ? t("profile.wrongPassword") : errorMessage(caught)),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (valid) change.mutate();
  };
  return (
    <Modal open={open} onClose={onClose} title={t("profile.changePassword")}>
      <form onSubmit={submit} className="flex flex-col gap-md">
        <Field label={t("profile.currentPassword")}>
          <Input type="password" required autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </Field>
        <Field label={t("profile.newPassword")} hint={<PasswordRules password={next} />}>
          <Input type="password" required autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        {error && <p className="rounded bg-error-container px-sm py-xs text-label-md text-on-error-container">{error}</p>}
        <div className="flex justify-end gap-sm">
          <Button type="button" variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" loading={change.isPending} disabled={!valid || !current}>
            {t("profile.updatePassword")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function ProfilePage() {
  const { t } = useTranslation();
  const user = useUser();
  const { setUser, logout } = useAuth();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [modal, setModal] = useState<"profile" | "password" | null>(null);

  const summary = useQuery({ queryKey: ["portfolio", "summary"], queryFn: portfolioApi.summary });
  const pantry = useQuery({ queryKey: ["pantry"], queryFn: pantryApi.list });
  const kitchen = useQuery({ queryKey: ["kitchen"], queryFn: kitchenApi.list });
  const inProgress = useQuery({ queryKey: ["preparations", "count", "in_progress"], queryFn: () => preparationApi.list({ status: "in_progress", limit: 1 }) });
  const completed = useQuery({ queryKey: ["preparations", "count", "completed"], queryFn: () => preparationApi.list({ status: "completed", limit: 1 }) });

  const preference = useMutation({
    mutationFn: (change: { units?: UnitSystem; language?: Language }) =>
      change.units ? usersApi.setUnitSystem(change.units) : usersApi.setLanguage(change.language!),
    onSuccess: (updated) => {
      // setUser also switches the interface language right away (§3).
      setUser(updated);
      toast(t("profile.preferencesSaved"));
    },
    onError: (error) => toast(errorMessage(error), "error"),
  });

  const names = (list: string[] | undefined) => list?.slice(0, 4).join(", ") + (list && list.length > 4 ? "…" : "");

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title={t("profile.title")} subtitle={t("profile.subtitle")} />
      <div className="grid gap-gutter lg:grid-cols-[320px_1fr]">
        <div className="flex flex-col gap-gutter">
          <Card className="flex flex-col items-center gap-sm p-md text-center">
            <button type="button" onClick={() => setModal("profile")} className="relative" aria-label={t("profile.edit")}>
              <Avatar size={96} />
              <span className="absolute bottom-0 right-0 flex h-8 w-8 items-center justify-center rounded-full bg-primary text-on-primary shadow-card">
                <Icon name="edit" className="text-[16px]" />
              </span>
            </button>
            <div>
              <h2 className="text-headline-md">{user.full_name}</h2>
              <p className="text-label-md text-on-surface-variant">{user.email}</p>
            </div>
            <div className="grid w-full grid-cols-3 gap-xs border-y border-outline-variant/50 py-sm">
              {[
                [summary.data?.original_count, t("profile.recipes")],
                [summary.data?.personalized_count, t("profile.versions")],
                [summary.data?.saved_count, t("profile.favorites")],
              ].map(([value, label]) => (
                <div key={label}>
                  <p className="text-headline-md">{value ?? "–"}</p>
                  <p className="text-label-sm text-on-surface-variant">{label}</p>
                </div>
              ))}
            </div>
            <Link to="/portfolio" className="w-full">
              <Button variant="secondary" icon="menu_book" className="w-full">
                {t("profile.goToPortfolio")}
              </Button>
            </Link>
          </Card>

          <Section title={t("profile.security")} icon="shield">
            <div className="flex flex-col gap-sm">
              <Button variant="secondary" icon="lock_reset" onClick={() => setModal("password")}>
                {t("profile.changePassword")}
              </Button>
              <Button variant="ghost" icon="logout" className="text-error" onClick={logout}>
                {t("profile.logout")}
              </Button>
              <p className="text-label-sm font-normal text-on-surface-variant">{t("profile.logoutHint")}</p>
            </div>
          </Section>
        </div>

        <div className="flex flex-col gap-gutter">
          <div>
            <h2 className="mb-sm text-headline-md">{t("profile.workshop")}</h2>
            <div className="grid gap-gutter sm:grid-cols-3">
              <WorkshopCard
                to="/profile/pantry"
                icon="kitchen"
                title={t("pantry.title")}
                count={t("profile.pantryCount", { count: pantry.data?.length ?? 0 })}
                preview={names(pantry.data?.map((item) => item.ingredient.name))}
                hint={t("profile.pantryHint")}
              />
              <WorkshopCard
                to="/profile/kitchen"
                icon="countertops"
                title={t("kitchen.title")}
                count={t("profile.kitchenCount", { count: kitchen.data?.length ?? 0 })}
                preview={names(kitchen.data?.map((item) => item.equipment.name))}
                hint={t("profile.kitchenHint")}
              />
              <WorkshopCard
                to="/profile/history"
                icon="history_edu"
                title={t("history.title")}
                count={t("profile.historyCount", { inProgress: inProgress.data?.total ?? 0, completed: completed.data?.total ?? 0 })}
                hint={t("profile.historyHint")}
              />
            </div>
          </div>

          <Section title={t("profile.preferences")} icon="tune">
            <div className="flex flex-col gap-md">
              <div className="flex flex-col gap-xs">
                <span className="text-label-md">{t("profile.unitSystem")}</span>
                <Segmented
                  label={t("profile.unitSystem")}
                  value={user.preferred_unit_system}
                  onChange={(units) => preference.mutate({ units })}
                  options={[
                    { value: "metric", label: t("profile.metricLong") },
                    { value: "us", label: t("profile.usLong") },
                  ]}
                />
                <span className="flex items-center gap-xs text-label-sm font-normal text-on-surface-variant">
                  <Icon name="info" className="text-[16px]" /> {t("profile.unitSystemHint")}
                </span>
              </div>
              <div className="flex flex-col gap-xs">
                <span className="text-label-md">{t("profile.language")}</span>
                <Segmented
                  label={t("profile.language")}
                  value={user.preferred_language}
                  onChange={(language) => preference.mutate({ language })}
                  options={[
                    { value: "es", label: "Español (ES)" },
                    { value: "en", label: "English (EN)" },
                  ]}
                />
                <span className="flex items-center gap-xs text-label-sm font-normal text-on-surface-variant">
                  <Icon name="translate" className="text-[16px]" /> {t("profile.languageHint")}
                </span>
              </div>
            </div>
          </Section>
          <p className="text-center text-label-sm text-on-surface-variant">Crave Bake v{__APP_VERSION__}</p>
        </div>
      </div>

      <EditProfileModal key={`${modal}-profile`} open={modal === "profile"} onClose={() => setModal(null)} />
      <ChangePasswordModal open={modal === "password"} onClose={() => setModal(null)} />
    </div>
  );
}
