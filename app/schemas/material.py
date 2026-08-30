from pydantic import BaseModel
from typing import List, Optional

class ImportRowError(BaseModel):
    row: int
    error: str

class ImportSummary(BaseModel):
    total_rows: int
    imported_rows: int
    rejected_rows: int
    duplicate_rows: int
    errors: List[ImportRowError]

