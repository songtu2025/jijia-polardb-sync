from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.app.core.errors import ApiError
from backend.app.core.security import utc_now
from backend.app.models.account_api_policy import AccountApiPolicy
from backend.app.models.jijia_account import JijiaAccount, JijiaAccountStatus
from backend.app.models.sync_job import SyncJob
from backend.app.services.scheduler import SyncScheduler
from backend.app.services.sync_job_service import ScheduledJobOutcome
from backend.tests.conftest import AuthHarness
from backend.tests.test_api_policies_api import create_active_account


def _scheduled_policy(harness: AuthHarness, monkeypatch):
    client, auth, account = create_active_account(harness, monkeypatch)
    response = client.put(
        f"/api/v1/jijia-accounts/{account['id']}/api-policies/sale_return_order_page",
        json={
            "enabled": True,
            "schedule_mode": "daily",
            "schedule_expr": "02:30",
            "timezone": "Asia/Shanghai",
            "window_mode": "checkpoint",
        },
        headers={"X-CSRF-Token": auth["csrfToken"]},
    )
    assert response.status_code == 200
    with harness.session_factory() as db:
        policy = db.scalar(
            select(AccountApiPolicy).where(
                AccountApiPolicy.jijia_account_id == account["id"],
                AccountApiPolicy.api_code == "sale_return_order_page",
            )
        )
        return account["id"], policy.id


def test_scheduler_creates_one_job_per_slot_and_advances_policy(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    account_id, policy_id = _scheduled_policy(harness, monkeypatch)
    now = utc_now()
    due = now - timedelta(days=3)
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        policy.next_run_at = due
        db.commit()

    scheduler = SyncScheduler(harness.session_factory, harness.settings)

    assert scheduler.enqueue_due_jobs(now) == 1
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        job = db.scalar(select(SyncJob))
        assert job.jijia_account_id == account_id
        assert job.trigger_type == "schedule"
        assert job.schedule_slot_key == f"policy:{policy_id}:{due:%Y%m%dT%H%M%S}"
        assert policy.next_run_at > now
        policy.next_run_at = due
        db.commit()

    assert scheduler.enqueue_due_jobs(now) == 0
    with harness.session_factory() as db:
        assert db.scalar(select(func.count(SyncJob.id))) == 1
        assert db.get(AccountApiPolicy, policy_id).next_run_at > now


def test_scheduler_ignores_disabled_manual_and_inactive_policies(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    account_id, policy_id = _scheduled_policy(harness, monkeypatch)
    now = utc_now()
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        policy.next_run_at = now - timedelta(minutes=1)
        account = db.get(JijiaAccount, account_id)
        account.status = JijiaAccountStatus.INACTIVE
        db.commit()

    scheduler = SyncScheduler(harness.session_factory, harness.settings)

    assert scheduler.enqueue_due_jobs(now) == 0
    with harness.session_factory() as db:
        assert db.scalar(select(func.count(SyncJob.id))) == 0


def test_scheduler_preserves_due_slot_until_active_job_finishes(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    account_id, policy_id = _scheduled_policy(harness, monkeypatch)
    now = utc_now()
    due = now - timedelta(minutes=1)
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        policy.next_run_at = due
        db.add(
            SyncJob(
                job_no="job-active-blocker",
                jijia_account_id=account_id,
                api_code="sale_return_order_page",
                job_type="history_backfill",
                trigger_type="manual",
                status="queued",
                attempt_count=0,
                max_attempts=1,
                queued_at=now,
            )
        )
        db.commit()

    scheduler = SyncScheduler(harness.session_factory, harness.settings)

    assert scheduler.enqueue_due_jobs(now) == 0
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        blocker = db.scalar(select(SyncJob).where(SyncJob.job_no == "job-active-blocker"))
        assert policy.next_run_at == due
        assert db.scalar(select(func.count(SyncJob.id))) == 1
        blocker.status = "success"
        blocker.finished_at = now
        db.commit()

    assert scheduler.enqueue_due_jobs(now) == 1
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        scheduled = db.scalar(select(SyncJob).where(SyncJob.schedule_slot_key.is_not(None)))
        assert scheduled.schedule_slot_key == f"policy:{policy_id}:{due:%Y%m%dT%H%M%S}"
        assert policy.next_run_at > now
        policy.next_run_at = due
        db.commit()

    assert scheduler.enqueue_due_jobs(now) == 0
    with harness.session_factory() as db:
        assert db.scalar(select(func.count(SyncJob.id))) == 2
        assert db.get(AccountApiPolicy, policy_id).next_run_at > now


def test_scheduler_ignores_paused_history_when_latest_execution_succeeded(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    account_id, policy_id = _scheduled_policy(harness, monkeypatch)
    now = utc_now()
    due = now - timedelta(minutes=1)
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        policy.next_run_at = due
        db.add_all(
            [
                SyncJob(
                    job_no="scheduler-history-paused",
                    task_no="scheduler-history",
                    jijia_account_id=account_id,
                    api_code="sale_return_order_page",
                    job_type="history_backfill",
                    trigger_type="manual",
                    status="paused",
                    queued_at=now - timedelta(minutes=2),
                ),
                SyncJob(
                    job_no="scheduler-history-success",
                    task_no="scheduler-history",
                    jijia_account_id=account_id,
                    api_code="sale_return_order_page",
                    job_type="history_backfill",
                    trigger_type="retry",
                    status="success",
                    queued_at=now - timedelta(minutes=1),
                ),
            ]
        )
        db.commit()

    created = SyncScheduler(harness.session_factory, harness.settings).enqueue_due_jobs(now)

    assert created == 1
    with harness.session_factory() as db:
        scheduled = db.scalar(select(SyncJob).where(SyncJob.schedule_slot_key.is_not(None)))
        assert scheduled is not None
        assert scheduled.trigger_type == "schedule"
        assert db.get(AccountApiPolicy, policy_id).next_run_at > now


def test_scheduler_advances_caught_up_slot_without_hot_loop(
    harness: AuthHarness,
    monkeypatch,
) -> None:
    _account_id, policy_id = _scheduled_policy(harness, monkeypatch)
    now = utc_now()
    due = now - timedelta(minutes=1)
    with harness.session_factory() as db:
        policy = db.get(AccountApiPolicy, policy_id)
        policy.next_run_at = due
        db.commit()

    def caught_up(*_args, **_kwargs):
        raise ApiError(409, "INCREMENTAL_CAUGHT_UP", "修改时间增量已经追平")

    monkeypatch.setattr(
        "backend.app.services.scheduler.create_scheduled_job",
        caught_up,
    )
    scheduler = SyncScheduler(harness.session_factory, harness.settings)

    assert scheduler.enqueue_due_jobs(now) == 0
    with harness.session_factory() as db:
        assert db.get(AccountApiPolicy, policy_id).next_run_at > now
        assert db.scalar(select(func.count(SyncJob.id))) == 0


@pytest.mark.parametrize(
    "failure",
    [
        ApiError(409, "BACKFILL_CHECKPOINT_INVALID", "检查点不可用"),
        RuntimeError("unexpected policy failure"),
    ],
)
def test_scheduler_isolates_one_policy_failure_and_processes_the_next(
    harness: AuthHarness,
    monkeypatch,
    failure: Exception,
) -> None:
    _account_id, first_policy_id = _scheduled_policy(harness, monkeypatch)
    now = utc_now()
    due = now - timedelta(days=3)
    with harness.session_factory() as db:
        first_policy = db.get(AccountApiPolicy, first_policy_id)
        second_policy = db.scalar(
            select(AccountApiPolicy).where(
                AccountApiPolicy.jijia_account_id == first_policy.jijia_account_id,
                AccountApiPolicy.api_code == "traffic_analysis_page",
            )
        )
        second_policy.enabled = True
        second_policy.schedule_mode = first_policy.schedule_mode
        second_policy.schedule_expr = first_policy.schedule_expr
        second_policy.window_mode = first_policy.window_mode
        first_policy.next_run_at = due
        second_policy.next_run_at = due
        second_policy_id = second_policy.id
        db.commit()

    processed: list[int] = []

    def create_job(_db, policy, _scheduled_for, _settings):
        processed.append(policy.id)
        if policy.id == first_policy_id:
            raise failure
        return ScheduledJobOutcome.CREATED

    monkeypatch.setattr("backend.app.services.scheduler.create_scheduled_job", create_job)

    assert SyncScheduler(harness.session_factory, harness.settings).enqueue_due_jobs(now) == 1
    assert set(processed) == {first_policy_id, second_policy_id}
    with harness.session_factory() as db:
        assert db.get(AccountApiPolicy, first_policy_id).next_run_at == due
        assert db.get(AccountApiPolicy, second_policy_id).next_run_at > now
