# Implementation checklist
- [x] Inspect workspace and verify accounts and both official feeds
- [x] Preserve original downloads with collection timestamps
- [x] Implement repeatable ingestion, normalization, provenance and RLS
- [x] Load and verify real Supabase records
- [x] Produce dictionary, five plots, and 2–3 page data note
- [x] Reserve grouped holdout before tuning
- [x] Implement dashboard, API, controlled tagging and review
- [x] Implement preference-based recommendations and evaluation plan
- [x] Verify important behavior and existing app checks
- [x] Deploy and verify Modal dashboard/API
- [x] Publish private repository and record actual commit

- [ ] Unattended refresh: deferred by user. Server secret and signed-in browser needed when resumed; deployment file ready.
- [ ] Human-reviewed evaluation: no labels or relevance feedback yet.

## Niner Engage scope revision
- [x] Collect and serve only Niner Engage; preserve historical campus-calendar records
- [x] Regenerate five plots and three-page note for 638 records
- [x] Preserve split assignments in an active-source subset
- [x] Verify and redeploy the source-scoped dashboard/API
