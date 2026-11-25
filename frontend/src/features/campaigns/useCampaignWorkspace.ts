"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import { ApiError, api } from "@/lib/api";
import type {
  Campaign,
  CampaignCreate,
  CampaignSummary,
  OfferSummary,
  References,
} from "@/lib/types";

const emptyCampaign: CampaignCreate = { name: "", geo: "", offer_id: 0 };

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Произошла непредвиденная ошибка. Попробуйте ещё раз.";
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
  const [isSaving, setIsSaving] = useState(false);
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

  useEffect(() => {
    let active = true;
    api
      .campaigns(search)
      .then((items) => {
        if (active) setCampaigns(items);
      })
      .catch((reason: unknown) => {
        if (active) setError(getErrorMessage(reason));
      });
    return () => {
      active = false;
    };
  }, [search]);

  function updateForm(value: CampaignCreate) {
    idempotencyKey.current = null;
    setForm(value);
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
      toast.error(getErrorMessage(reason));
      setIsSaving(false);
      return;
    }

    idempotencyKey.current = null;
    setCampaign(created);
    setForm(emptyCampaign);
    toast.success(`Кампания «${created.name}» создана.`);

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
      setCampaign({
        ...campaign,
        streams: campaign.streams.map((stream) =>
          stream.id === updatedStream.id ? updatedStream : stream,
        ),
      });
      const offerName =
        offers.find((offer) => offer.id === offerId)?.name ??
        campaign.streams
          .flatMap((stream) => stream.offers)
          .find((offer) => offer.offer_id === offerId)?.name ??
        `#${offerId}`;
      toast.success(
        action === "add"
          ? `Оффер «${offerName}» добавлен.`
          : `Оффер «${offerName}» удалён.`,
      );
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
    isSaving,
    setForm: updateForm,
    setSearch,
    setError,
    createCampaign,
    selectCampaign,
    changeOffer,
  };
}
