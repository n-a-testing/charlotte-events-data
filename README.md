# Charlotte Events Data Foundation

Fresh Python data/API project, independent of the earlier `campus-app`. Existing browser-local saved events and preferences were left untouched.

## Live services
- Dashboard: https://n-a-testing--charlotte-events-data-dashboard.us-east.modal.run
- API / OpenAPI docs: https://n-a-testing--charlotte-events-data-api.us-east.modal.run/docs
- Supabase: https://supabase.com/dashboard/project/spmwoqrgyjilbivzodxw
- Modal deployment: https://modal.com/apps/n-a-testing/main/deployed/charlotte-events-data
- Private repository: https://github.com/n-a-testing/charlotte-events-data

Snapshot: **1,487 real source occurrences**, 638 Niner Engage + 849 campus-calendar records, collected November 2, 2026. No fabricated events or evaluation scores. Public dashboard/API use a publishable key and read-only RLS. Raw source records, run details, reviewer identities and split assignments are private.

## Setup and run
Python 3.13 was used for verification and Modal deployment.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Set these in your shell or secret manager; .env.example is documentation,
# not automatically loaded by Python.
export SUPABASE_URL=https://spmwoqrgyjilbivzodxw.supabase.co
export SUPABASE_PUBLISHABLE_KEY=sb_publishable_tRll82_bbG7_XbYCvFgMqQ_0iR6liu7
streamlit run dashboard.py
# in another terminal with the same environment:
uvicorn api:app --host 127.0.0.1 --port 8080
pytest tests -q
```

The publishable key is intentionally public and grants no write/private-table privileges. Never replace it in committed configuration with a secret key.

## Ingestion and analysis

`schema.sql` is the exact schema blueprint applied once to the new project through the Supabase connector migration `event_data_foundation`. Do not rerun it on an existing database; use a new migration for changes. The initial load was published through authorized connector SQL, so no service-role secret was needed locally.

```sh
# In a server-side shell only, configure SUPABASE_SERVICE_ROLE_KEY securely.
python pipeline.py                     # collect both feeds and publish to Supabase
python pipeline.py --replay data/raw/SNAPSHOT_DIRECTORY
python analysis.py                     # five PNGs, statistics, immutable split manifest
python review.py queue                 # private blinded review queue
python review.py approve EVENT_ID labels.json --reviewer YOUR_NAME
python review.py tag-pending            # optional configured model; no key means no model claims
```

For connector-based publication without a local privileged key, `python pipeline.py --export` archives feeds and emits ordered SQL batches under ignored `data/sql/`. Apply `SOURCE-000.sql`, numbered batches, then `SOURCE-999.sql` in order using an authorized server connector. These SQL files contain raw source material and stay out of Git. The tail marks success only after all batches succeed. Do not mark a partially applied batch sequence successful. Replaying identical batches is safe and preserves first-seen timestamps and reviewed unchanged labels.

Original byte feeds and sidecar collection timestamps are under ignored `data/raw/`; item XML versions persist in Supabase. `analysis.py` currently analyzes `data/events.json` from the most recent ingestion/export; the interactive dashboard always reads Supabase directly. Reports describe the original frozen snapshot. To reproduce the PDF, use a Python environment with reportlab and run `python make_note.py`; the already-rendered three-page PDF is committed. Full-snapshot grouping audit skips in a fresh checkout until ingestion has created `data/events.json`; all parser/evidence tests use checked-in source excerpts.

## Deployment and unattended refresh

```sh
modal deploy modal_app.py --env main
```

The public serving app is deployed. **Automatic ingestion is deferred at the user’s request.** The initial attempt also lacked a server credential: the connector does not expose it, native computer-control permission was unavailable, and the in-app Supabase browser required sign-in. The dashboard continues to read the stored snapshot.

Prepared separate deployment `modal_ingest.py` mounts a durable archive Volume and refreshes at 11:00 UTC daily (6 AM EST / 7 AM EDT). To activate it, place `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in a Modal secret named `charlotte-events-ingest`, then:

```sh
modal deploy modal_ingest.py --env main
modal run modal_ingest.py::refresh --env main
```

Verify a successful ingestion run and new last-refresh timestamp before calling the schedule operational. The serving functions never receive this secret. Daily refresh can consume Modal credits. No LLM provider key was available, so all current labels are keyword candidates pending review; optional OpenAI-compatible extraction uses TAG_MODEL_URL, TAG_MODEL_NAME and TAG_MODEL_API_KEY in the ingestion/review environment only.

## API
- `GET /health`: database connectivity, event count and source refresh timestamps.
- `GET /events?source=ninerengage&q=chess&upcoming=true&offset=0&limit=50`: search and pagination (max 200); start dates are UTC ISO strings, campus display America/New_York.
- `POST /recommendations`: JSON interests, saved_ids, audience, free_food, free_admission, limit. No preference persistence. See OpenAPI for schema.

Reads cache for up to 120 seconds. Saved IDs can come from a future client adapter; existing localStorage is neither read nor altered by this new foundation. Factual filters require explicit yes; unknown is never a negative label. A read-only dashboard can show unreviewed tags with their provisional status; do not treat these as gold labels.

## D2 submission checklist
- [x] Real clean event records in Supabase, raw provenance and collection timestamps
- [x] Data dictionary: `DATA_DICTIONARY.md`
- [x] Five plots: `reports/figure-1.png` through `figure-5.png`, interpreted in the note
- [x] Three-page note: `reports/D2-data-note.pdf`
- [x] Frozen grouped split: `data/split_manifest.json`, also stored privately in Supabase
- [x] Supabase-backed Streamlit dashboard deployed on Modal
- [x] API, conservative tagging, review CLI and preference recommendations
- [x] Repeat-load, update, date/DST, recurrence, unsupported-food and private-access checks
- [ ] Configure server secret and verify scheduled refresh (deferred by user)
- [ ] Obtain independent human annotations and measure evaluation results (later phase)

## Files and verification
- `pipeline.py`, `storage.py`, `schema.sql`: source archival, parsing and database publication.
- `tagging.py`, `review.py`, `recommend.py`, `api.py`: tagging/review/ranking/API foundation.
- `dashboard.py`, `modal_app.py`, `modal_ingest.py`: user-facing data dashboard and deployment.
- `analysis.py`, `make_note.py`, reports, dictionary and `EVALUATION.md`: D2 and evaluation design.
- `tests/`: deterministic source-excerpt tests plus full-snapshot grouping audit.

See `reports/live-verification.json` for actual verification. Replaying all 1,487 records produced no extra events, raw versions or tags. A changed-content upsert was verified inside a rolled-back transaction. Public private-table reads and catalog writes returned HTTP 401. Supabase security advisory reported only four informational RLS-with-no-policy notices, intentional for private tables. Nine foundation tests passed; the untouched earlier app passed syntax checks and all eleven tests. No learned-model quality or recommendation performance is asserted.
