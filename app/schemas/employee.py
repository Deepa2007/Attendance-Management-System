from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
