# OneMate

### AI-Driven Standardization & Harmonization of Material Codes Across CPSEs

**Smart India Hackathon 2026** · SIH26099 · Smart Automation · Software

OneMate converts fragmented CPSE material data into a governed national
catalog — while preserving engineering identity, source provenance, human
decisions, and audit history.

[Problem](#the-problem) ·
[Solution](#solution) ·
[How It Works](#how-it-works) ·
[Architecture](#architecture) ·
[API Surface](#api-surface) ·
[Status](#current-status) ·
[Getting Started](#getting-started)

---

## The Problem

Across CPSEs, the same engineering material can be represented in completely
different ways:

```text
BALL VALVE 2" CL300 RF CS SS304
BALL VLV DN50 CLASS 300 RF CARBON STEEL
2 IN BALL VALVE 300 LB RAISED FACE CS
```

These descriptions may refer to the same material. But a harmonization
system cannot rely on textual similarity alone — a single changed technical
attribute can mean a genuinely different engineering item:

```text
CLASS150  ≠  CLASS300
DN50      ≠  DN100
BALL      ≠  GATE
RF        ≠  SOCKET_WELD
SS304     ≠  SS316
```

The real challenge:

> How do we standardize material descriptions across enterprises without
> losing engineering meaning or creating unsafe mappings?

---

## Solution

OneMate provides a governed workflow for moving source material catalogs
from multiple CPSEs into a common National Material registry.

```text
CPSE SOURCE DATA
      │
      ▼
   IMPORT
      │
      ▼
 NORMALIZATION
      │
      ▼
   MATCHING
 ┌────┼────┐
 ▼    ▼    ▼
SAME POTENTIAL DIFFERENT
 │    │
 ▼    ▼
HARMONIZE REVIEW
 │    │
 └─┬──┘
   ▼
NATIONAL MATERIAL
   │
   ▼
AUDIT TRAIL
   │
   ▼
DASHBOARD
```

Core design principle:

> Similarity can suggest. Engineering rules decide. Humans govern
> uncertainty.

### Why it's built this way

- **Engineering-first** — identity comes from structured technical
  attributes, not text similarity alone.
- **Safety-first** — a hard technical conflict always overrides a high
  similarity score.
- **Human-in-the-loop** — uncertain matches are surfaced for review, never
  silently mapped.
- **Traceable** — the original uploaded row is preserved alongside
  normalized values.
- **Auditable** — every governance decision is recorded with actor, reason,
  and before/after state.
- **Minimal infrastructure** — a conventional relational architecture; no
  vector databases, queues, or external AI APIs for the MVP.

---

## How It Works

**1. Register a CPSE** — create the enterprise source namespace for a
catalog.

**2. Import Materials** — upload a CPSE material catalog as CSV or XLSX.
OneMate preserves the source material code, description, UOM,
specifications, and raw source payload, separately from anything derived
from it.

**3. Normalize** — descriptions are converted into structured attributes:
valve type, size, body material, pressure class, connection type, trim,
UOM. Missing information stays missing — `NULL` is unknown, never a
wildcard.

**4. Match** — materials are compared against candidates and classified as
`SAME`, `POTENTIALLY_EQUIVALENT`, or `DIFFERENT`, each with evidence,
confidence, and an explanation.

**5. Harmonize** — complete, safe `SAME` matches map automatically to an
existing or newly created National Material, so equivalent materials from
different CPSEs converge on one canonical identity.

**6. Human Review** — uncertain recommendations enter a review queue.
Reviewers can accept, reject, mark different, or override — with a reason
required for anything that contradicts the AI's evidence.

**7. Audit** — every material operation and governance decision is
recorded: actor, action, entity, reason, before state, after state,
timestamp.

### Matching safety

`BALL VALVE DN50 CLASS150` and `BALL VALVE DN50 CLASS300` can be lexically
and semantically almost identical — but the pressure class differs, so the
result is `DIFFERENT`, unconditionally. The same holds for `SS304` vs.
`SS316`, `DN50` vs. `DN100`, `BALL` vs. `GATE`, `RF` vs. `SOCKET_WELD`. A
hard technical conflict is never overridden by a similarity score, no
matter how high.

---

## Architecture

```text
┌─────────────────────────────────────────┐
│              Frontend                    │
│      React + TypeScript + Vite           │
└───────────────────┬───────────────────────┘
                    │ REST
                    ▼
┌─────────────────────────────────────────┐
│            FastAPI Backend               │
│                                           │
│  CPSE Management                         │
│        │                                 │
│        ▼                                 │
│  Material Ingestion                      │
│        │                                 │
│        ▼                                 │
│  Normalization                           │
│        │                                 │
│        ▼                                 │
│  Deterministic Matching                  │
│        │                                 │
│        ├──────────────┐                  │
│        ▼              ▼                  │
│  Harmonization    Human Review           │
│        │              │                  │
│        └──────┬───────┘                  │
│               ▼                          │
│       National Materials                 │
│               │                          │
│               ▼                          │
│           Audit Trail                    │
└───────────────────┬───────────────────────┘
                    ▼
               PostgreSQL
```

The MVP deliberately avoids infrastructure it doesn't need: no Redis, no
Celery, no vector database, no background workers, no external LLM calls
in the core matching path.

---

## Tech Stack

| Layer      | Technology          |
| ---------- | -------------------- |
| Frontend   | React + TypeScript   |
| Build      | Vite                 |
| Styling    | Tailwind CSS         |
| Backend    | FastAPI              |
| ORM        | SQLAlchemy           |
| Database   | PostgreSQL           |
| Validation | Pydantic             |
| Testing    | Pytest               |

---

## API Surface

```http
# CPSE
POST   /api/v1/cpses
GET    /api/v1/cpses
GET    /api/v1/cpses/{cpse_id}/materials

# Materials
POST   /api/v1/materials/import
GET    /api/v1/materials/{material_id}
POST   /api/v1/materials/{material_id}/normalize
POST   /api/v1/materials/{material_id}/match
POST   /api/v1/materials/{material_id}/harmonize
GET    /api/v1/materials/{material_id}/mapping-history

# Review
GET    /api/v1/reviews/queue
POST   /api/v1/reviews/{recommendation_id}/action

# National Materials
GET    /api/v1/national-materials
GET    /api/v1/national-materials/{national_material_id}

# Audit
GET    /api/v1/audit

# Dashboard
GET    /api/v1/dashboard
```

See `docs/FRONTEND_API_CONTRACT.md` for request/response schemas.

---

## Demo Dataset

Synthetic fixtures live in `backend/tests/demo_data/` (`cpse_a.csv`,
`cpse_b.csv`, `cpse_c.csv`). They're built to exercise: equivalent
descriptions, formatting and abbreviation differences, missing attributes,
and deliberate hard conflicts (pressure class, size, valve type, connection
type, trim).

> The included material data is synthetic and used for demonstration and
> testing — it is not real CPSE data.

---

## Getting Started

### Prerequisites

Python 3.x · Node.js · npm · PostgreSQL

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .

# configure DATABASE_URL, REVIEWER_TOKEN, etc. in .env
uvicorn app.main:app --reload --port 8000
```

Runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`.

### Testing

```bash
# backend
cd backend && pytest -v

# frontend
cd frontend && npm run lint && npm run build
```

---

## Current Status

This section reflects what's actually implemented, not the target design —
kept current as the build progresses.

| Area | Status |
| --- | --- |
| Project foundation (FastAPI, PostgreSQL, SQLAlchemy) | ✅ Done |
| CPSE management | ✅ Done |
| Ingestion (CSV/XLSX, source preservation) | ✅ Done |
| Normalization + attribute extraction (VALVE) | ✅ Done |
| Deterministic matching (hard conflicts, 3-way classification) | ✅ Done |
| Harmonization + National Material creation | ✅ Done |
| Human review (accept/reject/mark different/override) | ✅ Done |
| Audit log | ✅ Done |
| Read APIs — material detail, national material list/detail, mapping history, audit | 🚧 In progress |
| Dashboard / analytics endpoint | 🚧 In progress |
| AI/ML enhancement layer (embeddings as an additional signal) | ⏳ Planned, not started |
| Frontend | 🚧 In progress (Dhruv) |

Update the checkboxes as each phase lands — an accurate status table is
worth more here than a "ready for demo" banner that outruns the code.

---

## Security & Governance

- **Reviewer-protected actions** — review endpoints require a reviewer
  token (`X-Reviewer-Token`), validated server-side.
- **Source provenance** — original uploaded row data is preserved
  separately from anything derived from it.
- **Backend authority** — classification, national code generation, and
  governance decisions originate from the backend only. The frontend never
  supplies a confidence score, a threshold, or a national code.
- **Audit preservation** — audit history is retained independently of the
  records it describes.

---

## MVP Scope

**Included:** CPSE management, material ingestion with source preservation,
deterministic normalization and matching, safe automatic harmonization,
human review, National Material registry, mapping history, audit trail.

**Intentionally out of scope for the MVP:** procurement/financial
analytics, vector search infrastructure, external LLM APIs, live SAP/ERP
integration, background job infrastructure (Redis/Celery/Kafka), production
SSO.

The objective isn't the largest possible platform — it's a safe,
explainable, demonstrable core workflow. See `docs/ARCHITECTURE.md` for the
full production design and `docs/MVP_SCOPE.md` for the exact MVP boundary.

---

## Project Structure

```text
onemate/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── models.py
│   ├── alembic/
│   ├── docs/
│   └── tests/
│       └── demo_data/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   └── types/
│   └── package.json
└── docs/
    ├── ARCHITECTURE.md
    ├── FRONTEND_API_CONTRACT.md
    ├── FRONTEND_DESIGN.md
    └── MVP_SCOPE.md
```

---

## Smart India Hackathon

**Problem Statement:** SIH26099
**Title:** AI-Driven Standardization and Harmonization of Material Codes
Across CPSEs
**Theme:** Smart Automation · **Category:** Software
**Organization:** Ministry of Petroleum & Natural Gas — Chennai Petroleum
Corporation Limited (CPCL)

## Team

| Member   | Role                                 |
| -------- | ------------------------------------- |
| Rohinish | Backend, Architecture & Integration   |
| Dhruv    | Frontend / Product                    |
| Shiven   | AI / Matching / Research              |
