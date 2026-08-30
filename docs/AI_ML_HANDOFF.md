# AI/ML Handoff Guide

This document defines the architectural boundaries for future AI and Machine Learning components integrating into the SIH26099 CPSE Material Harmonization backend.


## AI/ML Implementation Rules
The existing backend already has deterministic matching logic. AI/ML improvements must adhere to the following constraints:

**AI/ML MUST:**
- Evaluate the existing deterministic matcher first and build an improved ML approach only if it provides measurable benefit.
- Preserve hard-conflict rules and NULL safety (missing identity-defining attributes prevent SAME classification).
- Return standard outputs: `classification`, `confidence`, `evidence`, and `explanation`.

**AI/ML MUST NOT:**
- Write directly to PostgreSQL or change the database schema.
- Change automated harmonization logic, human review logic, or authentication.
- Build a separate service (a normal Python module/function is sufficient for MVP).
- Introduce external infrastructure (e.g., Vector Databases, Redis, Kafka, Celery, MLOps, LLM agents, or online training).

## Current Backend (The Baseline)
Currently, `app/services/` relies on deterministic logic:
- **Normalization (`normalization.py`):** Uses Regex and string-matching to extract technical attributes.
- **Candidate Generation (`matching.py`):** Uses cross-CPSE nested loops.
- **Similarity/Matching (`matching.py`):** Uses standard library `difflib.SequenceMatcher` combined with structured attribute weightings to calculate a 0.0 - 1.0 confidence score.
- **Classification (`matching.py`):** Sorts recommendations into `SAME`, `POTENTIALLY_EQUIVALENT`, or `DIFFERENT` based on static thresholds (`0.88` and `0.45`).
- **Evidence Generation (`matching.py`):** Emits JSON attribute-by-attribute comparison dictionaries.

## Future AI/ML Extension Points

### 1. NLP / LLM Normalization
**Location to replace/extend:** `app.services.normalization.normalize_material()`
- **Goal:** Replace brittle Regex matching with LLM parsing to extract `valve_type`, `size`, `body_material`, `pressure_class`, `connection_type`, and `trim`.
- **Constraint:** The output MUST map directly back into the existing PostgreSQL `Material` model columns. `NULL` must still be passed if an attribute cannot be definitively identified. 

### 2. Candidate Generation
**Location to replace/extend:** `app.services.matching.generate_candidates()`
- **Goal:** Replace the current O(n²) loop with a more efficient candidate generation algorithm (e.g., in-memory embeddings or semantic search via a normal Python module/function). Do NOT introduce external vector databases (pgvector, Milvus), Redis, Kafka, or MLOps infrastructure for the MVP.
- **Constraint:** The function must still return a list of `MatchRecommendation` objects. Candidates must still be strictly filtered so that intra-CPSE matches (matching a material to another material in the same CPSE) are rejected.

### 3. ML Confidence Scoring & Classification
**Location to replace/extend:** `app.services.matching.classify_match()`
- **Goal:** Replace `difflib` with a specialized ML model (e.g., cross-encoder or fine-tuned LLM) to generate the `confidence` float.
- **Constraint:** **Hard-Conflict Vetoes must remain.** If a model predicts two materials are 0.99 identical, but one is clearly marked `DN50` and the other `DN100`, the system MUST strictly override the model to `DIFFERENT` with `0.0` confidence.

### 4. Human-In-The-Loop Training Data
**Location for extraction:** `AuditLog` and `MatchRecommendation`
- **Goal:** Fine-tune ML models using human reviewer feedback.
- **Integration:** Do not add a new feedback pipeline. Simply periodically dump the `AuditLog` where `entity_type="RECOMMENDATION"` and use the explicit `REJECT` or `MARK_DIFFERENT` statuses as negative samples, and `ACCEPT` as positive samples.

