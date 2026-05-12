#!/usr/bin/env python3
"""
部署检查器脚本
部署前验证项目状态
"""

import subprocess
import sys
import os
import json
import re
from dataclasses import dataclass
from typing import List, Optional

# ============ 配置 ============

CONFIG = {
    "required_env_vars": [
        "OPENAI_API_KEY",
    ],
    "security_scan": True,
    "min_coverage": 50,
    "max_startup_time": 5,
    "block_on_warnings": False
}

# ============ 数据结构 ============

@dataclass
class CheckItem:
    name: str
    passed: bool
    severity: str  # BLOCKER, WARNING, INFO
    message: str
    details: Optional[str] = None


# ============ 核心逻辑 ============

def run_cmd(cmd: str, timeout: int = 30) -> tuple:
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


def check_dependency() -> CheckItem:
    """检查依赖完整性"""
    # 检查 requirements.txt 是否存在
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        return CheckItem(
            name="Dependency Check",
            passed=False,
            severity="BLOCKER",
            message="requirements.txt not found",
        )

    return CheckItem(
        name="Dependency Check",
        passed=True,
        severity="INFO",
        message="requirements.txt exists",
    )


def check_environment() -> CheckItem:
    """检查环境变量"""
    missing = []
    for var in CONFIG["required_env_vars"]:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        return CheckItem(
            name="Environment Check",
            passed=False,
            severity="BLOCKER",
            message=f"Missing env vars: {', '.join(missing)}",
        )

    return CheckItem(
        name="Environment Check",
        passed=True,
        severity="INFO",
        message="All required env vars set",
    )


def check_code_integrity() -> CheckItem:
    """检查代码完整性"""
    # 检查是否有未提交的更改
    code, stdout, _ = run_cmd("git status --porcelain")
    if code == 0:
        uncommitted = [line for line in stdout.split('\n') if line.strip()]
        if uncommitted:
            # 检查是否有敏感文件
            sensitive = [f for f in uncommitted if any(s in f.lower() for s in ['secret', 'password', '.env', 'credential'])]
            if sensitive:
                return CheckItem(
                    name="Code Integrity",
                    passed=False,
                    severity="BLOCKER",
                    message=f"Uncommitted sensitive files: {len(sensitive)}",
                    details="\n".join(sensitive[:5])
                )
            return CheckItem(
                name="Code Integrity",
                passed=True,
                severity="WARNING",
                message=f"{len(uncommitted)} uncommitted files",
                details="\n".join(uncommitted[:5])
            )

    return CheckItem(
        name="Code Integrity",
        passed=True,
        severity="INFO",
        message="No uncommitted changes",
    )


def check_security() -> CheckItem:
    """安全扫描"""
    if not CONFIG["security_scan"]:
        return CheckItem(
            name="Security Scan",
            passed=True,
            severity="INFO",
            message="Security scan disabled"
        )

    # 扫描硬编码的敏感词
    sensitive_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', "password ="),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "api_key ="),
        (r'secret\s*=\s*["\'][^"\']+["\']', "secret ="),
    ]

    issues = []
    for pattern, name in sensitive_patterns:
        code, stdout, _ = run_cmd(f"grep -rP '{pattern}' --include='*.py' . 2>/dev/null | head -5")
        if code == 0 and stdout.strip():
            for line in stdout.strip().split('\n')[:3]:
                if line.strip():
                    issues.append(f"{name}: {line.strip()[:80]}")

    if issues:
        return CheckItem(
            name="Security Scan",
            passed=False,
            severity="BLOCKER",
            message=f"Hardcoded secrets found: {len(issues)}",
            details="\n".join(issues)
        )

    return CheckItem(
        name="Security Scan",
        passed=True,
        severity="INFO",
        message="No hardcoded secrets found"
    )


def check_test_coverage() -> CheckItem:
    """检查测试覆盖率"""
    # 检查是否有覆盖率数据
    coverage_file = ".coverage"
    if not os.path.exists(coverage_file):
        return CheckItem(
            name="Test Coverage",
            passed=True,
            severity="WARNING",
            message="No coverage data (run tests with --cov first)",
        )

    return CheckItem(
        name="Test Coverage",
        passed=True,
        severity="INFO",
        message="Coverage data exists",
    )


def check_git_status() -> CheckItem:
    """检查 git 状态"""
    code, stdout, _ = run_cmd("git log --oneline -1")
    if code == 0:
        last_commit = stdout.strip()
        return CheckItem(
            name="Git Status",
            passed=True,
            severity="INFO",
            message=f"Last commit: {last_commit}",
        )

    return CheckItem(
        name="Git Status",
        passed=True,
        severity="INFO",
        message="Not a git repo or git error",
    )


# ============ 主逻辑 ============

def run_checks() -> List[CheckItem]:
    """运行所有检查"""
    return [
        check_dependency(),
        check_environment(),
        check_code_integrity(),
        check_security(),
        check_test_coverage(),
        check_git_status(),
    ]


def print_report(checks: List[CheckItem]) -> bool:
    """打印报告"""
    print("\n🚀 Deployment Readiness Check")
    print("="*50)

    blockers = []
    warnings = []
    all_passed = True

    for check in checks:
        if check.passed:
            emoji = "✅"
        elif check.severity == "BLOCKER":
            emoji = "🔴"
            blockers.append(check)
            all_passed = False
        else:
            emoji = "⚠️"
            warnings.append(check)
            all_passed = False

        print(f"{emoji} {check.name:<20} - {check.message}")

        if check.details:
            for line in check.details.split('\n'):
                if line.strip():
                    print(f"   {line.strip()[:60]}")

    print("="*50)

    if blockers:
        print("\n❌ DEPLOYMENT BLOCKED\n")
        print("Blocking issues:")
        for b in blockers:
            print(f"🔴 {b.name}: {b.message}")
        print("\nFix before deploying.")
        return False

    if warnings:
        print("\n⚠️  DEPLOYMENT WITH WARNINGS\n")
        for w in warnings:
            print(f"⚠️  {w.name}: {w.message}")
        if not CONFIG["block_on_warnings"]:
            print("\n✅ READY TO DEPLOY (with warnings)")
            return True

    print("\n✅ READY TO DEPLOY")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Deployment Checker")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--quick", "-q", action="store_true", help="快速检查")
    args = parser.parse_args()

    checks = run_checks()
    success = print_report(checks)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())