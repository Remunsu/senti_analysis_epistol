import os
import signal
import subprocess
import sys
import threading
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def backend_python():
    if os.name == "nt":
        venv_python = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = BACKEND_DIR / "venv" / "bin" / "python"

    if venv_python.exists():
        return str(venv_python)

    return sys.executable


def npm_command():
    return "npm.cmd" if os.name == "nt" else "npm"


def stream_output(name, process):
    assert process.stdout is not None

    for line in process.stdout:
        print(f"[{name}] {line}", end="")


def start_process(name, command, cwd):
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    thread = threading.Thread(target=stream_output, args=(name, process), daemon=True)
    thread.start()

    return process


def stop_processes(processes):
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


def main():
    python = backend_python()
    npm = npm_command()
    processes = [
        start_process("django", [python, "manage.py", "runserver"], BACKEND_DIR),
        start_process("qcluster", [python, "manage.py", "qcluster"], BACKEND_DIR),
        start_process("vite", [npm, "run", "dev"], FRONTEND_DIR),
    ]

    def handle_signal(signum, frame):
        stop_processes(processes)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while True:
            for process in processes:
                return_code = process.poll()

                if return_code is not None:
                    stop_processes(processes)
                    return return_code

            threading.Event().wait(0.5)
    finally:
        stop_processes(processes)


if __name__ == "__main__":
    raise SystemExit(main())
