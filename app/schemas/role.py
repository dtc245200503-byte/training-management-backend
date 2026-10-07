from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: Optional[str] = None
    module: Optional[str] = None
    created_at: Optional[datetime] = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    permissions: List[PermissionResponse] = []


class RoleListResponse(BaseModel):
    items: List[RoleResponse]
