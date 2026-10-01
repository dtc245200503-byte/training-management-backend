from pydantic import BaseModel


class AssignRoleRequest(BaseModel):
    role_id: int


class RemoveRoleRequest(BaseModel):
    role_id: int