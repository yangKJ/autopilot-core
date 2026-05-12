#!/usr/bin/env python3
"""
测试运行器脚本
通用模板，适用于任何 Python 项目
"""

import subprocess
import sys
import os
import argparse
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

# ============ 配置区域 ============
PROJECT_ROOT = Path.cwd()
DEFAULT_TIMEOUT = 300

# ============ 数据结构 ============

@dataclass
class TestResult:
    """测试结果"""
    passed: int
    failed: int
    skipped: int
    duration: float
    errors: List[str]
    output: str

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == []

    def summary(self) -> str:
        parts = []
        if self.passed > 0:
            parts.append(f"{self.passed} passed")
        if self.failed > 0:
            parts.append(f"{self.failed} failed")
        if self.skipped > 0:
            parts.append(f"{self.skipped} skipped")
        return ", ".join(parts)


# ============ 核心逻辑 ============

def run_cmd(cmd: List[str], timeout: int = DEFAULT_TIMEOUT) -> tuple:
    """执行命令并返回 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=PROJECT_ROOT
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 3, "", "Test timeout"
    except Exception as e:
        return 2, "", str(e)


def parse_pytest_output(output: str) -> TestResult:
    """解析 pytest 输出"""
    passed = failed = skipped = 0
    duration = 0.0
    errors = []

    # 匹配统计数据
    passed_match = re.search(r'(\d+) passed', output)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r'(\d+) failed', output)
    if failed_match:
        failed = int(failed_match.group(1))

    skipped_match = re.search(r'(\d+) skipped', output)
    if skipped_match:
        skipped = int(skipped_match.group(1))

    # 匹配耗时
    duration_match = re.search(r'in ([\d.]+)s', output)
    if duration_match:
        duration = float(duration_match.group(1))

    # 提取失败信息
    failed_section = re.search(r'===.*?FAILED.*?===(.*?)(?====|$)', output, re.DOTALL)
    if failed_section:
        errors = [line.strip() for line in failed_section.group(1).split('\n') if line.strip() and '::' in line][:5]

    return TestResult(
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration=duration,
        errors=errors,
        output=output[-2000:]  # 保留最后 2000 字符
    )


def notify(title: str, message: str):
    """发送系统通知"""
    if sys.platform == "darwin":
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ])


def print_summary(result: TestResult, verbose: bool = False):
    """打印测试结果摘要"""
    if result.success:
        print(f"✅ {result.summary()} ({result.duration:.1f}s)")
    else:
        print(f"❌ {result.summary()} ({result.duration:.1f}s)")
        if result.errors:
            print("\n失败测试:")
            for err in result.errors:
                print(f"  - {err}")


def run_tests(
    path: Optional[str] = None,
    mode: str = "quick",
    parallel: int = 1,
    coverage: bool = False,
    fail_fast: bool = False,
    verbose: bool = False,
    notify_on_failure: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    on_failure: Optional[str] = None,
    on_success: Optional[str] = None
) -> TestResult:
    """运行测试"""
    # 构建命令
    cmd = ["python3", "-m", "pytest"]

    # 路径
    if path:
        cmd.append(path)
    elif mode == "quick":
        cmd.append("tests/")
    elif mode == "full":
        cmd.append(".")

    # 选项
    if not verbose:
        cmd.extend(["--tb=no", "-q"])
    else:
        cmd.extend(["--tb=short", "-v"])

    if fail_fast:
        cmd.append("-x")

    if parallel > 1:
        cmd.extend(["-n", str(parallel)])

    if coverage:
        cmd.append("--cov")
        cmd.append("--cov-report=term-missing")

    # 执行
    returncode, stdout, stderr = run_cmd(cmd, timeout)

    # 解析结果
    output = stdout + stderr
    result = parse_pytest_output(output)
    result.duration = parse_duration(output) or result.duration

    # 输出
    if verbose:
        print(output)
    else:
        print_summary(result)

    # 通知
    if not result.success and notify_on_failure:
        notify("Test Failed", f"{result.summary()} - Check logs")

    # 回调：失败时触发技能
    if not result.success and on_failure:
        _trigger_callback(on_failure, result, "failure")

    # 回调：成功时触发技能
    if result.success and on_success:
        _trigger_callback(on_success, result, "success")

    return result


def _trigger_callback(callback: str, result: TestResult, status: str):
    """触发回调技能"""
    import json
    from pathlib import Path

    # 解析 callback 格式：skill-name:method
    parts = callback.split(":")
    skill_name = parts[0]

    # 写入结果到临时文件供技能使用
    SKILLS_DIR = Path(__file__).parent.parent.parent
    result_file = SKILLS_DIR / f".callback_{status}.json"

    callback_data = {
        "status": status,
        "summary": result.summary(),
        "passed": result.passed,
        "failed": result.failed,
        "errors": result.errors[:10],  # 限制错误数量
        "duration": result.duration,
    }

    with open(result_file, "w") as f:
        json.dump(callback_data, f)

    # 根据技能类型调用对应脚本
    skill_paths = {
        "self-healing-executor": "self-healing-executor/scripts/heal.py",
        "learning-recorder": "learning-recorder/scripts/record.py",
        "notification-hub": "notification-hub/scripts/notify.py",
    }

    if skill_name in skill_paths:
        script = SKILLS_DIR / skill_paths[skill_name]
        if script.exists():
            try:
                subprocess.run(["python3", str(script)], capture_output=True, timeout=60)
                print(f"🔗 Triggered callback: {skill_name}")
            except Exception as e:
                print(f"⚠️ Callback failed: {e}")


def parse_duration(output: str) -> Optional[float]:
    """从输出解析耗时"""
    match = re.search(r'in ([\d.]+)s', output)
    return float(match.group(1)) if match else None


# ============ CLI 入口 ============

def main():
    parser = argparse.ArgumentParser(description="Test Runner")
    parser.add_argument("--path", "-p", help="测试路径")
    parser.add_argument("--mode", "-m", choices=["quick", "full"], default="quick", help="模式")
    parser.add_argument("--parallel", "-n", type=int, default=1, help="并行进程数")
    parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率")
    parser.add_argument("--fail-fast", "-x", action="store_true", help="遇错即停")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--notify", action="store_true", help="失败时通知")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT, help="超时秒数")
    parser.add_argument("--on-failure", help="失败时调用的技能，如 self-healing-executor:heal")
    parser.add_argument("--on-success", help="成功时调用的技能，如 learning-recorder:record")

    args = parser.parse_args()

    result = run_tests(
        path=args.path,
        mode=args.mode,
        parallel=args.parallel,
        coverage=args.coverage,
        fail_fast=args.fail_fast,
        verbose=args.verbose,
        notify_on_failure=args.notify,
        timeout=args.timeout,
        on_failure=args.on_failure,
        on_success=args.on_success
    )

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()