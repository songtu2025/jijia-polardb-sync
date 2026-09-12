import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
E2E_PASSWORD = "Synthetic-Password-123!"


def _run_e2e_process(
    tmp_path: Path,
    script: str,
    *,
    enabled: bool,
    password: str | None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    if enabled:
        env["JIJIA_E2E_ENABLED"] = "1"
    else:
        env.pop("JIJIA_E2E_ENABLED", None)
    if password is None:
        env.pop("JIJIA_E2E_PASSWORD", None)
    else:
        env["JIJIA_E2E_PASSWORD"] = password
    return subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_e2e_factory_rejects_without_explicit_switch(tmp_path: Path) -> None:
    result = _run_e2e_process(
        tmp_path,
        "from backend.tests.e2e_app import create_e2e_app; create_e2e_app()",
        enabled=False,
        password=E2E_PASSWORD,
    )

    assert result.returncode != 0
    assert "JIJIA_E2E_ENABLED=1" in result.stderr


@pytest.mark.parametrize("password", [None, "too-short"])
def test_e2e_factory_requires_safe_password(
    tmp_path: Path,
    password: str | None,
) -> None:
    result = _run_e2e_process(
        tmp_path,
        "from backend.tests.e2e_app import create_e2e_app; create_e2e_app()",
        enabled=True,
        password=password,
    )

    assert result.returncode != 0
    assert "JIJIA_E2E_PASSWORD" in result.stderr


@pytest.mark.parametrize("module_name", ["app.config", "backend.app.core.config"])
def test_e2e_factory_rejects_process_with_loaded_production_module(
    tmp_path: Path,
    module_name: str,
) -> None:
    script = f"""
import importlib

importlib.import_module({module_name!r})
from backend.tests.e2e_app import create_e2e_app
create_e2e_app()
"""
    result = _run_e2e_process(
        tmp_path,
        script,
        enabled=True,
        password=E2E_PASSWORD,
    )

    assert result.returncode != 0
    assert "dedicated fresh process" in result.stderr


def test_e2e_factory_uses_sqlite_seed_data_and_local_verification(
    tmp_path: Path,
) -> None:
    script = """
import hashlib
import json
import sys
from datetime import UTC, date, datetime, timedelta
from socket import socket
from unittest.mock import patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.tests.e2e_app import create_e2e_app

app = create_e2e_app()
engine = app.state.e2e_engine
session_factory = app.state.e2e_session_factory

from backend.app.models import AccountApiPolicy, AppUser, JijiaAccount, SyncJob
from backend.app.models.sync_records import (
    raw_api_data_history_table,
    raw_api_data_table,
    sync_api_log_table,
    sync_batch_table,
    sync_checkpoint_table,
)

with session_factory() as db:
    users = list(db.scalars(select(AppUser).order_by(AppUser.id)).all())
    account = db.scalar(
        select(JijiaAccount).where(JijiaAccount.account_code == "acct_e2e_synthetic")
    )
    second_account = db.scalar(
        select(JijiaAccount).where(
            JijiaAccount.account_code == "acct_e2e_synthetic_second"
        )
    )
    policy = db.scalar(
        select(AccountApiPolicy).where(
            AccountApiPolicy.jijia_account_id == account.id,
            AccountApiPolicy.api_code == "sale_return_order_page",
        )
    )
    jobs_by_account = {
        job.jijia_account_id: job
        for job in db.scalars(select(SyncJob).order_by(SyncJob.id)).all()
    }
    batches_by_account = {
        row["jijia_account_id"]: row
        for row in db.execute(select(sync_batch_table)).mappings().all()
    }
    checkpoints_by_account = {
        row["jijia_account_id"]: row
        for row in db.execute(select(sync_checkpoint_table)).mappings().all()
    }
    log_rows = db.execute(select(sync_api_log_table)).mappings().all()
    current_raw_by_account = {
        row["jijia_account_id"]: row
        for row in db.execute(
            select(raw_api_data_table).where(
                raw_api_data_table.c.api_code == "sale_return_order_page"
            )
        ).mappings().all()
    }
    history_by_account = {
        row["jijia_account_id"]: row
        for row in db.execute(select(raw_api_data_history_table)).mappings().all()
    }

raw_marker = {"synthetic": True, "returnOrderId": "E2E-RETURN-001"}
second_raw_marker = {
    "synthetic": True,
    "returnOrderId": "E2E-RETURN-001",
    "accountMarker": "SECOND",
}
expected_identity = hashlib.sha256(b"pk:E2E-RETURN-001").hexdigest()
expected_hashes = {
    account.id: hashlib.sha256(
        json.dumps(
            raw_marker,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest(),
    second_account.id: hashlib.sha256(
        json.dumps(
            second_raw_marker,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest(),
}
expected_markers = {
    account.id: raw_marker,
    second_account.id: second_raw_marker,
}
history_floor = date(2020, 1, 1)
history_window_days = 31
backfill_t0_utc = datetime(2026, 8, 26, tzinfo=UTC)
incremental_timezone = "Asia/Shanghai"
incremental_lag_days = 1
frozen_end = backfill_t0_utc.astimezone(ZoneInfo(incremental_timezone)).date() - timedelta(
    days=incremental_lag_days
)
total_history_windows = (
    (frozen_end - history_floor).days + 1 + history_window_days - 1
) // history_window_days
final_window_start = history_floor + timedelta(
    days=(total_history_windows - 1) * history_window_days
)
expected_history_progress = {
    "completedWindows": total_history_windows,
    "totalWindows": total_history_windows,
    "currentWindow": {
        "startDate": final_window_start.isoformat(),
        "endDate": frozen_end.isoformat(),
    },
    "currentPage": 1,
    "totalPages": 1,
    "earliestObservedDataDate": "2026-08-24",
    "historyCompleteThrough": frozen_end.isoformat(),
    "changeCatchup": "incremental_ready",
}
private_progress_keys = {
    "_frozenWindowEnd",
    "_backfillStartedAt",
    "_incrementalWindowDays",
    "_incrementalTimezone",
    "_incrementalLagDays",
}
internal_t0_by_account = {
    account_id: datetime.fromisoformat(
        jobs_by_account[account_id].progress_json["_backfillStartedAt"].replace(
            "Z", "+00:00"
        )
    ).astimezone(UTC)
    for account_id in (account.id, second_account.id)
}
checkpoint_t0_by_account = {
    account_id: datetime.fromisoformat(
        checkpoints_by_account[account_id]["checkpoint_value"]["backfill_started_at"]
    ).replace(tzinfo=UTC)
    for account_id in (account.id, second_account.id)
}
with TestClient(app) as client:
    ready = client.get("/health/ready")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@e2e.example.com", "password": "Synthetic-Password-123!"},
    )
    if login.status_code != 200:
        raise AssertionError(f"login failed: {login.status_code} {login.text}")
    csrf_token = login.json()["data"]["csrfToken"]
    with patch.object(socket, "connect", side_effect=AssertionError("network blocked")):
        verified = client.post(
            f"/api/v1/jijia-accounts/{account.id}/verify",
            headers={"X-CSRF-Token": csrf_token},
        )
    raw_list = client.get(
        "/api/v1/raw-data",
        params={
            "jijia_account_id": account.id,
            "api_code": "sale_return_order_page",
        },
    )
    raw_items = raw_list.json()["data"]["items"]
    raw_id = raw_items[0]["id"]
    operator_detail = client.get(f"/api/v1/raw-data/{raw_id}")
    operator_versions = client.get(f"/api/v1/raw-data/{raw_id}/versions")
    second_raw_list = client.get(
        "/api/v1/raw-data",
        params={
            "jijia_account_id": second_account.id,
            "api_code": "sale_return_order_page",
        },
    )
    second_raw_items = second_raw_list.json()["data"]["items"]
    second_raw_id = second_raw_items[0]["id"]
    second_operator_detail = client.get(f"/api/v1/raw-data/{second_raw_id}")
    second_operator_versions = client.get(
        f"/api/v1/raw-data/{second_raw_id}/versions"
    )
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@e2e.example.com", "password": "Synthetic-Password-123!"},
    )
    admin_csrf = admin_login.json()["data"]["csrfToken"]
    admin_detail = client.get(f"/api/v1/raw-data/{raw_id}")
    admin_versions = client.get(f"/api/v1/raw-data/{raw_id}/versions")
    invitation = client.post(
        "/api/v1/invitations",
        json={"email": "invited@e2e.example.com", "role": "viewer"},
        headers={"X-CSRF-Token": admin_csrf},
    )
    viewer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@e2e.example.com", "password": "Synthetic-Password-123!"},
    )
    viewer_detail = client.get(f"/api/v1/raw-data/{raw_id}")
    viewer_versions = client.get(f"/api/v1/raw-data/{raw_id}/versions")
    viewer_jobs = client.get(
        "/api/v1/sync-jobs",
        params={
            "jijia_account_id": account.id,
            "api_code": "sale_return_order_page",
        },
    )
    viewer_job_items = viewer_jobs.json()["data"]["items"]
    viewer_job = client.get(f"/api/v1/sync-jobs/{viewer_job_items[0]['id']}")
    viewer_job_data = viewer_job.json()["data"]
    viewer_run = client.get(f"/api/v1/sync-runs/{viewer_job_data['syncRunId']}")
    viewer_run_data = viewer_run.json()["data"]
    viewer_logs = client.get(
        f"/api/v1/sync-runs/{viewer_job_data['syncRunId']}/logs"
    )
    viewer_log_items = viewer_logs.json()["data"]["items"]
    second_viewer_jobs = client.get(
        "/api/v1/sync-jobs",
        params={
            "jijia_account_id": second_account.id,
            "api_code": "sale_return_order_page",
        },
    )
    second_viewer_job_items = second_viewer_jobs.json()["data"]["items"]
    second_viewer_job = client.get(
        f"/api/v1/sync-jobs/{second_viewer_job_items[0]['id']}"
    )
    second_viewer_job_data = second_viewer_job.json()["data"]
    second_viewer_run = client.get(
        f"/api/v1/sync-runs/{second_viewer_job_data['syncRunId']}"
    )
    second_viewer_run_data = second_viewer_run.json()["data"]
    second_viewer_logs = client.get(
        f"/api/v1/sync-runs/{second_viewer_job_data['syncRunId']}/logs"
    )
    second_viewer_log_items = second_viewer_logs.json()["data"]["items"]
    viewer_batch_raw = client.get(
        "/api/v1/raw-data",
        params={
            "jijia_account_id": account.id,
            "api_code": "sale_return_order_page",
            "sync_batch_no": viewer_run_data["batchNo"],
        },
    )
    second_batch_raw = client.get(
        "/api/v1/raw-data",
        params={
            "jijia_account_id": second_account.id,
            "api_code": "sale_return_order_page",
            "sync_batch_no": "e2e-batch-raw-002",
        },
    )
    first_account_cross_batch = client.get(
        "/api/v1/raw-data",
        params={
            "jijia_account_id": account.id,
            "sync_batch_no": "e2e-batch-raw-002",
        },
    )
    second_account_cross_batch = client.get(
        "/api/v1/raw-data",
        params={
            "jijia_account_id": second_account.id,
            "sync_batch_no": viewer_run_data["batchNo"],
        },
    )

operator_detail_data = operator_detail.json()["data"]
operator_version_items = operator_versions.json()["data"]["items"]
admin_detail_data = admin_detail.json()["data"]
admin_version_items = admin_versions.json()["data"]["items"]
viewer_detail_data = viewer_detail.json()["data"]
viewer_version_items = viewer_versions.json()["data"]["items"]
public_history_progresses = [
    viewer_job_items[0]["historyProgress"],
    viewer_job_data["historyProgress"],
    second_viewer_job_items[0]["historyProgress"],
    second_viewer_job_data["historyProgress"],
]

print(json.dumps({
    "dialect": engine.dialect.name,
    "emails": sorted(user.email for user in users),
    "roles": sorted(user.role.value for user in users),
    "accountStatus": account.status.value,
    "policyApiCode": policy.api_code,
    "policyEnabled": policy.enabled,
    "overrideCount": len(app.dependency_overrides),
    "readyStatus": ready.status_code,
    "loginStatus": login.status_code,
    "verifyStatus": verified.status_code,
    "rawListStatus": raw_list.status_code,
    "rawListCount": len(raw_items),
    "rawListApiCode": raw_items[0]["apiCode"],
    "operatorDetailMarker": operator_detail_data.get("rawJson") == raw_marker,
    "operatorVersionsIsolated": len(operator_version_items) == 1
    and all(
            item.get("rawJson") == raw_marker
            and item.get("rawJson") != second_raw_marker
            for item in operator_version_items
        ),
    "secondRawListCount": len(second_raw_items),
    "secondRawMarker": second_operator_detail.json()["data"].get("rawJson")
    == second_raw_marker,
    "secondVersionsMarker": len(
        second_operator_versions.json()["data"]["items"]
    )
    == 1
    and all(
        item.get("rawJson") == second_raw_marker
        for item in second_operator_versions.json()["data"]["items"]
    ),
    "adminDetailMarker": admin_detail_data.get("rawJson") == raw_marker,
    "adminVersionsIsolated": len(admin_version_items) == 1
    and all(
        item.get("rawJson") == raw_marker and item.get("rawJson") != second_raw_marker
        for item in admin_version_items
    ),
    "viewerLoginStatus": viewer_login.status_code,
    "viewerDetailHidden": "rawJson" not in viewer_detail_data,
    "viewerVersionsHidden": len(viewer_version_items) == 1
    and all(
        "rawJson" not in item for item in viewer_version_items
    ),
    "viewerJobChain": len(viewer_job_items) == 1
    and viewer_job.status_code == 200
    and viewer_job_data["syncRunId"] == viewer_run_data["id"]
    and viewer_job_data["syncBatchNo"] == viewer_run_data["batchNo"]
    and viewer_run_data["jijiaAccountId"] == account.id,
    "viewerRunLogChain": viewer_run.status_code == 200
    and viewer_logs.status_code == 200
    and len(viewer_log_items) == 1
    and viewer_log_items[0]["apiCode"] == "sale_return_order_page",
    "secondViewerJobChain": len(second_viewer_job_items) == 1
    and second_viewer_job.status_code == 200
    and second_viewer_job_data["syncRunId"] == second_viewer_run_data["id"]
    and second_viewer_job_data["syncBatchNo"] == second_viewer_run_data["batchNo"]
    and second_viewer_run_data["jijiaAccountId"] == second_account.id,
    "secondViewerRunLogChain": second_viewer_run.status_code == 200
    and second_viewer_logs.status_code == 200
    and len(second_viewer_log_items) == 1
    and second_viewer_log_items[0]["apiCode"] == "sale_return_order_page",
    "jobBatchContract": all(
        jobs_by_account[account_id].sync_batch_no
        == batches_by_account[account_id]["sync_batch_no"]
        and batches_by_account[account_id]["sync_job_id"]
        == jobs_by_account[account_id].id
        and jobs_by_account[account_id].jijia_account_id
        == batches_by_account[account_id]["jijia_account_id"]
        == account_id
        for account_id in (account.id, second_account.id)
    ),
    "logScopeContract": all(
        len(
            [
                row
                for row in log_rows
                if row["sync_batch_no"]
                == batches_by_account[account_id]["sync_batch_no"]
                and row["jijia_account_id"] == account_id
                and row["api_code"] == "sale_return_order_page"
            ]
        )
        == 1
        for account_id in (account.id, second_account.id)
    )
    and len(
        [
            row
            for row in log_rows
            if row["sync_batch_no"] == batches_by_account[account.id]["sync_batch_no"]
            and row["jijia_account_id"] == second_account.id
            and row["api_code"] == "sale_return_order_page"
        ]
    )
    == 1,
    "checkpointContract": all(
        checkpoints_by_account[account_id]["jijia_account_id"] == account_id
        and checkpoints_by_account[account_id]["api_code"]
        == "sale_return_order_page"
        and checkpoints_by_account[account_id]["checkpoint_kind"]
        == "history_backfill"
        and checkpoints_by_account[account_id]["last_sync_batch_no"]
        == batches_by_account[account_id]["sync_batch_no"]
        for account_id in (account.id, second_account.id)
    ),
    "observationBatchContract": all(
        current_raw_by_account[account_id]["sync_batch_no"]
        == history_by_account[account_id]["sync_batch_no"]
        == checkpoints_by_account[account_id]["last_sync_batch_no"]
        == jobs_by_account[account_id].sync_batch_no
        == batches_by_account[account_id]["sync_batch_no"]
        for account_id in (account.id, second_account.id)
    ),
    "rawIdentityHashContract": all(
        current_raw_by_account[account_id]["record_identity"]
        == history_by_account[account_id]["record_identity"]
        == expected_identity
        and current_raw_by_account[account_id]["data_hash"]
        == history_by_account[account_id]["data_hash"]
        == expected_hashes[account_id]
        and current_raw_by_account[account_id]["raw_json"]
        == history_by_account[account_id]["raw_json"]
        == expected_markers[account_id]
        for account_id in (account.id, second_account.id)
    ),
    "checkpointValueContract": all(
        checkpoints_by_account[account_id]["checkpoint_value"]
        == {
            "window_start": final_window_start.isoformat(),
            "window_end": frozen_end.isoformat(),
            "next_window_start": (frozen_end + timedelta(days=1)).isoformat(),
            "frozen_window_end": frozen_end.isoformat(),
            "backfill_started_at": "2026-08-26T00:00:00",
            "window_days": history_window_days,
            "absolute_lower_bound": history_floor.isoformat(),
        }
        for account_id in (account.id, second_account.id)
    ),
    "historyProgressContract": all(
        progress == expected_history_progress for progress in public_history_progresses
    ),
    "historyProgressPrivateHidden": all(
        private_progress_keys.isdisjoint(progress)
        for progress in public_history_progresses
    ),
    "historyWindowContract": all(
        jobs_by_account[account_id].window_start.isoformat()
        == jobs_by_account[account_id].progress_json["currentWindow"]["startDate"]
        == checkpoints_by_account[account_id]["checkpoint_value"]["window_start"]
        == final_window_start.isoformat()
        and jobs_by_account[account_id].window_end.isoformat()
        == jobs_by_account[account_id].progress_json["currentWindow"]["endDate"]
        == jobs_by_account[account_id].progress_json["historyCompleteThrough"]
        == checkpoints_by_account[account_id]["checkpoint_value"]["window_end"]
        == frozen_end.isoformat()
        and jobs_by_account[account_id].progress_json["_frozenWindowEnd"]
        == checkpoints_by_account[account_id]["checkpoint_value"]["frozen_window_end"]
        == frozen_end.isoformat()
        and internal_t0_by_account[account_id]
        == checkpoint_t0_by_account[account_id]
        == backfill_t0_utc
        and jobs_by_account[account_id].progress_json["_incrementalWindowDays"]
        == history_window_days
        and jobs_by_account[account_id].progress_json["_incrementalTimezone"]
        == incremental_timezone
        and jobs_by_account[account_id].progress_json["_incrementalLagDays"]
        == incremental_lag_days
        and total_history_windows == 79
        and checkpoints_by_account[account_id]["checkpoint_value"]["absolute_lower_bound"]
        == history_floor.isoformat()
        and checkpoints_by_account[account_id]["checkpoint_value"]["window_days"]
        == history_window_days
        for account_id in (account.id, second_account.id)
    ),
    "backfillTimestampContract": all(
        jobs_by_account[account_id].queued_at.isoformat()
        == jobs_by_account[account_id].started_at.isoformat()
        == jobs_by_account[account_id].finished_at.isoformat()
        == batches_by_account[account_id]["started_at"].isoformat()
        == batches_by_account[account_id]["finished_at"].isoformat()
        == current_raw_by_account[account_id]["first_observed_at"].isoformat()
        == current_raw_by_account[account_id]["last_observed_at"].isoformat()
        == history_by_account[account_id]["observed_at"].isoformat()
        == "2026-08-26T00:00:00"
        for account_id in (account.id, second_account.id)
    ),
    "rawBatchIsolated": len(viewer_batch_raw.json()["data"]["items"]) == 1
    and len(second_batch_raw.json()["data"]["items"]) == 1
    and first_account_cross_batch.json()["data"]["items"] == []
    and second_account_cross_batch.json()["data"]["items"] == [],
    "invitationStatus": invitation.status_code,
    "fakeMailUsed": len(app.state.e2e_mail_sender.invitations) == 1,
    "settingsOverrideUsed": app.state.e2e_mail_sender.invitations[0]["url"].startswith(
        "http://127.0.0.1:5173/register#token="
    ),
    "workerImported": "backend.app.worker" in sys.modules,
}))
engine.dispose()
"""
    result = _run_e2e_process(
        tmp_path,
        script,
        enabled=True,
        password=E2E_PASSWORD,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "dialect": "sqlite",
        "emails": [
            "admin@e2e.example.com",
            "operator@e2e.example.com",
            "viewer@e2e.example.com",
        ],
        "roles": ["admin", "operator", "viewer"],
        "accountStatus": "active",
        "policyApiCode": "sale_return_order_page",
        "policyEnabled": True,
        "overrideCount": 3,
        "readyStatus": 200,
        "loginStatus": 200,
        "verifyStatus": 200,
        "rawListStatus": 200,
        "rawListCount": 1,
        "rawListApiCode": "sale_return_order_page",
        "operatorDetailMarker": True,
        "operatorVersionsIsolated": True,
        "secondRawListCount": 1,
        "secondRawMarker": True,
        "secondVersionsMarker": True,
        "adminDetailMarker": True,
        "adminVersionsIsolated": True,
        "viewerLoginStatus": 200,
        "viewerDetailHidden": True,
        "viewerVersionsHidden": True,
        "viewerJobChain": True,
        "viewerRunLogChain": True,
        "secondViewerJobChain": True,
        "secondViewerRunLogChain": True,
        "jobBatchContract": True,
        "logScopeContract": True,
        "checkpointContract": True,
        "observationBatchContract": True,
        "rawIdentityHashContract": True,
        "checkpointValueContract": True,
        "historyProgressContract": True,
        "historyProgressPrivateHidden": True,
        "historyWindowContract": True,
        "backfillTimestampContract": True,
        "rawBatchIsolated": True,
        "invitationStatus": 200,
        "fakeMailUsed": True,
        "settingsOverrideUsed": True,
        "workerImported": False,
    }
