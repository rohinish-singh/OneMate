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
```

These descriptions may refer to the same engineering material.

A harmonization system cannot rely on text similarity alone — a single changed technical attribute can represent a genuinely different engineering item:

```text
CLASS150  ≠  CLASS300
DN50      ≠  DN100
BALL      ≠  GATE
RF        ≠  SOCKET_WELD
SS304     ≠  SS316
```

The real challenge:

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
 ┌─────────────────┬───────────────────────┬─────────────────┐
 │      SAME       │ POTENTIALLY_EQUIVALENT│   DIFFERENT     │
 │  eligible for   │     human review      │ hard conflict   │
 │ harmonization   │                       │                 │
 └─────────────────┴───────────────────────┴─────────────────┘
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

- **Engineering-first** — identity comes from structured technical attributes, not text similarity alone.
- **Safety-first** — a hard technical conflict overrides a high similarity score.
- **Human-in-the-loop** — uncertain matches are surfaced for review instead of being silently mapped.
- **Traceable** — original uploaded data is preserved separately from derived normalized values.
- **Auditable** — governance actions retain actor, reason, and state history.
- **Practical MVP architecture** — the core workflow uses a conventional relational architecture without requiring a vector database, queue system, or external LLM API.

---

## How It Works

### Supported Material Categories

- VALVE
- PUMP
- GASKET
- FLANGE
- BEARING
- FASTENER

### Important Engineering Principles

- Deterministic engineering rules are authoritative.
- Hard technical conflicts override semantic similarity.
- `UNKNOWN` / `NULL` is not a wildcard.
- Uncertain cases require human review.
- Source provenance is preserved.
- Matching is cross-CPSE.
- Self-matching is prohibited.
- Same-CPSE matching is prohibited.

### AI Layer

The v2 implementation adds an AI assistance layer to the matching workflow:

- Material descriptions are encoded as semantic vectors using `all-MiniLM-L6-v2` (sentence-transformers).
- Cosine similarity between embeddings drives candidate scoring — far more robust than character-level string matching.
- Deterministic engineering validation remains authoritative.
- Missing engineering information is not invented by the AI layer.
- Hard conflicts remain `DIFFERENT` even when descriptions are semantically similar.
- Evidence, confidence, and explanations are retained for reviewability.
- The core MVP workflow does not depend on an external LLM API.

### Matching

- Candidate selection happens across CPSEs.
- Self-matching is prohibited.
- Same-CPSE matching is prohibited.
- Technical attributes drive the final comparison.
- Classifications: `SAME`, `POTENTIALLY_EQUIVALENT`, `DIFFERENT`
- Recommendations contain evidence, confidence, and an explanation.

Example of the evidence returned per match:

```text
Semantic similarity: 94%

Category:        MATCH
Type:            MATCH
Size:            MATCH
Material:        MATCH
Pressure:        MATCH
Connection:      MATCH

Hard conflicts:  NONE

Recommendation:  SAME
```

### Normalization

Normalization is deterministic and category-aware.

For supported material categories, descriptions are converted into structured engineering attributes:

- Valve type
- Size
- Body material
- Pressure class / rating
- Connection type
- Trim material
- Seat material where applicable
- Normalized UOM

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
SS316 TRIM           → trim = SS316
EPDM / NBR / PTFE    → seat_material (not trim)
```

This prevents a soft seat material from being incorrectly interpreted as metallic trim.

### Review Governance

- Actions: `ACCEPT`, `REJECT`, `MARK_DIFFERENT`, `UNMAP`, `OVERRIDE`
- `ACCEPT` is idempotent for the same active recommendation.
- Conflicting remaps are explicitly governed.
- Review actions are protected by a reviewer token and generate audit records.

### National Materials

A National Material represents a validated engineering family.

The harmonization flow:

1. Identifies authoritative `SAME` relationships.
2. Verifies compatible engineering identity.
3. Reuses an existing National Material where appropriate.
4. Creates a National Material when a valid cross-CPSE family exists.
5. Maps participating source materials to that National Material.
6. Preserves source-to-national traceability.

`POTENTIALLY_EQUIVALENT` recommendations are not automatically mapped. `DIFFERENT` materials are never placed in the same National Material family.

### Example Engineering Decision

```text
GATE VALVE DN50 CS CLASS150 RF
vs
GATE VALVE DN50 CS CLASS300 RF
```

Engineering rule for pressure class takes precedence over textual similarity:

```text
Result: DIFFERENT
Reason: pressure class conflict
```

The same principle applies to size, material grade, valve type, connection type, and other category-specific engineering attributes.

---

## End-to-End Workflow

**1. Register a CPSE** — create the enterprise source namespace for a catalog.

**2. Import Materials** — upload a CPSE material catalog as CSV or XLSX. OneMate preserves source material code, description, UOM, specifications, and raw source payload separately from derived data.

**3. Normalize** — descriptions are converted into structured, category-aware engineering attributes. Missing information stays missing.

**4. Match** — materials are compared against cross-CPSE candidates. The system combines AI-assisted semantic candidate retrieval with deterministic engineering validation. Each recommendation is classified as `SAME`, `POTENTIALLY_EQUIVALENT`, or `DIFFERENT`.

**5. Harmonize** — validated `SAME` relationships can converge on an existing or newly created National Material family.

**6. Human Review** — uncertain recommendations enter the review queue. Reviewers can accept, reject, mark different, or override according to the governance workflow.

**7. Audit** — material and governance operations are recorded for traceability.

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
│  AI-Assisted Candidate Retrieval            │
│  (sentence-transformers, cosine similarity) │
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

- Backend is authoritative for classification and governance.
- Frontend does not supply confidence scores, thresholds, or National Material codes.
- Source records are preserved independently from derived normalized attributes.
- National Material mappings remain traceable to source materials.
- No Redis, Celery, Kafka, vector database, or external LLM API required for the core workflow.

---

## Tech Stack

| Layer      | Technology                          |
| ---------- | ----------------------------------- |
| Frontend   | React + TypeScript                  |
| Build      | Vite                                |
| Styling    | Tailwind CSS                        |
| Backend    | FastAPI                             |
| Language   | Python                              |
| ORM        | SQLAlchemy                          |
| Database   | PostgreSQL                          |
| Validation | Pydantic                            |
| Migrations | Alembic                             |
| AI / NLP   | sentence-transformers, scikit-learn |
| Testing    | Pytest                              |

---

## API Surface

```http
# Health
GET    /api/v1/health

# CPSE
POST   /api/v1/cpses
GET    /api/v1/cpses
GET    /api/v1/cpses/{cpse_id}/materials
DELETE /api/v1/cpses/{cpse_id}

# Materials
POST   /api/v1/materials/import
GET    /api/v1/materials/{material_id}
POST   /api/v1/materials/{material_id}/normalize
POST   /api/v1/materials/{material_id}/match
POST   /api/v1/materials/{material_id}/harmonize
POST   /api/v1/materials/{material_id}/unmap
GET    /api/v1/materials/{material_id}/mapping-history
GET    /api/v1/materials/{material_id}/ai-explain?candidate_id={id}
DELETE /api/v1/materials/{material_id}

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

Sample upload files are provided in `demo_data/`:

```text
demo_data/
├── CPSE_A.xlsx
├── CPSE_B.xlsx
└── CPSE_C.xlsx
```

These files are synthetic demonstration data, separate from application database state. They are built to exercise: equivalent descriptions, formatting and abbreviation differences, missing attributes, and deliberate hard conflicts (pressure class, size, valve type, connection type, trim).

The repository does **not** include `ground_truth.xlsx`.

> The included material data is synthetic and used for demonstration and testing — it is not real CPSE data.

---

## Getting Started

### Prerequisites

- Python 3.x
- Node.js
- npm
- PostgreSQL

### Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate

pip install -e .

# Configure DATABASE_URL, REVIEWER_TOKEN, and related settings in .env

uvicorn app.main:app --reload --port 8000
```

Runs at `http://localhost:8000`.

> On first startup the AI embedding model (`all-MiniLM-L6-v2`) downloads once and caches locally. Subsequent starts use the cache.

### Frontend

```bash
cd frontend

npm install
npm run dev
```

Runs at `http://localhost:5173`.

### Database

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

---

## Security & Governance

- **Reviewer-protected actions** — review endpoints require a reviewer token validated server-side.
- **Source provenance** — original uploaded row data is preserved separately from derived data.
- **Backend authority** — classification, National Material generation, and governance decisions originate from the backend only.
- **Human-in-the-loop** — uncertain cases are surfaced for review rather than silently mapped.
- **Audit preservation** — governance history is retained independently of the source records it describes.

---

## MVP Scope

**Included:** CPSE management, CSV/XLSX material ingestion, source data preservation, category-aware deterministic normalization, AI-assisted semantic candidate retrieval, deterministic engineering validation, safe automatic harmonization, human review, National Material registry, mapping history, audit trail, dashboard.

**Intentionally out of scope for the MVP:** live SAP/ERP integration, procurement and financial analytics, Redis/Celery/Kafka infrastructure, ANN/FAISS vector search, external LLM API dependency in the core workflow, production SSO, background job infrastructure.

The objective is a safe, explainable, demonstrable harmonization workflow — not the largest possible platform. See `docs/ARCHITECTURE.md` for the full production design and `docs/MVP_SCOPE.md` for the exact MVP boundary.

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
│   │   │       └── embedding.py
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
    ├── ARCHITECTURE.md
    ├── FRONTEND_API_CONTRACT.md
    ├── FRONTEND_DESIGN.md
    └── MVP_SCOPE.md
```

---

## Smart India Hackathon

**Problem Statement:** SIH26099  
**Title:** AI-Driven Standardization and Harmonization of Material Codes Across CPSEs  
**Theme:** Smart Automation · **Category:** Software  
**Organization:** Ministry of Petroleum & Natural Gas — Chennai Petroleum Corporation Limited (CPCL)


## License

MIT License.
