# Data dictionary

Version 1 · November 2, 2026 · PostgreSQL/Supabase · Campus display timezone America/New_York.
All timestamptz values represent instants; ingestion emits UTC ISO 8601. SQL NULL means missing, empty arrays mean no observed entries, and empty description means no usable text. No missing factual attribute becomes “no.” Strings are normalized Unicode text, HTML removed. All identifiers/hashes described as SHA-256 are 64 lowercase hex characters. Foreign keys enforce lineage. Schema is in `schema.sql`.

## event_sources (public read-only)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| id | text PK | Configured slug: ninerengage or campusevents; required |
| url | text unique | Official RSS endpoint; required |
| name | text | Source display name; configured, required |
| timezone | text | America/New_York; configured default |
| last_success_at | timestamptz nullable | Completed publication time, not event time; NULL before first success |

## ingestion_runs (private)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| id | uuid PK | New generated collection-run identifier |
| source_id | text FK | Owning source |
| started_at | timestamptz | Collection timestamp; replay uses archived timestamp |
| finished_at | timestamptz nullable | Run completion; NULL while running |
| status | text: running/success/failed | Pipeline lifecycle; success only after publishing |
| received | integer | Number of RSS item records |
| accepted | integer | Records normalized successfully |
| rejected | integer | Records failing required-field/date validation |
| error | text nullable | Sanitized operational failure; NULL on success |

## raw_records (private)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| id | text PK | SHA-256(source slug + XML hash); immutable raw version |
| source_id | text FK | Source provenance |
| source_identifier | text nullable | Original RSS GUID; missing GUID remains archived but is rejected for cleaning |
| content_hash | text SHA-256 | Serialized source-item XML hash; publication metadata can change this |
| collected_at | timestamptz | First collection of this raw version |
| run_id | uuid FK | First run observing this version; repeat versions retain first lineage |
| original_xml | text | Lossless XML item semantics; full byte-original feed is additionally archived locally before parsing |
| error | text nullable | Normalization rejection reason; NULL for valid items |

## events (public read-only)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| id | text PK | SHA-256(source + ':' + GUID); stable when content/time changes |
| source_id | text FK | Owning feed |
| source_identifier | text | RSS GUID, required; unique within source; Localist GUID identifies occurrence |
| raw_record_id | text FK | Latest imported raw version |
| content_hash | text SHA-256 | Normalized substantive fields, excluding collection/publication clocks |
| title | text | HTML-stripped title; Localist date prefix removed; venue suffix retained; required |
| description | text | Engage p-description or Localist HTML-stripped description, share footer removed; empty if absent |
| url | text http/https | Source event link, normalized host/trailing slash/fragment; required |
| start_at | timestamptz | Engage events:start or Localist dc:date; never RSS pubDate; required |
| end_at | timestamptz nullable | Engage events:end; Localist feed lacks end field; NULL retained |
| date_provenance | text | events:start or dc:date; exact field used for start |
| location | text nullable | Structured events:location only; NULL when unavailable; title suffix is not silently promoted |
| organizers | text[] | Engage hosts or explicit Hosted by text; empty if missing; no author email published |
| source_categories | text[] | Source category values, preserved without forced mapping; empty if missing |
| status | active/cancelled/unknown | Engage confirmed/cancelled mapping; Localist cancellation title marker otherwise source-listed active; not a guarantee against stale data |
| series_id | text nullable | Localist shared event URL; Engage NULL because explicit series ID unavailable |
| related_group | text SHA-256 | Conservative normalized-title grouping for split protection; not a factual recurrence assertion |
| duplicate_key | text SHA-256 | Canonical event URL (including explicit Engage cross-link) + start instant; candidate exact duplicate key |
| quality_flags | text[] | missing_end/location/organizer/description, midnight_time_unconfirmed, no_explicit_series_id; empty if none |
| first_seen_at | timestamptz | First observed collection; preserved on updates |
| last_seen_at | timestamptz | Latest observed collection; disappearance never means cancelled |
| updated_at | timestamptz | Last substantive content change; preserved on unchanged replay |

## event_tags (public read-only, provisional until approved)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| event_id | text PK/FK | One current candidate label record per event |
| content_hash | text | Event hash labels apply to; readers reject stale joins |
| topics | text[] | technology, arts, sports, wellness, career, community, academic, culture; empty if no supported topic |
| format | enum text | workshop/social/performance/sports/volunteering/meeting/unknown |
| free_admission | yes/no/unknown | Explicit admission evidence only; missing means unknown |
| free_food | yes/no/unknown | Explicit food evidence only; free admission is insufficient |
| registration_required | yes/no/unknown | Explicit requirement or waiver; missing means unknown |
| audience_restricted | yes/no/unknown | Explicit eligibility restriction or openness; missing means unknown |
| audience | text[] | students/faculty/staff/graduate/undergraduate/members; supported by quoted restriction; empty otherwise |
| evidence | jsonb object | Factual field -> exact supporting source quote; absent key for unknown |
| method | text | keyword-v1/model/human; separates predictions from human labels |
| model_version | text nullable | Configured model name; NULL for keyword/human |
| prompt_version | text | extract-v1; version of extraction contract |
| review_status | pending/approved/rejected | Unreviewed candidates are pending; human approval required |
| updated_at | timestamptz | Label-generation/review time |

## tag_reviews (private)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| id | uuid PK | Generated immutable review record ID |
| event_id | text FK | Reviewed event |
| content_hash | text | Exact reviewed event version |
| reviewer | text | Operator-supplied reviewer identity, required; never public |
| labels | jsonb | Validated Labels schema, including evidence; not model gold |
| created_at | timestamptz | Review submission timestamp |

## evaluation_splits (private)
| Field | Type / allowed | Meaning, provenance and missing handling |
|---|---|---|
| event_id | text PK/FK | Frozen sampled event |
| group_id | text | Union-find representative of related/recurring/duplicate records |
| split | train/validation/test | Assignment by chronological group order, not tuned against outcomes |
| frozen_at | timestamptz | Timestamp of first immutable split manifest |

## Cleaning and coverage decisions
No records in the initial snapshot failed required date/ID/title validation. 638 Engage and 849 Localist records remain separate source occurrences. Three excess exact cross-source keys are flagged by analysis and collapsed during recommendations; no fuzzy merge is asserted. Seventeen cancellations are explicit. Missing structured venue/end values are retained even if prose or title offers clues. Localist dates can describe a registration window rather than the later activity date; users should inspect the official page. Midnight is not assumed all-day. Historical and far-future records remain available for analysis; upcoming API results use an explicit time/status filter. Full original feeds live under ignored `data/raw/`; item versions live privately in Supabase. RSS pubDate is preserved in raw XML only.
