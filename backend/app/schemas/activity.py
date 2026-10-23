from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActivityInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    activity_date: date
    start_time: time | None = None
    end_time: time | None = None
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("location", "notes")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None

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
    notes: str | None
    created_by: int
    created_at: datetime
    updated_at: datetime
