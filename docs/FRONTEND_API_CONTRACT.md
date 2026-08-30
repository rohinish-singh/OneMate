# SIH26099 Frontend API Contract

This document provides the API contract for the frontend team to integrate with the SIH26099 Material Harmonization backend.

## Base URL
All endpoints are relative to: `/api/v1`

*Note for local development: The default local backend typically runs on `http://localhost:8000`. Ensure your frontend environment variables point to the correct base URL.*

## Authentication
MVP endpoints requiring human governance (e.g., Review Queue and Review Actions) are protected by a static MVP token.
**Header Required:** `X-Reviewer-Token`
**Value:** `<configured reviewer token>` (Configured via backend environment)

*Do not implement complex JWT/SSO for the MVP. Pass this token explicitly in your API client headers when calling protected endpoints.*

## CORS
CORS is configured via the backend's environment variables (`CORS_ALLOWED_ORIGINS`). By default, it supports standard local development ports (e.g., `http://localhost:3000`). If your frontend runs on a different port, update the `.env` file on the backend. Do not bypass CORS using insecure extensions.

## Error Format
The API uses standardized HTTP status codes:
- **400 Bad Request**: Validation errors or business rule violations (e.g., trying to map an incomplete material, missing a required reason).
- **401 Unauthorized**: Missing or invalid `X-Reviewer-Token`.
- **404 Not Found**: The requested resource (Material or Recommendation) does not exist.
- **413 Content Too Large**: Uploaded file exceeds the 5MB limit.
- **500 Internal Server Error**: Unexpected backend failure.

Error responses always take the shape:
```json
{
  "detail": "Human readable error message explaining the rule violation."
}
```

---

## Endpoint Inventory

### 1. Upload Materials
**POST** `/materials/import`
**Auth Required**: No
**Content-Type**: `multipart/form-data`

**Request:**
- `cpse_id` (string/UUID, form data)
- `file` (binary, form data - `.csv` or `.xlsx` under 5MB)

**Response (200 OK):**
```json
{
  "total_rows": 100,
  "imported_rows": 98,
  "rejected_rows": 2,
  "duplicate_rows": 1,
  "errors": [
    {
      "row": 15,
      "error": "Missing mandatory fields (code, desc, or uom)"
    }
  ]
}
```

### 2. Normalize Material
**POST** `/materials/{material_id}/normalize`
**Auth Required**: No

**Request:** Empty body

**Response (200 OK):**
```json
{
  "status": "success",
  "material_id": "123e4567-e89b-12d3-a456-426614174000",
  "normalized": true
}
```

### 3. Generate Match Recommendations
**POST** `/materials/{material_id}/match`
**Auth Required**: No

**Request:** Empty body

**Response (200 OK):**
```json
{
  "status": "success",
  "material_id": "123e4567-e89b-12d3-a456-426614174000",
  "candidate_count": 5,
  "recommendations_created": 5,
  "recommendations": [
    {
      "candidate_id": "987e6543-e21b-34d5-c678-426614174999",
      "classification": "SAME",
      "confidence": 0.92,
      "explanation": "Same valve type, size, body material, pressure class, connection type, and trim."
    }
  ]
}
```

### 4. Auto-Harmonize Safe Matches
**POST** `/materials/{material_id}/harmonize`
**Auth Required**: No

**Request:** Empty body

**Response (200 OK):**
```json
{
  "status": "success",
  "national_material_id": "555e4567-e89b-12d3-a456-426614174111",
  "national_material_action": "CREATED",
  "mapping_id": "777e4567-e89b-12d3-a456-426614174222",
  "national_code": "NM-12345678"
}
```
*Note: If the material lacks safe recommendations or is already mapped, this returns an appropriate message indicating skipped processing.*

### 5. Fetch Review Queue
**GET** `/reviews/queue`
**Auth Required**: Yes (`X-Reviewer-Token`)

**Request:** None

**Response (200 OK):**
```json
{
  "queue": [
    {
      "recommendation_id": "444e4567-e89b-12d3-a456-426614174000",
      "source_material_id": "123e4567-e89b-12d3-a456-426614174000",
      "candidate_material_id": "987e6543-e21b-34d5-c678-426614174999",
      "classification": "POTENTIALLY_EQUIVALENT",
      "confidence": 0.86,
      "evidence": {
        "attributes": {
           "valve_type": {"match": true, "source": "BALL", "candidate": "BALL", "weight": 0.12},
           "trim": {"match": null, "source": "SS304", "candidate": null, "weight": 0.0}
        },
        "description_similarity": 0.86
      },
      "explanation": "Missing information for trim.",
      "source_valve_type": "BALL",
      "source_size": "DN50",
      "source_body_material": "CARBON_STEEL",
      "source_pressure_class": "CLASS300",
      "source_connection_type": "RF",
      "source_trim": "SS304"
    }
  ]
}
```

### 6. Perform Human Review Action
**POST** `/reviews/{recommendation_id}/action`
**Auth Required**: Yes (`X-Reviewer-Token`)
**Content-Type**: `application/json`

**Request Payload:**
```json
{
  "action": "ACCEPT",
  "reason": "Verified drawing specs matching the target.",
  "national_material_id": null
}
```

#### Supported Actions & Business Rules:
- **`ACCEPT`**: Approves a `SAME` or `POTENTIALLY_EQUIVALENT` match.
  - *Rule*: Will return `400 Bad Request` if the source material has an incomplete identity (e.g., missing trim). Incomplete identities CANNOT be accepted natively; they must use `OVERRIDE`.
- **`REJECT`**: Declines the match.
  - *Rule*: `reason` is **strictly required**.
- **`MARK_DIFFERENT`**: Declares the candidates technically distinct despite text similarities.
  - *Rule*: `reason` is **strictly required**.
- **`OVERRIDE`**: Forces a mapping to a specific National Material, bypassing automated logic.
  - *Rule*: `reason` and `national_material_id` are **strictly required**.

**Response (200 OK):**
```json
{
  "status": "success",
  "action": "ACCEPT",
  "mapping_created": true,
  "mapping_id": "777e4567-e89b-12d3-a456-426614174222"
}
```


---

## Workflows and Integration Rules

**The backend is the absolute authority on business rules, mappings, and state.**

### 1. Materials Workflow
- **Source vs Derived:** The frontend must clearly distinguish between source data (e.g. `raw_source_data`, `source_description`) and normalized data (`valve_type`, `size`, etc.).
- **Immutability:** Source data is immutable. The frontend must never offer inputs or forms attempting to mutate `source_` fields.

### 2. Matching Workflow
- **No Client-Side Scoring:** The frontend must NOT calculate text similarities or determine whether two values represent a "conflict". Simply display the JSON structure provided by the backend's `evidence` field.
- **Classification Display:** Utilize standard UI badges for the backend's strict enum outputs: `SAME`, `POTENTIALLY_EQUIVALENT`, and `DIFFERENT`.

### 3. Harmonization Workflow
- **Automated Mapping:** The backend decides which `SAME` materials are safe for auto-harmonization based on complete identities. The frontend merely triggers `/harmonize`. Do NOT attempt to build client-side logic to determine if a material "should" be auto-harmonized.

### 4. Review & Audit Workflow
- **Human Actions:** Present buttons exclusively for the available actions: `ACCEPT`, `REJECT`, `MARK_DIFFERENT`, and `OVERRIDE`.
- **Reasoning:** Enforce text boxes for `reason` where the backend requires it (e.g. `REJECT`). The backend will throw a `400 Bad Request` if a reason is missing.
- **Overrides:** The `OVERRIDE` action bypasses logic to map to a specific target; the UI must prompt the user for the `national_material_id` explicitly for this action.
