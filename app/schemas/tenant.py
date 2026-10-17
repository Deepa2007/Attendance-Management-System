from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
