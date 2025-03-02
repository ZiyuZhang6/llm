from pydantic import BaseModel
from typing import Optional


class PaperBase(BaseModel):
    title: str  # original file name
    shared: bool = False
    pdf_url: str  # every paper must have a PDF URL (s3 or core api?)


class PaperCreate(PaperBase):
    """Schema for creating a new paper (requires filename and pdf_url)."""

    owner_id: str


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    shared: Optional[bool] = None


class PaperResponse(PaperBase):
    """Schema for returning paper details."""

    id: str
    owner_id: str

    class Config:
        orm_mode = True
