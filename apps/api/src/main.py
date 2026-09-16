from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.projects import router as projects_router
from src.api.reports import router as reports_router
from src.api.websocket import router as websocket_router
from src.core.config import settings
from src.schemas.health import HealthResponse

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Quorum - Multi-Agent AI Research & Report-Generation Platform API",
)

# Structured Error Exception Handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Ensure standard { error: str, detail: str } structured error responses."""
    error_names = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
    }
    error_name = error_names.get(exc.status_code, "error")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_name, "detail": str(exc.detail)},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Ensure standard { error: str, detail: str } structured response for validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": str(exc.errors()),
        },
    )


# CORS middleware configured with frontend origins from settings
origins = (
    settings.CORS_ORIGINS
    if isinstance(settings.CORS_ORIGINS, list)
    else [settings.CORS_ORIGINS]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(projects_router)
app.include_router(reports_router)
app.include_router(websocket_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint responding 200 OK."""
    return HealthResponse(status="ok")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
