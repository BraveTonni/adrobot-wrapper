"use client";

import type { CampaignSummary } from "@/lib/types";

type Props = {
  campaigns: CampaignSummary[];
  search: string;
  selectedId?: number;
  isSaving: boolean;
  onSearch: (value: string) => void;
  onSelect: (id: number) => void;
};

export function CampaignPicker({
  campaigns,
  search,
  selectedId,
  isSaving,
  onSearch,
  onSelect,
}: Props) {
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>Выберите кампанию</h2>
        <span className="muted">{campaigns.length} найдено</span>
      </header>
      <div className="field">
        <label htmlFor="campaign-search">Поиск по названию</label>
        <input
          id="campaign-search"
          value={search}
          placeholder="Название кампании"
          onChange={(event) => onSearch(event.target.value)}
        />
      </div>
      <div className="campaign-list" aria-live="polite">
        {campaigns.map((campaign) => (
          <button
            aria-current={selectedId === campaign.id ? "true" : undefined}
            className={`campaign-row ${selectedId === campaign.id ? "selected" : ""}`}
            disabled={isSaving}
            key={campaign.id}
            type="button"
            onClick={() => onSelect(campaign.id)}
          >
            <span>
              <strong>{campaign.name}</strong>
              <span className="muted campaign-meta">
                ID {campaign.id}
                {campaign.alias ? ` · ${campaign.alias}` : ""}
              </span>
            </span>
            <span aria-hidden="true" className="icon">
              chevron_right
            </span>
          </button>
        ))}
        {campaigns.length === 0 && (
          <p className="empty">Кампании не найдены.</p>
        )}
      </div>
    </section>
  );
}
