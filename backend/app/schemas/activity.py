from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActivityInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    activity_date: date
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = Field(default=None, max_length=200)
    place_id: str | None = Field(default=None, max_length=255, pattern=r"^[A-Za-z0-9_-]+$")
    category: Literal["sight", "station", "lodging", "food", "other"] = "sight"
    stay_until: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("location", "notes", "place_id", mode="before")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return (value.strip() or None) if isinstance(value, str) else value

    @field_validator("start_time", "end_time")
    @classmethod
    def local_minutes(cls, value: time | None) -> time | None:
        if value and (value.tzinfo is not None or value.second or value.microsecond):
            raise ValueError("Use local time with minute precision")
        return value

    @model_validator(mode="after")
    def validate_times(self) -> "ActivityInput":
        if self.end_time and (not self.start_time or self.end_time < self.start_time):
            raise ValueError("End time requires a start time and cannot be earlier")
        if self.stay_until and (self.category != "lodging" or self.stay_until < self.activity_date):
            raise ValueError("Checkout must follow check-in and requires lodging")
        return self


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    title: str
    activity_date: date
    start_time: time | None
    end_time: time | None
    location: str | None
    place_id: str | None
    category: str
    stay_until: date | None
    position: int | None
    notes: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime


class ActivityOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    activity_date: date
    activity_ids: list[int] = Field(min_length=1, max_length=500)
