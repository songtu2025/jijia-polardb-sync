import signal
from collections.abc import Callable
from threading import Event
from types import FrameType, SimpleNamespace

from backend.app import worker as worker_entry
from backend.app.core import service_lifecycle


class RecoveringWorker:
    def __init__(self, stop_event: Event) -> None:
        self.stop_event = stop_event
        self.recover_calls = 0
        self.run_calls = 0
        self.runtime_heartbeats = 0

    def heartbeat_runtime(self) -> None:
        self.runtime_heartbeats += 1

    def recover_stale_jobs(self) -> int:
        self.recover_calls += 1
        if self.recover_calls == 2:
            self.stop_event.set()
        return 0

    def run_once(self) -> int | None:
        self.run_calls += 1
        return None


def test_worker_name_prefers_configuration_and_has_safe_default(monkeypatch) -> None:
    assert worker_entry.resolve_worker_name(" worker-east-1 ") == "worker-east-1"

    monkeypatch.setattr(worker_entry.socket, "gethostname", lambda: "sync-host")
    monkeypatch.setattr(worker_entry.os, "getpid", lambda: 4321)

    assert worker_entry.resolve_worker_name("") == "sync-host-4321"

    first_instance = worker_entry.create_worker_instance_id("worker-east-1")
    second_instance = worker_entry.create_worker_instance_id("worker-east-1")
    assert first_instance != second_instance
    assert first_instance.startswith("worker-east-1:")
    assert len(first_instance) <= 100


def test_worker_loop_rechecks_stale_jobs_after_initial_fresh_check() -> None:
    stop_event = Event()
    worker = RecoveringWorker(stop_event)

    worker_entry.run_worker_loop(worker, stop_event, poll_seconds=0)

    assert worker.recover_calls == 2
    assert worker.run_calls == 1
    assert worker.runtime_heartbeats == 2


def test_stop_request_during_run_once_waits_for_current_job_to_finish() -> None:
    stop_event = Event()
    events: list[str] = []

    class FinishingWorker:
        def heartbeat_runtime(self) -> None:
            return None

        def recover_stale_jobs(self) -> int:
            return 0

        def run_once(self) -> int:
            events.append("started")
            stop_event.set()
            events.append("finished")
            return 1

    worker_entry.run_worker_loop(
        FinishingWorker(),
        stop_event,
        poll_seconds=0,
    )

    assert events == ["started", "finished"]


def test_signal_handlers_only_request_graceful_stop(monkeypatch) -> None:
    handlers: dict[int, Callable[[int, FrameType | None], None]] = {}
    stop_event = Event()
    monkeypatch.setattr(
        service_lifecycle.signal,
        "signal",
        lambda signal_number, handler: handlers.setdefault(signal_number, handler),
    )

    worker_entry.install_shutdown_handlers(stop_event, "Worker")
    handlers[signal.SIGTERM](signal.SIGTERM, None)

    assert stop_event.is_set()


def test_main_disposes_engine_and_redacts_runtime_error(monkeypatch) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    fake_engine = FakeEngine()
    error_logs: list[tuple[str, tuple[object, ...]]] = []

    class FakeLogger:
        def error(self, message: str, *args: object) -> None:
            error_logs.append((message, args))

        def info(self, _message: str, *_args: object) -> None:
            return None

    settings = SimpleNamespace(worker_poll_seconds=0, log_level="INFO")
    monkeypatch.setattr(worker_entry, "engine", fake_engine)
    monkeypatch.setattr(worker_entry, "get_web_settings", lambda: settings)
    monkeypatch.setattr(worker_entry, "configure_service_logging", lambda _level="INFO": None)
    startup_validation_calls: list[tuple[object, object]] = []
    monkeypatch.setattr(
        worker_entry,
        "validate_runtime_startup",
        lambda *args: startup_validation_calls.append(args),
    )

    class FakeWorker:
        def start_runtime(self) -> None:
            return None

        def stop_runtime(self) -> None:
            return None

    monkeypatch.setattr(worker_entry, "build_worker", FakeWorker)
    monkeypatch.setattr(worker_entry, "install_shutdown_handlers", lambda _stop, _name: None)
    monkeypatch.setattr(worker_entry, "logger", FakeLogger())
    monkeypatch.setattr(
        worker_entry,
        "run_worker_loop",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("mysql://user:secret@example.invalid/db")
        ),
    )

    exit_code = worker_entry.main()

    assert exit_code == 1
    assert startup_validation_calls == [(settings, fake_engine)]
    assert fake_engine.disposed is True
    assert error_logs == [("Worker 运行失败: error_type=%s", ("RuntimeError",))]
    assert "mysql://" not in repr(error_logs)


def test_main_stops_before_worker_loop_when_startup_gate_fails(monkeypatch) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    fake_engine = FakeEngine()
    settings = SimpleNamespace(worker_poll_seconds=0, log_level="INFO")
    worker_built = False

    def reject_startup(_settings: object, _engine: object) -> None:
        raise RuntimeError("RUNTIME_API_CONFIG_INVALID")

    def build_worker() -> object:
        nonlocal worker_built
        worker_built = True
        return object()

    monkeypatch.setattr(worker_entry, "engine", fake_engine)
    monkeypatch.setattr(worker_entry, "get_web_settings", lambda: settings)
    monkeypatch.setattr(worker_entry, "configure_service_logging", lambda _level="INFO": None)
    monkeypatch.setattr(worker_entry, "validate_runtime_startup", reject_startup)
    monkeypatch.setattr(worker_entry, "build_worker", build_worker)

    exit_code = worker_entry.main()

    assert exit_code == 1
    assert worker_built is False
    assert fake_engine.disposed is True
