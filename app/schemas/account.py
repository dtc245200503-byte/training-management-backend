from pydantic import BaseModel


class LockAccountRequest(BaseModel):
    reason: str