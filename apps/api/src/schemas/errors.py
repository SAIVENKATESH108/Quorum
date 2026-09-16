from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    """Standard structured error response format."""
    error: str
    detail: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "not_found",
                "detail": "Resource not found",
            }
        }
    )
