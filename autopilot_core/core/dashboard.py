#!/usr/bin/env python3
"""
统一监控面板
实时显示自动驾驶模式的所有状态
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from .learning_engine import get_trend_analysis, predict_success_rate


@dataclass
class DashboardData:
    """仪表盘数据"""
    chain_stats: Dict
    recent_runs: List[Dict]
    health_status: Dict
    predictions: Dict
    notification_history: List[Dict]


def get_db_path(project_root: Path = None) -> Path:
    """获取数据库路径"""
    if project_root is None:
        project_root = Path.cwd()
    return project_root / ".autopilot" / ".learning.db"


def get_health_db_path(project_root: Path = None) -> Path:
    """获取健康检查数据库路径"""
    if project_root is None:
        project_root = Path.cwd()
    return project_root / ".autopilot" / ".health_failure.db"


def get_chain_stats(project_root: Path = None) -> Dict:
    """获取链条统计"""
    db_path = get_db_path(project_root)
    if not db_path.exists():
        return {"total_runs": 0, "success_rate": 0, "chains": {}}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT chain, COUNT(*) as runs,
               SUM(success) as successes,
               AVG(success) as rate
        FROM file_runs
        GROUP BY chain
    """)

    chains = {}
    total_runs = 0
    total_success = 0

    for row in cursor.fetchall():
        chain = row["chain"]
        runs = row["runs"]
        successes = row["successes"] or 0
        rate = row["rate"] or 0.5

        chains[chain] = {
            "runs": runs,
            "successes": successes,
            "failures": runs - successes,
            "success_rate": round(rate, 3)
        }
        total_runs += runs
        total_success += successes

    conn.close()

    return {
        "total_runs": total_runs,
        "total_successes": total_success,
        "total_failures": total_runs - total_success,
        "overall_rate": round(total_success / total_runs, 3) if total_runs > 0 else 0,
        "chains": chains
    }


def get_recent_runs(project_root: Path = None, limit: int = 10) -> List[Dict]:
    """获取最近运行记录"""
    db_path = get_db_path(project_root)
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    cursor = conn.execute("""
        SELECT chain, success, timestamp
        FROM file_runs
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    runs = []
    for row in cursor.fetchall():
        runs.append({
            "chain": row["chain"],
            "success": bool(row["success"]),
            "timestamp": row["timestamp"]
        })

    conn.close()
    return runs


def get_health_status(project_root: Path = None) -> Dict:
    """获取健康状态"""
    if project_root is None:
        project_root = Path.cwd()

    status = {
        "overall": "healthy",
        "checks": {},
        "recent_failures": 0
    }

    health_db = get_health_db_path(project_root)

    if health_db.exists():
        conn = sqlite3.connect(str(health_db))
        conn.row_factory = sqlite3.Row

        since = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor = conn.execute(
            "SELECT COUNT(*) as count FROM health_failures WHERE timestamp >= ?",
            (since,)
        )
        failure_count = cursor.fetchone()["count"]
        conn.close()

        if failure_count > 10:
            status["overall"] = "critical"
        elif failure_count > 0:
            status["overall"] = "warning"

        status["recent_failures"] = failure_count

    return status


def get_predictions(project_root: Path = None) -> Dict:
    """获取预测状态"""
    try:
        trend = get_trend_analysis(days=7)
        pred = predict_success_rate(days_ahead=3)

        return {
            "trend": trend.get("trend", "unknown"),
            "prediction": pred.get("prediction", 0.5),
            "confidence": pred.get("confidence", 0),
            "risk": pred.get("risk", "unknown")
        }
    except Exception as e:
        return {"trend": "unknown", "prediction": 0.5, "confidence": 0, "risk": "unknown"}


def get_notification_history(project_root: Path = None, limit: int = 5) -> List[Dict]:
    """获取通知历史"""
    if project_root is None:
        project_root = Path.cwd()

    cache_file = project_root / ".autopilot" / "notification_cache.json"

    if not cache_file.exists():
        return []

    try:
        with open(cache_file) as f:
            cache = json.load(f)

        last_sent = cache.get("last_sent", {})
        history = []

        for key, ts in list(last_sent.items())[-limit:]:
            history.append({
                "key": key[:50],
                "timestamp": ts
            })

        return history
    except:
        return []


def format_dashboard(data: DashboardData) -> str:
    """格式化仪表盘输出"""
    stats = data.chain_stats
    health = data.health_status
    pred = data.predictions

    trend_emoji = {"improving": "📈", "degrading": "📉", "stable": "➡️", "unknown": "❓"}.get(
        pred.get("trend", "unknown"), "❓"
    )
    risk_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢", "unknown": "⚪"}.get(
        pred.get("risk", "unknown"), "⚪"
    )
    health_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "❌"}.get(
        health.get("overall", "unknown"), "❓"
    )

    lines = [
        "",
        "🚗" + "="*58,
        "   自动驾驶模式 - 统一监控面板",
        "   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "="*60,
        "",
        "📊 执行统计",
        f"   总运行次数: {stats.get('total_runs', 0)}",
        f"   成功率: {stats.get('overall_rate', 0):.1%}",
        f"   失败次数: {stats.get('total_failures', 0)}",
        "",
        "📈 趋势预测",
        f"   趋势: {trend_emoji} {pred.get('trend', 'unknown')}",
        f"   预测成功率: {pred.get('prediction', 0.5):.1%}",
        f"   置信度: {pred.get('confidence', 0):.0%}",
        f"   风险等级: {risk_emoji} {pred.get('risk', 'unknown')}",
        "",
        "🏥 健康状态",
        f"   整体: {health_emoji} {health.get('overall', 'unknown')}",
        f"   过去24小时失败: {health.get('recent_failures', 0)}次",
    ]

    if data.recent_runs:
        lines.append("")
        lines.append("📋 最近运行:")
        for run in data.recent_runs[:5]:
            emoji = "✅" if run["success"] else "❌"
            ts = run["timestamp"][:16] if run["timestamp"] else ""
            lines.append(f"   {emoji} {run['chain']} - {ts}")

    if stats.get("chains"):
        lines.append("")
        lines.append("🔗 链条详情:")
        for chain, info in stats["chains"].items():
            rate = info["success_rate"]
            rate_emoji = "🟢" if rate > 0.7 else "🟡" if rate > 0.4 else "🔴"
            lines.append(f"   {rate_emoji} {chain}: {info['runs']}次, {rate:.0%}成功")

    lines.append("")
    lines.append("="*60)

    return "\n".join(lines)


def get_dashboard_data(project_root: Path = None) -> DashboardData:
    """获取仪表盘数据"""
    return DashboardData(
        chain_stats=get_chain_stats(project_root),
        recent_runs=get_recent_runs(project_root),
        health_status=get_health_status(project_root),
        predictions=get_predictions(project_root),
        notification_history=get_notification_history(project_root)
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="统一监控面板")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 输出")
    parser.add_argument("--refresh", "-r", type=int, default=0, help="自动刷新间隔（秒）")

    args = parser.parse_args()

    if args.refresh > 0:
        import time
        print("按 Ctrl+C 停止监控...")
        while True:
            print("\033[2J\033[H")
            data = get_dashboard_data()
            print(format_dashboard(data))
            time.sleep(args.refresh)
    elif args.json:
        data = get_dashboard_data()
        print(json.dumps({
            "chain_stats": data.chain_stats,
            "recent_runs": data.recent_runs,
            "health_status": data.health_status,
            "predictions": data.predictions,
            "notification_history": data.notification_history
        }, indent=2))
    else:
        data = get_dashboard_data()
        print(format_dashboard(data))

    return 0


if __name__ == "__main__":
    sys.exit(main())