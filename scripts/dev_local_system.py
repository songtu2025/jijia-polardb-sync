import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "scripts"
MAX_LOCAL_WORKER_PROCESSES = 8


def _powershell_command(script_name: str, *arguments: str) -> list[str]:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise RuntimeError("POWERSHELL_NOT_FOUND")
    return [
        executable,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT_DIR / script_name),
        *arguments,
    ]


def _process_specs() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """按配置生成本地服务清单，并给每个 Worker 注入唯一名称。"""
    try:
        worker_processes = int(os.getenv("WORKER_PROCESSES", "1"))
    except ValueError as error:
        raise RuntimeError("WORKER_PROCESSES_INVALID") from error
    if not 1 <= worker_processes <= MAX_LOCAL_WORKER_PROCESSES:
        raise RuntimeError("WORKER_PROCESSES_INVALID")
    workers = tuple(
        (f"Worker {index}", "dev-local-worker.ps1", ("-WorkerName", f"local-worker-{index}"))
        for index in range(1, worker_processes + 1)
    )
    return (
        ("API", "dev-local-api.ps1", ()),
        ("Scheduler", "dev-local-scheduler.ps1", ()),
        *workers,
        ("Web", "dev-local-web.ps1", ()),
    )


def _start_processes(
    specs: tuple[tuple[str, str, tuple[str, ...]], ...],
) -> list[subprocess.Popen[bytes]]:
    """让所有服务各自拥有控制台进程组，便于统一优雅停止。"""
    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for _name, script, arguments in specs:
            processes.append(
                subprocess.Popen(
                    _powershell_command(script, *arguments),
                    cwd=PROJECT_ROOT,
                    creationflags=creation_flags,
                )
            )
    except Exception:
        _force_stop(processes)
        _wait_for_all(processes)
        raise
    return processes


def _request_stop(processes: list[subprocess.Popen[bytes]]) -> None:
    """第一次停止只发送控制台信号，让 Worker 完成当前安全窗口。"""
    for process in processes:
        if process.poll() is not None:
            continue
        if sys.platform == "win32":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.send_signal(signal.SIGINT)


def _force_stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()


def _wait_for_all(processes: list[subprocess.Popen[bytes]]) -> None:
    while any(process.poll() is None for process in processes):
        time.sleep(0.2)


def main() -> int:
    """同时监管 Web、API、Scheduler 和 Worker，任一退出时关闭整套系统。"""
    processes: list[subprocess.Popen[bytes]] = []
    try:
        specs = _process_specs()
        processes = _start_processes(specs)
        print("本地完整系统已启动：Web、API、Scheduler、Worker。按 Ctrl+C 安全停止。")
        while True:
            for (name, _script, _arguments), process in zip(specs, processes, strict=True):
                exit_code = process.poll()
                if exit_code is not None:
                    print(f"{name} 已退出，正在停止其他服务。")
                    _request_stop(processes)
                    _wait_for_all(processes)
                    return exit_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("正在安全停止；Worker 会先结束当前窗口。再次 Ctrl+C 可强制退出。")
        _request_stop(processes)
        try:
            _wait_for_all(processes)
        except KeyboardInterrupt:
            print("正在强制停止本地服务。")
            _force_stop(processes)
            _wait_for_all(processes)
        return 0
    except Exception as error:
        print(f"本地系统启动失败：{type(error).__name__}")
        _force_stop(processes)
        _wait_for_all(processes)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
