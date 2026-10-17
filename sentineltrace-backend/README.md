# SentinelTrace Backend

Backend for SentinelTrace — a predictive cybercrime intelligence platform (SIH 2026). This document covers **Stage 1** (Model A research → runtime artifacts) and **Stage 2** (FastAPI + PostgreSQL foundation), which are both complete. Later stages (predictions API, risk engine, alerts, Model B, authentication, frontend integration) are **not yet implemented** — see "Current scope" below.

## Terminology (do not change)

- **Model A = Experiment 2 = Mule-Chain Identification** — PRIMARY, implemented.
- **Model B = Experiment 1 = Cash-Out Location Prediction** — DEFERRED, not implemented in this backend.

## Architecture

```
React/Vite Frontend (frozen, separate project)
             │  REST, /api/v1/*
             ▼
          FastAPI  (app/main.py)
             │
      ┌──────┴──────┐
      ▼             ▼
 PostgreSQL     Model A (model_a_v1.pkl, loaded once at startup)
 (accounts,          │
  transactions,      ▼
  complaints)   Graph engine (app/services/graph.py, NetworkX,
                database-backed, infrastructure only)
```

## Directory structure

```
sentineltrace-backend/
├── app/
│   ├── main.py            FastAPI app + lifespan (loads Model A once at startup)
│   ├── config.py           Settings, loaded from .env
│   ├── database.py         SQLAlchemy engine/session/Base
│   ├── models/             SQLAlchemy ORM models (Account, Transaction, Complaint)
│   ├── schemas/             Pydantic response schemas
│   ├── api/                 Route modules (health, accounts, transactions, complaints)
│   ├── services/
│   │   ├── model_a.py      Model A loading/registry service
│   │   └── graph.py         Database-backed graph engine (NetworkX), bounded BFS
│   └── core/
│       └── dependencies.py  Shared FastAPI dependency re-exports
├── scripts/
│   ├── seed_model_a.py                Imports persisted Stage 1 CSVs into PostgreSQL
│   └── check_model_a_compatibility.py Verifies model/metadata/data alignment
├── tests/                    pytest suite (16 tests, see below)
├── research_model_a/         Verbatim copies of the authoritative Model A research code
├── data/model_a/             Persisted Stage 1 dataset (accounts/transactions/complaints/candidates CSVs)
├── artifacts/model_a/        Trained model_a_v1.pkl + metadata JSON files
├── train_model_a.py          Stage 1 training entry point
├── verify_model_a.py         Stage 1 independent-process verification script
├── requirements.txt
├── .env.example
└── .gitignore
```

## Python version

Python 3.12.3 (confirmed working; recorded in `artifacts/model_a/training_metadata.json`).

## Setup

```bash
cd sentineltrace-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Do not casually upgrade `numpy`/`pandas`/`scikit-learn`/`joblib`** beyond the versions pinned in `requirements.txt` — those exact versions were used to train `model_a_v1.pkl`, and scikit-learn does not guarantee cross-version pickle compatibility for `HistGradientBoostingClassifier`.

## Environment variables

Copy `.env.example` to `.env` and fill in real values (never commit `.env`):

```
DATABASE_URL=postgresql+psycopg2://<user>:<password>@localhost:5432/sentineltrace
MODEL_A_PATH=artifacts/model_a/model_a_v1.pkl
MODEL_A_VERSION=model_a_v1
ENVIRONMENT=development
API_HOST=0.0.0.0
API_PORT=8000
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:4173
```

This backend's `.env`/`.env.local` are entirely separate from the frontend's `.env.local` (which holds `VITE_CARTO_API_KEY`) — neither project reads the other's environment file.

## PostgreSQL setup

Any PostgreSQL 14+ works. Locally:

```bash
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"
sudo -u postgres psql -c "CREATE DATABASE sentineltrace;"
```

Make sure PostgreSQL is listening on TCP (not just the Unix socket) if you connect via `localhost` in `DATABASE_URL` — check `listen_addresses` in `postgresql.conf`.

## Database seeding

**Seeds from the already-persisted Stage 1 CSVs — does not regenerate synthetic data.**

```bash
python scripts/seed_model_a.py
```

Expected output: `accounts = 4025`, `transactions = 38830`, `complaints = 500`. If these numbers differ, investigate — do not silently regenerate a new synthetic world.

## Running the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Model A is loaded exactly once at startup (via FastAPI's lifespan handler), not per-request. If the artifact or its metadata is missing/incompatible, the app fails to start rather than serving without a model.

## Running tests

```bash
python -m pytest tests/ -v
```

The test suite runs against the real configured PostgreSQL database (no separate test-database setup in Stage 2) and auto-seeds it via `scripts/seed_model_a.py` if empty.

## Model A

- Artifact: `artifacts/model_a/model_a_v1.pkl`
- Class: `sklearn.ensemble.HistGradientBoostingClassifier(max_depth=6, random_state=42)`
- Version: `model_a_v1`
- Features (exact order): `hop_distance, pass_through_ratio, fan_in_recent_30d, out_degree_recent_30d, account_age_days, confirmed_history_count, amount_consistency, subgraph_degree_centrality`

Run `python scripts/check_model_a_compatibility.py` at any time to verify the artifact, its metadata, and the persisted candidate data are mutually consistent.

### Known feature-naming discrepancy

`SentinelTrace_Technical_Contract.md` §8 names two features `fan_in_recent` and `out_degree_recent`. The actual, authoritative Model A code (`research_model_a/experiment2_features.py`) — and therefore the trained artifact and this entire backend — uses `fan_in_recent_30d` and `out_degree_recent_30d`. **The code and artifact are treated as authoritative; the Contract document is out of date on this point and should be corrected there, not by renaming the model's features.**

## Current scope (Stage 2 + Stage 3A + Stage 3B + Stage 4 + Stage 5 + Stage 6)

**Implemented (Stage 2):** FastAPI app, PostgreSQL schema + seeding, Model A loaded once at startup, `GET /api/v1/health`, `GET/{id} /api/v1/accounts`, `GET /api/v1/transactions`, `GET/{id} /api/v1/complaints`, a database-backed graph engine foundation (build graph, neighbors, bounded BFS, hop distance).

**Implemented (Stage 3A):** Real Model A inference — `POST /api/v1/predictions/run` and `GET /api/v1/complaints/{id}/mule-chain`. Candidate discovery and feature engineering reuse `research_model_a/experiment2_features.py::build_candidate_table` UNCHANGED against real PostgreSQL data (see `app/services/candidate_generation.py`). Results are ranked, explained (deterministic feature-threshold notes, not SHAP), and persisted to `mule_chain_predictions` using a "replace current" idempotency strategy.

**Implemented (Stage 3B):** `GET /api/v1/complaints/{id}/graph` — a complaint-specific investigation graph (see `app/services/complaint_graph.py`), built by reusing Stage 3A's validated `build_candidates_for_complaint` for node membership/hop-distance (deliberately NOT app/services/graph.py's generic time-unaware BFS — see that module's docstring for why), plus real transaction edges from PostgreSQL, plus persisted-prediction metadata attached to matching nodes where available. Prediction persistence was hardened: delete+insert is now an explicit atomic transaction with rollback-on-failure, and concurrent requests for the same complaint are serialized via a PostgreSQL advisory lock (`pg_advisory_xact_lock`) so they can never interleave into an inconsistent state. `POST /predictions/run`'s response now reads its `generated_at` back from the committed row, so it is byte-identical to what a subsequent `GET` returns.

**Ground-truth leakage found and fixed during Stage 3B:** an early draft of the graph endpoint exposed `accounts.acc_type` directly as `"account_type"`. Inspection of `research_model_a/generate_graph_v1.py` confirmed this field's values (`legit_low`/`legit_high`/`hub`/`confusor`/`mule`/`adversarial_bait`) are the synthetic simulation's ground-truth role labels — exposing them would have let any API consumer bypass Model A entirely by filtering on `account_type=="mule"`. This field has been removed from the graph response; see `app/services/complaint_graph.py`'s module docstring.

**Known limitation carried from Stage 3A (unchanged, not "fixed" in 3B per instructions):** `confirmed_history_count` is always `0` in production because no real resolved-case ledger exists — an honest value, not a fabricated one. Diverges from `candidates.csv` for ~3.75% of candidates dataset-wide; see `SentinelTrace_Stage3B_Report.md` for the measured impact.

**Intentionally NOT implemented yet** (later stages):
- Model B / cash-out location prediction
- Case actions, investigation workflow, investigator notes/assignment, evidence management, audit log
- Authentication / authorization
- Frontend integration (the frontend remains on its own mock data layer)
- Docker/Kubernetes, cloud deployment, production hardening
- A real resolved-case ledger for `confirmed_history_count`
- Full prediction-run / risk-run / alert-run audit history (current design keeps only the latest run per complaint)

## Stage 4 — Risk Scoring + Intervention Window

Implements `SentinelTrace_Technical_Contract.md` §10 (Risk Engine) and §11 (Intervention Window). **The operational risk score is a derived prioritization signal, not a calibrated probability.** **The intervention window is an estimate based on available synthetic temporal/network evidence and has not been validated against real-world cash-out timing.**

### Architecture

```
Persisted Model A prediction (Stage 3A/3B, unchanged)
        │
        ▼
app.services.risk_engine          app.services.intervention_engine
   ml_score (copied verbatim)        estimated_window_minutes (from real
   heuristic_score (graph-only)      historical account/dataset transaction
   priority.{level,value}            timing, day < complaint.day only)
   drivers (permutation importance
     × candidate's actual feature value)
        │                                   │
        └──────────────┬────────────────────┘
                        ▼
        app.services.risk_orchestration.compute_and_persist()
        (atomic, per-complaint advisory-locked, "replace current")
                        │
                        ▼
  risk_scores table          intervention_windows table
```

### Risk score — inputs, formula, weights (all in `app/core/risk_config.py`, nothing scattered inline)

- `ml_score`: Model A's own output, copied verbatim from the persisted `mule_chain_predictions` row. Never modified.
- `heuristic_score`: an independent, ML-free "graph flow-decay" formula — `0.35·e^(-0.5·hop_distance) + 0.30·pass_through_ratio + 0.15·min(fan_in_recent_30d/10, 1) + 0.20·subgraph_degree_centrality`, clipped to [0, 1]. Reported alongside `ml_score` as a sanity-check view, and is **not** an input to `priority.value` (per the Contract's own worked example).
- `priority.value = 0.60·ml_score + 0.25·fraud_amount_tier + 0.15·hours_since_complaint_normalized`, clipped to [0, 1] — exactly the three inputs (`ml_score`, `fraud_amount_tier`, `hours_since_complaint`) named in Contract §10.
  - `fraud_amount_tier`: `complaint.fraud_amount` bucketed at ₹10k/₹50k/₹200k into {0.25, 0.50, 0.75, 1.00}.
  - `hours_since_complaint_normalized`: hours elapsed since the complaint (mapped from its synthetic `day` via a fixed, documented, arbitrary epoch — `2026-01-01T00:00:00Z` — since the synthetic dataset has no real calendar anchor), saturating at 1.0 after 72 hours.
- `priority.level` bands: low `[0, 0.40)`, medium `[0.40, 0.65)`, high `[0.65, 0.85)`, critical `[0.85, 1.0]`.
- `priority.method` is always the fixed literal `"heuristic_combination"` — there is no labeled outcome data to train a priority model on.
- `drivers`: top-3 Model A features by **permutation importance**, computed once (cached in-process) from the existing frozen `model_a_v1.pkl` against Stage 1's own held-out evaluation split — a read-only post-hoc analysis that does not retrain or modify the model, and is **not** written back into `feature_metadata.json` (Stage 1 artifacts stay untouched on disk). Each driver combines that global ranking with the specific candidate's own feature value via a fixed plain-language template (see `DRIVER_TEMPLATES` in `risk_config.py`).

### Intervention window — method (`synthetic_historical_hop_timing`)

For the top-ranked candidate, `estimated_window_minutes` is the median of that **specific account's own historical incoming→outgoing transaction time gaps**, restricted to `day < complaint.day` (no future leakage) — real persisted data, not fabricated. If the account has no such history (common for very new accounts), falls back to a dataset-wide median computed the same way, and the response's `rationale` field says so explicitly. Result is clipped to [5, 1440] minutes. `validation_status` is always the fixed literal `"synthetic_demo_only"` — this has not been validated against any real cash-out event, because no such ground truth exists in this project.

### API

```
POST /api/v1/complaints/{complaint_id}/risk    — computes + persists risk scores AND
                                                   the intervention window together,
                                                   atomically. 409 if no Model A
                                                   prediction exists yet for the complaint.
GET  /api/v1/complaints/{complaint_id}/risk               — retrieves persisted risk scores (never recomputes)
GET  /api/v1/complaints/{complaint_id}/intervention-window — retrieves the persisted window (never recomputes)
```

### Persistence

Two new tables, `risk_scores` and `intervention_windows` (see `app/models/risk.py` / `app/models/intervention.py` for the exact column-by-column mapping to the Contract's frozen schema, including the one documented adaptation: integer `complaint_id`/`account_id` foreign keys, matching every other table in this project, instead of the Contract's generic UUID assumption). Same "replace current" idempotency strategy as Stage 3B's `mule_chain_predictions`, in the **same transaction** as the risk rows (a partial write — risk without intervention, or vice versa — cannot happen), serialized per-complaint via the same `pg_advisory_xact_lock` pattern.

### Known limitations (Stage 4)

- The risk score is a heuristic prioritization signal with hand-chosen (documented) weights — it has not been tuned against any labeled outcome data, because none exists for this synthetic project.
- The intervention window's timing estimate is derived from synthetic transaction data only; it has no relationship to real-world cash-out behavior.
- `confirmed_history_count` remains `0` in every risk driver calculation, unchanged from Stage 3A/3B, for the same documented reason (no real resolved-case ledger exists).
- The existing API response envelope (flat JSON, not the Contract §14's generic `{data, error}` wrapper) is a pre-existing deviation carried forward from Stage 2/3A/3B for consistency with every other endpoint in this backend, not something introduced in Stage 4.

### Intentionally NOT implemented yet (later stages, as of Stage 4)

- Model B / cash-out location prediction
- Alerts, case actions, investigator audit log
- Authentication / authorization
- Frontend integration (the frontend remains on its own mock data layer)
- Docker/Kubernetes, cloud deployment, production hardening
- A real resolved-case ledger for `confirmed_history_count`
- Full prediction-run / risk-run audit history (current design keeps only the latest run per complaint)

## Stage 5 — Alerts + Prioritization

**No `SentinelTrace_Technical_Contract.md` file exists anywhere in this repository or the surrounding environment** (confirmed by exhaustive search before any Stage 5 code was written). Every prior stage's code and this README cite that file as authoritative, but Stage 5 could not locate it. Stage 5 therefore follows the Stage 5 brief's own explicit fallback rule: build "the smallest defensible alert model" from the concepts it lists, document every threshold/weight/name choice in one place, and flag the missing contract clearly rather than inventing contract language. **If `SentinelTrace_Technical_Contract.md` is located later, Stage 5's schema/config should be reconciled against it.**

**The alert `priority_score` is a derived prioritization value, not a calibrated probability of fraud, and must never be presented as one.**

### Architecture

```
Persisted Stage 4 output (risk_scores, intervention_windows — unchanged, frozen)
        │
        ▼
app.services.alert_engine.compute_alerts_for_complaint()
   - filters to priority_level in {high, critical}          (app/core/alert_config.py)
   - alert_type: high_risk_mule_chain_detection, or
     critical_intervention_urgency for the rank==1 account
     if its intervention urgency band is high/critical
   - priority_score = 0.70·risk_priority_value + 0.30·urgency_component
   - explanation reuses Stage 4's own drivers/rationale text
        │
        ▼
app.services.alert_orchestration.compute_and_persist()
   (atomic, per-complaint advisory-locked, "replace current" — same lock
    key as Stage 4, so alert generation can't interleave with risk regen)
        │
        ▼
                    alerts table
```

### Alert generation — trigger rule

An alert is generated for a candidate account **iff** its already-persisted Stage 4 `RiskScore.priority_level` is `high` or `critical` (`ALERT_TRIGGERING_PRIORITY_LEVELS` in `app/core/alert_config.py`). Nothing is re-scored; Stage 5 only reads `risk_scores`, `intervention_windows`, and `mule_chain_predictions.rank/model_version` (all already leakage-safe). Never reads `complaints.chain`, `accounts.acc_type`, or `candidate.label`.

### Alert prioritization — exact formula

```
priority_score = ALERT_PRIORITY_WEIGHT_RISK (0.70) × risk_priority_value
                + ALERT_PRIORITY_WEIGHT_URGENCY (0.30) × urgency_component
urgency_component = 1 − min(estimated_window_minutes / 1440, 1)   [0.0 if this
                      account has no intervention window — i.e. every
                      candidate except Stage 4's rank==1 account]
```

Weights (sum to 1.0, enforced by a test) and all thresholds live in `app/core/alert_config.py` — nothing scattered inline. `priority_score` is distinct from, and never overwrites, Model A's `ml_score` or Stage 4's `priority.value` (both are also carried onto the alert row, unmodified, for transparency).

### Alert types / severity

- `high_risk_mule_chain_detection` — default type whenever the trigger rule fires.
- `critical_intervention_urgency` — upgrade applied only to the rank==1 candidate (the only account Stage 4's intervention engine computes a window for) when its urgency band (`app.services.intervention_engine.urgency_band`) is `high` or `critical`.
- `severity` is copied verbatim from Stage 4's `priority_level` (`high`/`critical` only, by construction).

### Alert lifecycle

`status` ∈ `{open, acknowledged, resolved}` (`ALERT_VALID_STATUSES`). Every generated alert is created — and, on regeneration, reset — to `open`. **No status-mutation endpoint is implemented in Stage 5**; investigator-driven transitions belong to a later case-management stage. Because generation uses "replace current" and `alerts.risk_score_id` has an `ON DELETE CASCADE` to `risk_scores.score_id`, re-running `POST /risk` for a complaint also deletes that complaint's alerts (they were derived from the now-superseded risk rows) — a deliberate consistency choice, not a bug.

### Database

New table `alerts` (`app/models/alert.py`): `alert_id` (UUID PK), `complaint_id`/`account_id` (integer FKs, same convention as every other Stage 2+ table), `risk_score_id` (UUID FK → `risk_scores.score_id`, `ON DELETE CASCADE`), `rank`, `alert_type`, `severity`, `status`, `priority_score`, `risk_priority_value`, `title`, `explanation`, `model_version`, `created_at`, `updated_at`. No `label`/`chain`/role column.

### API

```
POST /api/v1/complaints/{complaint_id}/alerts/generate  — generate + persist alerts (idempotent,
                                                             replace-current). 409 if no Stage 4
                                                             risk score exists yet for the complaint.
GET  /api/v1/complaints/{complaint_id}/alerts            — retrieve persisted alerts (never recomputes)
GET  /api/v1/alerts/queue?limit=100                       — deterministic prioritized queue across
                                                             all complaints
```

### Ordering rule (alert queue)

1. `priority_score` desc
2. Stage 4 `risk_priority_value` desc
3. Model A `rank` asc
4. `complaint_id`, `account_id` asc (deterministic tie-breaker)

Never relies on database default/insertion ordering.

### Known limitations (Stage 5)

- Built without the referenced technical contract file, which could not be located (see above) — schema/thresholds are a documented, defensible default, not a contract-verified one.
- `priority_score`'s weights are hand-chosen and undocumented against any labeled outcome data, because none exists for this synthetic project (same limitation as Stage 4's `priority.value`).
- No status-mutation endpoint; `status` exists in the schema for forward compatibility but cannot yet be changed via the API.
- Regenerating an alert set (or the underlying risk score) resets/removes prior alert state — there is no alert history/audit trail yet.

### Intentionally NOT implemented (Stage 5)

- Case actions, investigation workflow, investigator notes, evidence management
- Authentication / authorization
- Frontend integration
- Model B / cash-out location prediction
- Notification infrastructure (email/SMS/push), Kafka/Redis/Celery, microservices
- Deployment / production infrastructure

### Stage 5 static audit (post-implementation hardening)

A follow-up static audit (no PostgreSQL/pytest/Python packages were available in that environment either — see "Runtime verification" note below) found and fixed two genuine bugs, and confirmed the rest of the implementation correct by inspection:

1. **`GET /complaints/{id}/alerts` incorrectly 404'd on legitimately-empty results.** The original code treated "zero alert rows persisted" as always meaning "generate was never called" (mirroring Stage 4's risk/intervention 404 pattern, which is safe there because a successful risk computation always produces ≥1 row). That assumption doesn't hold for alerts: a legitimate generation run can correctly produce zero rows (e.g. a complaint whose top candidate is only medium priority), and the endpoint had no way to tell that apart from "never generated" — it returned a misleading "run generate first" 404 even when generate had already run correctly. **Fix:** `GET` now 404s only when the complaint itself doesn't exist; an empty alert list is always returned as `200` with `results: []`. See `app/services/alert_orchestration.py::get_persisted_alerts` and `app/api/alerts.py::get_alerts` docstrings for the full explanation, and `tests/test_alert_api.py`'s two new regression tests.
2. **The leakage-protection test used an unsound check.** `tests/test_alert_engine.py::test_alert_engine_never_reads_forbidden_fields` did a raw substring search for `.chain`/`.label`/`.acc_type` against `alert_engine.py`'s full source text — which also matches those same words appearing in the module's own docstring (documenting what it deliberately does *not* read), so the test would fail against a file that is actually leakage-safe. **Fix:** rewritten to parse the file with `ast` and only inspect genuine `Attribute`/`Subscript`/keyword-argument nodes, which correctly ignores docstrings/comments while still catching real executable access. Confirmed via a one-off AST scan that `alert_engine.py` has zero forbidden executable accesses either way — this was a test-correctness bug, not an actual leakage bug.

No other correctness issues were found. In particular, the `priority_score` formula, the delete-then-insert idempotency strategy (verified safe under concurrent regeneration via the shared per-complaint advisory lock), the `alert_type` upgrade rule, and complaint 452's traced values (account 3722, `risk_priority_value ≈ 0.873176`, urgency_component `0.0` because its intervention window is clipped to the 1440-minute maximum → `urgency_band="low"`, `priority_score ≈ 0.611223`) were all verified correct against the documented policy and were **not** changed.

**Runtime verification note:** none of this was executed — no PostgreSQL, network, or Python packages (fastapi/sqlalchemy/pytest/etc.) were available in the auditing environment. All findings above come from direct source reading, manual arithmetic tracing, and standalone `ast`/string analysis run with the Python 3 standard library only. Run `pytest -q` in a properly configured environment to get an actual pass/fail count.

## Stage 6 — Case Management / Investigation Workflow

**`SentinelTrace_Technical_Contract.md` remains unavailable** (searched exhaustively again before Stage 6 work began — same result as Stages 5). This scope was derived from the only non-speculative source of truth available: every prior stage's own scope document explicitly and repeatedly names "case actions, investigation workflow, investigator notes, assignment, evidence management" as belonging to "Stage 6 or later", and Stage 5's `Alert.status` field was deliberately built with no mutation endpoint for exactly this reason. Evidence/attachment management is **excluded** from this Stage 6 scope — every prior stage's deferred-list treats "case notes" and "evidence management" as two separate future items, and there is no basis in this repo to design a file/evidence schema without a contract.

### Architecture

```
Stage 5 Alert (persisted, derived, deterministic — unchanged)
        │
        ▼  POST /alerts/{alert_id}/cases   (one case per alert; 409 if one already exists)
app.services.case_engine.open_case_for_alert()
        │
        ▼
                    cases table  ◄── PATCH /cases/{case_id}       (validated status transition and/or assignment)
                         │
                         ▼
                    case_notes table  ◄── POST /cases/{case_id}/notes   (append-only)
```

Unlike Stage 5's alerts (fully-derived, safely regenerable via "replace current"), a **Case is investigator-authored state**: created once, then mutated by real, validated UPDATEs — there is no regeneration concept for a case.

### Status lifecycle (exact transition graph, `app/core/case_config.py`)

```
open          -> investigating, escalated, resolved
investigating -> escalated, resolved
escalated     -> resolved
resolved      -> (terminal — no transitions out via this API)
```

Any other transition request returns `409 Conflict` and mutates nothing (validated before any write). An unrecognized status value returns `422`.

### Assignment

`assigned_to` is a free-text investigator identifier (no auth/user table exists in this backend at any stage). `PATCH /cases/{case_id}` distinguishes "field omitted from the request body" (leave unchanged) from "field explicitly set to `null`" (clear the assignment) using Pydantic v2's `model_fields_set` — both otherwise parse to the same Python `None`, so this distinction is deliberate, not accidental.

### Database

Two new tables, `app/models/case.py`:
- `cases`: `case_id` (UUID PK), `alert_id` (UUID FK → `alerts.alert_id`, **unique**, `ON DELETE CASCADE`), `complaint_id`/`account_id` (denormalized from the alert at creation time only, for query convenience), `status`, `assigned_to` (nullable), `created_at`, `updated_at`.
- `case_notes`: `note_id` (UUID PK), `case_id` (FK → `cases.case_id`, `ON DELETE CASCADE`), `author`, `note_text`, `created_at` (append-only — no `updated_at`, no edit/delete endpoint).

**Cascade behavior (inherited from Stage 5, verified not assumed):** because `alerts.risk_score_id` has `ON DELETE CASCADE` to `risk_scores.score_id`, and `cases.alert_id` has `ON DELETE CASCADE` to `alerts.alert_id`, **regenerating Stage 4 risk for a complaint (`POST /risk`) deletes that complaint's alerts and, transitively, any cases built on them.** This was already true and documented in Stage 5; Stage 6 does not change it, and `tests/test_case_api.py::test_alert_deletion_cascades_to_case` verifies it directly rather than assuming it.

### API

```
POST  /api/v1/alerts/{alert_id}/cases   — open a case from an alert (201; 404 if alert missing; 409 if a case already exists for it)
GET   /api/v1/cases/{case_id}           — retrieve a case (404 if missing)
GET   /api/v1/cases                     — deterministic case queue
PATCH /api/v1/cases/{case_id}           — status transition and/or assignment (404/409/422 as above)
POST  /api/v1/cases/{case_id}/notes     — append an investigator note (201; 404 if case missing)
GET   /api/v1/cases/{case_id}/notes     — retrieve notes, chronological order
```

### Case queue ordering

1. Status urgency rank: `escalated` → `investigating` → `open` → `resolved` (`CASE_STATUS_QUEUE_RANK`)
2. Most recently updated first
3. `case_id` as a final deterministic tie-breaker

### Leakage protection

No `label`/`chain`/`acc_type`/synthetic-role column exists anywhere in the Case/CaseNote schema. `tests/test_case_api.py::test_case_modules_never_read_forbidden_fields` uses the same AST-based check (not naive substring matching — see the Stage 5 static audit note above for why that matters) established for `alert_engine.py`, and confirms zero forbidden executable accesses in `case_engine.py`, `cases.py`, and `case.py`.

### Known limitations (Stage 6)

- Built without the referenced technical contract, which remains unlocatable — status names/transition graph are a documented, defensible default, not a contract-verified one.
- No auth/user system exists at any stage of this backend, so `assigned_to`/note `author` are unauthenticated free-text fields — anyone calling the API can set/spoof either.
- No evidence/attachment management (deliberately excluded from this scope — see above).
- `resolved` is terminal via this API; there is no "reopen" workflow yet.
- The case queue ordering test in `tests/test_case_api.py` is only a weak, single-case-in-practice check under this test suite's own setup (every test drives Stage 4/5 regeneration, which cascades to delete prior cases — see above), not a proven multi-case ordering test. The ordering *logic* itself (`case_engine.get_case_queue`) is simple and inspectable, but a true multi-case regression test would need a second complaint with a known triggering alert, which isn't available to construct without database access.

### Runtime verification status (Stage 6)

**Not executed in this authoring environment** — no PostgreSQL, network, or Python packages (fastapi/sqlalchemy/pytest/etc.) were available, same as every prior stage's authoring session. All of the above (transition-graph correctness, cascade behavior, AST leakage checks, `Pydantic` `model_fields_set` semantics) was verified by direct source reading, manual tracing, and standalone script runs using only the Python 3 standard library — never claimed as an executed `pytest` result. The Stage 5 baseline (110 passed, 0 failed) was reported from the project owner's own separately-configured machine, not reproduced here; Stage 6 additions should be verified there the same way before being treated as passing.

## Stage 7 — Structured Case Evidence

Explicitly authorized scope: let an investigator attach **references to evidence that already exists** in the backend to a Case. **Not** file/document management — no upload, no object storage, no new binary/JSON blob storage anywhere in this stage.

### Evidence types (closed set, `app/core/evidence_config.py`)

1. `transaction_reference` → an existing `transactions.transaction_id`
2. `graph_explanation_reference` → an existing `mule_chain_predictions.id` (the row whose already-persisted `explanation` JSONB is being cited — no second graph/explanation representation is computed)
3. `risk_driver_reference` → an existing `risk_scores.score_id`, optionally with a `driver_index` pointing into that row's already-persisted `drivers` JSONB array

No other evidence types exist; adding one requires explicit authorization (enforced by the closed `EVIDENCE_VALID_TYPES` list and a 422 for anything else).

### Design decision: three normalized tables, not one table with nullable columns

`app/models/evidence.py` defines `case_evidence_transaction`, `case_evidence_graph_explanation`, and `case_evidence_risk_driver` — three independent tables, each with exactly one always-required, DB-enforced foreign key to its specific target. This was an explicit instruction ("avoid unnecessary nullable reference fields if a cleaner normalized design is possible") — the alternative (one `case_evidence` table with three nullable FK columns, only one ever populated per row) would leave referential integrity for two out of three columns unenforced by the database on every row. `app/services/evidence_engine.py` composes reads across all three tables into one chronologically-ordered response.

### Relevance invariant (documented design decision, not dictated verbatim by the authorization)

Every evidence row must involve the case's **own** `complaint_id`/`account_id` (both denormalized onto the case at Stage 6 creation time):
- `transaction_reference`: the transaction's `src_account_id` or `dst_account_id` must equal the case's `account_id`.
- `graph_explanation_reference`: the prediction row's `complaint_id` **and** `candidate_account_id` must match the case's.
- `risk_driver_reference`: the risk score's `complaint_id` **and** `account_id` must match the case's.

A reference that exists in the database but fails this check is rejected as `422` (invalid reference target), distinct from `404` (reference doesn't exist at all). This prevents attaching an unrelated complaint's evidence to a case.

### API

```
POST /api/v1/cases/{case_id}/evidence   — attach evidence (201; 404 case/reference missing; 422 wrong shape/type/relevance)
GET  /api/v1/cases/{case_id}/evidence    — retrieve evidence, chronological order (404 if case missing)
```

No update/delete endpoint anywhere in this stage — evidence is immutable once attached, verified by `tests/test_evidence_api.py::test_evidence_has_no_update_or_delete_routes` (inspects the actual FastAPI route table, not just "we didn't write one").

### What is NOT persisted (critical data rule, explicitly required)

No evidence table has a free-form JSON/text column beyond an optional investigator `note` — there is structurally no place to put a duplicated transaction row, a second graph/explanation snapshot, `candidate.label`, `complaint.chain`, or any synthetic role. Every evidence row is a foreign key (plus, for risk drivers, an optional integer index into an already-persisted array) and nothing else.

### Leakage protection

Same AST-based check established in Stages 5–6 (not naive substring matching), run against all four new Stage 7 source files — zero forbidden executable accesses found.

### Known limitations (Stage 7)

- Built without the referenced technical contract, which remains unlocatable — the relevance invariant and closed evidence-type set are documented design decisions, not contract-verified ones.
- No auth, so `added_by` is unauthenticated free text, same limitation as Stage 6's `assigned_to`.
- Inherits Stage 5/6's cascade behavior: regenerating Stage 4 risk for a complaint cascades all the way down to delete that complaint's alerts, cases, **and now evidence** — verified directly in `tests/test_evidence_api.py::test_case_deletion_cascades_to_evidence`, not assumed.

### Runtime verification status (Stage 7)

**Not executed in this authoring environment** — no PostgreSQL, network, or Python packages were available, same as every prior stage's authoring session. All of the above was verified by direct source reading, manual tracing, and standalone `ast` script runs using only the Python 3 standard library. The Stage 6 baseline (**135 passed, 0 failed, 1 warning**) was reported from the project owner's own separately-configured machine; Stage 7 should be verified there the same way.

## Stage 8 — Case Resolution Outcomes

Explicitly authorized scope: an immutable, structured ledger recording an investigator's **outcome** after a Case reaches `resolved`. This is the one piece of the case lifecycle Stage 6 deliberately left as a bare status, and it begins accumulating real-world data toward (but does **not** itself implement) a genuine resolved-case ledger — a gap this project's own code and docs have flagged since Stage 3A (`app/services/candidate_generation.py`'s `confirmed_history_count` comment, and "A real resolved-case ledger for `confirmed_history_count`" in the Stage 3B/4/5 README sections above).

### Authorized outcome types (closed set, `app/core/resolution_config.py`)

`confirmed_mule`, `false_positive`, `insufficient_evidence`, `referred_external`. No others; adding one requires explicit authorization.

### Critical leakage distinction

**`confirmed_mule` is an investigator's real-world determination recorded after Stage 6/7 case work — it is NOT, and must never be confused with, this project's synthetic dataset's hidden ground-truth role labels** (`mule`, `legit_low`, `legit_high`, `hub`, `confusor`, `adversarial_bait`) or Model A's training/evaluation `label`/`chain` fields. The resemblance between `confirmed_mule` and the synthetic `mule` role is intentional and expected — building a *real*, investigator-verified alternative to the synthetic labels is the entire point of a resolved-case ledger. `app/services/resolution_engine.py` and every other Stage 8 file contain zero executable references to `label`/`chain`/`acc_type` (AST-verified, same method used since Stage 5).

### Business rules

- A resolution can be created **only** for a case whose current status is exactly `resolved` (409 otherwise) — read via `app.services.case_engine.get_case`, reused not reimplemented.
- Exactly one resolution per case, enforced by a **database-level UNIQUE constraint** on `case_resolutions.case_id`, not just application logic (409 on a second attempt).
- **Immutable once created** — no PATCH/DELETE endpoint exists at all (verified programmatically by inspecting the actual FastAPI route table, same technique as Stage 7). No case reopening, no outcome correction, no new case statuses.

### Critical boundary — `confirmed_history_count` remains untouched

**Stage 8 only builds and populates the `case_resolutions` table.** It is explicitly **not** wired into `candidate_generation.py`, `risk_engine.py`, Model A features/scoring, prediction generation, graph generation, or risk calculation — `confirmed_history_count` remains exactly `0` in production, unchanged. `resolution_engine.py` imports nothing from `candidate_generation.py` or `risk_engine.py` (statically verified). Any future consumption of this ledger by Model A is a **separately-authorized future stage** requiring full Model A parity/reproducibility re-verification.

### Database

One new table, `case_resolutions` (`app/models/case_resolution.py`): `resolution_id` (UUID PK), `case_id` (UUID FK → `cases.case_id`, **UNIQUE**, `ON DELETE CASCADE`), `outcome_type` (closed set), `resolution_note` (nullable text), `recorded_by` (free-text investigator id — no auth/user table exists in this backend), `created_at`. No `updated_at`. No JSON/blob/snapshot column — nowhere to duplicate transaction/prediction/graph/risk/complaint data even by accident.

### API

```
POST /api/v1/cases/{case_id}/resolution   — record outcome (201; 404 case missing; 409 case not resolved; 409 duplicate; 422 invalid/malformed)
GET  /api/v1/cases/{case_id}/resolution    — retrieve (200; 404 case missing; 404 no resolution recorded yet)
```

### Cascade behavior (inherited, verified not assumed)

Regenerating Stage 4 risk for a complaint cascades `risk_scores → alerts → cases → case_resolutions` (all `ON DELETE CASCADE`), same chain Stage 6/7 already established — verified directly in `tests/test_resolution_api.py::test_case_deletion_cascades_to_resolution`.

### Known limitations (Stage 8)

- Built against an explicit, detailed authorization rather than an actual contract file (still unlocatable) — the outcome-type set and business rules are a direct transcription of that authorization, not independently contract-verified.
- No auth, so `recorded_by` is unauthenticated free text, same limitation as Stage 6/7's `assigned_to`/`added_by`.
- No correction path for a mis-recorded outcome (immutable by design; a wrong entry has no fix mechanism in this stage).
- Not wired into `confirmed_history_count` — by design, and explicitly deferred to a separately-authorized future stage.

### Runtime verification status (Stage 8)

**Not executed in this authoring environment** — no PostgreSQL, network, or Python packages were available, same as every prior stage's authoring session. All of the above was verified by direct source reading, manual tracing, `ast` script runs, and `diff`/`md5sum` comparisons against the Stage 7 delivery, using only the Python 3 standard library. The Stage 6 baseline (**135 passed, 0 failed, 1 warning**) was reported from the project owner's own separately-configured machine; Stage 7/8 should be verified there the same way.

## Stage 9 — Investigation Dossier

A single, read-only endpoint that composes everything already computed and persisted across Stages 3A–8 for one Case into one coherent response — eliminating the need to manually cross-reference 7 separate endpoints to see the full story of an investigation.

### Endpoint

```
GET /api/v1/cases/{case_id}/dossier   — 200 if the case exists, 404 otherwise
```

No POST/PUT/PATCH/DELETE anywhere in this stage — verified programmatically (`tests/test_dossier_api.py::test_dossier_route_is_get_only`) that the router exposes `GET` only.

### Response composition

The response (`app/schemas/dossier.py`'s `DossierOut`) reuses every existing, already-established response schema rather than defining parallel copies: `case` → `CaseOut`, `notes` → `list[CaseNoteOut]`, `evidence` → `list[CaseEvidenceOut]`, `resolution` → `CaseResolutionOut | None`, `alert` → `AlertOut | None`, `risk` → `RiskScoreOut | None`, `intervention` → `InterventionWindowOut | None`, `prediction` → `RankedCandidateOut | None`, plus a `limitations: list[str]` field explaining any section that came back null and why.

### Deterministic association rules (no invented joins)

Every cross-stage link is either an actual persisted foreign key or the same `(complaint_id, account_id)` equality-matching pattern this repository already established in Stage 7's evidence-relevance checks — nothing new was invented:

- `Case.alert_id → Alert.alert_id` — persisted FK, exact.
- `Alert.risk_score_id → RiskScore.score_id` — persisted FK, exact.
- `InterventionWindowRecord` has no FK to Case/Alert at all — matched by `(complaint_id, account_id)` equality. Because Stage 4's intervention engine only ever computes a window for a complaint's **rank==1** candidate, this section is legitimately `null` for any case whose account wasn't top-ranked — a documented limitation, not a bug, and appended to the response's own `limitations` list when it occurs.
- `MuleChainPrediction` also has no FK to Case/Alert — matched by `(complaint_id, candidate_account_id)` equality, the identical pattern already used by `evidence_engine.py` to validate `graph_explanation_reference` evidence.

### Read-only guarantee

`app/services/dossier_engine.py` performs exclusively `db.get()`/`db.query()` calls — no `db.add`, `db.commit`, `db.delete`, and no SQLAlchemy `update()`/`delete()`/`insert()` construct anywhere in the file. Verified via `tests/test_dossier_api.py::test_dossier_engine_has_no_write_operations` (AST inspection of the actual source, not just a design intention) and `test_dossier_get_does_not_mutate_persisted_state` (snapshots every relevant table before/after two consecutive `GET`s and asserts byte-for-byte equality).

### Database

**No schema changes.** Zero new tables, columns, or indexes — this is the first stage since Stage 4 requiring no persistence at all.

### Leakage protection

Same AST-based check established since Stage 5, run against all 3 new source files — zero forbidden executable accesses to `chain`/`label`/`acc_type`. Response-level check confirms the bare synthetic-role string `"mule"` never appears as a standalone value (an investigator-recorded `"confirmed_mule"` resolution outcome, if present, is legitimate and expected — see Stage 8's leakage-distinction note above).

### Known limitations (Stage 9)

- Built against an explicit, detailed authorization rather than a locatable contract file.
- Case-level only — no complaint-level or cross-case rollup (a natural, low-risk future extension, not attempted here to keep scope tight).
- `intervention`/`prediction` sections are legitimately absent for a case whose account isn't the complaint's top-ranked candidate or whose original prediction row was superseded by a later re-run — both explained in the response's own `limitations` list rather than left as a silent null.
- Does not address `confirmed_history_count` at all — that remains fully deferred, and this stage introduces no new argument for or against pursuing it.

### Runtime verification status (Stage 9)

**Not executed in this authoring environment** — no PostgreSQL, network, or Python packages were available, same as every prior stage's authoring session. All of the above was verified by direct source reading, manual tracing, `ast` script runs, and `diff`/`md5sum` comparisons against the Stage 8 delivery, using only the Python 3 standard library. The Stage 6 baseline (**135 passed, 0 failed, 1 warning**) was reported from the project owner's own separately-configured machine; Stages 7, 8, and 9 remain pending local runtime verification there.
