from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class MemberResponse(BaseModel):
    user_id: int
    username: str
    joined_at: datetime
    is_owner: bool


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    accepted_at: datetime | None

    @computed_field
    @property
    def status(self) -> Literal["revoked", "used", "expired", "pending"]:
        if self.revoked_at:
            return "revoked"
        if self.accepted_at:
            return "used"
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return "expired" if expires <= datetime.now(timezone.utc) else "pending"


class InvitationCreated(InvitationResponse):
    # Returned once to the owner; never stored as plaintext or listed again.
    token: str


class AcceptInvitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")
