"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import { ApiError, api, isCreationBlocked } from "@/lib/api";
import type {
  Campaign,
  CampaignCreate,
  CampaignSummary,
  OfferSummary,
  References,
  Stream,
} from "@/lib/types";

const emptyCampaign: CampaignCreate = { name: "", geo: "", offer_id: 0 };

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Произошла непредвиденная ошибка. Попробуйте ещё раз.";
}

/** Сообщение зависит от режима: изменения уходят в Keitaro сразу или копятся в черновике. */
function offerChangeMessage(
  stream: Stream,
  action: "add" | "remove",
  offerName: string,
): string {
  if (stream.offers.some((offer) => offer.has_draft)) {
    return action === "add"
      ? `Оффер «${offerName}» добавлен в черновик.`
      : `Оффер «${offerName}» помечен на удаление.`;
  }
  return action === "add"
    ? `Оффер «${offerName}» добавлен, изменения опубликованы в Keitaro.`
    : `Оффер «${offerName}» удалён, доли пересчитаны в Keitaro.`;
}

export function useCampaignWorkspace() {
  const [references, setReferences] = useState<References | null>(null);
  const [offers, setOffers] = useState<OfferSummary[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [form, setForm] = useState(emptyCampaign);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  // Backend держит предыдущую попытку: повтор с тем же ключом вернёт 409.
  const [creationBlocked, setCreationBlocked] = useState(false);
  const idempotencyKey = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([api.references(), api.offers()] as const)
      .then(([referencesResult, offersResult]) => {
        if (!active) return;

        const errors: string[] = [];
        if (referencesResult.status === "fulfilled") {
          setReferences(referencesResult.value);
        } else {
          errors.push(getErrorMessage(referencesResult.reason));
        }
        if (offersResult.status === "fulfilled") {
          setOffers(offersResult.value);
        } else {
          errors.push(getErrorMessage(offersResult.reason));
        }
        if (errors.length > 0) setError(errors.join(" "));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function replaceStream(updatedStream: Stream) {
    setCampaign((current) =>
      current
        ? {
            ...current,
            streams: current.streams.map((stream) =>
              stream.id === updatedStream.id ? updatedStream : stream,
            ),
          }
        : current,
    );
  }

  function offerName(offerId: number): string {
    return (
      offers.find((offer) => offer.id === offerId)?.name ??
      campaign?.streams
        .flatMap((stream) => stream.offers)
        .find((offer) => offer.offer_id === offerId)?.name ??
      `#${offerId}`
    );
  }

  function updateForm(value: CampaignCreate) {
    idempotencyKey.current = null;
    setCreationBlocked(false);
    setForm(value);
  }

  /** Новая попытка: после проверки, что прошлая кампания не создалась в Keitaro. */
  function restartCreation() {
    idempotencyKey.current = null;
    setCreationBlocked(false);
  }

  async function refreshCatalog() {
    setIsRefreshing(true);
    setError("");
    try {
      const refreshed = await api.refreshCatalog();
      setOffers(refreshed.offers);
      setReferences(refreshed.references);
      toast.success("Каталог Keitaro обновлён.");
    } catch (reason) {
      toast.error(getErrorMessage(reason));
    } finally {
      setIsRefreshing(false);
    }
  }

  async function createCampaign(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!form.name.trim() || !form.geo.trim() || form.offer_id < 1) {
      toast.error("Укажите название, код страны и целевой оффер.");
      return;
    }

    setIsSaving(true);
    let created: Campaign;
    try {
      idempotencyKey.current ??= crypto.randomUUID();
      created = await api.createCampaign({
        ...form,
        name: form.name.trim(),
        geo: form.geo.trim().toUpperCase(),
      }, idempotencyKey.current);
    } catch (reason) {
      if (isCreationBlocked(reason)) setCreationBlocked(true);
      toast.error(getErrorMessage(reason));
      setIsSaving(false);
      return;
    }

    idempotencyKey.current = null;
    setCreationBlocked(false);
    setCampaign(created);
    setForm(emptyCampaign);
    toast.success(`Кампания «${created.name}» создана.`);
    created.warnings.forEach((warning) => toast.warning(warning));

    try {
      setCampaigns(await api.campaigns(search));
    } catch (reason) {
      setError(getErrorMessage(reason));
    } finally {
      setIsSaving(false);
    }
  }

  async function selectCampaign(id: number) {
    setIsSaving(true);
    setError("");
    try {
      setCampaign(await api.campaign(id));
    } catch (reason) {
      setError(getErrorMessage(reason));
    } finally {
      setIsSaving(false);
    }
  }

  async function changeOffer(
    streamId: number,
    offerId: number,
    action: "add" | "remove",
  ) {
    if (!campaign) return;
    setIsSaving(true);
    setError("");
    try {
      const updatedStream =
        action === "add"
          ? await api.addOffer(campaign.id, streamId, offerId)
          : await api.removeOffer(campaign.id, streamId, offerId);
      replaceStream(updatedStream);
      toast.success(offerChangeMessage(updatedStream, action, offerName(offerId)));
    } catch (reason) {
      toast.error(getErrorMessage(reason));
    } finally {
      setIsSaving(false);
    }
  }

  async function updateStreamDraft(
    streamId: number,
    action: "push" | "cancel",
  ) {
    if (!campaign) return;
    setIsSaving(true);
    try {
      const updatedStream =
        action === "push"
          ? await api.pushStream(campaign.id, streamId)
          : await api.cancelStreamDraft(campaign.id, streamId);
      replaceStream(updatedStream);
      toast.success(
        action === "push"
          ? "Изменения потока опубликованы."
          : "Черновик потока отменён.",
      );
    } catch (reason) {
      toast.error(getErrorMessage(reason));
    } finally {
      setIsSaving(false);
    }
  }

  async function restoreOffer(streamId: number, offerId: number) {
    if (!campaign) return;
    setIsSaving(true);
    try {
      const updatedStream = await api.restoreOffer(
        campaign.id,
        streamId,
        offerId,
      );
      replaceStream(updatedStream);
      toast.success("Оффер восстановлен в черновике.");
    } catch (reason) {
      toast.error(getErrorMessage(reason));
    } finally {
      setIsSaving(false);
    }
  }

  return {
    references,
    offers,
    campaigns,
    campaign,
    form,
    search,
    error,
    isLoading,
    isRefreshing,
    isSaving,
    creationBlocked,
    setForm: updateForm,
    setSearch,
    setError,
    createCampaign,
    restartCreation,
    refreshCatalog,
    selectCampaign,
    changeOffer,
    updateStreamDraft,
    restoreOffer,
  };
}
