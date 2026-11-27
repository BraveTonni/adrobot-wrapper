"use client";

import { Icon } from "@/components/Icon";
import type { FormEvent } from "react";
import type { CampaignCreate, OfferSummary, References } from "@/lib/types";

type Props = {
  form: CampaignCreate;
  references: References | null;
  offers: OfferSummary[];
  isLoading: boolean;
  isRefreshing: boolean;
  isSaving: boolean;
  onChange: (value: CampaignCreate) => void;
  onRefresh: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function CampaignCreateForm({
  form,
  references,
  offers,
  isLoading,
  isRefreshing,
  isSaving,
  onChange,
  onRefresh,
  onSubmit,
}: Props) {
  function setOptionalId(
    key: "domain_id" | "group_id" | "source_id",
    value: string,
  ) {
    onChange({ ...form, [key]: value ? Number(value) : undefined });
  }

  return (
    <form onSubmit={onSubmit}>
      <section className="panel" data-aos="fade-up">
        <header className="panel-head">
          <h2>Основные параметры</h2>
          <span className="eyebrow">01 / 02</span>
        </header>
        <div className="grid">
          <div className="field wide">
            <label htmlFor="campaign-name">Название кампании</label>
            <input
              id="campaign-name"
              autoComplete="off"
              maxLength={255}
              required
              value={form.name}
              placeholder="Например, летняя кампания · US"
              onChange={(event) =>
                onChange({ ...form, name: event.target.value })
              }
            />
          </div>
          <div className="field">
            <label htmlFor="campaign-geo">Код страны (ISO 3166-1)</label>
            <input
              id="campaign-geo"
              autoComplete="country"
              maxLength={2}
              minLength={2}
              pattern="[A-Za-z]{2}"
              required
              value={form.geo}
              placeholder="US"
              onChange={(event) =>
                onChange({ ...form, geo: event.target.value.toUpperCase() })
              }
            />
            <small>Двухбуквенный код, например US или DE</small>
          </div>
          <div className="field">
            <label htmlFor="campaign-offer">Целевой оффер</label>
            <select
              id="campaign-offer"
              required
              value={form.offer_id || ""}
              onChange={(event) =>
                onChange({ ...form, offer_id: Number(event.target.value) })
              }
            >
              <option value="">
                {isLoading ? "Загружаем офферы…" : "Выберите оффер"}
              </option>
              {offers.map((offer) => (
                <option key={offer.id} value={offer.id}>
                  {offer.name} · #{offer.id}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      <section className="panel" data-aos="fade-up">
        <header className="panel-head">
          <h2>Инфраструктура</h2>
          <div className="panel-head-actions">
            <span className="eyebrow">02 / 02</span>
            <button
              className="button"
              disabled={isLoading || isSaving || isRefreshing}
              type="button"
              onClick={onRefresh}
            >
              {isRefreshing ? "Обновляем…" : "Обновить каталог"}
            </button>
          </div>
        </header>
        <div className="grid">
          <ReferenceSelect
            id="campaign-domain"
            label="Домен"
            items={references?.domains ?? []}
            value={form.domain_id}
            onChange={(value) => setOptionalId("domain_id", value)}
          />
          <ReferenceSelect
            id="campaign-group"
            label="Группа кампаний"
            items={references?.groups ?? []}
            value={form.group_id}
            onChange={(value) => setOptionalId("group_id", value)}
          />
          <ReferenceSelect
            id="campaign-source"
            label="Источник трафика"
            items={references?.sources ?? []}
            value={form.source_id}
            onChange={(value) => setOptionalId("source_id", value)}
          />
        </div>
        <p className="muted form-hint">
          Если оставить поле пустым, backend применит значение по умолчанию.
        </p>
      </section>

      <div className="actions">
        <button
          className="button primary"
          disabled={isLoading || isSaving || offers.length === 0}
          type="submit"
        >
          {isSaving ? "Создаём…" : "Создать кампанию"}
          <Icon name="arrow-forward" />
        </button>
      </div>
    </form>
  );
}

type ReferenceSelectProps = {
  id: string;
  label: string;
  items: References["domains"];
  value?: number;
  onChange: (value: string) => void;
};

function ReferenceSelect({
  id,
  label,
  items,
  value,
  onChange,
}: ReferenceSelectProps) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">По умолчанию</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name} · #{item.id}
          </option>
        ))}
      </select>
    </div>
  );
}
