"""
AiAgent — AI 代理命令构建器。

支持 kiro、codex、claude 三种 agent，自动适配 macOS/Windows 平台。
通过 config.yaml 的 ai_agent.type 字段配置使用哪个 agent。
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import List


def _is_windows() -> bool:
    return platform.system() == "Windows" or sys.platform == "win32"


def build_agent_cmd(agent_type: str, repo_root: Path) -> List[str]:
    """
    根据 agent_type 和当前平台构建子进程命令列表。

    Args:
        agent_type: "kiro" | "codex" | "claude"
        repo_root:  仓库根目录（绝对路径）

    Returns:
        可直接传给 subprocess.Popen 的命令列表。

    Raises:
        ValueError: agent_type 不支持时抛出。
    """
    agent_type = agent_type.lower().strip()
    windows = _is_windows()

    if agent_type == "codex":
        exe = "codex.cmd" if windows else "codex"
        return [
            exe,
            "exec",
            "-C", str(repo_root),
            "--dangerously-bypass-approvals-and-sandbox",
            "--sandbox", "danger-full-access",
            "-",
        ]

    if agent_type == "kiro":
        exe = "kiro.cmd" if windows else "kiro"
        return [
            exe,
            "exec",
            "-C", str(repo_root),
            "--dangerously-bypass-approvals-and-sandbox",
            "--sandbox", "danger-full-access",
            "-",
        ]

    if agent_type == "claude":
        exe = "claude.cmd" if windows else "claude"
        return [
            exe,
            "-p",          # --print: non-interactive, read prompt from stdin
            "--dangerously-skip-permissions",
        ]

    raise ValueError(
        f"Unsupported ai_agent type: '{agent_type}'. "
        "Supported values: kiro, codex, claude"
    )
