import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client", () => {
  it("requests references from the versioned backend route", async () => {
    const references = { domains: [], groups: [], sources: [] };
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(references, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.references()).resolves.toEqual(references);
    expect(fetchMock.mock.calls[0][0]).toContain("/api/backend/v1/references");
  });

  it("sends only the campaign creation contract", async () => {
    const campaign = {
      id: 7,
      name: "Кампания",
      alias: null,
      admin_url: "https://tracker.example/admin/campaign/7",
      streams: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(campaign, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.createCampaign({ name: "Кампания", geo: "RU", offer_id: 42 }),
    ).resolves.toEqual(campaign);

    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(request.method).toBe("POST");
    expect(JSON.parse(String(request.body))).toEqual({
      name: "Кампания",
      geo: "RU",
      offer_id: 42,
    });
  });

  it("uses the backend detail as the API error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({ detail: "Offer not found" }, { status: 404 }),
      ),
    );

    await expect(api.campaign(999)).rejects.toMatchObject({
      message: "Offer not found",
      status: 404,
    });
  });

  it("turns network failures into a readable API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await expect(api.campaigns()).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
      message: "Не удалось подключиться к backend. Проверьте его доступность.",
    });
  });
});
