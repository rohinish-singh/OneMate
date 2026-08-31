
````markdown
# OneMate

### AI-Assisted CPSE Material Harmonization Platform

OneMate is an AI-assisted material harmonization platform designed to help
Central Public Sector Enterprises (CPSEs) standardize and consolidate
engineering material data into unified National Materials.

It takes inconsistent material descriptions from different CPSEs, extracts
technical attributes, identifies potential equivalents, safely automates
high-confidence harmonization, and sends uncertain cases to human reviewers.

---

## Problem

Different CPSEs often maintain their own material descriptions, codes,
units, and naming conventions for technically identical or similar
materials.

For example:

```text
CPSE A:
BALL VALVE 2 IN CS CLASS300 RF SS304 TRIM

CPSE B:
VALVE, BALL, 2 INCH, CARBON STEEL, CLASS 300, RF, SS304
````

These may represent the same engineering material despite differences in
formatting and description.

Without harmonization, organizations can face:

* duplicate material records
* inconsistent descriptions
* fragmented procurement data
* difficulty identifying common materials
* unnecessary manual review
* unreliable material mapping

OneMate addresses this through a controlled matching and governance
pipeline.

---

## Solution

OneMate follows a simple pipeline:

```text
CPSE Material Data
        ↓
Validation & Ingestion
        ↓
Normalization
        ↓
Candidate Generation
        ↓
Material Matching
        ↓
SAME / POTENTIALLY_EQUIVALENT / DIFFERENT
        ↓
Safe Automatic Harmonization
        ↓
Human Review for Uncertain Cases
        ↓
National Material Mapping
        ↓
Audit Trail
```

The system is designed around an important principle:

> **Be aggressive in finding plausible candidates, but conservative in
> declaring SAME.**

---

## Key Features

### Material Ingestion

Import CPSE material data through CSV/XLSX files.

The ingestion layer validates required fields and preserves the original
source information.

### Deterministic Normalization

Converts inconsistent material descriptions into standardized attributes
such as:

* Valve Type
* Size
* Body Material
* Pressure Class
* Connection Type
* Trim
* UOM

Example:

```text
2 IN → DN50
CS → CARBON_STEEL
EA / NOS / PCS → EACH
150# → CLASS150
```

Original source values remain preserved.

### Intelligent Material Matching

Materials are classified into:

```text
SAME
POTENTIALLY_EQUIVALENT
DIFFERENT
```

The current backend contains a deterministic matching baseline. The AI/ML
component can improve upon this baseline while preserving the system's
technical safety rules.

### Hard Technical Conflict Protection

Known technical conflicts override textual similarity.

Examples:

```text
CLASS150 vs CLASS300
        → DIFFERENT

DN50 vs DN100
        → DIFFERENT

BALL vs GATE
        → DIFFERENT

RF vs SOCKET_WELD
        → DIFFERENT
```

### Missing Data Safety

Missing attributes are treated as unknown.

They are never treated as wildcards and are never automatically inferred
just to increase similarity.

For example:

```text
Known trim: SS304
Missing trim: NULL
        ↓
POTENTIALLY_EQUIVALENT
        ↓
Human Review
```

### Automatic Harmonization

Only complete, high-confidence `SAME` matches can be automatically mapped
to a National Material.

Incomplete identities are deliberately prevented from automatic
harmonization.

### Human Review

Uncertain cases can be reviewed using:

* ACCEPT
* REJECT
* MARK_DIFFERENT
* OVERRIDE

Human decisions are recorded with reasons where required.

### Auditability

Important system and reviewer actions are recorded through a unified
audit trail.

This preserves:

* who performed an action
* what action occurred
* affected entity
* previous state
* resulting state
* timestamp
* review reasoning

---

## Architecture

OneMate uses a modular monolithic architecture for the MVP.

```text
React Frontend
       ↓
FastAPI Backend
       ↓
┌─────────────────────────────┐
│ Ingestion                   │
│ Normalization               │
│ Matching                    │
│ Harmonization               │
│ Human Review                │
└─────────────────────────────┘
       ↓
PostgreSQL
```

The MVP intentionally avoids unnecessary distributed infrastructure.

No:

* Kafka
* Redis
* Celery
* microservices
* vector database
* ML microservice
* complex workflow engine

---

## Technology Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Pydantic
* pytest

### AI/ML

The MVP supports a replaceable matching intelligence layer.

The current backend provides a deterministic baseline, while the AI/ML
team can evaluate and improve matching using suitable models and features.

Possible approaches include:

* Logistic Regression
* Random Forest
* XGBoost / LightGBM
* fuzzy/text similarity features

The simplest approach that provides measurable improvement is preferred.

---

## AI/ML Boundary

The AI/ML component is recommendation-only.

Conceptually:

```python
classify(material_a, material_b) -> MatchResult
```

It returns:

```text
classification
confidence
evidence
explanation
```

The AI/ML component does **not** directly write to PostgreSQL.

The backend remains responsible for:

* database writes
* transactions
* National Materials
* mappings
* AuditLog
* human review
* authorization

---

## Security

The MVP includes a protected reviewer boundary for human governance
operations.

Protected review endpoints require the configured reviewer
authentication header:

```text
X-Reviewer-Token
```

The actual token is configured through the backend environment and is not
stored in the repository.

Additional safeguards include:

* environment-based configuration
* `.env` excluded from Git
* `.env.example` containing placeholders only
* no direct AI/ML database writes
* validation of uploaded material data
* source data preservation
* protection against unsafe automatic harmonization
* API errors that do not expose internal stack traces

---

## Project Structure

```text
onemate/
│
├── app/
│   ├── api/
│   │   └── v1/
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── normalization.py
│   │   ├── matching.py
│   │   ├── harmonization.py
│   │   └── review.py
│   ├── schemas/
│   ├── models.py
│   └── ...
│
├── tests/
│   ├── demo_data/
│   ├── test_normalization.py
│   ├── test_matching.py
│   ├── test_harmonization.py
│   ├── test_review.py
│   └── test_e2e.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── MVP_SCOPE.md
│   
│ 
│
├── .env.example
├── .gitignore
└── README.md
```

---

## MVP Status

The backend MVP has been implemented and verified.

### Current verification

```text
P0 Foundation                  ✓
P1A Ingestion                 ✓
P1B Normalization             ✓
P2 Matching                   ✓
P3 Harmonization              ✓
P4 Human Review               ✓
API Contract                  ✓
End-to-End Verification       ✓
```

### Tests

```text
68 / 68 passing
0 failed
0 skipped
```

The test suite covers the complete backend flow from ingestion through
matching, harmonization, human review, and audit behavior.

---

## Demo Flow

A typical OneMate demonstration follows:

```text
1. Upload CPSE material files
             ↓
2. Validate and ingest materials
             ↓
3. Normalize technical attributes
             ↓
4. Generate cross-CPSE candidates
             ↓
5. Match materials
             ↓
6. Automatically harmonize safe SAME matches
             ↓
7. Send uncertain cases to Review Queue
             ↓
8. Human accepts/rejects/overrides
             ↓
9. Create final National Material mapping
             ↓
10. Display audit history
```

---

## MVP Scope

The current MVP intentionally focuses on the core harmonization workflow.

### Included

* CPSE material ingestion
* deterministic normalization
* technical attribute extraction
* candidate matching
* three-way classification
* safe automatic harmonization
* National Material creation/reuse
* material mapping
* human review
* reviewer actions
* audit logging
* API contract for frontend integration

### Deferred

Production-scale capabilities such as:

* SAP/ERP integration
* enterprise SSO
* advanced material lifecycle governance
* large-scale distributed processing
* advanced MLOps
* automated online model training
* large-scale vector retrieval
* production infrastructure orchestration

These are outside the current MVP scope.

---

## Documentation

Project architecture:

`docs/ARCHITECTURE.md`

MVP boundaries and requirements:

`docs/MVP_SCOPE.md`

These documents should be treated as the project's authoritative
technical references.

---

## Running Locally

### 1. Clone

```bash
git clone <repository-url>
cd onemate
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the example configuration:

```bash
cp .env.example .env
```

Update the local database configuration as required.

### 5. Run the backend

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

---

## Testing

Run the complete test suite:

```bash
pytest -v
```

Expected MVP baseline:

```text
68 passed
```

---

## Project Principle

OneMate is designed around **safe automation rather than blind
automation**.

The system should automate what can be proven safely, surface uncertainty
when information is incomplete, and keep humans in control of decisions
that require judgment.

```text
AI recommends
      ↓
Backend validates
      ↓
Safe matches automate
      ↓
Uncertain cases go to humans
      ↓
Every important decision is auditable
```

---

## SIH26099

OneMate is being developed as an MVP solution for **SIH26099 — Material
Code Harmonization for CPSEs**.

The implementation prioritizes:

* correctness
* explainability
* data safety
* controlled automation
* human governance
* demonstrable MVP scope
