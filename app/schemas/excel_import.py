from typing import List, Optional
from pydantic import BaseModel


class UserImportErrorDetail(BaseModel):
    row: int
    email: Optional[str] = None
    reason: str


class UserImportResult(BaseModel):
    total_rows: int
    imported_count: int
    skipped_count: int
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    errors: List[UserImportErrorDetail] = []
    imported_users: List[str] = []
    imported_emails: List[str] = []
