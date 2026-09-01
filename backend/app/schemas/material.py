from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
import uuid

class ImportRowError(BaseModel):
    row: int
    error: str

class ImportSummary(BaseModel):
    total_rows: int
    imported_rows: int
    rejected_rows: int
    duplicate_rows: int
    errors: List[ImportRowError]

class MaterialListResponse(BaseModel):
    id: uuid.UUID
    cpse_id: uuid.UUID
    source_material_code: str
    source_description: str
    category: Optional[str] = None
    normalized_description: Optional[str] = None
    mapping_status: Optional[str] = None
    national_material_code: Optional[str] = None
    national_material_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)



class MaterialDetailResponse(BaseModel):
    id: uuid.UUID
    cpse_id: uuid.UUID
    source_material_code: str
    source_description: str
    source_uom: str
    source_specifications: Optional[str] = None
    raw_source_data: Optional[Any] = None

    category: Optional[str] = None

    valve_type: Optional[str] = None
    size: Optional[str] = None
    body_material: Optional[str] = None
    pressure_class: Optional[str] = None
    connection_type: Optional[str] = None
    trim: Optional[str] = None

    normalized_uom: Optional[str] = None
    normalized_description: Optional[str] = None
    normalized_attributes: Optional[Any] = None

    mapping_status: Optional[str] = None
    national_material_code: Optional[str] = None
    national_material_id: Optional[uuid.UUID] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialMappingHistory(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    national_material_id: uuid.UUID
    basis: str
    status: str
    recommendation_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialDeleteResponse(BaseModel):
    status: str = "success"
    deleted_id: str
    deleted_type: str = "MATERIAL"
