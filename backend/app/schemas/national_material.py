from uuid import UUID
from pydantic import BaseModel, ConfigDict

class NationalMaterialListResponse(BaseModel):
    id: UUID
    national_code: str
    canonical_description: str
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)

class NationalMaterialDetailResponse(BaseModel):
    id: UUID
    national_code: str
    category: str
    canonical_description: str
    valve_type: str
    size: str
    body_material: str
    pressure_class: str
    connection_type: str
    trim: str
    normalized_uom: str
    identity_key: str
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)
