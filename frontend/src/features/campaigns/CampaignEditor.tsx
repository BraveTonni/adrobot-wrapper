"use client";

import type { FormEvent } from "react";
import type { Campaign, OfferSummary, Stream } from "@/lib/types";
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
};

export function CampaignEditor({
  campaign,
  offers,
  isSaving,
  onOfferChange,
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
};

function StreamCard({
  stream,
  index,
  offers,
  isSaving,
  onOfferChange,
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

  return (
    <article className="stream-card">
      <header className="stream-title">
        <h3>{stream.name || `Поток ${index + 1}`}</h3>
        <span className="eyebrow">ID {stream.id}</span>
      </header>
      {stream.offers.length === 0 ? (
        <p className="empty">В потоке пока нет офферов.</p>
      ) : (
        <ul className="offer-stack">
          {stream.offers.map((offer) => (
            <li className="offer-row" key={offer.offer_id}>
              <span>
                <strong>{offer.name || `Оффер ${offer.offer_id}`}</strong>
                <span className="muted offer-meta">
                  Доля {offer.share}% · ID {offer.offer_id}
                </span>
              </span>
              {stream.uses_offers && (
                <button
                  aria-label={`Удалить оффер ${offer.name || offer.offer_id}`}
                  className="button danger icon-button"
                  disabled={isSaving || stream.offers.length <= 1}
                  type="button"
                  onClick={() =>
                    onOfferChange(stream.id, offer.offer_id, "remove")
                  }
                >
                  <span aria-hidden="true" className="icon">
                    delete
                  </span>
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {stream.uses_offers && (
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
            <span aria-hidden="true" className="icon">
              add
            </span>
          </button>
        </form>
      )}
    </article>
  );
}
