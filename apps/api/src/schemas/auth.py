from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.db.models import UserRole


class AuthCredentials(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class RegisterRequest(AuthCredentials):
    name: Optional[str] = Field(None, max_length=255)


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
