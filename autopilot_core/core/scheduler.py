#!/usr/bin/env python3
"""
定时任务调度器
每日自动健康检查 + 报告生成
"""

import sys
import json
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

PROJECT_ROOT = Path.cwd()
CRON_DIR = PROJECT_ROOT / ".autopilot" / ".scheduled"
STATE_FILE = CRON_DIR / "last_run.json"
REPORT_DIR = PROJECT_ROOT / ".autopilot" / "reports"


@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    command: List[str]
    schedule: str
    enabled: bool = True
    last_run: Optional[str] = None
    last_result: Optional[bool] = None


class TaskScheduler:
    """任务调度器"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.tasks: Dict[str, ScheduledTask] = {}
        self.load_state()
        self._register_default_tasks()

    def _register_default_tasks(self):
        """注册默认任务"""
        self.tasks["daily_health_check"] = ScheduledTask(
            name="每日健康检查",
            command=["python3", "-m", "autopilot_core.cli", "health"],
            schedule="0 9 * * *",
            enabled=True
        )

        self.tasks["weekly_report"] = ScheduledTask(
            name="每周报告",
            command=["python3", "-m", "autopilot_core.cli", "dashboard"],
            schedule="0 10 * * 1",
            enabled=True
        )

        self.tasks["trend_analysis"] = ScheduledTask(
            name="趋势分析",
            command=["python3", "-m", "autopilot_core.cli", "predict", "--report"],
            schedule="0 8 * * *",
            enabled=True
        )

    def load_state(self):
        """加载状态"""
        CRON_DIR.mkdir(parents=True, exist_ok=True)

        if STATE_FILE.exists():
            try:
                with open(STATE_FILE) as f:
                    state = json.load(f)
                    for task_name, task_data in state.items():
                        if task_name in self.tasks:
                            self.tasks[task_name].last_run = task_data.get("last_run")
                            self.tasks[task_name].last_result = task_data.get("last_result")
            except:
                pass

    def save_state(self):
        """保存状态"""
        state = {
            name: {"last_run": task.last_run, "last_result": task.last_result}
            for name, task in self.tasks.items()
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)

    def should_run(self, task: ScheduledTask) -> bool:
        """检查任务是否应该运行"""
        if not task.enabled:
            return False

        if not task.last_run:
            return True

        last_run = datetime.fromisoformat(task.last_run)
        now = datetime.now()

        schedule_parts = task.schedule.split()
        if len(schedule_parts) != 5:
            return False

        minute, hour, day, month, weekday = schedule_parts

        if minute != "*" and int(minute) != now.minute:
            return False

        if hour != "*" and int(hour) != now.hour:
            return False

        if weekday != "*":
            weekday_num = int(weekday)
            if weekday_num != now.weekday():
                return False

        if (now - last_run).total_seconds() < 3600:
            return False

        return True

    def run_task(self, task_name: str) -> bool:
        """运行任务"""
        if task_name not in self.tasks:
            print(f"❌ 任务不存在: {task_name}")
            return False

        task = self.tasks[task_name]
        print(f"\n🚀 运行任务: {task.name}")
        print(f"   命令: {' '.join(task.command)}")

        try:
            result = subprocess.run(
                task.command,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300
            )

            success = result.returncode == 0
            task.last_run = datetime.now().isoformat()
            task.last_result = success

            if success:
                print(f"   ✅ 任务成功")
            else:
                print(f"   ❌ 任务失败")
                if result.stderr:
                    print(f"   错误: {result.stderr[:200]}")

            self.save_state()
            return success

        except subprocess.TimeoutExpired:
            print(f"   ❌ 任务超时")
            task.last_run = datetime.now().isoformat()
            task.last_result = False
            self.save_state()
            return False

        except Exception as e:
            print(f"   ❌ 执行异常: {e}")
            task.last_run = datetime.now().isoformat()
            task.last_result = False
            self.save_state()
            return False

    def run_pending(self):
        """运行所有待执行的任务"""
        pending = [name for name, task in self.tasks.items() if self.should_run(task)]

        if not pending:
            print(f"📅 没有待执行的任务")
            return

        print(f"\n📋 待执行任务: {len(pending)}")
        for name in pending:
            self.run_task(name)

    def list_tasks(self):
        """列出所有任务"""
        print(f"\n📋 定时任务列表")
        print("="*60)

        for name, task in self.tasks.items():
            status = "✅" if task.enabled else "❌"
            last_run = task.last_run[:16] if task.last_run else "从未运行"
            last_result = "✅" if task.last_result else "❌" if task.last_result is not None else "-"

            print(f"{status} {task.name}")
            print(f"   任务名: {name}")
            print(f"   调度: {task.schedule}")
            print(f"   上次运行: {last_run} ({last_result})")
            print()

    def generate_report(self, days: int = 7) -> str:
        """生成报告"""
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        db_path = self.project_root / ".autopilot" / ".learning.db"
        if not db_path.exists():
            return "无历史数据"

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor = conn.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as runs, AVG(success) as rate
            FROM file_runs
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (since,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "无数据"

        total_runs = sum(row["runs"] for row in rows)
        avg_rate = sum(row["rate"] * row["runs"] for row in rows) / total_runs if total_runs > 0 else 0

        report = f"""
📊 自动驾驶周报 ({datetime.now().strftime('%Y-%m-%d')})
{'='*50}

📈 概述
   统计周期: 最近{days}天
   总运行次数: {total_runs}
   平均成功率: {avg_rate:.1%}

📅 每日详情
"""

        for row in rows:
            rate = row["rate"] or 0.5
            emoji = "🟢" if rate > 0.7 else "🟡" if rate > 0.4 else "🔴"
            report += f"   {emoji} {row['date']}: {row['runs']}次, {rate:.0%}成功\n"

        report_file = REPORT_DIR / f"report_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(report_file, "w") as f:
            f.write(report)

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="定时任务调度器")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    run_parser = subparsers.add_parser("run", help="运行待执行任务")
    list_parser = subparsers.add_parser("list", help="列出所有任务")
    task_parser = subparsers.add_parser("run-task", help="运行指定任务")
    task_parser.add_argument("task_name", help="任务名称")
    report_parser = subparsers.add_parser("report", help="生成报告")
    report_parser.add_argument("--days", "-d", type=int, default=7, help="报告天数")
    watch_parser = subparsers.add_parser("watch", help="持续监控模式")
    watch_parser.add_argument("--interval", type=int, default=60, help="检查间隔（秒）")

    args = parser.parse_args()

    scheduler = TaskScheduler()

    if args.command == "run" or args.command is None:
        scheduler.run_pending()

    elif args.command == "list":
        scheduler.list_tasks()

    elif args.command == "run-task":
        scheduler.run_task(args.task_name)

    elif args.command == "report":
        print(scheduler.generate_report(args.days))

    elif args.command == "watch":
        print(f"\n🔄{'='*58}")
        print(f"   定时任务监控模式")
        print(f"   检查间隔: {args.interval}秒")
        print(f"   按 Ctrl+C 停止")
        print(f"{'='*60}\n")

        while True:
            scheduler.run_pending()
            time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main())