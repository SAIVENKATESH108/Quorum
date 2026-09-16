"""API routers package."""
from src.api.projects import router as projects_router
from src.api.reports import router as reports_router
from src.api.websocket import router as websocket_router

__all__ = ["projects_router", "reports_router", "websocket_router"]
