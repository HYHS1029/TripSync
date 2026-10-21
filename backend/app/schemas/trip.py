from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TripCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("description")
    @classmethod
    def empty_description(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_dates(self) -> "TripCreate":
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        return self


class TripUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    destination: str | None = Field(default=None, min_length=1, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("description")
    @classmethod
    def empty_description(cls, value: str | None) -> str | None:
        return value or None

    @model_validator(mode="after")
    def validate_changes(self) -> "TripUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        for field in ("name", "destination", "start_date", "end_date"):
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
    owner_id: int
    created_at: datetime
    updated_at: datetime
