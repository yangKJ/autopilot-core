#!/usr/bin/env python3
"""
持续监控模式
文件变更 → 自动驾驶调度中心
"""

import sys
import time
import json
import subprocess
import argparse
import threading
import signal
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

PROJECT_ROOT = Path.cwd()

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

WATCH_CONFIG = {
    "debounce_seconds": 10,
    "max_batch_size": 30,
    "check_interval": 2,
    "ignored_patterns": [
        ".git/*",
        "__pycache__/*",
        "*.pyc",
        ".pytest_cache/*",
        ".autopilot/*",
    ],
}


@dataclass
class FileChange:
    path: str
    timestamp: float
    operation: str


class ChangeHandler(FileSystemEventHandler):
    def __init__(self, ignored_patterns: List[str], change_queue: List[FileChange], queue_lock: threading.Lock):
        self.ignored_patterns = ignored_patterns
        self.change_queue = change_queue
        self.queue_lock = queue_lock

    def should_ignore(self, path: str) -> bool:
        import fnmatch
        rel_path = str(Path(path).relative_to(PROJECT_ROOT))
        for pattern in self.ignored_patterns:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(path, pattern):
                return True
        return False

    def on_any_event(self, event: FileSystemEvent):
        if event.is_directory:
            return
        path = event.src_path
        if self.should_ignore(path):
            return

        op = "add" if event.event_type == "created" else "delete" if event.event_type == "deleted" else "modify"

        with self.queue_lock:
            self.change_queue.append(FileChange(
                path=str(Path(path).relative_to(PROJECT_ROOT)),
                timestamp=time.time(),
                operation=op
            ))


class ContinuousMonitor:
    def __init__(self, config: Dict = None):
        self.config = config or WATCH_CONFIG
        self.running = False
        self.observer: Optional[Observer] = None
        self.change_queue: List[FileChange] = []
        self.queue_lock = threading.Lock()
        self.pending_files: Set[str] = set()
        self.last_trigger_time = 0
        self.total_triggers = 0
        self.successful_triggers = 0

    def _get_recent_changes(self) -> List[FileChange]:
        with self.queue_lock:
            since = time.time() - self.config["debounce_seconds"]
            return [c for c in self.change_queue if c.timestamp > since]

    def _should_trigger(self, files: List[str]) -> bool:
        if not files:
            return False

        time_since_last = time.time() - self.last_trigger_time
        if time_since_last < self.config["debounce_seconds"]:
            return False

        if len(files) >= self.config["max_batch_size"]:
            return True

        if len(self.pending_files) >= 3:
            return True

        return False

    def _trigger_autonomous(self, files: List[str]):
        """触发自动驾驶"""
        print(f"\n{'='*60}")
        print(f"🚗 触发自动驾驶 ({len(files)} 个文件)")
        print(f"{'='*60}")

        try:
            from .autonomous import AutonomousScheduler

            scheduler = AutonomousScheduler(dry_run=False)
            success = scheduler.run_full_cycle(files=files[:20])

            self.total_triggers += 1
            if success:
                self.successful_triggers += 1
                print(f"✅ 自动驾驶执行成功")
            else:
                print(f"❌ 自动驾驶执行失败")

        except Exception as e:
            print(f"❌ 执行异常: {e}")
            self.total_triggers += 1

    def _check_loop(self):
        """检查循环"""
        recent = self._get_recent_changes()
        file_paths = list(set(c.path for c in recent))

        if file_paths:
            for f in file_paths:
                self.pending_files.add(f)

            print(f"\n📝 检测到 {len(file_paths)} 个变更: {', '.join(file_paths[:3])}...")

            if self._should_trigger(file_paths):
                self._trigger_autonomous(list(self.pending_files))
                self.pending_files.clear()
                self.last_trigger_time = time.time()

        time.sleep(self.config["check_interval"])

    def start(self):
        """启动监控"""
        if not WATCHDOG_AVAILABLE:
            print("❌ watchdog 未安装: pip install watchdog")
            return

        self.running = True

        print(f"\n🔄{'='*58}")
        print(f"   持续监控模式启动")
        print(f"   监控目录: {PROJECT_ROOT}")
        print(f"   防抖时间: {self.config['debounce_seconds']}秒")
        print(f"   按 Ctrl+C 停止")
        print(f"{'='*60}\n")

        event_handler = ChangeHandler(
            self.config.get("ignored_patterns", WATCH_CONFIG["ignored_patterns"]),
            self.change_queue,
            self.queue_lock
        )

        self.observer = Observer()
        self.observer.schedule(event_handler, str(PROJECT_ROOT), recursive=True)
        self.observer.start()

        try:
            while self.running:
                self._check_loop()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止监控"""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()

        print(f"\n\n📊 监控统计:")
        print(f"   总触发次数: {self.total_triggers}")
        print(f"   成功次数: {self.successful_triggers}")
        print(f"   成功率: {self.successful_triggers/self.total_triggers*100:.0f}%" if self.total_triggers > 0 else "N/A")
        print(f"\n👋 监控已停止")


def main():
    parser = argparse.ArgumentParser(description="持续监控模式")
    parser.add_argument("--debounce", "-d", type=int, default=10, help="防抖时间（秒）")
    parser.add_argument("--max-batch", "-m", type=int, default=30, help="最大批量")

    args = parser.parse_args()

    config = {
        **WATCH_CONFIG,
        "debounce_seconds": args.debounce,
        "max_batch_size": args.max_batch
    }

    monitor = ContinuousMonitor(config)
    monitor.start()


if __name__ == "__main__":
    main()