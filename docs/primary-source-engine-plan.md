# infrss Primary-Source Engine — Implementation Plan

A specialised, user-facing feed catalog restricted to **primary sources** (government agencies,
SEC filers, corporate newsrooms, research institutions) plus an on-device layman summariser for
dense primary documents. Secondary/tertiary reporting (news outlets, aggregators, blogs that
merely relay press releases) is excluded by a gatekeeper.

This plan adapts an earlier standalone TypeScript specification to this repository. Where the
spec and the repo conflict, **the repo wins**.

## Locked decisions

| Topic | Decision | Rationale |
|---|---|---|
| Engine language/location | Python under `server/app/` | The backend is FastAPI; a TS engine would fork the data layer. |
| Database | Postgres via SQLAlchemy 2.x + Alembic | Existing stack. No SQLite. |
| Catalog visibility | Catalog rows are separate from `feeds` | A feed is only promoted into the global `feeds` table on an **explicit subscribe**; until then it lives in `catalog_feeds`. |
| Audience | User-facing | Users browse the catalog and subscribe; admin-only curation uses the existing `get_current_admin` pattern. |
| Lifecycle | Own columns on `catalog_feeds` | The repo's article refresh is subscriber-gated (`get_feeds_for_worker`: `Feed.subscriber_count > 0`); catalog verification must poll independently, before any subscription exists. |
| Synthetic feeds | DOM-parser first, Playwright fallback | `trafilatura`/`bs4` are already dependencies and handle static newsrooms; Playwright is lazily imported only when a page yields too few items or looks JS-rendered. |
| Synthetic serving | Backend-served Atom URL | The generated feed is served at a real HTTP URL and used as the promoted `feeds.url`, so the entire existing fetch/parse/ingest/Meilisearch pipeline works unchanged. |
| SEC connector | Required `User-Agent` + 10 req/s limit | SEC EDGAR fair-access policy. Config: `SEC_USER_AGENT`, `SEC_RATE_LIMIT_RPS`. |
| Summarisation | WebLLM preferred, server AI fallback | Coexists with the existing `generate_summary`/`AiSummaryCard`; not a replacement. Default model `Qwen2.5-1.5B-Instruct-q4f16_1-MLC` (~1 GB), low-memory preset `Llama-3.2-1B-Instruct-q4f16_1-MLC`. Fallback chain: WebGPU → local Ollama → server Gemini. |

## Architecture

```
Discovery                    Verification                    Reader
─────────                    ────────────                    ──────
autodiscovery  ──feeds──►  gatekeeper  ──►  catalog_feeds  ──subscribe──►  feeds
(link tags + probes)       (domain,          (PENDING /           (promotion)   │
                            outbound %,      VERIFIED_PRIMARY /                ▼
                            redirects)       REJECTED_AGGREGATOR)      feed_articles
                                                                      article_contents
                                                                            │
                                                            ArticleContent ──► Layman summary
                                                                              (WebLLM / Ollama /
                                                                               Gemini fallback)
```

## Data model

The spec's `CatalogFeed` and `FeedItem` map almost entirely onto existing tables; only two tables
are genuinely new. `primary_entities` records the authoritative organisation; `catalog_feeds`
holds candidate feeds and their verification lifecycle until a subscription promotes them.

| Spec type | Where it lives |
|---|---|
| `PrimaryEntity` | **new** `primary_entities` |
| `CatalogFeed` | **new** `catalog_feeds` (promoted to `feeds` on subscribe) |
| `FeedItem` | existing `feed_articles` (`guid_hash`, `UniqueConstraint(feed_id, guid_hash)`) + `article_contents` |
| `CatalogFeed.etag/lastModified/failureCount/lastPolledAt` | `feeds.etag_header/last_modified_header/fetch_error_count/last_fetched_at` after promotion; own columns before it |
| `LaymanSummary` | **new** `article_layman_summaries` keyed by `content_hash` (shared across users, mirrors `ArticleContent`) |

### `primary_entities`
`id`, `name`, `entity_type` (`GOV_FEDERAL|GOV_STATE|CORP_PUBLIC|CORP_PRIVATE|RESEARCH_ACADEMIC`),
`canonical_domain` (unique), `cik` (10-digit, nullable), `jurisdiction` (ISO 3166, nullable),
`created_at`.

### `catalog_feeds`
`id`, `entity_id` → `primary_entities`, `feed_url` (unique), `feed_type`
(`NATIVE_RSS|NATIVE_ATOM|SYNTHETIC_HTML`), `verification_status`
(`VERIFIED_PRIMARY|PENDING|REJECTED_AGGREGATOR|QUARANTINED`), `rejection_reason`,
`outbound_third_party_ratio`, `etag_header`, `last_modified_header`, `failure_count`,
`last_polled_at`, `next_poll_at`, `created_at`, `last_updated_at`.

RLS is enabled with no policies on both tables (backend/service-role bypass RLS; clients reach
them only through the API), matching `9b2e4d6f1a37_enable_rls`.

## Gatekeeper rules

A candidate is `VERIFIED_PRIMARY` iff all hold:

1. **Strict domain alignment** — the feed host is the entity's canonical domain or a subdomain of
   it (or a configured feed CDN, `CATALOG_ALLOWED_FEED_HOSTS`).
2. **Outbound-link filter** — no more than `CATALOG_OUTBOUND_THIRD_PARTY_RATIO` (5%) of item
   links leave the entity's domain; otherwise `REJECTED_AGGREGATOR`.
3. **Redirect guard** — every redirect hop stays on an authorised origin.

## Phases

- **Phase 1 (this change):** enums, `primary_entities` + `catalog_feeds` models + migration,
  catalog schemas, CRUD, gatekeeper, autodiscovery. Unit + integration tested.
- **Phase 2 (done):** SEC / Federal Register / Wikidata connectors, synthetic generation + serving
  endpoint, catalog verification worker + schedules, subscribe→promote flow. gov-TLD scanning is
  **deferred** — it is an unbounded crawl; Federal Register covers U.S. federal agencies and
  Wikidata covers research institutions, so a curated state-gov registry can follow later.
- **Phase 3 (server done):** `doc_cleaner`, `LAYMAN_SUMMARY_SYSTEM_PROMPT`, `article_layman_summaries`
  persistence and GET / PUT / generate endpoints, plus the server-side fallback generation. The
  browser `@mlc-ai/web-llm` worker, IndexedDB cache and client fallback chain move to Phase 4:
  they only matter once the UI exists, require WebGPU to test, and adding the dependency would
  break web typecheck where the web toolchain isn't installed.
- **Phase 4 (UI + WebLLM, done):** `LaymanSummaryCard`, `PrimarySourceBadge`, `WebLlmStatusIndicator`;
  `@mlc-ai/web-llm` worker + `use-layman-summary` hook + IndexedDB cache + Ollama fallback; wired
  into the reader above the article body and the header badge. Catalog browse page
  (`/catalog`, `CatalogBrowser`) with entity list, feed list and subscribe-to-promote, plus a
  sidebar entry.

### Phase 1 file map
- `server/app/models/enums.py` — `EntityType`, `CatalogFeedType`, `VerificationStatus`
- `server/app/models/catalog.py` — `PrimaryEntity`, `CatalogFeed`
- `server/app/models/__init__.py` — register models
- `server/alembic/versions/*_add_primary_catalog.py` — tables, enums, indexes, RLS
- `server/app/core/constants.py` — catalog constants
- `server/app/typing/catalog.py` — request/response schemas + `GatekeeperResult`
- `server/app/crud/catalog/{entities,feeds}.py`
- `server/app/services/catalog/{gatekeeper,autodiscovery}.py`
- `server/tests/unit/test_catalog_{gatekeeper,autodiscovery}.py`
- `server/tests/integration/test_catalog_{entities,gatekeeper,autodiscovery}.py`

### Phase 2 file map
- `server/app/services/catalog/connectors/{base,sec,federal_register,wikidata}.py` — registry
  connectors, pure parsers + `RateLimiter` (SEC 10 req/s)
- `server/app/services/catalog/synthetic.py` — DOM extraction, Atom 1.0 generation, Redis-cached
  render, optional Playwright fallback
- `server/app/services/catalog/verification.py` — gatekeeper polling, circuit breakers/quarantine
- `server/app/services/catalog/promotion.py` — subscribe→promote into `feeds`
- `server/app/routers/catalog.py` — unauthenticated `GET /catalog/synthetic/{id}.atom`, plus
  authenticated browse + subscribe routes
- `server/app/workers/catalog_tasks.py` + `server/app/workers/catalog/{verify,sync}.py`
- `server/alembic/versions/*_add_primary_entity_to_feeds.py` — `feeds.primary_entity_id`
- `server/tests/unit/test_catalog_{connectors,synthetic}.py`
- `server/tests/integration/test_catalog_{verification,promotion,synthetic_endpoint}.py`

### Phase 3 file map (server-side)
- `server/app/services/catalog/doc_cleaner.py` — boilerplate strip, section isolation, token cap
- `server/app/services/ai/{layman.py,prompts.py}` — JSON-contract generation + system prompt
- `server/app/models/article.py` — `ArticleLaymanSummary`; migration `*_add_article_layman_summaries.py`
- `server/app/crud/article/layman.py`, `server/app/typing/layman.py`
- `server/app/routers/articles/articles_layman.py` — `GET` / `PUT` / `POST .../generate`
- `server/tests/unit/test_catalog_doc_cleaner.py`, `tests/unit/test_ai_layman.py`
- `server/tests/integration/test_layman_summary.py`

### Phase 4 file map
- `packages/shared/src/api/{types/layman.ts,endpoints/articles.ts,hooks/use-articles.ts,query-keys.ts}`
  — layman-summary types, endpoints and hooks; `feed_is_primary` on feed context
- `apps/web/lib/primary/{prompt,doc-cleaner,summary-cache,ollama,webllm}.ts` — prompt, cleaning,
  IndexedDB cache, Ollama + WebLLM adapters
- `apps/web/workers/summarizer.worker.ts` — WebWorkerMLCEngineHandler
- `apps/web/components/features/articles/{LaymanSummaryCard,PrimarySourceBadge,WebLlmStatusIndicator}.tsx`
  + `hooks/use-layman-summary.ts`
- `server/app/typing/entries.py`, `server/app/crud/article/reader.py` — `feed_is_primary` field
- `packages/shared/src/api/{types/catalog.ts,endpoints/catalog.ts,hooks/use-catalog.ts}` — catalog
  browse + subscribe
- `apps/web/app/(protected)/catalog/page.tsx`, `components/features/catalog/CatalogBrowser.tsx`,
  sidebar entry in `features/navigation/SidebarMain.tsx`

## Follow-ups / open items

- Catalog browse endpoint (paginated Postgres list) and subscribe→promote service.
- A second Meilisearch index for catalog search, only if Postgres browse proves insufficient.
- Synthetic Atom serving endpoint and its DOM re-parse schedule (2-hourly).
- Prompt parity: the layman prompt must be duplicated in Python (fallback) and TS (WebLLM); keep a
  shared fixture set to prevent drift.
