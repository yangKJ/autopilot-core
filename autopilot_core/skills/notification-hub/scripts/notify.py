#!/usr/bin/env python3
"""
统一通知中心脚本
聚合、去重、统一发送通知
"""

import subprocess
import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass, field

# ============ 配置 ============

CONFIG_FILE = Path.home() / ".claude" / "notification-hub" / "config.json"
CACHE_FILE = Path.home() / ".claude" / "notification-hub" / "cache.json"

CONFIG = {
    "enabled": True,
    "dedup_window_minutes": 5,
    "aggregate_window_minutes": 15,
    "channels": ["osascript"],
    "mute_until": None,
    "rules": {
        "success": {"notify": False},
        "failure": {"notify": True, "immediate": True},
        "warning": {"notify": True, "aggregate": True},
        "info": {"notify": True, "aggregate": True},
    }
}

# ============ 数据结构 ============

@dataclass
class Notification:
    message: str
    level: str  # success, failure, warning, info
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    deduplication_key: str = ""


# ============ 核心逻辑 ============

def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_cache() -> dict:
    """加载缓存"""
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {"notifications": [], "muted_until": None}


def save_cache(cache: dict):
    """保存缓存"""
    ensure_config_dir()
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def is_muted() -> bool:
    """检查是否在免打扰模式"""
    cache = load_cache()
    muted_until = cache.get("muted_until")
    if not muted_until:
        return False
    muted_time = datetime.fromisoformat(muted_until)
    return datetime.now() < muted_time


def should_notify(level: str) -> bool:
    """根据规则判断是否应该通知"""
    rules = CONFIG.get("rules", {})
    rule = rules.get(level, {})
    if not rule.get("notify", True):
        return False
    return True


def deduplicate(notifications: List[Notification]) -> List[Notification]:
    """去重：同类型消息在时间窗口内只保留一条"""
    deduped = []
    dedup_keys = set()

    now = datetime.now()
    window = timedelta(minutes=CONFIG["dedup_window_minutes"])

    for notif in notifications:
        key = notif.deduplication_key or f"{notif.level}:{notif.source}:{notif.message[:50]}"
        if key in dedup_keys:
            continue

        # 检查时间窗口
        notif_time = datetime.fromisoformat(notif.timestamp)
        if now - notif_time > window:
            continue

        dedup_keys.add(key)
        deduped.append(notif)

    return deduped


def aggregate(notifications: List[Notification]) -> str:
    """聚合多条消息为一条摘要"""
    if len(notifications) == 1:
        return notifications[0].message

    lines = [f"{i+1}. [{n.source}] {n.message}" for i, n in enumerate(notifications)]
    return f"Aggregated {len(notifications)} notifications:\n" + "\n".join(lines[:5])


def send_osascript(title: str, message: str):
    """发送 macOS 系统通知"""
    if sys.platform == "darwin":
        # macOS 通知有长度限制，截断超长消息
        if len(message) > 100:
            message = message[:100] + "..."
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ])


def send_slack(webhook_url: str, title: str, message: str, level: str = "info"):
    """发送 Slack 通知"""
    if not webhook_url:
        return

    # 根据级别选择 emoji
    emoji = {"failure": "🔴", "warning": "🟡", "success": "🟢", "info": "🔵"}.get(level, "🔵")

    payload = {
        "text": f"{emoji} {title}",
        "attachments": [{
            "color": {"failure": "danger", "warning": "warning", "success": "good", "info": "#439FE0"}.get(level, "#439FE0"),
            "fields": [
                {"title": "Message", "value": message[:500], "short": False},
                {"title": "Source", "value": "iOS Automation MCP", "short": True},
                {"title": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "short": True}
            ]
        }]
    }

    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print(f"📱 Slack notification sent: {title}")
    except Exception as e:
        print(f"⚠️ Slack notification failed: {e}")


def send_email(smtp_server: str, smtp_port: int, sender: str, recipients: List[str],
               subject: str, body: str, username: str = None, password: str = None):
    """发送邮件通知"""
    if not smtp_server or not recipients:
        return

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if username and password:
                server.starttls()
                server.login(username, password)
            server.send_message(msg)

        print(f"📧 Email notification sent: {subject}")
    except Exception as e:
        print(f"⚠️ Email notification failed: {e}")


def send_silent(message: str):
    """静默发送（仅打印）"""
    print(f"🔔 [SILENT] {message}")


def send_notification(title: str, message: str, level: str = "info", source: str = "unknown"):
    """发送通知"""
    # 检查是否禁用
    if not CONFIG["enabled"]:
        return

    # 检查免打扰
    if is_muted() and level != "failure":
        print(f"🔕 [MUTED] {message}")
        return

    # 检查规则
    if not should_notify(level):
        print(f"🔕 [SILENT] {message} (level={level})")
        return

    # 去重检查
    cache = load_cache()
    dedup_key = f"{level}:{source}:{message[:50]}"
    last_sent = cache.get("last_sent", {})
    last_time_str = last_sent.get(dedup_key)

    if last_time_str:
        last_time = datetime.fromisoformat(last_time_str)
        if datetime.now() - last_time < timedelta(minutes=CONFIG["dedup_window_minutes"]):
            print(f"🔕 [DEDUP] {message[:50]}... (suppressed)")
            return

    # 发送 - 根据配置的渠道
    channels = CONFIG.get("channels", ["osascript"])

    if "osascript" in channels:
        send_osascript(title, message)

    if "slack" in channels:
        slack_config = CONFIG.get("slack", {})
        webhook_url = slack_config.get("webhook_url")
        if webhook_url:
            send_slack(webhook_url, title, message, level)

    if "email" in channels:
        email_config = CONFIG.get("email", {})
        smtp_server = email_config.get("smtp_server")
        if smtp_server:
            send_email(
                smtp_server=smtp_server,
                smtp_port=email_config.get("smtp_port", 587),
                sender=email_config.get("sender", "noreply@mcp.local"),
                recipients=email_config.get("recipients", []),
                subject=title,
                body=message,
                username=email_config.get("username"),
                password=email_config.get("password")
            )

    if not any(c in channels for c in ["osascript", "slack", "email"]):
        send_silent(message)

    # 更新缓存
    last_sent[dedup_key] = datetime.now().isoformat()
    cache["last_sent"] = last_sent
    save_cache(cache)


def send_notification_batch(notifications: List[Notification]):
    """批量发送通知（先去重再聚合）"""
    if not notifications:
        return

    # 去重
    deduped = deduplicate(notifications)

    if not deduped:
        print("🔕 [ALL DEDUPED] No notifications to send")
        return

    # 根据级别判断
    levels = set(n.level for n in deduped)
    if "failure" in levels:
        level = "failure"
        title = "❌ Failure Alert"
    elif "warning" in levels:
        level = "warning"
        title = "⚠️  Warning"
    else:
        level = "info"
        title = "🔔 Notification"

    # 聚合消息
    message = aggregate(deduped)
    send_notification(title, message, level, "batch")


# ============ CLI 入口 ============

def main():
    parser = argparse.ArgumentParser(description="Notification Hub")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # send 命令
    send_parser = subparsers.add_parser("send", help="发送通知")
    send_parser.add_argument("--message", "-m", required=True, help="通知消息")
    send_parser.add_argument("--level", "-l", default="info", choices=["success", "failure", "warning", "info"])
    send_parser.add_argument("--source", "-s", default="unknown", help="来源")
    send_parser.add_argument("--title", "-t", default="Notification", help="标题")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量发送")
    batch_parser.add_argument("--file", "-f", help="JSON 文件")

    # history 命令
    history_parser = subparsers.add_parser("history", help="查看历史")

    # mute 命令
    mute_parser = subparsers.add_parser("mute", help="设置免打扰")
    mute_parser.add_argument("--duration", "-d", type=int, help="静默时长（分钟）")
    mute_parser.add_argument("--until", "-u", help="静默到指定时间")

    # unmute 命令
    unmute_parser = subparsers.add_parser("unmute", help="取消免打扰")

    args = parser.parse_args()

    if args.command == "send":
        send_notification(args.title, args.message, args.level, args.source)
        print(f"✅ Sent: [{args.level}] {args.message[:80]}")
        return 0

    elif args.command == "batch":
        if args.file:
            with open(args.file) as f:
                data = json.load(f)
            notifications = [Notification(**n) for n in data]
        else:
            notifications = []
        send_notification_batch(notifications)
        return 0

    elif args.command == "history":
        cache = load_cache()
        last_sent = cache.get("last_sent", {})
        if last_sent:
            print("📋 Recent notifications:")
            for key, ts in list(last_sent.items())[-10:]:
                print(f"  {ts[:19]}: {key}")
        else:
            print("📋 No notification history")
        return 0

    elif args.command == "mute":
        cache = load_cache()
        if args.duration:
            muted_until = (datetime.now() + timedelta(minutes=args.duration)).isoformat()
        elif args.until:
            # 解析时间 "18:00" -> 今天的 18:00
            now = datetime.now()
            hour, minute = map(int, args.until.split(":"))
            muted_until = now.replace(hour=hour, minute=minute, second=0).isoformat()
            if muted_until < now.isoformat():
                muted_until = (datetime.now() + timedelta(days=1)).replace(hour=hour, minute=minute).isoformat()
        else:
            print("Error: --duration or --until required")
            return 1

        cache["muted_until"] = muted_until
        save_cache(cache)
        print(f"🔇 Muted until {muted_until}")
        return 0

    elif args.command == "unmute":
        cache = load_cache()
        cache["muted_until"] = None
        save_cache(cache)
        print("🔊 Unmuted")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    import argparse
    sys.exit(main())