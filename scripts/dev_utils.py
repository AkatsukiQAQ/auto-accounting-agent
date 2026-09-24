"""Cross-platform helpers for the Makefile.

The Makefile must work from both PowerShell (no lsof/rm/bash on PATH) and
Git Bash / POSIX shells, so anything beyond a plain `uv run ...` command
lives here. Stdlib only.

Usage:
    python scripts/dev_utils.py free-port <port>
    python scripts/dev_utils.py clean-db
"""

import subprocess
import sys
from pathlib import Path

DB_FILES = ("mita.db", "mita.db-wal", "mita.db-shm")


def _listening_pids_windows(port: int) -> set[int]:
    proc = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True
    )
    pids: set[int] = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        # TCP <local addr> <foreign addr> LISTENING <pid>
        if (
            len(parts) >= 5
            and parts[0].upper() == "TCP"
            and parts[3].upper() == "LISTENING"
            and parts[1].endswith(f":{port}")
        ):
            pids.add(int(parts[4]))
    return pids


def _listening_pids_posix(port: int) -> set[int]:
    proc = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True
    )
    return {int(p) for p in proc.stdout.split()}


def free_port(port: int) -> None:
    if sys.platform == "win32":
        pids = _listening_pids_windows(port)
        for pid in pids:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True
            )
    else:
        pids = _listening_pids_posix(port)
        for pid in pids:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True)
    if pids:
        print(f"-> Killed stale process(es) on :{port}: {sorted(pids)}")
    else:
        print(f"No process on :{port}")


def clean_db() -> None:
    removed = []
    for name in DB_FILES:
        path = Path(name)
        if path.exists():
            path.unlink()
            removed.append(name)
    print(f"-> Removed {removed}" if removed else "No DB files to remove")


def main(argv: list[str]) -> int:
    match argv:
        case ["free-port", port] if port.isdigit():
            free_port(int(port))
        case ["clean-db"]:
            clean_db()
        case _:
            print(__doc__, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))