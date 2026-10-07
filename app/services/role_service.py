from typing import List
from sqlalchemy.orm import Session
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.role import PermissionResponse, RoleListResponse, RoleResponse


class RoleService:
    def __init__(self, db: Session):
        self.db = db
        self.role_repo = RoleRepository(db)
        self.perm_repo = PermissionRepository(db)

    def list_roles(self) -> RoleListResponse:
        roles = self.role_repo.get_all()
        return RoleListResponse(
            items=[RoleResponse.model_validate(r) for r in roles]
        )

    def list_permissions(self) -> List[PermissionResponse]:
        perms = self.perm_repo.get_all()
        return [PermissionResponse.model_validate(p) for p in perms]
