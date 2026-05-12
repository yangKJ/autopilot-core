#!/usr/bin/env python3
"""
Git Hooks 管理器
自动配置 pre-commit、post-commit 和 pre-push hooks
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path.cwd()
GIT_DIR = PROJECT_ROOT / ".git"
HOOKS_DIR = GIT_DIR / "hooks"


def create_pre_commit_hook() -> str:
    """创建 pre-commit hook 脚本"""
    return '''#!/bin/bash
# Pre-commit hook - 自动驾驶模式
# 自动检查变更的文件

echo "🚗 Pre-commit: 检查变更..."

CHANGED_FILES=$(git diff --cached --name-only)
if [ -z "$CHANGED_FILES" ]; then
    echo "没有暂存的变更"
    exit 0
fi

# 过滤 Python 文件
PYTHON_FILES=$(echo "$CHANGED_FILES" | grep -E '\\.py$|^server\\.py$' || true)
if [ -z "$PYTHON_FILES" ]; then
    echo "没有变更的 Python 文件，跳过检查"
    exit 0
fi

echo "检查变更的 Python 文件..."
echo "$PYTHON_FILES"

# 快速 Lint 检查
echo "Running ruff check..."
echo "$PYTHON_FILES" | xargs python3 -m ruff check --select E,F,W 2>/dev/null || true

# 快速语法检查
echo "Checking syntax..."
for file in $PYTHON_FILES; do
    python3 -m py_compile "$file" 2>/dev/null || {
        echo "❌ Syntax error in $file"
        exit 1
    }
done

echo "✅ Pre-commit 检查通过"
exit 0
'''


def create_post_commit_hook() -> str:
    """创建 post-commit hook 脚本"""
    return '''#!/bin/bash
# Post-commit hook - 自动驾驶模式
# 提交后自动运行检查（如果需要）

echo "🚗 Post-commit: 提交完成"

# 获取刚提交的文件
COMMITTED_FILES=$(git diff --cached --name-only | head -20)
if [ -z "$COMMITTED_FILES" ]; then
    exit 0
fi

# 检查是否包含高风险文件
HIGH_RISK_FILES=$(echo "$COMMITTED_FILES" | grep -E "server\\.py|template_engine/.*\\.py|ai_self_healing/.*\\.py" || true)

if [ -n "$HIGH_RISK_FILES" ]; then
    echo "⚠️  检测到高风险文件变更:"
    echo "$HIGH_RISK_FILES"
    echo ""
    echo "是否需要运行完整检查？ (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "运行自动驾驶检查..."
        python3 -m autopilot_core.cli run -f $HIGH_RISK_FILES
    fi
fi

echo "✅ Post-commit 完成"
exit 0
'''


def create_pre_push_hook() -> str:
    """创建 pre-push hook 脚本"""
    return '''#!/bin/bash
# Pre-push hook - 自动驾驶模式
# 推送前运行完整检查

echo "🚗 Pre-push: 运行完整检查..."

# 获取将要推送的 commit
COMMITS=$(git log --not --oneline HEAD 2>/dev/null | wc -l | tr -d ' ')
echo "待推送 commits: $COMMITS"

if [ "$COMMITS" -gt 10 ]; then
    echo "⚠️  大量 commits 待推送，建议先在本地运行测试"
fi

# 运行快速健康检查
echo "运行健康检查..."
python3 -m autopilot_core.cli health 2>/dev/null || {
    echo "❌ 健康检查失败，推送被阻止"
    exit 1
}

echo "✅ Pre-push 检查通过"
exit 0
'''


def install_hooks(dry_run: bool = False) -> bool:
    """安装 Git hooks"""
    if not HOOKS_DIR.exists():
        print(f"❌ .git/hooks 目录不存在: {HOOKS_DIR}")
        return False

    hooks = {
        "pre-commit": create_pre_commit_hook(),
        "post-commit": create_post_commit_hook(),
        "pre-push": create_pre_push_hook()
    }

    for hook_name, content in hooks.items():
        hook_path = HOOKS_DIR / hook_name

        if dry_run:
            print(f"[DRY RUN] Would create {hook_path}")
            continue

        try:
            with open(hook_path, "w") as f:
                f.write(content)

            os.chmod(hook_path, 0o755)
            print(f"✅ Installed {hook_name}")

        except Exception as e:
            print(f"❌ Failed to install {hook_name}: {e}")
            return False

    return True


def uninstall_hooks(dry_run: bool = False) -> bool:
    """卸载 Git hooks"""
    hooks = ["pre-commit", "post-commit", "pre-push"]

    for hook_name in hooks:
        hook_path = HOOKS_DIR / hook_name

        if dry_run:
            print(f"[DRY RUN] Would remove {hook_path}")
            continue

        if hook_path.exists():
            try:
                hook_path.unlink()
                print(f"✅ Removed {hook_name}")
            except Exception as e:
                print(f"❌ Failed to remove {hook_name}: {e}")
                return False

    return True


def list_hooks() -> Dict[str, bool]:
    """列出已安装的 hooks"""
    hooks = ["pre-commit", "post-commit", "pre-push"]
    return {name: (HOOKS_DIR / name).exists() for name in hooks}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Git Hooks 管理器")
    parser.add_argument("--install", "-i", action="store_true", help="安装 hooks")
    parser.add_argument("--uninstall", "-u", action="store_true", help="卸载 hooks")
    parser.add_argument("--list", "-l", action="store_true", help="列出已安装的 hooks")
    parser.add_argument("--dry-run", "-n", action="store_true", help="干跑模式")

    args = parser.parse_args()

    if args.list:
        hooks = list_hooks()
        print("\n📋 Git Hooks 状态:")
        for name, installed in hooks.items():
            status = "✅ 已安装" if installed else "❌ 未安装"
            print(f"   {status} {name}")
        return 0

    if args.install:
        print("🚀 安装 Git Hooks...")
        success = install_hooks(dry_run=args.dry_run)
        if success:
            print("\n✅ Git Hooks 安装完成")
            print("\n可用 hooks:")
            print("   pre-commit: 提交前检查 (ruff + 语法)")
            print("   post-commit: 提交后检查 (高风险文件)")
            print("   pre-push: 推送前检查 (健康检查)")
        return 0 if success else 1

    if args.uninstall:
        print("🗑️  卸载 Git Hooks...")
        success = uninstall_hooks(dry_run=args.dry_run)
        return 0 if success else 1

    # 默认显示状态
    hooks = list_hooks()
    print("\n📋 Git Hooks 状态:")
    for name, installed in hooks.items():
        status = "✅ 已安装" if installed else "❌ 未安装"
        print(f"   {status} {name}")

    print("\n使用 --install 安装，--uninstall 卸载，--list 查看状态")

    return 0


if __name__ == "__main__":
    sys.exit(main())