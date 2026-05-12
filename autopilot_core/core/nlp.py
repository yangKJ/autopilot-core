#!/usr/bin/env python3
"""
自然语言接口
将自然语言指令转换为技能链条执行
"""

import sys
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path.cwd()
SKILLS_DIR = Path(__file__).parent.parent / "skills"


# 自然语言模式 → 动作映射
INTENT_PATTERNS = {
    # 审查类
    r"(审查|检查|review).*(这个|这个PR|PR|pull request)": {
        "action": "review_pr",
        "chain": "full-auto",
        "description": "完整审查"
    },
    r"(审查|检查|review).*文件?(.+)": {
        "action": "review_files",
        "chain": "on-change",
        "description": "审查指定文件"
    },
    r"(帮我)?审查(.+)": {
        "action": "review",
        "chain": "commit-validator",
        "description": "审查"
    },

    # 执行类
    r"运行(完整)?检查": {
        "action": "full_check",
        "chain": "full-auto",
        "description": "完整检查"
    },
    r"执行(.+)链条": {
        "action": "run_chain",
        "chain": "on-change",
        "description": "执行链条"
    },
    r"跑(一下)?(测试|test)": {
        "action": "run_test",
        "chain": "test-runner",
        "description": "运行测试"
    },

    # 分析类
    r"(分析|查看)趋势": {
        "action": "analyze_trend",
        "chain": None,
        "description": "分析趋势"
    },
    r"(查看|显示|show)(仪表盘|面板|dashboard|状态)": {
        "action": "show_dashboard",
        "chain": None,
        "description": "显示监控面板"
    },
    r"(查看)?健康(状况|状态|检查)": {
        "action": "health_check",
        "chain": "hourly-check",
        "description": "健康检查"
    },

    # 部署类
    r"部署|deploy": {
        "action": "deploy",
        "chain": "on-deploy",
        "description": "部署前检查"
    },

    # 帮助
    r"帮助|help|怎么用": {
        "action": "help",
        "chain": None,
        "description": "显示帮助"
    }
}

# 文件模式提取
FILE_PATTERNS = [
    (r"server\.py", ["server.py"]),
    (r"template[_\s]engine", ["template_engine/"]),
    (r"tests?/", ["tests/"]),
    (r"ai[_\s]self[_\s]healing", ["ai_self_healing/"]),
]

# 链条映射
CHAIN_MAP = {
    "commit": "on-commit",
    "change": "on-change",
    "deploy": "on-deploy",
    "check": "hourly-check",
    "full": "full-auto",
    "auto": "full-auto",
}


def parse_intent(text: str) -> Dict:
    """解析自然语言意图"""
    text = text.lower().strip()

    for pattern, config in INTENT_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return {
                "action": config["action"],
                "chain": config["chain"],
                "description": config["description"],
                "raw_text": text
            }

    return {"action": "unknown", "chain": None, "description": "未知指令", "raw_text": text}


def extract_files(text: str) -> List[str]:
    """从文本中提取文件"""
    files = []

    for pattern, default_files in FILE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            files.extend(default_files)

    py_files = re.findall(r'[\w/]+\.py', text)
    files.extend(py_files)

    return list(set(files))


def extract_chain(text: str) -> Optional[str]:
    """从文本中提取链条名称"""
    text = text.lower()

    for keyword, chain in CHAIN_MAP.items():
        if keyword in text:
            return chain

    return None


def execute_chain(files: List[str] = None) -> Tuple[bool, str]:
    """执行自动驾驶链条"""
    try:
        from .autonomous import AutonomousScheduler

        scheduler = AutonomousScheduler(dry_run=False)
        success = scheduler.run_full_cycle(files=files if files else None)
        return success, f"执行{'成功' if success else '失败'}"

    except Exception as e:
        return False, str(e)


def show_help():
    """显示帮助"""
    return """
🚗 自动驾驶自然语言接口

使用方法:
  autopilot nlp "帮我审查这个PR"
  autopilot nlp "运行完整检查"
  autopilot nlp "查看趋势"
  autopilot nlp "检查 server.py"

支持指令:
  审查类: "帮我审查这个PR" → 运行完整审查流程
  执行类: "运行完整检查" → 执行完整自动驾驶流程
  分析类: "分析趋势" → 显示趋势分析
  部署类: "部署检查" → 运行部署前检查
"""


def show_trend():
    """显示趋势"""
    try:
        from .learning_engine import get_trend_analysis
        trend = get_trend_analysis(days=7)
        return f"""
📈 趋势分析
   趋势: {trend.get('trend', 'unknown')}
   斜率: {trend.get('slope', 0):.3f}
   预测: {trend.get('prediction', 'N/A')}
"""
    except:
        return "趋势分析不可用"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="自然语言接口")
    parser.add_argument("command", nargs="+", help="自然语言指令")
    parser.add_argument("--dry-run", "-n", action="store_true", help="只解析不执行")

    args = parser.parse_args()

    command_text = " ".join(args.command)

    print(f"\n🗣️  解析指令: \"{command_text}\"")
    print("="*60)

    intent = parse_intent(command_text)
    print(f"\n📋 意图识别:")
    print(f"   动作: {intent['action']}")
    print(f"   链条: {intent['chain'] or '无'}")
    print(f"   描述: {intent['description']}")

    files = extract_files(command_text)
    if files:
        print(f"   文件: {', '.join(files[:5])}")

    if args.dry_run:
        print(f"\n[DRY RUN] 不会实际执行")
        return 0

    action = intent["action"]

    if action == "unknown":
        print("❓ 无法理解指令")
        print(show_help())
        return 1

    elif action == "help":
        print(show_help())
        return 0

    elif action == "analyze_trend":
        print(show_trend())
        return 0

    elif action == "show_dashboard":
        from .dashboard import get_dashboard_data, format_dashboard
        data = get_dashboard_data(PROJECT_ROOT)
        print(format_dashboard(data))
        return 0

    elif action == "health_check":
        from .auto_heal import ClosedLoopHealer
        healer = ClosedLoopHealer(max_cycles=1)
        result = healer.run_healing_cycle()
        return 0 if result.healed else 1

    elif action in ("review", "review_pr", "review_files"):
        success, output = execute_chain(files if files else None)
        return 0 if success else 1

    elif action in ("full_check", "run_chain", "run_test", "deploy"):
        success, output = execute_chain(files if files else None)
        return 0 if success else 1

    else:
        print("❌ 无法确定执行动作")
        return 1


if __name__ == "__main__":
    sys.exit(main())