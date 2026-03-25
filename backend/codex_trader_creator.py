from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # backend/codex_trader_creator.py -> repo root
    return Path(__file__).resolve().parents[1]


def build_prompt(repo_root: Path) -> str:
    skill_path = (repo_root / "skills" / "retail-quant-trainer" / "SKILL.md").as_posix()

    # Keep this as a compact, imperative instruction to reduce the chance of the
    # model slipping into a "please provide task details" loop.
    return (
        f"Use [$retail-quant-trainer]({skill_path}). "
        "Execute immediately and end-to-end: create exactly one trader now"
    )


def _collect_trader_artifacts(repo_root: Path) -> set[Path]:
    traders_root = repo_root / "data" / "traders"
    found: set[Path] = set()

    if traders_root.exists():
        for p in traders_root.rglob("*"):
            if p.is_file():
                found.add(p.resolve())

    return found


def _resolve_codex_bin() -> str:
    env_bin = os.environ.get("CODEX_BIN", "").strip()
    if env_bin:
        return env_bin

    for candidate in ("codex", "codex.cmd", "codex.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise FileNotFoundError(
        "Cannot find Codex CLI. Set CODEX_BIN to the codex executable path "
        "or add codex to PATH."
    )


def create_trader_via_codex() -> int:
    repo_root = _repo_root()
    before = _collect_trader_artifacts(repo_root)
    prompt = build_prompt(repo_root=repo_root)

    cmd = [
        _resolve_codex_bin(),
        "exec",
        "-C",
        str(repo_root),
        "--sandbox",
        "workspace-write",
        "-",
    ]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdin is not None
    process.stdin.write(prompt)
    process.stdin.close()

    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
    rc = process.wait()

    after = _collect_trader_artifacts(repo_root)
    created = after - before
    if rc == 0 and not created:
        print(
            "codex exec finished but no new trader artifacts were created "
            "(expected files under data/traders).",
            file=sys.stderr,
        )
        return 2
    return rc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create one trader by calling Codex CLI with retail-quant-trainer skill."
    )
    parser.parse_args()
    try:
        code = create_trader_via_codex()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(127)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
