import json
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.api_config_registry import api_config_hash, publication_records
from backend.app.core.security import utc_now
from backend.app.models.account_api_policy import AccountApiPolicy
from backend.app.models.jijia_account import JijiaAccount
from backend.app.models.sync_records import api_config_table
from backend.app.services.api_policy_service import build_default_policy


def publish_api_configs(
    db: Session,
    api_configs: list[dict[str, Any]],
    official_catalog_path: str | Path,
) -> dict[str, int]:
    """原子发布接口配置，并为已有账号补齐默认关闭策略。"""
    records = publication_records(api_configs, official_catalog_path)
    now = utc_now()
    current_rows = {
        str(row["api_code"]): row
        for row in db.execute(select(api_config_table).with_for_update()).mappings()
    }
    published_codes = {str(record["api_code"]) for record in records}
    created = 0
    updated = 0
    disabled = 0

    for record in records:
        api_code = str(record["api_code"])
        current = current_rows.get(api_code)
        version = 1
        if current is not None:
            version = int(current["config_version"])
            if str(current["config_hash"]) != record["config_hash"]:
                version += 1
            db.execute(
                update(api_config_table)
                .where(api_config_table.c.id == current["id"])
                .values(
                    **record,
                    config_version=version,
                    published_at=now,
                    updated_at=now,
                )
            )
            updated += 1
            continue
        db.execute(
            insert(api_config_table).values(
                **record,
                config_version=version,
                published_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        created += 1

    for api_code, current in current_rows.items():
        if api_code in published_codes or (
            not bool(current["enabled"]) and not bool(current["platform_enabled"])
        ):
            continue
        config = _config_mapping(current["config_json"])
        config["enabled"] = False
        db.execute(
            update(api_config_table)
            .where(api_config_table.c.id == current["id"])
            .values(
                enabled=False,
                platform_enabled=False,
                config_json=config,
                config_hash=api_config_hash(config),
                config_version=int(current["config_version"]) + 1,
                published_at=now,
                updated_at=now,
            )
        )
        disabled += 1

    policy_count = _reconcile_account_policies(db, records)
    db.commit()
    return {
        "published": len(records),
        "created": created,
        "updated": updated,
        "disabled": disabled,
        "policiesCreated": policy_count,
    }


def _reconcile_account_policies(
    db: Session,
    records: list[dict[str, Any]],
) -> int:
    """新接口面向所有现有账号创建关闭态策略，启用仍由账号管理员决定。"""
    accounts = list(db.scalars(select(JijiaAccount).order_by(JijiaAccount.id)).all())
    existing = set(
        db.execute(
            select(
                AccountApiPolicy.jijia_account_id,
                AccountApiPolicy.api_code,
            )
        ).all()
    )
    created = 0
    for account in accounts:
        for record in records:
            api_code = str(record["api_code"])
            if (account.id, api_code) in existing:
                continue
            config = _config_mapping(record["config_json"])
            supports_window = bool((config.get("date_window") or {}).get("enabled"))
            db.add(build_default_policy(account.id, api_code, supports_window, None))
            created += 1
    return created


def _config_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)
