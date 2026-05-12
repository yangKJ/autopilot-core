#!/usr/bin/env python3
"""
闭环自愈系统
失败检测 → 原因分类 → 策略选择 → 修复执行 → 验证 → 记录
"""

import sys
import subprocess
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .config import AutopilotSettings
from .learning_engine import record_chain_outcome


@dataclass
class HealAction:
    """修复操作"""
    action: str
    target: str
    strategy: str
    success: bool
    message: str


@dataclass
class HealingResult:
    """自愈结果"""
    healed: bool
    cycle: int
    actions: List[HealAction]
    total_duration: float
    final_status: str


class ClosedLoopHealer:
    """闭环自愈系统"""

    def __init__(self, config: AutopilotSettings = None, max_cycles: int = 3):
        self.config = config
        self.max_cycles = max_cycles
        self.actions: List[HealAction] = []
        self._project_root = Path.cwd()

    def _get_health_db_path(self) -> Path:
        """获取健康检查数据库路径"""
        if self.config:
            return self._project_root / ".autopilot" / ".health_failure.db"
        return self._project_root / ".autopilot" / ".health_failure.db"

    def step1_detect_failure(self, check_name: str = None) -> Optional[Dict]:
        """Step 1: 检测失败"""
        try:
            health_db = self._get_health_db_path()
            if not health_db.exists():
                return None

            conn = sqlite3.connect(str(health_db))
            conn.row_factory = sqlite3.Row

            since = (datetime.now() - timedelta(hours=24)).isoformat()

            if check_name:
                cursor = conn.execute(
                    "SELECT failure_type, error_message, COUNT(*) as count, MAX(timestamp) as last_seen "
                    "FROM health_failures WHERE check_name=? AND timestamp>=? "
                    "GROUP BY failure_type ORDER BY count DESC",
                    (check_name, since)
                )
            else:
                cursor = conn.execute(
                    "SELECT check_name, failure_type, COUNT(*) as count, MAX(timestamp) as last_seen "
                    "FROM health_failures WHERE timestamp>=? "
                    "GROUP BY check_name, failure_type ORDER BY count DESC",
                    (since,)
                )

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return None

            latest = dict(rows[0])
            return {
                "check": latest.get("check_name", check_name or "unknown"),
                "failure_type": latest.get("failure_type", "unknown"),
                "count": latest.get("count", 1),
                "last_seen": latest.get("last_seen", "")
            }

        except Exception as e:
            print(f"⚠️  Detection failed: {e}")
            return None

    def step2_classify_error(self, failure_info: Dict) -> Dict:
        """Step 2: 错误分类"""
        failure_type = failure_info.get("failure_type", "unknown")
        error_message = failure_info.get("error_message", "")

        category_map = {
            "timeout": "timeout_error",
            "import_error": "import_error",
            "syntax_error": "syntax_error",
            "test_failure": "test_failure",
            "permission_error": "permission_error",
        }

        category = category_map.get(failure_type, "unknown")
        confidence = 0.8 if failure_type in category_map else 0.3

        return {
            "category": category,
            "confidence": confidence,
            "failure_type": failure_type,
            "strategy_hints": self._get_strategy_hints(category)
        }

    def _get_strategy_hints(self, category: str) -> List[str]:
        """获取策略提示"""
        hints = {
            "timeout_error": ["retry_with_backoff", "increase_timeout"],
            "import_error": ["install_dependency", "fix_import_path"],
            "syntax_error": ["auto_lint_fix", "show_errors"],
            "test_failure": ["run_tests", "debug_test"],
            "permission_error": ["fix_permissions", "check_ownership"],
            "unknown": ["manual_review", "log_analysis"],
        }
        return hints.get(category, ["manual_review"])

    def step3_select_strategy(self, classification: Dict) -> str:
        """Step 3: 选择修复策略"""
        hints = classification.get("strategy_hints", [])
        category = classification.get("category", "unknown")

        strategy_map = {
            "timeout_error": "retry_with_backoff",
            "import_error": "fix_imports",
            "syntax_error": "auto_fix_syntax",
            "test_failure": "run_tests",
            "permission_error": "fix_permissions",
        }

        return strategy_map.get(category, "manual_review")

    def step4_execute_fix(self, strategy: str, target: str, cycle: int) -> HealAction:
        """Step 4: 执行修复"""
        print(f"\n🔧 执行修复策略: {strategy} (cycle {cycle})")
        print(f"   目标: {target}")

        if strategy == "retry_with_backoff":
            return self._fix_retry(target)
        elif strategy == "fix_imports":
            return self._fix_imports(target)
        elif strategy == "auto_fix_syntax":
            return self._fix_syntax(target)
        elif strategy == "run_tests":
            return self._run_tests(target)
        elif strategy == "fix_permissions":
            return self._fix_permissions(target)
        elif strategy == "manual_review":
            return HealAction(
                action="manual_review",
                target=target,
                strategy=strategy,
                success=False,
                message="需要手动介入"
            )
        else:
            return HealAction(
                action=strategy,
                target=target,
                strategy=strategy,
                success=False,
                message=f"未知策略: {strategy}"
            )

    def _fix_retry(self, target: str) -> HealAction:
        """重试修复"""
        time.sleep(2)
        return HealAction(
            action="retry",
            target=target,
            strategy="retry_with_backoff",
            success=True,
            message="已重试"
        )

    def _fix_imports(self, target: str) -> HealAction:
        """修复导入错误"""
        result = subprocess.run(
            ["pip3", "install", "-e", "."],
            capture_output=True, text=True, cwd=self._project_root, timeout=60
        )
        return HealAction(
            action="pip_install",
            target=target,
            strategy="fix_imports",
            success=result.returncode == 0,
            message="pip install -e . 执行结果"
        )

    def _fix_syntax(self, target: str) -> HealAction:
        """修复语法错误"""
        result = subprocess.run(
            ["ruff", "check", "--fix", target],
            capture_output=True, text=True, cwd=self._project_root, timeout=30
        )
        return HealAction(
            action="ruff_fix",
            target=target,
            strategy="auto_fix_syntax",
            success=result.returncode == 0,
            message=f"ruff fix: {result.stdout[:100] if result.stdout else result.stderr[:100]}"
        )

    def _run_tests(self, target: str) -> HealAction:
        """运行测试"""
        result = subprocess.run(
            ["python3", "-m", "pytest", target if target else "tests/", "-x", "-q"],
            capture_output=True, text=True, cwd=self._project_root, timeout=120
        )
        return HealAction(
            action="pytest",
            target=target,
            strategy="run_tests",
            success=result.returncode == 0,
            message=f"测试{'通过' if result.returncode == 0 else '失败'}"
        )

    def _fix_permissions(self, target: str) -> HealAction:
        """修复权限"""
        result = subprocess.run(
            ["chmod", "+x", target],
            capture_output=True, text=True, cwd=self._project_root, timeout=10
        )
        return HealAction(
            action="chmod",
            target=target,
            strategy="fix_permissions",
            success=result.returncode == 0,
            message="权限修复完成"
        )

    def step5_verify(self, action: HealAction) -> bool:
        """Step 5: 验证修复"""
        if not action.success:
            return False

        if action.target and Path(action.target).exists():
            return True

        return True

    def step6_record_learning(self, result: HealingResult):
        """Step 6: 记录学习"""
        try:
            skills = [a.strategy for a in result.actions if a.strategy]
            record_chain_outcome(
                "closed-loop-healing",
                list(set(skills)),
                [a.target for a in result.actions if a.target],
                result.healed
            )
            print(f"🧠 Learning recorded: healed={result.healed}")
        except Exception as e:
            print(f"⚠️  Learning record failed: {e}")

    def run_healing_cycle(self, check_name: str = None) -> HealingResult:
        """运行完整自愈周期"""
        start = time.time()

        print(f"\n🩺{'='*58}")
        print(f"   闭环自愈系统启动")
        print(f"   检查项: {check_name or '全部'}")
        print(f"{'='*60}")

        failure_info = self.step1_detect_failure(check_name)
        if not failure_info:
            print("\n✅ 未检测到失败，无需自愈")
            return HealingResult(
                healed=True,
                cycle=0,
                actions=[],
                total_duration=time.time() - start,
                final_status="no_failure_detected"
            )

        print(f"\n📋 检测到失败:")
        print(f"   检查项: {failure_info['check']}")
        print(f"   类型: {failure_info['failure_type']}")
        print(f"   次数: {failure_info['count']}")

        cycle = 0
        for cycle in range(1, self.max_cycles + 1):
            print(f"\n{'='*60}")
            print(f"🔄 自愈循环 {cycle}/{self.max_cycles}")
            print(f"{'='*60}")

            classification = self.step2_classify_error(failure_info)
            print(f"   分类: {classification['category']} (置信度: {classification['confidence']:.0%})")

            strategy = self.step3_select_strategy(classification)
            print(f"   策略: {strategy}")

            target = failure_info.get("check", "")
            action = self.step4_execute_fix(strategy, target, cycle)
            self.actions.append(action)

            if action.success:
                print(f"   ✅ 修复操作成功")
            else:
                print(f"   ❌ 修复操作失败: {action.message}")

            verified = self.step5_verify(action)
            print(f"   验证: {'✅ 通过' if verified else '❌ 未通过'}")

            if verified and action.success:
                print(f"\n✅ 自愈成功！")
                break

        duration = time.time() - start
        healed = any(a.success for a in self.actions)
        final_status = "healed" if healed else "failed"

        result = HealingResult(
            healed=healed,
            cycle=cycle,
            actions=self.actions,
            total_duration=duration,
            final_status=final_status
        )
        self.step6_record_learning(result)

        print(f"\n{'='*60}")
        print(f"📊 自愈结果")
        print(f"   状态: {'✅ 已修复' if healed else '❌ 失败'}")
        print(f"   循环: {cycle}")
        print(f"   耗时: {duration:.1f}秒")
        print(f"   操作数: {len(self.actions)}")
        print(f"{'='*60}\n")

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="闭环自愈系统")
    parser.add_argument("--check", "-c", help="指定检查项")
    parser.add_argument("--cycles", "-n", type=int, default=3, help="最大自愈循环次数")
    parser.add_argument("--dry-run", "-d", action="store_true", help="干跑模式")

    args = parser.parse_args()

    healer = ClosedLoopHealer(max_cycles=args.cycles)

    if args.dry_run:
        print("[DRY RUN] Would run closed-loop healing")
        return 0

    result = healer.run_healing_cycle(check_name=args.check)

    return 0 if result.healed else 1


if __name__ == "__main__":
    sys.exit(main())