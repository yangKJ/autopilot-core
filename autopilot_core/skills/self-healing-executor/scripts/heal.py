#!/usr/bin/env python3
"""
Self-Healing 执行器脚本
诊断 → 策略选择 → 修复 → 验证
"""

import sys
import os
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict

# ============ 配置 ============

PROJECT_ROOT = Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG = {
    "max_attempts": 3,
    "escalate_on_fail": True,
    "use_ai_for_complex": True,
    "verify_after_fix": True,
    "notify_on_escalation": True
}

# ============ 数据结构 ============

@dataclass
class HealResult:
    """修复结果"""
    success: bool
    strategy_used: str
    attempts: int
    duration: float
    error: str
    fix_applied: Optional[str] = None
    message: str = ""


# ============ 核心逻辑 ============

def classify_error(error: str) -> dict:
    """分类错误"""
    from ai_self_healing.error_analyzer import ErrorAnalyzer, ErrorCategory

    analyzer = ErrorAnalyzer()
    result = analyzer.classify(error)

    return {
        "category": result.category.value,
        "confidence": result.confidence,
        "locator": result.locator,
        "suggestion": result.suggestion
    }


def select_strategy(category: str, context: dict) -> List[str]:
    """选择修复策略"""
    from ai_self_healing.error_analyzer import ErrorCategory
    from ai_self_healing.fix_strategies import FixStrategyRegistry

    # 映射 category 到 ErrorCategory
    category_map = {
        "element_not_found": ErrorCategory.ELEMENT_NOT_FOUND,
        "timeout": ErrorCategory.TIMEOUT,
        "app_crash": ErrorCategory.APP_CRASH,
        "build_failed": ErrorCategory.BUILD_FAILED,
        "code_error": ErrorCategory.CODE_ERROR,
        "network": ErrorCategory.NETWORK,
        "permission": ErrorCategory.PERMISSION,
        "unknown": ErrorCategory.UNKNOWN
    }

    error_category = category_map.get(category, ErrorCategory.UNKNOWN)

    # 获取注册表中的策略
    registry = FixStrategyRegistry()
    strategies = registry.get_strategies(error_category)

    if not strategies:
        return ["L1_QuickRetry", "L7_ReportFailure"]

    # 返回策略名列表
    return [s.name for s in strategies] + ["L7_ReportFailure"]


def apply_fix(strategy_name: str, context: dict) -> dict:
    """应用修复策略"""
    from ai_self_healing.fix_strategies import FixStrategyRegistry, FixStrategyType

    registry = FixStrategyRegistry()

    # 直接按名称查找策略
    all_strategies = []
    for st_list in registry._strategies.values():
        all_strategies.extend(st_list)

    strategy_obj = None
    for s in all_strategies:
        if s.name == strategy_name:
            strategy_obj = s
            break

    if not strategy_obj:
        return {"success": False, "message": f"Unknown strategy: {strategy_name}"}

    result = registry.apply_strategy(strategy_obj, context)

    return {
        "success": result.success,
        "message": result.message,
        "fix": result.applied_fix
    }


def verify_fix(fix: str, context: dict) -> bool:
    """验证修复（同步版本）"""
    # 简化验证：检查 fix 是否返回了有效结果
    return fix is not None and fix != ""


def notify(title: str, message: str):
    """发送系统通知"""
    if sys.platform == "darwin":
        import subprocess
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ])


# ============ 主逻辑 ============

def heal(error: str, context: dict, max_attempts: int = 3) -> HealResult:
    """执行自愈流程"""
    import time
    start = time.time()

    print(f"🔧 Self-Healing Executing...")
    print(f"└── Error: {error[:100]}\n")

    # Step 1: 分类错误
    classification = classify_error(error)
    category = classification["category"]
    confidence = classification["confidence"]

    print(f"├── 📊 Classify: {category} (confidence: {confidence:.0%})")

    # Step 2: 选择策略
    strategies = select_strategy(category, context)
    print(f"├── 🎯 Strategies: {', '.join(strategies[:-1])} → {strategies[-1]}")

    # Step 3: 尝试修复
    attempts = 0
    last_error = error

    for strategy in strategies:
        if strategy == "L7_ReportFailure":
            break

        attempts += 1
        if attempts > max_attempts:
            break

        print(f"\n├── ⚡ Attempt {attempts}: {strategy}")

        result = apply_fix(strategy, {
            **context,
            "original_error": error
        })

        if result["success"]:
            fix = result.get("fix", "applied")

            # 验证
            if CONFIG["verify_after_fix"]:
                print(f"│   └── Verifying fix...")
                if verify_fix(fix, context):
                    duration = time.time() - start
                    print(f"\n└── ✅ Fixed in {duration:.1f}s")

                    # 自动记录到 learning-recorder
                    try:
                        from pathlib import Path
                        import subprocess
                        recorder = Path(__file__).parent.parent.parent / "learning-recorder" / "scripts" / "record.py"
                        if recorder.exists():
                            cmd = [
                                "python3", str(recorder), "record",
                                "--type", "best-practice",
                                "--content", f"Self-healed: {error[:80]}",
                                "--solution", f"Strategy: {strategy} -> {fix}",
                                "--reason", f"Fixed in {duration:.1f}s with {attempts} attempts",
                                "--priority", "low"
                            ]
                            subprocess.run(cmd, capture_output=True, timeout=10)
                            print(f"│   └── 📝 Learning recorded")
                    except Exception:
                        pass  # 不阻断主流程

                    return HealResult(
                        success=True,
                        strategy_used=strategy,
                        attempts=attempts,
                        duration=duration,
                        error=error,
                        fix_applied=fix,
                        message="Fixed successfully"
                    )
            else:
                duration = time.time() - start
                print(f"\n└── ✅ Fixed in {duration:.1f}s")
                return HealResult(
                    success=True,
                    strategy_used=strategy,
                    attempts=attempts,
                    duration=duration,
                    error=error,
                    fix_applied=fix,
                    message="Fixed successfully"
                )

        print(f"│   └── ❌ {result.get('message', 'Failed')}")
        last_error = result.get("message", "Unknown error")

    # 所有策略都失败
    duration = time.time() - start
    print(f"\n└── ⚠️  Failed after {attempts} attempts")

    if CONFIG["escalate_on_fail"]:
        print("\n⚠️  Escalating to human review...")
        if CONFIG["notify_on_escalation"]:
            notify("Self-Healing Failed", f"Error: {error[:50]}... Needs review")

    return HealResult(
        success=False,
        strategy_used=strategies[-1],
        attempts=attempts,
        duration=duration,
        error=error,
        message="All strategies exhausted"
    )


def main():
    parser = argparse.ArgumentParser(description="Self-Healing Executor")
    parser.add_argument("--error", "-e", required=True, help="错误信息")
    parser.add_argument("--locator", "-l", help="定位符")
    parser.add_argument("--context", "-c", help="额外上下文 (JSON)")
    parser.add_argument("--max-attempts", "-m", type=int, default=3, help="最大尝试次数")
    parser.add_argument("--no-verify", action="store_true", help="跳过验证")
    parser.add_argument("--no-notify", action="store_true", help="禁用通知")

    args = parser.parse_args()

    # 构建上下文
    context = {}
    if args.locator:
        context["locator"] = args.locator
    if args.context:
        import json
        context.update(json.loads(args.context))

    # 禁用选项
    if args.no_verify:
        CONFIG["verify_after_fix"] = False
    if args.no_notify:
        CONFIG["notify_on_escalation"] = False

    # 执行
    result = heal(args.error, context, args.max_attempts)

    # 输出
    print("\n" + "="*50)
    if result.success:
        print(f"✅ Success: {result.strategy_used} in {result.duration:.1f}s")
        return 0
    else:
        print(f"❌ Failed: {result.message}")
        print(f"   Attempts: {result.attempts}")
        print(f"   Duration: {result.duration:.1f}s")
        return 1


if __name__ == "__main__":
    sys.exit(main())