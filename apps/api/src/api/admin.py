import hashlib
import logging
import uuid
from typing import Any, Dict, List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import get_current_user
from src.db.models import Project, Report, User
from src.db.session import get_db

logger = logging.getLogger("quorum.api.admin")

router = APIRouter(prefix="/api/admin", tags=["Admin & Observability"])


class CurationRequest(BaseModel):
    is_guest_demo: bool = Field(..., description="Whether this resource is visible to guest judge evaluators")


@router.get(
    "/diagnostics",
    summary="Non-sensitive system diagnostics (Admin Only)",
)
async def get_system_diagnostics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Safe observability probe for authenticated administrators.
    Exposes only non-sensitive system health without passwords, credentials,
    user emails, or raw database hostnames.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for system diagnostics",
        )

    # Safe database host fingerprint (masked sha256 prefix)
    raw_host = ""
    if settings.DATABASE_URL:
        try:
            parsed = urlparse(settings.DATABASE_URL)
            raw_host = parsed.hostname or ""
        except Exception:
            raw_host = ""

    safe_db_host = (
        f"sha256:{hashlib.sha256(raw_host.encode('utf-8')).hexdigest()[:12]}"
        if raw_host
        else "sha256:local"
    )
    db_host_label = (
        "neon-production-ap-southeast-1"
        if "neon.tech" in (settings.DATABASE_URL or "")
        else "local-environment"
    )

    # Schema migration revision from alembic_version table
    migration_revision = "unknown"
    try:
        rev_res = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        migration_revision = rev_res.scalar() or "none"
    except Exception:
        migration_revision = "untracked"

    return {
        "application_environment": settings.ENVIRONMENT,
        "backend_reachable": True,
        "data_source": "fastapi_backend",
        "schema_migration_revision": migration_revision,
        "safe_db_host_fingerprint": safe_db_host,
        "db_host_label": db_host_label,
        "backend_version": settings.VERSION,
    }


@router.patch(
    "/curate/{resource_type}/{resource_id}",
    summary="Curate demo resources for Guest Judge visibility (Admin Only)",
)
async def curate_resource(
    resource_type: str,
    resource_id: uuid.UUID,
    payload: CurationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Admin-only endpoint for toggling is_guest_demo on approved resources.
    resource_type is strictly validated against fixed allowlist: ['project', 'report'].
    Never dynamically constructs model/table references.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for demo resource curation",
        )

    resource_type_clean = resource_type.strip().lower()
    if resource_type_clean == "project":
        project = (await db.execute(select(Project).where(Project.id == resource_id))).scalars().first()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        project.is_guest_demo = payload.is_guest_demo
        await db.commit()
        await db.refresh(project)
        logger.info(
            f"[CURATION_AUDIT] Admin {current_user.id} set Project {project.id} is_guest_demo={payload.is_guest_demo}"
        )
        return {
            "success": True,
            "resource_type": "project",
            "id": str(project.id),
            "is_guest_demo": project.is_guest_demo,
        }

    elif resource_type_clean == "report":
        report = (await db.execute(select(Report).where(Report.id == resource_id))).scalars().first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        report.is_guest_demo = payload.is_guest_demo
        await db.commit()
        await db.refresh(report)
        logger.info(
            f"[CURATION_AUDIT] Admin {current_user.id} set Report {report.id} is_guest_demo={payload.is_guest_demo}"
        )
        return {
            "success": True,
            "resource_type": "report",
            "id": str(report.id),
            "is_guest_demo": report.is_guest_demo,
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource_type. Permitted allowlist: ['project', 'report']",
        )



@router.get(
    "/audit/legacy-records",
    summary="Audit records created during legacy fallback mode (Admin Only)",
)
async def audit_legacy_records(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Safe audit list identifying records potentially created through legacy
    serverStore fallback paths. Contains ONLY identifiers, timestamps, and
    report counts. Does NOT expose private titles, queries, or source text.
    Ownership is left intact per Stage 3 safety policy.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for legacy record audit",
        )

    # Known legacy fallback user UUID
    legacy_uuid = uuid.UUID("9918d84c-7694-4df4-ad1b-39313d6577dc")

    stmt = (
        select(
            Project.id,
            Project.user_id,
            Project.created_at,
            func.count(Report.id).label("report_count"),
        )
        .outerjoin(Report, Report.project_id == Project.id)
        .where(Project.user_id == legacy_uuid)
        .group_by(Project.id, Project.user_id, Project.created_at)
        .order_by(Project.created_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        {
            "project_id": str(r.id),
            "owner_id": str(r.user_id),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "associated_report_count": r.report_count,
            "creation_path_confident": False,
            "status": "integrity_repair_item_requiring_manual_admin_review",
        }
        for r in rows
    ]

    return {
        "total_flagged_records": len(items),
        "audit_note": (
            "Ownership remains intact. Automatic re-assignment is prohibited per safety policy. "
            "Manual review required if provenance can be verified from external audit logs."
        ),
        "records": items,
    }
