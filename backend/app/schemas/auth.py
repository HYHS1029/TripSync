from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, TypeAdapter, field_validator


_EMAIL = TypeAdapter(EmailStr)


class LoginRequest(BaseModel):
    # Match existing UserCreate normalization so existing accounts keep working.
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(min_length=3, max_length=254, validation_alias=AliasChoices("identifier", "email"))
    password: str = Field(min_length=8, max_length=128)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return str(_EMAIL.validate_python(value)) if "@" in value else value


class EmailVerificationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class EmailVerificationConfirm(BaseModel):
    token: str = Field(min_length=43, max_length=43, pattern=r"^[A-Za-z0-9_-]{43}$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
