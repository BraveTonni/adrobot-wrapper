"use client";

import { useEffect, useRef, useState } from "react";
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
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const idempotencyKey = useRef<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.references(), api.offers()])
      .then(([loadedReferences, loadedOffers]) => {
        if (!active) return;
        setReferences(loadedReferences);
        setOffers(loadedOffers);
      })
      .catch((reason: unknown) => {
        if (active) setError(getErrorMessage(reason));
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
    setNotice("");
    if (!form.name.trim() || !form.geo.trim() || form.offer_id < 1) {
      setError("Укажите название, код страны и целевой оффер.");
      return;
    }

    setIsSaving(true);
    try {
      idempotencyKey.current ??= crypto.randomUUID();
      const created = await api.createCampaign({
        ...form,
        name: form.name.trim(),
        geo: form.geo.trim().toUpperCase(),
      }, idempotencyKey.current);
      idempotencyKey.current = null;
      setCampaign(created);
      setNotice(`Кампания «${created.name}» создана.`);
      setForm(emptyCampaign);
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
    } catch (reason) {
      setError(getErrorMessage(reason));
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
    notice,
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
