#!/usr/bin/env python3
"""
安装 commit-validator pre-commit hook
"""

import os
import sys
import subprocess
from pathlib import Path

def install():
    """安装 pre-commit hook"""
    # 获取项目根目录
    repo_root = Path(__file__).parent.parent.parent.parent.resolve()
    hooks_dir = repo_root / ".git" / "hooks"
    pre_commit_script = Path(__file__).parent / "pre-commit.sh"

    # 确保 hooks 目录存在
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # 创建 pre-commit 链接
    pre_commit_hook = hooks_dir / "pre-commit"
    if pre_commit_hook.exists() and not pre_commit_hook.is_symlink():
        print(f"⚠️  {pre_commit_hook} already exists (not a symlink)")
        response = input("Replace it with a link to commit-validator? [y/N] ")
        if response.lower() != 'y':
            print("Aborted.")
            return

        # 备份原文件
        backup_path = hooks_dir / "pre-commit.backup"
        pre_commit_hook.rename(backup_path)
        print(f"📦 Backed up existing hook to {backup_path}")

    # 创建符号链接
    os.symlink(pre_commit_script.resolve(), pre_commit_hook)
    os.chmod(pre_commit_script, 0o755)

    print(f"✅ Installed pre-commit hook: {pre_commit_hook}")
    print(f"   Script: {pre_commit_script}")
    print("\nNow git commits will automatically run lint + tests.")

    # 验证安装
    try:
        result = subprocess.run(
            ["git", "config", "--get", "core.hooksPath"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"\nℹ️  Git is using custom hooks path: {result.stdout.strip()}")
    except:
        pass


def uninstall():
    """卸载 pre-commit hook"""
    repo_root = Path(__file__).parent.parent.parent.parent.resolve()
    pre_commit_hook = repo_root / ".git" / "hooks" / "pre-commit"

    if pre_commit_hook.is_symlink():
        target = os.readlink(pre_commit_hook)
        if "commit-validator" in target:
            pre_commit_hook.unlink()
            print(f"✅ Removed pre-commit hook")
            return

    print(f"⚠️  No commit-validator hook found at {pre_commit_hook}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        uninstall()
    else:
        install()