import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    title: str = Field(..., min_length=1, max_length=255, description="Title of the project")


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""
    title: str = Field(..., min_length=1, max_length=255, description="Updated title of the project")


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
