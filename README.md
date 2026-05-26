# quali-fit — Explainable Staffing Recommender

An internal web tool that, given a work code, recommends the best-fit employees
**with the reason for each match shown next to the score**. It started as a real
in-house tool for a cost-engineering consultancy and is being grown into a
multi-tenant SaaS. This repo is the **generalized, synthetic-data version** — no
real data or real organization names are included.

**Status: active learning rebuild.** The app is being rewritten from scratch
("hello world" upward) by hand, one small phase per version, to study every
layer. See the [open issues](../../issues) for the live phase checklist.
Current target stack: **Streamlit + SQLite + layered Python** (db / domain / UI).

> **AI collaboration, stated up front.** The code is written together with an AI
> agent. My contribution is problem framing, data-model and scoring design,
> trade-off decisions, review, and course corrections. This README, the issues,
> and `docs/adr/` (planned) are the real artifacts — the *trace of judgment*, not
> the raw lines.

## Problem & context

When the firm bids on a project, the proposal must say "we will staff this work
with these people" — with evidence. That was manual. The input data (employees,
education, certifications, work codes) lived in messy CSV files. The goal: pick
a work code and get a ranked list of suitable employees, with a short, readable
**reason per person** (which certificates contributed, with what weight).

## What it does

- Manages six normalized tables (employees, education, employee↔cert,
  cert master, work-code master, work-code↔cert mapping) with validation and
  safe writes; anyone in the org can edit.
- For a chosen work code, joins the mapping table to find qualifying certs,
  sums per-cert influence (1–5), and produces a ranked employee list **with the
  rationale row-by-row**.
- Uses URL query parameters so a browser refresh keeps you on the same screen.

## Stack (target, in progress)

| Layer | Choice |
|---|---|
| UI / server | Streamlit (single Python process; no separate front-end) |
| Domain | Pure Python modules (scoring, validation) — no Streamlit imports |
| Storage | SQLite (one file per database; WAL mode; foreign keys enforced) |
| Runtime | Python 3.13 venv, `streamlit run app.py` |

The point of the layering is portability: the same `db` and domain code can
later sit behind FastAPI or another front-end with no rewrite.

## Key engineering decisions (planned ADRs in `docs/adr/`)

- **Surrogate keys, single source of truth.** Natural keys like `(name, dept,
  title)` were replaced by `employee_id`. The cert↔work-code mapping lives in
  one join table — not duplicated in the cert master.
- **Explainable scoring, not a black box.** Each contributing cert is shown
  with its influence level (1–5), its mapping rationale, and an expiry-adjusted
  contribution. Total = best contribution + diversity bonus (capped).
- **Deliberate trade-offs.** SQLite is right-sized for a small org and one or
  two tenants; Postgres would be over-engineering today. The plan documents the
  trigger for each next step (e.g., multi-tenant → SQLite-per-tenant → auth).
- **Mistakes and recovery.** A past migration accidentally lost three rows;
  they were restored from the timestamped backup, and the lesson became a
  guardrail in the code.

## Roadmap

1. **v0.0.1 – v0.1.0 — hand-rebuild to feature parity** (current path):
   hello-world → SQLite schema + CSV seed → read-only views → CRUD → validation
   → derived/dropdown UX → scoring → safe writes + backup → docs and parity.
2. **v0.2.x — authentication.** Local accounts for the demo; OIDC (`st.login`)
   for production. Auth boundary in its own module.
3. **v0.3.x — multi-tenant SaaS.** One SQLite file per tenant under
   `data/tenants/<id>/`. **Tenant is derived from the authenticated session
   only** (never from a query parameter or client input). Per-tenant
   `config.yaml` for display and weights. A synthetic demo tenant ships with
   the repo so reviewers can log in and try it.
4. **v0.4.x — FastAPI in front.** Add a REST API in front of the same `db` and
   domain code. The UI stays separate.

Out of scope for now (on purpose): billing, self-serve signup, automatic
tenant provisioning, RBAC, audit logs. Scope control is part of the design.

## Data and privacy (public repo)

- **No real data, no real names, no real organization, ever — not now, not in
  history.** Anonymizing 40 employees with rich attributes is not safe (small
  size + many attributes = re-identifiable). The repo will ship a synthetic
  data generator instead.
- Real data lives outside the repo (a separate `DATA_DIR`). Only synthetic
  samples and the generator get committed.
- Cleanliness is structural, not a chore: real data never enters the repo, so
  there is nothing to scrub.

## Run (current)

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Right now `app.py` is intentionally a "hello world" — the rebuild is in
progress. A working app with the SQLite layer and real (synthetic) data will
arrive over the next phases listed in the issues.

## How this is built (portfolio intent)

Even solo, the work is run through real artifacts: **one GitHub issue per
decision (context, options chosen, reason) → branch → PR with a self-review
(risks, rejected alternatives, verification) → meaningful merge**. Major forks
get an ADR in `docs/adr/`. The point is not commit count — it is a trace of
judgment that can be explained out loud.
