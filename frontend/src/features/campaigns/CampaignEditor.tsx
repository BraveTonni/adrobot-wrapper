"use client";

import type { FormEvent } from "react";
import { Icon } from "@/components/Icon";
import type { Campaign, CampaignOffer, OfferSummary, Stream } from "@/lib/types";
import { getSafeAdminUrl } from "@/lib/urls";

type Props = {
  campaign: Campaign;
  offers: OfferSummary[];
  isSaving: boolean;
  onOfferChange: (
    streamId: number,
    offerId: number,
    action: "add" | "remove",
  ) => void;
  onOfferRestore: (streamId: number, offerId: number) => void;
  onStreamPush: (streamId: number) => void;
  onStreamCancel: (streamId: number) => void;
};

const LAST_OFFER_HINT = "Последний оффер потока удалить нельзя";

export function CampaignEditor({
  campaign,
  offers,
  isSaving,
  onOfferChange,
  onOfferRestore,
  onStreamPush,
  onStreamCancel,
}: Props) {
  const adminUrl = getSafeAdminUrl(campaign.admin_url);

  return (
    <section className="panel" aria-labelledby="editor-title">
      <header className="panel-head">
        <div>
          <h2 id="editor-title">{campaign.name}</h2>
          <span className="muted">Кампания #{campaign.id}</span>
        </div>
        {adminUrl ? (
          <a
            className="button"
            href={adminUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            Открыть в Keitaro ↗
          </a>
        ) : (
          <span className="muted" role="status">
            Ссылка Keitaro недоступна
          </span>
        )}
      </header>
      {campaign.streams.length === 0 ? (
        <p className="empty">У кампании пока нет потоков.</p>
      ) : (
        <div className="stream-grid">
          {campaign.streams.map((stream, index) => (
            <StreamCard
              key={stream.id}
              stream={stream}
              index={index}
              offers={offers}
              isSaving={isSaving}
              onOfferChange={onOfferChange}
              onOfferRestore={onOfferRestore}
              onStreamPush={onStreamPush}
              onStreamCancel={onStreamCancel}
            />
          ))}
        </div>
      )}
    </section>
  );
}

type StreamCardProps = {
  stream: Stream;
  index: number;
  offers: OfferSummary[];
  isSaving: boolean;
  onOfferChange: Props["onOfferChange"];
  onOfferRestore: Props["onOfferRestore"];
  onStreamPush: Props["onStreamPush"];
  onStreamCancel: Props["onStreamCancel"];
};

function StreamCard({
  stream,
  index,
  offers,
  isSaving,
  onOfferChange,
  onOfferRestore,
  onStreamPush,
  onStreamCancel,
}: StreamCardProps) {
  function addOffer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const offerId = Number(form.get("offerId"));
    if (offerId > 0) onOfferChange(stream.id, offerId, "add");
    event.currentTarget.reset();
  }

  const availableOffers = offers.filter(
    (offer) => !stream.offers.some((current) => current.offer_id === offer.id),
  );
  const hasDraft = stream.offers.some((offer) => offer.has_draft);
  const activeOffers = stream.offers.filter((offer) => !offer.is_deleted).length;

  return (
    <article className="stream-card">
      <header className="stream-title">
        <h3>{stream.name || `Поток ${index + 1}`}</h3>
        <span className="eyebrow">ID {stream.id}</span>
      </header>
      {stream.uses_offers ? (
        <section className="stream-offers">
          <h4 className="stream-offers-title">Офферы этого потока</h4>
          {stream.offers.length === 0 ? (
            <p className="empty">В этом потоке пока нет настроенных офферов.</p>
          ) : (
            <ul className="offer-stack">
              {stream.offers.map((offer) => (
                <OfferRow
                  key={offer.offer_id}
                  offer={offer}
                  isLast={activeOffers <= 1}
                  isSaving={isSaving}
                  onRemove={() => onOfferChange(stream.id, offer.offer_id, "remove")}
                  onRestore={() => onOfferRestore(stream.id, offer.offer_id)}
                />
              ))}
            </ul>
          )}
          <form className="inline-form" onSubmit={addOffer}>
            <label className="sr-only" htmlFor={`offer-${stream.id}`}>
              Оффер для добавления
            </label>
            <select
              id={`offer-${stream.id}`}
              name="offerId"
              defaultValue=""
              required
            >
              <option value="">Добавить оффер…</option>
              {availableOffers.map((offer) => (
                <option key={offer.id} value={offer.id}>
                  {offer.name} · #{offer.id}
                </option>
              ))}
            </select>
            <button
              aria-label="Добавить оффер"
              className="button icon-button"
              disabled={isSaving || availableOffers.length === 0}
              type="submit"
            >
              <Icon name="add" />
            </button>
          </form>
          {hasDraft && (
            <div className="inline-form">
              <button
                className="button primary"
                disabled={isSaving}
                type="button"
                onClick={() => onStreamPush(stream.id)}
              >
                Опубликовать изменения
              </button>
              <button
                className="button"
                disabled={isSaving}
                type="button"
                onClick={() => onStreamCancel(stream.id)}
              >
                Отменить черновик
              </button>
            </div>
          )}
        </section>
      ) : (
        <p className="empty">
          Этот поток перенаправляет трафик напрямую; офферы не используются.
        </p>
      )}
    </article>
  );
}

function offerStateLabel(state: string | null): string {
  switch (state) {
    case "active":
      return "активен";
    case "disabled":
      return "отключён";
    case "deleted":
      return "удалён";
    default:
      return "неизвестно";
  }
}

function OfferRow({
  offer,
  isLast,
  isSaving,
  onRemove,
  onRestore,
}: {
  offer: CampaignOffer;
  isLast: boolean;
  isSaving: boolean;
  onRemove: () => void;
  onRestore: () => void;
}) {
  const label = offer.name || `Оффер ${offer.offer_id}`;

  return (
    <li className="offer-row">
      <span>
        <strong>
          {label}
          {offer.is_pinned ? " · закреплён" : ""}
        </strong>
        <span className="muted offer-meta">
          <span className="offer-state" data-state={offer.state ?? "unknown"}>
            Состояние: {offerStateLabel(offer.state)}
          </span>
          {" · "}
          {offer.has_draft
            ? `Опубликовано ${offer.published_share}% · черновик ${
                offer.is_deleted ? "удалён" : `${offer.draft_share}%`
              }`
            : `Доля ${offer.share}%`}
          {" · ID "}
          {offer.offer_id}
        </span>
      </span>
      {offer.is_deleted ? (
        <button
          aria-label={`Восстановить оффер ${label}`}
          className="button icon-button"
          disabled={isSaving}
          type="button"
          onClick={onRestore}
        >
          <Icon name="restore" />
        </button>
      ) : (
        <button
          aria-label={`Удалить оффер ${label}`}
          className="button danger icon-button"
          disabled={isSaving || isLast}
          title={isLast ? LAST_OFFER_HINT : undefined}
          type="button"
          onClick={onRemove}
        >
          <Icon name="delete" />
        </button>
      )}
    </li>
  );
}
