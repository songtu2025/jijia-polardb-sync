from threading import Event
from types import SimpleNamespace

from backend.app import scheduler as scheduler_entry


def test_scheduler_loop_scans_immediately_and_repeats_until_stopped() -> None:
    stop_event = Event()

    class FakeScheduler:
        def __init__(self) -> None:
            self.calls = 0

        def enqueue_due_jobs(self) -> int:
            self.calls += 1
            if self.calls == 2:
                stop_event.set()
            return 0

    scheduler = FakeScheduler()

    scheduler_entry.run_scheduler_loop(scheduler, stop_event, poll_seconds=0)

    assert scheduler.calls == 2


def test_scheduler_main_validates_startup_and_disposes_engine(monkeypatch) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    fake_engine = FakeEngine()
    settings = SimpleNamespace(worker_poll_seconds=3, log_level="INFO")
    scheduler = object()
    startup_validation_calls: list[tuple[object, object]] = []
    loop_calls: list[tuple[object, float]] = []

    monkeypatch.setattr(scheduler_entry, "engine", fake_engine)
    monkeypatch.setattr(scheduler_entry, "get_web_settings", lambda: settings)
    monkeypatch.setattr(scheduler_entry, "configure_service_logging", lambda _level="INFO": None)
    monkeypatch.setattr(
        scheduler_entry,
        "validate_runtime_startup",
        lambda *args: startup_validation_calls.append(args),
    )
    monkeypatch.setattr(scheduler_entry, "build_scheduler", lambda: scheduler)
    monkeypatch.setattr(
        scheduler_entry,
        "install_shutdown_handlers",
        lambda _stop, _name: None,
    )
    monkeypatch.setattr(
        scheduler_entry,
        "run_scheduler_loop",
        lambda value, _stop, *, poll_seconds: loop_calls.append((value, poll_seconds)),
    )

    exit_code = scheduler_entry.main()

    assert exit_code == 0
    assert startup_validation_calls == [(settings, fake_engine)]
    assert loop_calls == [(scheduler, 3)]
    assert fake_engine.disposed is True


def test_scheduler_main_stops_before_loop_when_startup_gate_fails(monkeypatch) -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    fake_engine = FakeEngine()
    settings = SimpleNamespace(worker_poll_seconds=3, log_level="INFO")
    loop_started = False

    def reject_startup(_settings: object, _engine: object) -> None:
        raise RuntimeError("RUNTIME_API_CONFIG_INVALID")

    def run_loop(*_args, **_kwargs) -> None:
        nonlocal loop_started
        loop_started = True

    monkeypatch.setattr(scheduler_entry, "engine", fake_engine)
    monkeypatch.setattr(scheduler_entry, "get_web_settings", lambda: settings)
    monkeypatch.setattr(scheduler_entry, "configure_service_logging", lambda _level="INFO": None)
    monkeypatch.setattr(scheduler_entry, "validate_runtime_startup", reject_startup)
    monkeypatch.setattr(scheduler_entry, "run_scheduler_loop", run_loop)

    exit_code = scheduler_entry.main()

    assert exit_code == 1
    assert loop_started is False
    assert fake_engine.disposed is True
