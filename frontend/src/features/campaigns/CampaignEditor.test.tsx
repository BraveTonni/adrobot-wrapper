import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Campaign, CampaignOffer } from "@/lib/types";
import { CampaignEditor } from "./CampaignEditor";

const LAST_OFFER_HINT = 'title="Последний оффер потока удалить нельзя"';

function offer(overrides: Partial<CampaignOffer> = {}): CampaignOffer {
  return {
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
    ...overrides,
  };
}

function renderEditor(...streamOffers: CampaignOffer[]): string {
  const campaign: Campaign = {
    id: 7,
    name: "Launch",
    alias: "launch",
    admin_url: "https://tracker.example/admin/#!/campaign.editor/7",
    warnings: [],
    streams: [
      {
        id: 11,
        name: "Offers",
        type: "default",
        schema: "landings",
        uses_offers: true,
        offers: streamOffers,
      },
    ],
  };

  return renderToStaticMarkup(
    createElement(CampaignEditor, {
      campaign,
      offers: [
        ...streamOffers.map((item) => ({ id: item.offer_id, name: "Offer" })),
        // Оффер вне потока, чтобы кнопка добавления оставалась доступной.
        { id: 1000, name: "Spare offer" },
      ],
      isSaving: false,
      onOfferChange: vi.fn(),
      onOfferRestore: vi.fn(),
      onStreamPush: vi.fn(),
      onStreamCancel: vi.fn(),
    }),
  );
}

describe("CampaignEditor", () => {
  it("shows the share and the Keitaro state of a published offer", () => {
    const markup = renderEditor(offer());

    expect(markup).toContain("Доля 100%");
    expect(markup).toContain("Состояние: активен");
    expect(markup).toContain('data-state="active"');
    expect(markup).toContain("ID 42");
    expect(markup).not.toContain("Опубликовать изменения");
  });

  it("names offers that Keitaro disabled", () => {
    const markup = renderEditor(
      offer({ state: "disabled", draft_state: "disabled" }),
    );

    expect(markup).toContain("Состояние: отключён");
    expect(markup).toContain('data-state="disabled"');
  });

  it("does not offer removing the last active offer", () => {
    const markup = renderEditor(offer());

    expect(markup).toContain(LAST_OFFER_HINT);
    expect(markup).toMatch(/aria-label="Удалить оффер Offer"[^>]*disabled=""/);
  });

  it("allows removing an offer while another one stays", () => {
    const markup = renderEditor(
      offer({
        offer_id: 1,
        share: 50,
        published_share: 50,
        draft_share: 50,
      }),
      offer({
        offer_id: 2,
        share: 50,
        published_share: 50,
        draft_share: 50,
      }),
    );

    expect(markup).toContain("Доля 50%");
    expect(markup).not.toContain(LAST_OFFER_HINT);
    expect(markup).not.toContain('disabled=""');
  });

  it("renders published and draft shares with publish and cancel controls", () => {
    const markup = renderEditor(
      offer({
        share: 60,
        published_share: 40,
        draft_share: 60,
        is_pinned: true,
        has_draft: true,
      }),
    );

    expect(markup).toContain("Опубликовано 40%");
    expect(markup).toContain("черновик 60%");
    expect(markup).toContain("закреплён");
    expect(markup).toContain("Опубликовать изменения");
    expect(markup).toContain("Отменить черновик");
  });

  it("renders restore control for a deleted offer", () => {
    const markup = renderEditor(
      offer({
        state: "deleted",
        share: 60,
        published_share: 40,
        draft_share: 60,
        draft_state: "deleted",
        is_deleted: true,
        has_draft: true,
      }),
    );

    expect(markup).toContain('aria-label="Восстановить оффер Offer"');
    expect(markup).toContain("черновик удалён");
  });

  it("draws icons without an external icon font", () => {
    const markup = renderEditor(offer());

    expect(markup).toContain('<svg aria-hidden="true" class="icon"');
    expect(markup).not.toContain("Material Icons");
  });
});
