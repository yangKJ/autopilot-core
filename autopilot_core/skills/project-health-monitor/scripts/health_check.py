#!/usr/bin/env python3
"""
项目健康检查脚本
通用模板，适用于任何 Python 项目
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

# ============ 配置区域 ============
# 项目根目录（默认当前目录）
PROJECT_ROOT = Path(os.getcwd())

# 健康检查配置
HEALTH_CHECKS = {
    "测试": {
        "command": "python3 -m pytest tests/ --tb=no -q 2>&1 | tail -5",
        "type": "test"
    },
    "熔断器": {
        "command": "python3 -c \"from template_engine.circuit_breaker import CircuitBreakerRegistry; print('OK')\"",
        "type": "import"
    },
    "工具注册表": {
        "command": "python -c \"from server import TOOL_CLASSES; print(len(TOOL_CLASSES))\"",
        "type": "count"
    },
    "Lint": {
        "command": "ruff check . --select E,F,W --ignore PGH,INP 2>&1 | head -5",
        "type": "lint"
    },
}

# 是否发送系统通知
NOTIFY_ON_FAILURE = True

# ============ 核心逻辑 ============

def run_cmd(cmd: str, cwd: Path = None) -> Tuple[str, int]:
    """执行命令并返回 (输出, 返回码)"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd or PROJECT_ROOT, timeout=300
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def check_tests() -> dict:
    """检查测试状态"""
    output, code = run_cmd("python3 -m pytest tests/ --tb=no -q 2>&1 | tail -20")
    return {
        "status": "pass" if code == 0 else "fail",
        "output": output[-500:] if output else "No output",
        "passed": "passed" in output.lower()
    }


def check_circuit_breakers() -> dict:
    """检查熔断器状态"""
    output, code = run_cmd("python3 -c \"from template_engine.circuit_breaker import CircuitBreakerRegistry; print('OK')\"")
    return {
        "status": "ok" if output.strip() == "OK" and code == 0 else "fail",
        "details": "CircuitBreakerRegistry available" if code == 0 else f"Error: {output[:100]}"
    }


def check_tool_registry() -> dict:
    """检查工具注册表"""
    # 检查 server.py 中 TOOL_CLASSES 定义
    output, _ = run_cmd("grep -c 'TOOL_CLASSES' server.py")
    return {
        "status": "ok" if output.strip() and int(output.strip()) > 0 else "fail",
        "tool_registry_found": output.strip() if output else "0"
    }


def check_lint() -> dict:
    """检查 lint 状态"""
    output, code = run_cmd("ruff check . --select E,F,W --ignore PGH,INP 2>&1 | head -10")
    return {
        "status": "pass" if code == 0 else "fail",
        "issues": output[:300] if output else ""
    }


def check_recent_commits() -> dict:
    """检查最近的 git 提交"""
    output, _ = run_cmd("git log --since '1 hour ago' --oneline")
    commits = [c.strip() for c in output.split('\n') if c.strip()]
    return {
        "count": len(commits),
        "commits": commits[:5]
    }


# ============ 失败原因分析 ============

import sqlite3
from datetime import datetime, timedelta

FAILURE_DB = PROJECT_ROOT / ".claude" / "skills" / ".health_failure.db"


def init_failure_db():
    """初始化失败数据库"""
    FAILURE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(FAILURE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_name TEXT,
            failure_type TEXT,
            error_message TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_name TEXT,
            status TEXT,
            duration REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def record_failure(check_name: str, failure_type: str, error_message: str):
    """记录失败到数据库"""
    try:
        conn = sqlite3.connect(str(FAILURE_DB))
        conn.execute(
            "INSERT INTO health_failures (check_name, failure_type, error_message) VALUES (?, ?, ?)",
            (check_name, failure_type, error_message)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def record_health_stats(check_name: str, status: str, duration: float):
    """记录健康检查统计"""
    try:
        conn = sqlite3.connect(str(FAILURE_DB))
        conn.execute(
            "INSERT INTO health_stats (check_name, status, duration) VALUES (?, ?, ?)",
            (check_name, status, duration)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def analyze_failures(check_name: str = None) -> dict:
    """分析失败原因"""
    init_failure_db()
    conn = sqlite3.connect(str(FAILURE_DB))
    conn.row_factory = sqlite3.Row

    # 过去24小时的失败记录
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
        return {"status": "no_recent_failures", "patterns": []}

    patterns = []
    for row in rows:
        patterns.append({
            "check": row["check_name"] if "check_name" in row.keys() else check_name,
            "failure_type": row["failure_type"],
            "count": row["count"],
            "last_seen": row["last_seen"]
        })

    return {"status": "patterns_found", "patterns": patterns, "total_failures": sum(p["count"] for p in patterns)}


def get_failure_trends(days: int = 7) -> dict:
    """获取失败趋势"""
    init_failure_db()
    conn = sqlite3.connect(str(FAILURE_DB))
    conn.row_factory = sqlite3.Row

    since = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = conn.execute(
        """SELECT DATE(timestamp) as date, check_name, COUNT(*) as failures
           FROM health_failures WHERE timestamp>=?
           GROUP BY DATE(timestamp), check_name
           ORDER BY date""",
        (since,)
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {"status": "no_data", "trend": "stable"}

    by_date = {}
    for row in rows:
        d = row["date"]
        if d not in by_date:
            by_date[d] = {"date": d, "total": 0, "checks": {}}
        by_date[d]["total"] += row["failures"]
        by_date[d]["checks"][row["check_name"]] = row["failures"]

    trend_data = sorted(by_date.values(), key=lambda x: x["date"])

    # 计算趋势
    if len(trend_data) >= 2:
        recent = sum(d["total"] for d in trend_data[-3:])
        older = sum(d["total"] for d in trend_data[:3])
        if recent < older * 0.8:
            trend = "improving"
        elif recent > older * 1.2:
            trend = "degrading"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    return {"status": "ok", "trend": trend, "data": trend_data}


def classify_failure(check_name: str, output: str, error: str = None) -> str:
    """分类失败类型"""
    msg = (output + " " + (error or "")).lower()

    # 超时
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    # 导入错误
    if "importerror" in msg or "modulenotfounderror" in msg or "no module named" in msg:
        return "import_error"
    # 语法错误
    if "syntaxerror" in msg or "indentationerror" in msg:
        return "syntax_error"
    # 测试失败
    if "failed" in msg or "error" in msg:
        return "test_failure"
    # 权限问题
    if "permission" in msg or "access denied" in msg:
        return "permission_error"
    return "unknown"


def notify(message: str, title: str = "MCP Health Alert"):
    """发送系统通知"""
    if sys.platform == "darwin":
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ])


def run_health_checks() -> Dict[str, dict]:
    """运行所有健康检查"""
    init_failure_db()
    results = {}
    import time
    for name, check_func in [
        ("测试", check_tests),
        ("熔断器", check_circuit_breakers),
        ("工具注册表", check_tool_registry),
        ("Lint", check_lint),
        ("最近提交", check_recent_commits),
    ]:
        start = time.time()
        result = check_func()
        duration = time.time() - start
        results[name] = result
        record_health_stats(name, result.get("status", "unknown"), duration)

        # 失败时记录
        if result.get("status") in ("fail", "open"):
            error_msg = result.get("output", result.get("details", ""))[:300]
            failure_type = classify_failure(name, error_msg)
            record_failure(name, failure_type, error_msg)

    return results


def print_report(checks: Dict[str, dict]) -> bool:
    """打印健康报告，返回是否有问题"""
    print(f"\n{'='*50}")
    print(f"📊 项目健康检查")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    has_issue = False

    for name, result in checks.items():
        status = result.get("status", "unknown")

        if status == "fail":
            print(f"❌ {name}: {status.upper()}")
            if "output" in result:
                print(f"   {result['output'][:200]}")
            has_issue = True
        elif status == "open":
            print(f"⚠️  {name}: {status.upper()}")
            print(f"   {result.get('details', '')[:200]}")
            has_issue = True
        elif status == "ok":
            details = result.get("details", result.get("output", ""))
            if details and details != "ok":
                print(f"✅ {name}: {details}")
            else:
                print(f"✅ {name}: OK")
        else:
            print(f"✅ {name}: OK")

    print(f"\n{'='*50}")

    if has_issue:
        print("⚠️  发现问题，需要关注\n")
        return True
    else:
        print("✅ 项目健康，一切正常\n")
        return False


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description="Health Check Tool")
    parser.add_argument("--check", "-c", help="只运行指定检查")
    parser.add_argument("--analyze", "-a", action="store_true", help="分析失败原因")
    parser.add_argument("--trends", "-t", action="store_true", help="显示趋势")
    parser.add_argument("--days", "-d", type=int, default=7, help="趋势分析天数")
    args = parser.parse_args()

    # 如果需要分析，先初始化数据库
    if args.analyze or args.trends:
        init_failure_db()

    if args.analyze:
        print("\n🔍 失败原因分析 (过去24小时):")
        analysis = analyze_failures(args.check)
        if analysis["status"] == "no_recent_failures":
            print("   没有最近失败记录")
        else:
            for p in analysis["patterns"]:
                print(f"   • {p['check']}/{p['failure_type']}: {p['count']}次 (最后: {p['last_seen'][:19]})")
        print()
        return 0

    if args.trends:
        print(f"\n📈 失败趋势 (过去{args.days}天):")
        trends = get_failure_trends(args.days)
        if trends["status"] == "no_data":
            print("   没有趋势数据")
        else:
            print(f"   趋势: {trends['trend']}")
            for d in trends.get("data", [])[-7:]:
                print(f"   • {d['date']}: {d['total']}次失败")
        print()
        return 0

    checks = run_health_checks()
    has_issue = print_report(checks)

    if has_issue and NOTIFY_ON_FAILURE:
        notify("项目健康检查发现问题，请检查日志")

    return 0 if not has_issue else 1


if __name__ == "__main__":
    exit(main())