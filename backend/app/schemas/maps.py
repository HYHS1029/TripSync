from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RouteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin_id: int = Field(gt=0, le=2_147_483_647)
    destination_id: int = Field(gt=0, le=2_147_483_647)
    day: date
    mode: Literal["WALK", "DRIVE", "TRANSIT"] = "TRANSIT"
    departure_time: time | None = None

    @field_validator("departure_time")
    @classmethod
    def local_time(cls, value):
        if value and (value.tzinfo is not None or value.second or value.microsecond):
            raise ValueError("Use a local time with minute precision")
        return value

    @model_validator(mode="after")
    def different_places(self):
        if self.origin_id == self.destination_id:
            raise ValueError("Choose different activities")
        return self
