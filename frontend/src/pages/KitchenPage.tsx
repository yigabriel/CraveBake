import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { catalogApi, kitchenApi } from "../api/endpoints";
import { useErrorMessage } from "../api/queries";
import type { Equipment, EquipmentType, UserEquipment } from "../api/types";
import { EquipmentPicker } from "../components/Pickers";
import { useToast } from "../components/Toast";
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorState,
  Field,
  Icon,
  IconButton,
  Input,
  inputClass,
  Modal,
  PageHeader,
  Skeleton,
} from "../components/ui";
import { EquipmentIcon } from "../lib/equipment";

const TYPES: EquipmentType[] = ["mold", "utensil", "appliance", "other"];
const TYPE_ICONS: Record<EquipmentType, string> = {
  mold: "cake",
  utensil: "flatware",
  appliance: "kitchen",
  other: "category",
};
const KEY = ["kitchen"];

/**
 * Optimistic kitchen edits: the list changes on screen at once and the request
 * runs behind it (Render can take a while). A failure puts the list back.
 */
function useKitchenMutations() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();

  const rollback = (previous: UserEquipment[] | undefined, error: unknown) => {
    queryClient.setQueryData(KEY, previous);
    toast(errorMessage(error), "error");
  };

  const upsert = useMutation({
    mutationFn: (input: { equipment: Equipment; quantity: number; notes: string | null }) =>
      kitchenApi.upsert({ equipment_id: input.equipment.id, quantity: input.quantity, notes: input.notes }),
    onMutate: async ({ equipment, quantity, notes }) => {
      await queryClient.cancelQueries({ queryKey: KEY });
      const previous = queryClient.getQueryData<UserEquipment[]>(KEY);
      const optimistic: UserEquipment = {
        id: `optimistic-${equipment.id}`,
        equipment,
        quantity,
        notes,
        updated_at: new Date().toISOString(),
      };
      queryClient.setQueryData<UserEquipment[]>(KEY, (list = []) =>
        list.some((item) => item.equipment.id === equipment.id)
          ? list.map((item) => (item.equipment.id === equipment.id ? { ...item, quantity, notes } : item))
          : [...list, optimistic],
      );
      return { previous };
    },
    // The server's row replaces the optimistic one: no list refetch per click.
    onSuccess: (saved) =>
      queryClient.setQueryData<UserEquipment[]>(KEY, (list = []) =>
        list.map((item) => (item.equipment.id === saved.equipment.id ? saved : item)),
      ),
    onError: (error, _input, context) => rollback(context?.previous, error),
  });

  const remove = useMutation({
    mutationFn: (equipmentId: string) => kitchenApi.remove(equipmentId),
    onMutate: async (equipmentId) => {
      await queryClient.cancelQueries({ queryKey: KEY });
      const previous = queryClient.getQueryData<UserEquipment[]>(KEY);
      queryClient.setQueryData<UserEquipment[]>(KEY, (list = []) => list.filter((item) => item.equipment.id !== equipmentId));
      return { previous };
    },
    onError: (error, _id, context) => rollback(context?.previous, error),
  });

  return { upsert, remove };
}

/** Register a piece of equipment: new to the catalog (name unique) and/or into my kitchen. */
function EquipmentModal({ onClose, existing }: { onClose: () => void; existing: UserEquipment | null }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { upsert } = useKitchenMutations();
  const [picked, setPicked] = useState<Equipment | null>(existing?.equipment ?? null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<EquipmentType>("utensil");
  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState(existing?.quantity ?? 1);
  const [notes, setNotes] = useState(existing?.notes ?? "");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      // 409 if the name already exists: the user should pick it from the search instead.
      const equipment = creating
        ? await catalogApi.createEquipment({ name: name.trim(), equipment_type: type, description: description.trim() || null })
        : picked;
      if (!equipment) return;
      upsert.mutate({ equipment, quantity, notes: notes.trim() || null });
      toast(existing ? t("kitchen.updated") : t("kitchen.added", { name: equipment.name }));
      onClose();
    } catch (error) {
      toast(errorMessage(error), "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={existing ? existing.equipment.name : t("kitchen.register")}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button loading={saving} disabled={creating ? !name.trim() : !picked} onClick={() => void save()}>
            {existing ? t("common.save") : t("kitchen.addToKitchen")}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-md">
        {!existing &&
          (creating ? (
            <>
              <Field label={t("kitchen.name")}>
                <Input value={name} maxLength={150} autoFocus onChange={(e) => setName(e.target.value)} />
              </Field>
              <Field label={t("kitchen.type")}>
                <select value={type} onChange={(e) => setType(e.target.value as EquipmentType)} className={inputClass}>
                  {TYPES.map((value) => (
                    <option key={value} value={value}>
                      {t(`kitchen.types.${value}`)}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t("kitchen.description")}>
                <Input value={description} maxLength={1024} onChange={(e) => setDescription(e.target.value)} />
              </Field>
              <button type="button" onClick={() => setCreating(false)} className="self-start text-label-md text-primary">
                {t("kitchen.searchInstead")}
              </button>
            </>
          ) : picked ? (
            <span className="inline-flex items-center gap-xs self-start rounded-full bg-tertiary-fixed py-[6px] pl-sm pr-xs text-label-md text-on-tertiary-fixed-variant">
              <EquipmentIcon name={picked.name} type={picked.equipment_type} className="text-[18px]" />
              {picked.name}
              <IconButton icon="close" label={t("common.close")} className="h-7 w-7" onClick={() => setPicked(null)} />
            </span>
          ) : (
            <>
              <EquipmentPicker onPick={setPicked} />
              <button type="button" onClick={() => setCreating(true)} className="self-start text-label-md text-primary">
                {t("kitchen.notInCatalog")}
              </button>
            </>
          ))}
        <div className="grid grid-cols-[120px_1fr] gap-sm">
          <Field label={t("kitchen.quantity")}>
            <Input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Math.max(1, Number(e.target.value) || 1))} />
          </Field>
          <Field label={t("kitchen.notes")}>
            <Input value={notes} maxLength={500} placeholder={t("kitchen.notesPlaceholder")} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </div>
      </div>
    </Modal>
  );
}

/** Suggested onboarding after sign-up: tick what you have (§12). Every tick is instant. */
function Onboarding({ mine, onDone }: { mine: UserEquipment[]; onDone: () => void }) {
  const { t } = useTranslation();
  const { upsert, remove } = useKitchenMutations();
  const common = useQuery({
    queryKey: ["equipment", "common"],
    queryFn: () => catalogApi.searchEquipment("", undefined, 24),
    staleTime: Infinity,
  });
  const owned = new Set(mine.map((item) => item.equipment.id));
  const toggle = (equipment: Equipment) =>
    owned.has(equipment.id) ? remove.mutate(equipment.id) : upsert.mutate({ equipment, quantity: 1, notes: null });

  return (
    <Card className="mb-md p-md">
      <h2 className="text-headline-md">{t("kitchen.welcomeTitle")}</h2>
      <p className="mb-md text-body-md text-on-surface-variant">{t("kitchen.welcomeText")}</p>
      {common.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="grid grid-cols-2 gap-sm sm:grid-cols-3 lg:grid-cols-4">
          {common.data?.items.map((equipment) => {
            const has = owned.has(equipment.id);
            return (
              <button
                key={equipment.id}
                type="button"
                aria-pressed={has}
                onClick={() => toggle(equipment)}
                className={`relative flex flex-col items-center gap-xs rounded-lg border-2 p-sm text-center text-label-md transition-colors ${
                  has ? "border-tertiary bg-tertiary-fixed/50" : "border-outline-variant hover:bg-surface-container-high"
                }`}
              >
                {has && <Icon name="check_circle" filled className="absolute right-xs top-xs text-[18px] text-tertiary" />}
                <EquipmentIcon name={equipment.name} type={equipment.equipment_type} className={`text-[30px] ${has ? "text-tertiary" : "text-secondary"}`} />
                {equipment.name}
              </button>
            );
          })}
        </div>
      )}
      <div className="mt-md flex justify-end gap-sm">
        <Link to="/">
          <Button variant="ghost">{t("kitchen.later")}</Button>
        </Link>
        <Button icon="check" onClick={onDone}>
          {t("common.done")}
        </Button>
      </div>
    </Card>
  );
}

export function KitchenPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const errorMessage = useErrorMessage();
  const [type, setType] = useState<EquipmentType | null>(null);
  const [modal, setModal] = useState<{ existing: UserEquipment | null } | null>(null);
  const kitchen = useQuery({ queryKey: KEY, queryFn: kitchenApi.list });
  const { remove } = useKitchenMutations();
  const items = kitchen.data ?? [];
  const shown = type ? items.filter((item) => item.equipment.equipment_type === type) : items;
  const welcome = params.get("welcome") === "1";

  return (
    <div className="mx-auto max-w-4xl">
      {!welcome && (
        <Link to="/profile" className="mb-sm inline-flex items-center gap-xs text-label-md text-primary">
          <Icon name="arrow_back" className="text-[18px]" /> {t("profile.title")}
        </Link>
      )}
      <PageHeader
        title={t("kitchen.title")}
        subtitle={t("kitchen.subtitle")}
        actions={
          <Button icon="add_circle" onClick={() => setModal({ existing: null })}>
            {t("kitchen.add")}
          </Button>
        }
      />
      {welcome && kitchen.data && <Onboarding mine={items} onDone={() => setParams({}, { replace: true })} />}

      {kitchen.isLoading ? (
        <Skeleton className="h-64" />
      ) : kitchen.isError ? (
        <ErrorState message={errorMessage(kitchen.error)} onRetry={() => void kitchen.refetch()} />
      ) : items.length === 0 ? (
        !welcome && <EmptyState icon="countertops" title={t("kitchen.emptyTitle")} text={t("kitchen.emptyText")} />
      ) : (
        <>
          <div className="mb-md flex flex-wrap gap-xs">
            <Chip active={!type} onClick={() => setType(null)}>
              {t("common.all")} ({items.length})
            </Chip>
            {TYPES.map((value) => {
              const count = items.filter((item) => item.equipment.equipment_type === value).length;
              return count ? (
                <Chip key={value} icon={TYPE_ICONS[value]} active={type === value} onClick={() => setType(value)}>
                  {t(`kitchen.types.${value}`)} ({count})
                </Chip>
              ) : null;
            })}
          </div>
          <div className="grid gap-gutter sm:grid-cols-2">
            {shown.map((item) => (
              <Card key={item.equipment.id} className="flex items-start gap-sm p-sm">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-secondary-container text-primary">
                  <EquipmentIcon name={item.equipment.name} type={item.equipment.equipment_type} className="text-[26px]" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-label-sm uppercase text-on-surface-variant">{t(`kitchen.types.${item.equipment.equipment_type}`)}</p>
                  <p className="text-title-lg">
                    {item.equipment.name}{" "}
                    {item.quantity > 1 && <span className="text-label-md text-on-surface-variant">×{item.quantity}</span>}
                  </p>
                  {(item.notes || item.equipment.description) && (
                    <p className="text-label-md font-normal text-on-surface-variant">{item.notes || item.equipment.description}</p>
                  )}
                </div>
                <IconButton icon="edit" label={t("common.edit")} onClick={() => setModal({ existing: item })} />
                <IconButton icon="delete" label={t("common.delete")} className="text-error" onClick={() => remove.mutate(item.equipment.id)} />
              </Card>
            ))}
          </div>
          <p className="mt-md text-center text-label-sm text-on-surface-variant">{t("kitchen.usedFor")}</p>
        </>
      )}
      {modal && <EquipmentModal onClose={() => setModal(null)} existing={modal.existing} />}
    </div>
  );
}
