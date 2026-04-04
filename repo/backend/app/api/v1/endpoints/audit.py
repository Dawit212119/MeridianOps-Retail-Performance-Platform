from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user, require_roles
from app.db.models import AuditLog
from app.db.session import get_db
from app.schemas.auth import AuthUser

router = APIRouter(prefix="/audit", tags=["audit"])

_AUDIT_ROLES = {"administrator", "store_manager"}


def _apply_store_scope(stmt, current_user: AuthUser):
    """Enforce store-scoped filtering for non-administrator users.

    Administrators see all audit events. Store managers only see events
    scoped to their store (store_id matches) or unscoped events (store_id is NULL).
    """
    if "administrator" in current_user.roles:
        return stmt
    if current_user.store_id is not None:
        return stmt.where(
            (AuditLog.store_id == current_user.store_id) | (AuditLog.store_id.is_(None))
        )
    return stmt.where(AuditLog.store_id.is_(None))


def _entry_dict(entry: AuditLog) -> dict:
    return {
        "id": entry.id,
        "action": entry.action,
        "resource_type": entry.resource_type,
        "resource_id": entry.resource_id,
        "store_id": entry.store_id,
        "actor_user_id": entry.actor_user_id,
        "detail_json": entry.detail_json,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


@router.get("/events")
def list_audit_events(
    resource_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: AuthUser = Depends(require_roles(_AUDIT_ROLES)),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Query audit trail with optional filters. Store managers see only their store's events."""
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    stmt = _apply_store_scope(stmt, current_user)

    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if action:
        stmt = stmt.where(AuditLog.action.like(f"{action}%"))

    stmt = stmt.limit(limit)
    entries = db.execute(stmt).scalars().all()
    return [_entry_dict(entry) for entry in entries]


@router.get("/events/member")
def list_member_audit_events(
    member_code: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _: AuthUser = Depends(require_roles(_AUDIT_ROLES)),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Query audit trail for member/loyalty/wallet operations. Store-scoped for managers."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.resource_type == "member")
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    stmt = _apply_store_scope(stmt, current_user)
    entries = db.execute(stmt).scalars().all()

    results = []
    for entry in entries:
        if member_code:
            if member_code.upper() not in (entry.detail_json or "").upper():
                continue
        results.append(_entry_dict(entry))
    return results


@router.get("/events/campaign")
def list_campaign_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    _: AuthUser = Depends(require_roles(_AUDIT_ROLES)),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Query audit trail for campaign/coupon operations. Store-scoped for managers."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.action.like("campaign%") | AuditLog.action.like("coupon%"))
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    stmt = _apply_store_scope(stmt, current_user)
    entries = db.execute(stmt).scalars().all()
    return [_entry_dict(entry) for entry in entries]


@router.get("/events/order")
def list_order_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    _: AuthUser = Depends(require_roles(_AUDIT_ROLES)),
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Query audit trail for order lifecycle operations. Store-scoped for managers."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.resource_type == "order")
        .order_by(AuditLog.id.desc())
        .limit(limit)
    )
    stmt = _apply_store_scope(stmt, current_user)
    entries = db.execute(stmt).scalars().all()
    return [_entry_dict(entry) for entry in entries]
