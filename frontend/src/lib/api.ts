import type {
  Campaign,
  CampaignCreate,
  CampaignSummary,
  OfferSummary,
  References,
  Stream,
} from "./types";

type ApiErrorBody = { detail?: unknown };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type CatalogRefresh = { offers: OfferSummary[]; references: References };

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`/api/backend/v1${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Не удалось подключиться к backend. Проверьте его доступность.",
      0,
    );
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status);
  }

  return (await response.json()) as T;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Backend may return an empty or non-JSON error body.
  }

  return `Ошибка запроса (${response.status})`;
}

export const api = {
  references: () => request<References>("/references"),

  refreshCatalog: () =>
    request<CatalogRefresh>("/catalog/refresh", { method: "POST" }),

  offers: (search = "") =>
    request<OfferSummary[]>(
      `/offers?search=${encodeURIComponent(search)}&limit=100`,
    ),

  campaigns: (search = "") =>
    request<CampaignSummary[]>(`/campaigns?search=${encodeURIComponent(search)}`),

  campaign: (campaignId: number) =>
    request<Campaign>(`/campaigns/${campaignId}`),

  createCampaign: (body: CampaignCreate, idempotencyKey: string) =>
    request<Campaign>("/campaigns", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    }),

  addOffer: (campaignId: number, streamId: number, offerId: number) =>
    request<Stream>(
      `/campaigns/${campaignId}/streams/${streamId}/offers`,
      {
        method: "POST",
        body: JSON.stringify({ offer_id: offerId }),
      },
    ),

  removeOffer: (campaignId: number, streamId: number, offerId: number) =>
    request<Stream>(
      `/campaigns/${campaignId}/streams/${streamId}/offers/${offerId}`,
      { method: "DELETE" },
    ),

  restoreOffer: (campaignId: number, streamId: number, offerId: number) =>
    request<Stream>(
      `/campaigns/${campaignId}/streams/${streamId}/offers/${offerId}/restore`,
      { method: "POST" },
    ),

  pushStream: (campaignId: number, streamId: number) =>
    request<Stream>(
      `/campaigns/${campaignId}/streams/${streamId}/push`,
      { method: "POST" },
    ),

  cancelStreamDraft: (campaignId: number, streamId: number) =>
    request<Stream>(
      `/campaigns/${campaignId}/streams/${streamId}/draft/cancel`,
      { method: "POST" },
    ),
};
