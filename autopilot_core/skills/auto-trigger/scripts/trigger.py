#!/usr/bin/env python3
"""
自动触发器脚本
基于文件变更类型自动触发对应技能
"""

import subprocess
import sys
import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

PROJECT_ROOT = Path.cwd()
SKILLS_DIR = Path(__file__).parent.parent.parent

# 触发规则
TRIGGER_RULES = {
    "*.py": ["test-runner", "commit-validator"],
    "tests/**/*.py": ["test-runner"],
    "tests/test_*.py": ["test-runner"],
    "tests/**/test_*.py": ["test-runner"],
    "server.py": ["project-health-monitor"],
    "template_engine/**": ["commit-validator"],
    "ai_self_healing/**": ["self-healing-executor"],
    "ios_automation_core/**": ["commit-validator"],
    "*.json": ["deployment-checker"],
    ".claude/skills/**": ["learning-recorder"],
    "scripts/*.py": ["commit-validator"],
}

CHAIN_RULES = {
    "*.py": "full-auto",
    "tests/**/*.py": "full-auto",
    "server.py": "full-auto",
    "template_engine/**": "full-auto",
    "ai_self_healing/**": "full-auto",
    "ios_automation_core/**": "full-auto",
    "*.json": "on-deploy",
    "*.md": "on-change",
    ".claude/skills/**": "on-change",
}

DEFAULT_CHAIN = "full-auto"

SKILL_PATHS = {
    "test-runner": "test-runner/scripts/run_tests.py",
    "commit-validator": "commit-validator/scripts/validate.py",
    "self-healing-executor": "self-healing-executor/scripts/heal.py",
    "project-health-monitor": "project-health-monitor/scripts/health_check.py",
    "deployment-checker": "deployment-checker/scripts/check.py",
    "learning-recorder": "learning-recorder/scripts/record.py",
}


@dataclass
class TriggerResult:
    skill: str
    passed: bool
    duration: float
    output: str


def run_cmd(cmd: List[str], timeout: int = 300) -> tuple:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=PROJECT_ROOT
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 3, "", "Timeout"
    except Exception as e:
        return 2, "", str(e)


def match_pattern(filename: str, pattern: str) -> bool:
    regex_pattern = pattern.replace(".", r"\.").replace("**/", ".*/").replace("**", ".*").replace("*", "[^/]*")
    return bool(re.match(f"^{regex_pattern}$", filename))


def select_chain_for_files(filenames: List[str]) -> str:
    if not filenames:
        return DEFAULT_CHAIN

    matched_chains = []
    for filename in filenames:
        for pattern, chain in CHAIN_RULES.items():
            if match_pattern(filename, pattern):
                matched_chains.append(chain)
                break

    if not matched_chains:
        return DEFAULT_CHAIN

    priority = {"full-auto": 1, "on-deploy": 2, "on-change": 3, "hourly-check": 4}
    best_chain = min(matched_chains, key=lambda c: priority.get(c, 99))
    return best_chain


def get_skills_for_file(filename: str) -> List[str]:
    skills = set()
    for pattern, skill_list in TRIGGER_RULES.items():
        if match_pattern(filename, pattern):
            skills.update(skill_list)
    return list(skills)


def get_skills_for_files(filenames: List[str]) -> Dict[str, List[str]]:
    skill_map = {}
    for filename in filenames:
        skills = get_skills_for_file(filename)
        for skill in skills:
            if skill not in skill_map:
                skill_map[skill] = []
            if filename not in skill_map[skill]:
                skill_map[skill].append(filename)
    return skill_map


def run_skill(skill: str, files: List[str]) -> TriggerResult:
    import time
    start = time.time()

    skill_path = SKILL_PATHS.get(skill)
    if not skill_path:
        return TriggerResult(skill=skill, passed=False, duration=0, output="Unknown skill")

    script = SKILLS_DIR / skill_path
    if not script.exists():
        return TriggerResult(skill=skill, passed=False, duration=0, output=f"Script not found: {script}")

    cmd = ["python3", str(script)]

    if skill == "test-runner":
        cmd.extend(["--path", "tests/"])
    elif skill == "deployment-checker":
        cmd.append("--quick")

    code, stdout, stderr = run_cmd(cmd)
    duration = time.time() - start
    output = stdout + stderr
    passed = code == 0

    return TriggerResult(skill=skill, passed=passed, duration=duration, output=output)


def get_changed_files() -> List[str]:
    code, stdout, _ = run_cmd(["git", "diff", "--name-only", "HEAD~1"])
    if code != 0:
        code, stdout, _ = run_cmd(["git", "diff", "--cached", "--name-only"])
    if code != 0:
        return []

    files = [f.strip() for f in stdout.split('\n') if f.strip()]
    return files


def trigger(files: List[str] = None, parallel: bool = True, fail_fast: bool = False) -> bool:
    import time
    start = time.time()

    if files is None:
        files = get_changed_files()

    if not files:
        print("⚡ No files to trigger")
        return True

    print("⚡ Auto Trigger")
    print("=" * 50)
    print(f"\nChanged files ({len(files)}):")
    for f in files[:10]:
        print(f"  - {f}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")

    skill_map = get_skills_for_files(files)
    print(f"\nTriggering skills ({len(skill_map)}):")

    results = []

    for skill, skill_files in skill_map.items():
        print(f"🚀 {skill} → {', '.join(skill_files[:3])}")
        result = run_skill(skill, skill_files)
        results.append(result)

        emoji = "✅" if result.passed else "❌"
        print(f"{emoji} {skill}: {'PASS' if result.passed else 'FAIL'} ({result.duration:.1f}s)")

        if fail_fast and not result.passed:
            break

    total_duration = time.time() - start
    passed_count = sum(1 for r in results if r.passed)

    print(f"\n{'=' * 50}")
    print(f"Summary: {passed_count}/{len(results)} skills passed")
    print(f"Duration: {total_duration:.1f}s")

    if all(r.passed for r in results):
        print("\n✅ All skills passed")
        return True
    else:
        print("\n❌ Some skills failed")
        return False


def run_skill_chain(chain_name: str, context: dict = None) -> bool:
    from autopilot_core.core.autonomous import AutonomousScheduler

    files = context.get("files") if context else None
    scheduler = AutonomousScheduler(dry_run=False)
    success = scheduler.run_full_cycle(files=files)
    return success


def main():
    parser = argparse.ArgumentParser(description="Auto Trigger")
    parser.add_argument("--files", "-f", nargs="+", help="指定文件列表")
    parser.add_argument("--diff", "-d", action="store_true", help="从 git diff 获取变更")
    parser.add_argument("--parallel", "-p", action="store_true", default=True, help="并行执行")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="遇错即停")
    parser.add_argument("--chain", "-c", help="使用 skill-chain 编排执行")
    parser.add_argument("--auto-chain", "-a", action="store_true", help="根据文件类型自动选择链条")
    parser.add_argument("--legacy", action="store_true", help="禁用 auto-chain")

    args = parser.parse_args()

    files = None
    if args.diff:
        files = get_changed_files()
    elif args.files:
        files = args.files

    if args.diff and not args.legacy:
        chain = select_chain_for_files(files) if files else DEFAULT_CHAIN
        print(f"🔗 Auto-trigger: using chain '{chain}' for {len(files or [])} files")
        context = {"files": files} if files else {}
        success = run_skill_chain(chain, context)
        return 0 if success else 1

    if args.auto_chain:
        chain = select_chain_for_files(files) if files else DEFAULT_CHAIN
        print(f"🔗 Auto-selected chain: {chain}")
        context = {"files": files} if files else {}
        success = run_skill_chain(chain, context)
        return 0 if success else 1

    if args.chain:
        context = {"files": files} if files else {}
        success = run_skill_chain(args.chain, context)
        return 0 if success else 1

    success = trigger(files=files, parallel=args.parallel, fail_fast=args.fail_fast)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())