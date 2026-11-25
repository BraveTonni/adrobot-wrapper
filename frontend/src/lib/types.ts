export type Reference = { id: number; name: string };
export type References = {
  domains: Reference[];
  groups: Reference[];
  sources: Reference[];
};
export type OfferSummary = { id: number; name: string };
export type CampaignSummary = {
  id: number;
  name: string;
  alias: string | null;
};
export type CampaignOffer = {
  offer_id: number;
  name: string | null;
  share: number;
  state: string | null;
  published_share: number;
  published_state: string | null;
  draft_share: number;
  draft_state: string | null;
  is_pinned: boolean;
  is_deleted: boolean;
  has_draft: boolean;
};
export type Stream = {
  id: number;
  name: string | null;
  type: string | null;
  schema: string | null;
  uses_offers: boolean;
  offers: CampaignOffer[];
};
export type Campaign = {
  id: number;
  name: string;
  alias: string | null;
  admin_url: string;
  streams: Stream[];
};
export type CampaignCreate = {
  name: string;
  geo: string;
  offer_id: number;
  domain_id?: number;
  group_id?: number;
  source_id?: number;
};
