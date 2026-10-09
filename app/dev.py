#!/usr/bin/env python3
"""Run the whole stack with one command. Y.3172 node: SINK."""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
WEB = APP / "web"
BUNDLE = WEB / "public" / "data" / "bundle.json"
PY = sys.executable

API_PORT = int(os.environ.get("CHAKRAVYUH_API_PORT", "8000"))
WEB_PORT = int(os.environ.get("CHAKRAVYUH_WEB_PORT", "3000"))

RESET, DIM = "\033[0m", "\033[2m"
COLOURS = {"backend": "\033[36m", "frontend": "\033[35m", "setup": "\033[33m"}


def port_free(port: int) -> bool:
    """Ask by connecting, not by binding."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.25)
                if sock.connect_ex((host, port)) == 0:
                    return False
        except OSError:
            continue
    return True


def holder_of(port: int) -> str:
    """Whatever is already listening, named if the platform will tell us."""
    try:
        out = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                             capture_output=True, text=True, check=False).stdout.splitlines()
        if len(out) > 1:
            cols = out[1].split()
            return f"{cols[0]} (pid {cols[1]})"
    except FileNotFoundError:
        pass
    return "something"


def pick_port(preferred: int, what: str) -> int:
    """Another project's dev server should not stop this one from starting."""
    if port_free(preferred):
        return preferred
    for port in range(preferred + 1, preferred + 21):
        if port_free(port):
            say("setup", f"port {preferred} is held by {holder_of(preferred)}; "
                         f"running the {what} on {port} instead")
            return port
    raise SystemExit(f"no free port for the {what} near {preferred}")


def say(who: str, line: str) -> None:
    print(f"{COLOURS.get(who, '')}{who:>8}{RESET} │ {line}", flush=True)


def run_blocking(cmd: list[str], who: str, cwd: Path = ROOT) -> int:
    say(who, f"{DIM}$ {' '.join(cmd)}{RESET}")
    return subprocess.run(cmd, cwd=cwd, check=False).returncode


def ensure_artefacts(rebuild: bool) -> bool:
    """The UI renders artefacts; without them it has nothing to say. Build them first."""
    if BUNDLE.exists() and not rebuild:
        say("setup", f"artefacts present ({BUNDLE.relative_to(ROOT)})")
        return True
    if not BUNDLE.exists():
        say("setup", "no data bundle yet — running the pipeline first (about 35 s)")
    if run_blocking([PY, "app/scripts/showcase.py", "--fast"], "setup") != 0:
        say("setup", "pipeline failed; not starting the servers")
        return False
    return run_blocking([PY, "app/scripts/export_web.py"], "setup") == 0


def ensure_node_modules() -> bool:
    if (WEB / "node_modules").exists():
        return True
    say("setup", "installing frontend dependencies (first run only)")
    return run_blocking(["npm", "install"], "setup", cwd=WEB) == 0


def pump(stream, who: str) -> None:
    for raw in iter(stream.readline, ""):
        line = raw.rstrip()
        if line:
            say(who, line)
    stream.close()


def spawn(cmd: list[str], who: str, cwd: Path, env: dict) -> subprocess.Popen:
    say(who, f"{DIM}$ {' '.join(cmd)}{RESET}")
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
        start_new_session=True,
    )
    threading.Thread(target=pump, args=(proc.stdout, who), daemon=True).start()
    return proc


def stop(procs: list[tuple[str, subprocess.Popen]]) -> None:
    for who, proc in procs:
        if proc.poll() is not None:
            continue
        say(who, "stopping")
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.terminate()
    deadline = time.time() + 6
    for who, proc in procs:
        try:
            proc.wait(timeout=max(0.1, deadline - time.time()))
        except subprocess.TimeoutExpired:
            say(who, "did not stop; killing")
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()


def main() -> int:
    ap = argparse.ArgumentParser(description="Run the CHAKRAVYUH backend and frontend together.")
    ap.add_argument("--rebuild", action="store_true",
                    help="re-run the pipeline before starting, even if artefacts exist")
    ap.add_argument("--no-backend", action="store_true",
                    help="frontend only; it falls back to the static files under public/data")
    args = ap.parse_args()

    if not ensure_artefacts(args.rebuild):
        return 1
    if not ensure_node_modules():
        return 1

    api_port = pick_port(API_PORT, "backend") if not args.no_backend else None
    web_port = pick_port(WEB_PORT, "frontend")

    procs: list[tuple[str, subprocess.Popen]] = []
    env = os.environ.copy()

    if api_port is not None:
        procs.append(("backend", spawn(
            [PY, "-m", "uvicorn", "app.api.main:app", "--reload",
             "--host", "127.0.0.1", "--port", str(api_port)],
            "backend", ROOT, env)))

    web_env = env | {
        "NEXT_PUBLIC_API_BASE": "" if api_port is None else f"http://127.0.0.1:{api_port}",
        "PORT": str(web_port),
    }
    procs.append(("frontend", spawn(["npm", "run", "dev", "--", "--port", str(web_port)],
                                    "frontend", WEB, web_env)))

    say("setup", f"frontend  http://localhost:{web_port}")
    if api_port is not None:
        say("setup", f"backend   http://127.0.0.1:{api_port}/api/health")
    say("setup", "Ctrl-C stops both")

    try:
        while True:
            for who, proc in procs:
                code = proc.poll()
                if code is not None:
                    say(who, f"exited with code {code}; stopping the rest")
                    stop(procs)
                    return code or 1
            time.sleep(0.3)
    except KeyboardInterrupt:
        print()
        stop(procs)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
