#!/usr/bin/env python3
"""
状态趋势分析器
分析 .skills-state/ 中的历史数据，提供趋势和告警
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# ============ 配置 ============

PROJECT_ROOT = Path.cwd()
STATE_DIR = PROJECT_ROOT / ".skills-state"

# 告警阈值
THRESHOLDS = {
    "failure_rate_warning": 0.3,      # 30% 失败率告警
    "failure_rate_critical": 0.5,      # 50% 失败率严重告警
    "avg_duration_warning": 120,      # 平均执行时间超过2分钟告警
    "consecutive_failures_critical": 3, # 连续失败3次严重告警
}


@dataclass
class TrendReport:
    chain_name: str
    total_runs: int
    success_rate: float
    avg_duration: float
    trend: str  # "improving", "stable", "degrading"
    recent_failures: int
    consecutive_failures: int
    alerts: List[str]
    recommendations: List[str]


def load_history(chain_name: str, limit: int = 10) -> List[Dict]:
    """加载历史数据"""
    history_file = STATE_DIR / f"{chain_name}_history.json"
    if not history_file.exists():
        return []

    with open(history_file) as f:
        return json.load(f)


def analyze_trend(history: List[Dict]) -> str:
    """分析趋势"""
    if len(history) < 3:
        return "insufficient_data"

    # 比较前半和后半的成功率
    mid = len(history) // 2
    recent = history[:mid]  # 更近的数据
    older = history[mid:]    # 更早的数据

    recent_success = sum(1 for h in recent if h.get("success")) / len(recent) if recent else 0
    older_success = sum(1 for h in older if h.get("success")) / len(older) if older else 0

    diff = recent_success - older_success

    if diff > 0.1:
        return "improving"
    elif diff < -0.1:
        return "degrading"
    else:
        return "stable"


def analyze_chain(chain_name: str) -> TrendReport:
    """分析单个链条的趋势"""
    history = load_history(chain_name)

    if not history:
        return TrendReport(
            chain_name=chain_name,
            total_runs=0,
            success_rate=0.0,
            avg_duration=0.0,
            trend="no_data",
            recent_failures=0,
            consecutive_failures=0,
            alerts=["No historical data available"],
            recommendations=["Run the chain at least once to collect data"]
        )

    # 基本统计
    total_runs = len(history)
    successes = sum(1 for h in history if h.get("success"))
    success_rate = successes / total_runs if total_runs > 0 else 0

    durations = [h.get("duration", 0) for h in history if h.get("duration")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # 趋势
    trend = analyze_trend(history)

    # 最近的失败次数
    recent_failures = sum(1 for h in history[:3] if not h.get("success"))

    # 连续失败次数
    consecutive_failures = 0
    for h in history:
        if h.get("success"):
            break
        consecutive_failures += 1

    # 生成告警
    alerts = []
    recommendations = []

    if success_rate < (1 - THRESHOLDS["failure_rate_critical"]):
        alerts.append(f"🔴 CRITICAL: Success rate is only {success_rate:.0%} ({THRESHOLDS['failure_rate_critical']*100:.0f}% threshold)")
        recommendations.append("Investigate recent failures immediately")
    elif success_rate < (1 - THRESHOLDS["failure_rate_warning"]):
        alerts.append(f"🟡 WARNING: Success rate is {success_rate:.0%} ({THRESHOLDS['failure_rate_warning']*100:.0f}% threshold)")
        recommendations.append("Review recent failures and address root causes")

    if avg_duration > THRESHOLDS["avg_duration_warning"]:
        alerts.append(f"🟡 WARNING: Average duration {avg_duration:.0f}s exceeds {THRESHOLDS['avg_duration_warning']}s threshold")
        recommendations.append("Consider optimizing slow steps or enabling parallel execution")

    if consecutive_failures >= THRESHOLDS["consecutive_failures_critical"]:
        alerts.append(f"🔴 CRITICAL: {consecutive_failures} consecutive failures")
        recommendations.append("The chain may be broken - check for code changes or dependency issues")

    if trend == "degrading":
        alerts.append("🟡 WARNING: Success rate is declining over time")
        recommendations.append("Review recent changes that may have introduced regressions")

    if trend == "improving":
        recommendations.append("✅ The chain is improving - keep monitoring")

    if not alerts:
        alerts.append("✅ All metrics are within normal ranges")

    return TrendReport(
        chain_name=chain_name,
        total_runs=total_runs,
        success_rate=success_rate,
        avg_duration=avg_duration,
        trend=trend,
        recent_failures=recent_failures,
        consecutive_failures=consecutive_failures,
        alerts=alerts,
        recommendations=recommendations
    )


def print_report(report: TrendReport):
    """打印报告"""
    print(f"\n{'='*60}")
    print(f"📊 Trend Report: {report.chain_name}")
    print(f"{'='*60}")

    print(f"\n📈 Statistics:")
    print(f"  Total runs: {report.total_runs}")
    print(f"  Success rate: {report.success_rate:.0%}")
    print(f"  Average duration: {report.avg_duration:.1f}s")
    print(f"  Trend: {report.trend}")
    print(f"  Recent failures (last 3): {report.recent_failures}")
    print(f"  Consecutive failures: {report.consecutive_failures}")

    print(f"\n🚨 Alerts:")
    for alert in report.alerts:
        print(f"  {alert}")

    print(f"\n💡 Recommendations:")
    for rec in report.recommendations:
        print(f"  • {rec}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="State Trend Analyzer")
    parser.add_argument("--chain", "-c", help="分析指定链条")
    parser.add_argument("--all", "-a", action="store_true", help="分析所有链条")
    parser.add_argument("--days", "-d", type=int, default=7, help="分析最近N天的数据")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 输出")

    args = parser.parse_args()

    if args.all or args.chain:
        chains = [args.chain] if args.chain else []
    else:
        # 默认分析所有有历史数据的链条
        chains = [
            f.stem.replace("_last", "")
            for f in STATE_DIR.glob("*_last.json")
        ]

    reports = []
    for chain in chains:
        report = analyze_chain(chain)
        reports.append(report)

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "reports": [
                {
                    "chain_name": r.chain_name,
                    "total_runs": r.total_runs,
                    "success_rate": r.success_rate,
                    "avg_duration": r.avg_duration,
                    "trend": r.trend,
                    "recent_failures": r.recent_failures,
                    "consecutive_failures": r.consecutive_failures,
                    "alerts": r.alerts,
                    "recommendations": r.recommendations
                }
                for r in reports
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        for report in reports:
            print_report(report)

    # 汇总
    if len(reports) > 1:
        total_alerts = sum(len(r.alerts) for r in reports)
        critical_alerts = sum(1 for r in reports for a in r.alerts if "CRITICAL" in a)
        print(f"\n{'='*60}")
        print(f"📊 Summary: {len(reports)} chains analyzed")
        print(f"🚨 Total alerts: {total_alerts} ({critical_alerts} critical)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
