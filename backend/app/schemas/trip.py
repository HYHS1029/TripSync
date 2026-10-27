from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CURRENCIES = {"TWD": 2, "JPY": 0, "KRW": 0, "USD": 2, "EUR": 2, "GBP": 2,
              "HKD": 2, "CNY": 2, "THB": 2, "SGD": 2, "AUD": 2, "CAD": 2}


class TripSettings(BaseModel):
    @field_validator("timezone", check_fields=False)
    @classmethod
    def valid_timezone(cls, value):
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Use a valid IANA timezone") from None
        return value

    @field_validator("currency", check_fields=False)
    @classmethod
    def valid_currency(cls, value):
        if value is not None and value not in CURRENCIES:
            raise ValueError("Unsupported currency")
        return value


class TripCreate(TripSettings):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    description: str | None = Field(default=None, max_length=2000)
    timezone: str = Field(default="Asia/Taipei", min_length=1, max_length=64)
    currency: str = "TWD"

    @field_validator("description")
    @classmethod
    def empty_description(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_dates(self) -> "TripCreate":
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class TripUpdate(TripSettings):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    destination: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    currency: str | None = None

    @field_validator("description")
    @classmethod
    def empty_description(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_changes(self) -> "TripUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        for field in ("name", "destination", "start_date", "end_date", "timezone", "currency"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    destination: str
    start_date: date
    end_date: date
    description: str | None
    timezone: str
    currency: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
