# AI/ML Handoff Guide

This document defines the MVP-only AI/ML boundary for the SIH26099 backend. The purpose is to prevent scope expansion beyond the existing deterministic matching baseline and to keep the team aligned with the validated MVP.

## Core rule

The existing matcher in `app/services/matching.py` is the working deterministic baseline.

The AI/ML workflow is:

1. Evaluate the existing deterministic matcher.
2. Create labelled evaluation data from real or curated material pairs.
3. Build a simple ML improvement only if it is justified by measurable gains.
4. Compare baseline vs ML approach.
5. Keep the ML version only if it improves high-precision SAME detection and safe review decisions.
6. Integrate the final approach into the existing matching layer.

The team must not assume that matching needs to be rebuilt from scratch. The baseline remains the primary implementation for the MVP.

## MVP AI/ML scope

### In scope

- Evaluate the existing matching logic.
- Improve material-pair similarity or scoring only when justified.
- Use normalized technical attributes such as valve type, size, body material, pressure class, connection type, trim, and UOM.
- Use text similarity and structured feature engineering.
- Train a simple supervised model if labelled data is available.
- Calibrate `SAME`, `POTENTIALLY_EQUIVALENT`, and `DIFFERENT` thresholds.
- Produce `confidence`, `evidence`, and `explanation`.
- Add tests for model integration and comparison.
- Compare baseline vs improved approach using clear metrics.

Possible MVP models:

- Logistic Regression
- Random Forest
- XGBoost / LightGBM

Use the simplest model that demonstrates measurable improvement.

### Explicitly out of scope for the MVP

Do not build:

- LLM-based normalization
- LLM agents
- fine-tuned LLMs
- cross-encoder infrastructure
- vector databases
- pgvector
- Milvus
- Redis
- Kafka
- Celery
- separate ML microservices
- MLOps pipelines
- online learning
- automatic model retraining
- production model-serving infrastructure
- new database tables
- new feedback pipelines

Normalization remains the existing deterministic backend implementation for the MVP.

Human review data may be used to create an offline labelled dataset, but automated retraining is out of scope.

## Non-negotiable safety rules

The ML model is never the final authority over technical conflicts.

Hard conflicts must override ML predictions.

Examples:

- `CLASS150` vs `CLASS300` -> `DIFFERENT` -> confidence `0.0`
- `DN50` vs `DN100` -> `DIFFERENT` -> confidence `0.0`
- `BALL` vs `GATE` -> `DIFFERENT` -> confidence `0.0`
- `RF` vs `SOCKET_WELD` -> `DIFFERENT` -> confidence `0.0`

`NULL` means `UNKNOWN`.

`NULL` is never a wildcard.

Never infer a missing identity attribute simply to increase similarity.

If required identity information is missing, the system must not turn the pair into an automatic `SAME` mapping.

## Required output contract

The matching component must continue to produce:

- `classification`
- `confidence`
- `evidence`
- `explanation`

Classification values remain exactly:

- `SAME`
- `POTENTIALLY_EQUIVALENT`
- `DIFFERENT`

Do not introduce additional classifications for the MVP.

## Backend boundary

AI/ML must NOT directly:

- `INSERT`
- `UPDATE`
- `DELETE`

PostgreSQL data.

AI/ML only returns a matching result. The backend remains responsible for:

- database writes
- transactions
- `NationalMaterial`
- mappings
- `AuditLog`
- human review
- authentication
- API behavior

A normal Python module/function is sufficient. Do not create a separate service.

## Baseline comparison requirement

Before replacing any existing logic, the team must report:

1. Existing matcher accuracy, precision, and recall where labelled data allows.
2. False `SAME` cases.
3. False `DIFFERENT` cases.
4. `POTENTIALLY_EQUIVALENT` cases.
5. Proposed ML approach.
6. ML metrics.
7. Baseline vs ML comparison.
8. Recommended thresholds.

The objective is not to maximize `SAME` matches. The objective is:

- high-precision `SAME`
- safe `DIFFERENT`
- useful review queue

## Deliverable required from the AI/ML team

The AI/ML team must return:

- baseline evaluation
- labelled dataset
- ML implementation
- baseline-vs-ML comparison
- calibrated thresholds
- evidence/explanation format
- tests
- integration instructions

Keep the implementation compatible with the existing `app/services/matching.py` architecture.

## Final rule

If an AI/ML feature is not required to demonstrate a better MVP matching result, do not build it.

No scope expansion without explicit approval.

