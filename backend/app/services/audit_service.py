from typing import Any, Literal

from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog

AuditResult = Literal["success", "failure"]
AuditChanges = dict[str, Any]


def add_audit_log(
    db: Session,
    *,
    actor_user_id: int | None,
    jijia_account_id: int | None,
    action: str,
    resource_type: str,
    resource_id: int | str | None,
    request_id: str | None,
    result: AuditResult,
    changes: AuditChanges | None = None,
) -> None:
    """把脱敏审计加入调用方事务，但不负责提交。"""
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            jijia_account_id=jijia_account_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            request_id=request_id,
            result=result,
            changes_json=changes,
        )
    )
