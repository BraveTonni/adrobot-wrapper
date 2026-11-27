import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Campaign, CampaignOffer } from "@/lib/types";
import { CampaignEditor } from "./CampaignEditor";

function renderEditor(offer: CampaignOffer): string {
  const campaign: Campaign = {
    id: 7,
    name: "Launch",
    alias: "launch",
    admin_url: "https://tracker.example/admin/#!/campaign.editor/7",
    streams: [
      {
        id: 11,
        name: "Offers",
        type: "default",
        schema: "landings",
        uses_offers: true,
        offers: [offer],
      },
    ],
  };

  return renderToStaticMarkup(
    createElement(CampaignEditor, {
      campaign,
      offers: [{ id: offer.offer_id, name: offer.name ?? "Offer" }],
      isSaving: false,
      onOfferChange: vi.fn(),
      onOfferRestore: vi.fn(),
      onStreamPush: vi.fn(),
      onStreamCancel: vi.fn(),
    }),
  );
}

describe("CampaignEditor draft state", () => {
  it("renders published and draft shares with publish and cancel controls", () => {
    const markup = renderEditor({
      offer_id: 42,
      name: "Offer",
      share: 60,
      state: "active",
      published_share: 40,
      published_state: "active",
      draft_share: 60,
      draft_state: "active",
      is_pinned: true,
      is_deleted: false,
      has_draft: true,
    });

    expect(markup).toContain("Опубликовано 40%");
    expect(markup).toContain("черновик 60%");
    expect(markup).toContain("закреплён");
    expect(markup).toContain("Опубликовать изменения");
    expect(markup).toContain("Отменить черновик");
  });

  it("renders restore control for a deleted offer", () => {
    const markup = renderEditor({
      offer_id: 42,
      name: "Offer",
      share: 60,
      state: "deleted",
      published_share: 40,
      published_state: "active",
      draft_share: 60,
      draft_state: "deleted",
      is_pinned: false,
      is_deleted: true,
      has_draft: true,
    });

    expect(markup).toContain('aria-label="Восстановить оффер Offer"');
    expect(markup).toContain("черновик удалён");
  });
});

describe("CampaignEditor icons", () => {
  it("draws icons without an external icon font", () => {
    const markup = renderEditor({
      offer_id: 42,
      name: "Offer",
      share: 100,
      state: "active",
      published_share: 100,
      published_state: "active",
      draft_share: 100,
      draft_state: "active",
      is_pinned: false,
      is_deleted: false,
      has_draft: false,
    });

    expect(markup).toContain('<svg aria-hidden="true" class="icon"');
    expect(markup).not.toContain("Material Icons");
  });
});
