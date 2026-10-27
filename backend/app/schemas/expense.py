from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Money = Annotated[int, Field(strict=True, ge=0, le=1_000_000_000_000)]
PersonId = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]


class ShareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: PersonId
    amount_minor: Money


class ExpenseInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(min_length=1, max_length=100)
    expense_date: date
    category: Literal["lodging", "transport", "food", "tickets", "shopping", "other"] = "other"
    amount_minor: Money
    payer_id: PersonId
    split_mode: Literal["equal", "custom"] = "equal"
    participant_ids: list[PersonId] = Field(min_length=1, max_length=100)
    custom_shares: list[ShareInput] = Field(default_factory=list, max_length=100)
    activity_id: PersonId | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_split(self):
        if self.amount_minor <= 0 or len(set(self.participant_ids)) != len(self.participant_ids):
            raise ValueError("Positive amount and unique participants required")
        if self.split_mode == "custom":
            ids = [share.user_id for share in self.custom_shares]
            if len(set(ids)) != len(ids) or set(ids) != set(self.participant_ids):
                raise ValueError("Custom shares must match selected participants")
            if sum(share.amount_minor for share in self.custom_shares) != self.amount_minor:
                raise ValueError("Shares must add up to expense amount")
        elif self.custom_shares:
            raise ValueError("Equal split cannot include custom amounts")
        return self


class ShareResponse(ShareInput):
    model_config = ConfigDict(from_attributes=True)
    username: str


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    expense_date: date
    category: str
    currency: str
    amount_minor: int
    payer_id: int
    payer_name: str
    split_mode: str
    shares: list[ShareResponse]
    activity_id: int | None
    notes: str | None
    created_by: int
    created_at: datetime


class SettlementInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    sender_id: PersonId
    recipient_id: PersonId
    amount_minor: Money
    settled_on: date
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def valid_transfer(self):
        if self.sender_id == self.recipient_id or self.amount_minor <= 0:
            raise ValueError("Positive amount and different people required")
        return self


class SettlementResponse(SettlementInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sender_name: str
    recipient_name: str
    currency: str
    created_by: int
    created_at: datetime


class BalanceResponse(BaseModel):
    user_id: int
    username: str
    active: bool
    paid_minor: int = 0
    owed_minor: int = 0
    balance_minor: int = 0


class TransferSuggestion(BaseModel):
    sender_id: int
    recipient_id: int
    amount_minor: int


class LedgerResponse(BaseModel):
    currency: str
    minor_digits: int
    total_minor: int
    expenses: list[ExpenseResponse]
    settlements: list[SettlementResponse]
    balances: list[BalanceResponse]
    suggestions: list[TransferSuggestion]
