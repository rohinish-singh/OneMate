from fastapi import Header, HTTPException
from app.core.config import settings

def get_current_reviewer(x_reviewer_token: str = Header(None)) -> str:
    """
    MVP authentication for human review endpoints.
    Requires X-Reviewer-Token header.
    """
    if not x_reviewer_token or x_reviewer_token != settings.reviewer_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return "human_reviewer"

