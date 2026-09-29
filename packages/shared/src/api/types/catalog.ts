/**
 * Primary-source catalog types. Entities are authoritative organisations; catalog feeds are
 * candidate feeds under verification that are only promoted into the user's library on subscribe.
 */

export type EntityType =
  | 'GOV_FEDERAL'
  | 'GOV_STATE'
  | 'CORP_PUBLIC'
  | 'CORP_PRIVATE'
  | 'RESEARCH_ACADEMIC';

export type CatalogFeedType = 'NATIVE_RSS' | 'NATIVE_ATOM' | 'SYNTHETIC_HTML';

export type VerificationStatus =
  | 'VERIFIED_PRIMARY'
  | 'PENDING'
  | 'REJECTED_AGGREGATOR'
  | 'QUARANTINED';

export interface PrimaryEntity {
  id: string;
  name: string;
  entity_type: EntityType;
  canonical_domain: string;
  cik: string | null;
  jurisdiction: string | null;
  created_at: string;
}

export interface CatalogFeed {
  id: string;
  entity_id: string;
  feed_url: string;
  feed_type: CatalogFeedType;
  verification_status: VerificationStatus;
  rejection_reason: string | null;
  outbound_third_party_ratio: number | null;
  failure_count: number;
  last_polled_at: string | null;
  next_poll_at: string | null;
  created_at: string;
}
