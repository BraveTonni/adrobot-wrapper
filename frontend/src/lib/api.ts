import type {
  Campaign,
  CampaignCreate,
  CampaignSummary,
  OfferSummary,
  References,
  Stream,
} from "./types";

type ApiErrorBody = { detail?: unknown; code?: unknown };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    // Машино-читаемый код от backend, например `idempotency_pending`.
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Backend держит предыдущую попытку создания: тот же ключ повторять нельзя. */
export function isCreationBlocked(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    (error.code?.startsWith("idempotency_") ?? false)
  );
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
    throw await readError(response);
  }

  return (await response.json()) as T;
}

async function readError(response: Response): Promise<ApiError> {
  const fallback = `Ошибка запроса (${response.status})`;
  try {
    const body = (await response.json()) as ApiErrorBody;
    return new ApiError(
      typeof body.detail === "string" ? body.detail : fallback,
      response.status,
      typeof body.code === "string" ? body.code : undefined,
    );
  } catch {
    // Backend may return an empty or non-JSON error body.
    return new ApiError(fallback, response.status);
  }
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
