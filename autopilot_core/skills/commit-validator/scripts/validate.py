#!/usr/bin/env python3
"""
提交验证器脚本
git commit 前自动运行 lint + 测试
"""

import subprocess
import sys
import os
import re
from dataclasses import dataclass
from typing import Optional, List

# ============ 配置 ============

CONFIG = {
    "lint": {
        "enabled": True,
        "command": "ruff check . --select E,F,W --ignore PGH,INP",
        "fail_on_error": True
    },
    "test": {
        "enabled": True,
        "mode": "quick",
        "fail_fast": True
    },
    "block_on_failure": True
}

# ============ 数据结构 ============

@dataclass
class CheckResult:
    name: str
    passed: bool
    duration: float
    errors: List[str]
    output: str


# ============ 核心逻辑 ============

def run_cmd(cmd: str, timeout: int = 120) -> tuple:
    """执行命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 3, "", "Timeout"
    except Exception as e:
        return 2, "", str(e)


def check_lint() -> CheckResult:
    """运行 Lint 检查"""
    import time
    start = time.time()

    code, stdout, stderr = run_cmd(CONFIG["lint"]["command"])

    output = stdout + stderr
    duration = time.time() - start

    errors = []
    if code != 0:
        # 提取错误列表
        for line in output.split('\n'):
            if 'error' in line.lower() or 'warning' in line.lower():
                errors.append(line.strip()[:100])
        errors = errors[:5]  # 最多显示5条

    return CheckResult(
        name="Lint",
        passed=code == 0,
        duration=duration,
        errors=errors,
        output=output[-500:]
    )


def check_test() -> CheckResult:
    """运行测试"""
    import time
    start = time.time()

    mode = CONFIG["test"]["mode"]
    cmd = f"python3 -m pytest tests/ --tb=no -q"
    if mode == "quick":
        cmd += " --ignore=tests/test_e2e_xctest_real.py"

    code, stdout, stderr = run_cmd(cmd, timeout=300)

    output = stdout + stderr
    duration = time.time() - start

    errors = []
    if code != 0:
        failed_match = re.search(r'(\d+) failed', output)
        if failed_match:
            errors.append(f"{failed_match.group(1)} tests failed")
        failed_section = re.findall(r'FAILED (.*)', output)
        errors.extend(failed_section[:3])

    return CheckResult(
        name="Test",
        passed=code == 0,
        duration=duration,
        errors=errors,
        output=output[-500:]
    )


def print_result(result: CheckResult, emoji: str = "✅"):
    """打印检查结果"""
    status = f"{emoji} {result.name}: {'PASS' if result.passed else 'FAIL'}"
    print(f"├── {status} ({result.duration:.1f}s)")

    if not result.passed and result.errors:
        for err in result.errors:
            print(f"│   └── {err}")


def notify(title: str, message: str):
    """发送系统通知"""
    if sys.platform == "darwin":
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ])


# ============ 主逻辑 ============

def validate() -> bool:
    """执行所有验证"""
    print("🔍 Running commit validation...\n")

    results = []
    all_passed = True

    # Lint 检查
    if CONFIG["lint"]["enabled"] and not os.getenv("SKIP_LINT"):
        result = check_lint()
        results.append(result)
        all_passed = all_passed and result.passed
        print_result(result, "✅" if result.passed else "❌")

    # Test 检查
    if CONFIG["test"]["enabled"] and not os.getenv("SKIP_TEST"):
        result = check_test()
        results.append(result)
        all_passed = all_passed and result.passed
        print_result(result, "✅" if result.passed else "❌")

    # 总时长
    total_duration = sum(r.duration for r in results)

    print(f"\n⏱️  Duration: {total_duration:.1f}s\n")

    if all_passed:
        print("✅ Commit Validation Passed")
        print("Ready to commit!")
        return True
    else:
        print("❌ Commit Validation Failed")

        # 检查是否是测试失败，如果是则提示可以运行 self-healing
        test_failed = False
        for r in results:
            if r.name == "Test" and not r.passed:
                test_failed = True
                break

        if test_failed:
            print("\n💡 Tip: Run self-healing to auto-fix test failures:")
            print("   python3 .claude/skills/self-healing-executor/scripts/heal.py --error '<error>' --locator '<locator>'")

        print("\nFix errors before committing.")
        if CONFIG["lint"]["enabled"]:
            print("Run: ruff check . --fix")
        return False


def main():
    # 跳过检查
    if os.getenv("SKIP_ALL"):
        print("⚠️  Skipping all checks (SKIP_ALL=1)")
        sys.exit(0)

    success = validate()

    if not success and CONFIG["block_on_failure"]:
        sys.exit(1)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()