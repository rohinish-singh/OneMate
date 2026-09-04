

````
# OneMate

### AI-Driven Standardization & Harmonization of Material Codes Across CPSEs

**Smart India Hackathon 2026** · SIH26099 · Smart Automation · Software

OneMate converts fragmented CPSE material data into a governed national catalog while preserving engineering identity, source provenance, human decisions, and audit history.

[Problem](#the-problem) ·
[Solution](#solution) ·
[How It Works](#how-it-works) ·
[Architecture](#architecture) ·
[Tech Stack](#tech-stack) ·
[API Surface](#api-surface) ·
[Demo Dataset](#demo-dataset) ·
[Current Status](#current-status) ·
[Getting Started](#getting-started)

---

## The Problem

Across CPSEs, the same engineering material can be represented in very different ways:

```text
BALL VALVE 2" CL300 RF CS SS304
BALL VLV DN50 CLASS 300 RF CARBON STEEL
2 IN BALL VALVE 300 LB RAISED FACE CS
````

These descriptions may refer to the same engineering material.

A harmonization system therefore cannot rely on text similarity alone: a single changed technical attribute can represent a genuinely different engineering item.

```text
CLASS150  ≠  CLASS300
DN50      ≠  DN100
BALL      ≠  GATE
RF        ≠  SOCKET_WELD
SS304     ≠  SS316
```

The real challenge is:

> How do we standardize material descriptions across enterprises without losing engineering meaning or creating unsafe mappings?

---

## Solution

OneMate provides a governed workflow for moving source material catalogs from multiple CPSEs into a common National Material registry.

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
 AI-ASSISTED CANDIDATE RETRIEVAL
      │
      ▼
 ENGINEERING VALIDATION
      │
      ▼
 ┌─────────────────┬──────────────────────-┬─────────────────┐
 │      SAME       │ POTENTIALLY_EQUIVALENT│   DIFFERENT     │
 │  eligible for   │     human review      │ hard conflict   │
 │ harmonization   │                       │                 │
 └─────────────────┴──────────────────────-┴─────────────────┘
      │                       │
      ▼                       ▼
 HARMONIZE                   REVIEW
      │                       │
      └────────────┬──────────┘
                   ▼
          NATIONAL MATERIAL
                   │
                   ▼
              AUDIT TRAIL
                   │
                   ▼
               DASHBOARD
```

### Core Design Principle

> **Similarity can suggest. Engineering rules decide. Humans govern uncertainty.**

### Why it's built this way

* **Engineering-first** — identity comes from structured technical attributes, not text similarity alone.
* **Safety-first** — a hard technical conflict overrides a high similarity score.
* **Human-in-the-loop** — uncertain matches are surfaced for review instead of being silently mapped.
* **Traceable** — original uploaded data is preserved separately from derived normalized values.
* **Auditable** — governance actions retain actor, reason, and state history.
* **Practical MVP architecture** — the core workflow uses a conventional relational architecture without requiring a vector database, queue system, or external LLM API.

---

## How It Works

### Supported Material Categories

The current prototype includes category-aware handling for:

* VALVE
* PIPE
* PUMP
* GASKET
* FLANGE
* BEARING
* FASTENER
* FITTING
* STRAINER
* BELT
* TRANSMITTER

### Important Engineering Principles

* Deterministic engineering rules are authoritative.
* Hard technical conflicts override semantic similarity.
* `UNKNOWN` / `NULL` is not a wildcard.
* Uncertain cases require human review.
* Source provenance is preserved.
* Matching is cross-CPSE.
* Self-matching is prohibited.
* Same-CPSE matching is prohibited.

### AI Layer

The v2 implementation adds an AI assistance layer to the matching workflow:

* Semantic embeddings support candidate retrieval.
* AI-assisted retrieval and reranking help identify likely equivalent materials.
* Deterministic engineering validation remains authoritative.
* Missing engineering information is not invented by the AI layer.
* Hard conflicts remain `DIFFERENT` even when descriptions are semantically similar.
* Evidence, confidence, and explanations are retained for reviewability.
* The core MVP workflow does not depend on an external LLM API.

### Matching

* Candidate selection happens across CPSEs.
* Self-matching is prohibited.
* Same-CPSE matching is prohibited.
* Technical attributes drive the final comparison.
* Classifications are:

  * `SAME`
  * `POTENTIALLY_EQUIVALENT`
  * `DIFFERENT`
* Recommendations contain evidence, confidence, and an explanation.

### Normalization

Normalization remains deterministic and category-aware.

For supported material categories, descriptions are converted into structured engineering attributes.

Examples include:

* Valve type
* Size
* Body material
* Pressure class / rating
* Connection type
* Trim material
* Seat material where applicable
* Category-specific technical attributes
* Normalized UOM

Examples of terminology normalization demonstrated by the dataset:

```text
2 IN     ↔ DN50
CLASS150 ↔ 150#
SS316    ↔ AISI 316
```

Missing information remains missing rather than being treated as a wildcard.

### Valve Seat / Trim Handling

The valve normalization logic distinguishes metallic trim from soft seat material:

```text
SS316 TRIM
    → trim = SS316

EPDM / NBR / PTFE / VITON
in seat context
    → seat_material
```

For example:

```text
trim          = NULL
seat_material = EPDM
```

This prevents a soft seat material from being incorrectly interpreted as metallic trim.

### Review Governance

Review actions include:

* `ACCEPT`
* `REJECT`
* `MARK_DIFFERENT`
* `UNMAP`
* `OVERRIDE`

Review actions are protected by a reviewer token and generate audit records.

### National Materials

A National Material represents a validated engineering family.

The harmonization flow:

1. Identifies authoritative `SAME` relationships.
2. Verifies compatible engineering identity.
3. Reuses an existing National Material where appropriate.
4. Creates a National Material when a valid cross-CPSE family exists.
5. Maps participating source materials to that National Material.
6. Preserves source-to-national traceability.

`POTENTIALLY_EQUIVALENT` recommendations are not automatically mapped.

`DIFFERENT` materials are never placed in the same National Material family.

### Example Engineering Decision

The system can encounter descriptions that are highly similar while still representing different engineering items:

```text
GATE VALVE DN50 CS CLASS150 RF
vs
GATE VALVE DN50 CS CLASS300 RF
```

The engineering rule for pressure class takes precedence over textual similarity:

```text
DIFFERENT
Reason: pressure class conflict
```

The same principle applies to hard conflicts such as:

* size
* material grade
* valve type
* connection type
* pressure class
* other category-specific engineering attributes

---

## End-to-End Workflow

### 1. Register a CPSE

Create the enterprise source namespace for a catalog.

### 2. Import Materials

Upload a CPSE material catalog as CSV or XLSX.

OneMate preserves source material code, description, UOM, specifications, and raw source payload separately from derived data.

### 3. Normalize

Descriptions are converted into structured, category-aware engineering attributes.

Missing information stays missing.

### 4. Match

Materials are compared against cross-CPSE candidates.

The system combines AI-assisted semantic candidate retrieval with deterministic engineering validation.

Each recommendation is classified as:

```text
SAME
POTENTIALLY_EQUIVALENT
DIFFERENT
```

### 5. Harmonize

Validated `SAME` relationships can converge on an existing or newly created National Material family.

### 6. Human Review

Uncertain recommendations enter the review queue.

Reviewers can accept, reject, mark different, or override according to the application's governance workflow.

### 7. Audit

Material and governance operations are recorded for traceability.

---

## Architecture

```text
┌─────────────────────────────────────────────┐
│                 Frontend                    │
│          React + TypeScript + Vite          │
└──────────────────────┬──────────────────────┘
                       │ REST
                       ▼
┌─────────────────────────────────────────────┐
│               FastAPI Backend               │
│                                             │
│  CPSE Management                            │
│        │                                    │
│        ▼                                    │
│  Material Ingestion                         │
│        │                                    │
│        ▼                                    │
│  Deterministic Normalization                │
│        │                                    │
│        ▼                                    │
│  AI-Assisted Candidate Retrieval / Ranking  │
│        │                                    │
│        ▼                                    │
│  Deterministic Engineering Validation       │
│        │                                    │
│        ├───────────────┐                    │
│        ▼               ▼                    │
│  Harmonization     Human Review             │
│        │               │                    │
│        └───────┬───────┘                    │
│                ▼                            │
│        National Materials                   │
│                │                            │
│                ▼                            │
│            Audit Trail                      │
└──────────────────────┬──────────────────────┘
                       ▼
                  PostgreSQL
```

### Architecture Principles

* Backend remains authoritative for classification and governance.
* Frontend does not supply confidence scores, thresholds, or National Material codes.
* Source records are preserved independently from derived normalized attributes.
* National Material mappings remain traceable to source materials.
* The MVP does not require Redis, Celery, Kafka, a vector database, or an external LLM API for the core workflow.

---

## Tech Stack

| Layer      | Technology                                    |
| ---------- | --------------------------------------------- |
| Frontend   | React + TypeScript                            |
| Build      | Vite                                          |
| Styling    | Tailwind CSS                                  |
| Backend    | FastAPI                                       |
| Language   | Python                                        |
| ORM        | SQLAlchemy                                    |
| Database   | PostgreSQL                                    |
| Validation | Pydantic                                      |
| Migrations | Alembic                                       |
| AI / NLP   | Embeddings, semantic retrieval, and reranking |
| Testing    | Pytest                                        |

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

See the repository documentation for detailed request and response schemas.

---

## Demo Dataset

Sample upload files are provided in:

```text
demo_data/
├── CPSE_A.xlsx
├── CPSE_B.xlsx
└── CPSE_C.xlsx
```

These files are sample input data for demonstration and testing. They are separate from application database state.

The repository does **not** include `ground_truth.xlsx`.

---

## Getting Started

### Prerequisites

* Python 3.x
* Node.js
* npm
* PostgreSQL

### Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -e .

# Configure DATABASE_URL, REVIEWER_TOKEN, and related settings in .env

uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

### Frontend

```bash
cd frontend

npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

### Database

Run the committed Alembic migrations against a fresh database:

```bash
cd backend
alembic upgrade head
```

### Demo Flow

```text
Create CPSE
    ↓
Upload CPSE_A.xlsx / CPSE_B.xlsx / CPSE_C.xlsx
    ↓
Normalize
    ↓
Find Matches
    ↓
Review uncertain recommendations
    ↓
Harmonize validated SAME relationships
    ↓
Inspect National Materials / Audit Trail
```

---

## Testing

### Backend

Use an isolated test database rather than the demo/development database:

```bash
cd backend

DATABASE_URL=<TEST_DATABASE_URL> .venv/bin/pytest tests/ -q
```

### Frontend

```bash
cd frontend

npm run build
```

---

## Current Status

This section reflects the implemented v2 prototype rather than the target design.

| Area                                                                                 | Status  |
| ------------------------------------------------------------------------------------ | ------- |
| Project foundation (FastAPI, PostgreSQL, SQLAlchemy)                                 | ✅ Done |
| CPSE management & controlled deletion                                                | ✅ Done |
| Ingestion (CSV/XLSX, source preservation)                                            | ✅ Done |
| Category-aware normalization + attribute extraction                                  | ✅ Done |
| AI-assisted semantic candidate retrieval / reranking                                 | ✅ Done |
| Deterministic engineering matching and 3-way classification                          | ✅ Done |
| Valve trim / seat-material handling                                                  | ✅ Done |
| Harmonization + National Material creation                                           | ✅ Done |
| Human review and governance actions                                                  | ✅ Done |
| Audit log & immutable event trail                                                    | ✅ Done |
| Material detail / mapping history APIs                                               | ✅ Done |
| National Material list/detail APIs                                                   | ✅ Done |
| Dashboard / operational analytics overview                                           | ✅ Done |
| CPSE-scoped Review Queue                                                             | ✅ Done |
| Responsive Frontend (Dashboard, Explorer, Matcher, Review, National Registry, Audit) | ✅ Done |
| Demo Excel dataset                                                                   | ✅ Done |

### Latest Local Validation

The latest local validation performed before the v2 release included:

```text
Backend tests:     263 passed, 1 warning
Frontend build:    passed
git diff --check:  passed
```

The warning did not cause a test failure.

---

## Security & Governance

* **Reviewer-protected actions** — review endpoints require a reviewer token validated server-side.
* **Source provenance** — original uploaded row data is preserved separately from derived data.
* **Backend authority** — classification, National Material generation, and governance decisions originate from the backend.
* **Human-in-the-loop** — uncertain cases are surfaced for review rather than silently mapped.
* **Audit preservation** — governance history is retained independently of the source records it describes.

---

## MVP Scope

### Included

* CPSE management
* CSV/XLSX material ingestion
* Source data preservation
* Category-aware deterministic normalization
* AI-assisted candidate retrieval / reranking
* Deterministic engineering validation
* Safe automatic harmonization
* Human review
* National Material registry
* Mapping history
* Audit trail
* Dashboard and operational views

### Intentionally Out of Scope for the MVP

* Live SAP / ERP integration
* Procurement and financial analytics
* Redis / Celery / Kafka infrastructure
* Vector database infrastructure
* External LLM API dependency in the core workflow
* Production SSO
* Background job infrastructure

The objective is a safe, explainable, demonstrable harmonization workflow rather than the largest possible platform.

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
│   │   │   └── ai/
│   │   └── models.py
│   ├── alembic/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   └── types/
│   └── package.json
├── demo_data/
│   ├── CPSE_A.xlsx
│   ├── CPSE_B.xlsx
│   └── CPSE_C.xlsx
└── docs/
```

---

## Smart India Hackathon

**Problem Statement:** SIH26099

**Title:** AI-Driven Standardization and Harmonization of Material Codes Across CPSEs

**Theme:** Smart Automation
**Category:** Software
**Organization:** Ministry of Petroleum & Natural Gas — Chennai Petroleum Corporation Limited (CPCL)

---

## Team

| Member   | Role                                |
| -------- | ----------------------------------- |
| Rohinish | Backend, Architecture & Integration |
| Dhruv    | Frontend / Product                  |
| Shiven   | AI / Matching / Research            |

---

## License

MIT License.

````

### One thing before replacing your README

Your existing README contains a few claims that are now stale, especially:

```text
Normalization + attribute extraction (VALVE) | ✅ Done
Deterministic matching
backend/tests/demo_data/
````

Those are the sections I specifically corrected for v2.  

Save the block above as:

```text
~/onemate/README.md
```

Then:

```bash
cd ~/onemate
git diff --check
git add README.md
git commit -m "docs: update README for v2 AI implementation"
git push origin ai-material-intelligence
```

