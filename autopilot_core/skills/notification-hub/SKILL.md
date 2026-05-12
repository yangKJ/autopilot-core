---
name: notification-hub
description: |
  🔔 统一通知中心技能 - 聚合多个技能的失败/成功通知，去重后统一发送

  触发场景：
  - 说"配置通知"
  - 说"设置通知中心"
  - 说"notification hub"
  - 任意技能需要发送通知时

  功能：
  - 接收来自各技能的通知
  - 去重（同类型消息合并）
  - 聚合（多条消息合并为一条）
  - 统一渠道发送（系统通知、Slack、邮件等）
  - 免打扰模式（静默时段）

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "配置通知"
  - "设置通知中心"
  - "notification hub"
  - "统一通知"
tags: [notification, alert, hub, deduplication]
---

# 🔔 Notification Hub v1.0

> 所有技能的通知汇聚点，去重后统一发送

## 问题背景

```
技能 A 失败 → 通知
技能 B 失败 → 通知
技能 A 又失败 → 又通知
        ↓
用户被轰炸 💥💥💥💥💥
```

## 解决方案

```
技能 A → ┐
技能 B → ├→ notification-hub → 去重/聚合 → 统一发送 → 用户
技能 C → ┘
```

## 通知类型

| 类型 | 说明 | 默认行为 |
|------|------|---------|
| `success` | 成功 | 不打扰（静默） |
| `failure` | 失败 | 立即通知 |
| `warning` | 警告 | 批量通知 |
| `info` | 信息 | 汇总通知 |

## 去重规则

```
时间窗口: 5 分钟内同类型消息视为同一条
聚合窗口: 15 分钟内合并为一条摘要
```

## 使用方式

### Python API

```python
from notification_hub import NotificationHub

hub = NotificationHub()

# 发送通知
hub.send(
    message="Test passed: 1071 tests",
    level="success",
    source="test-runner"
)

# 批量发送
hub.send_batch([
    {"message": "Lint failed", "level": "failure", "source": "commit-validator"},
    {"message": "Test passed", "level": "success", "source": "test-runner"},
])
```

### CLI

```bash
# 发送单条通知
python3 .claude/skills/notification-hub/scripts/notify.py send \
    --message "Test passed" --level success --source test-runner

# 批量发送
python3 .claude/skills/notification-hub/scripts/notify.py batch \
    --file /tmp/notifications.json

# 查看通知历史
python3 .claude/skills/notification-hub/scripts/notify.py history

# 设置免打扰
python3 .claude/skills/notification-hub/scripts/notify.py mute --duration 60
```

## 配置文件

```python
# config.py
CONFIG = {
    "enabled": True,
    "dedup_window_minutes": 5,
    "aggregate_window_minutes": 15,
    "channels": ["osascript"],  # osascript, slack, email
    "mute_until": None,  # timestamp
    "rules": {
        "success": {"notify": False},      # 静默成功
        "failure": {"notify": True, "immediate": True},  # 立即通知
        "warning": {"notify": True, "aggregate": True},   # 批量通知
    }
}
```

## 免打扰模式

```bash
# 静默 30 分钟
python3 .claude/skills/notification-hub/scripts/notify.py mute --duration 30

# 静默直到指定时间
python3 .claude/skills/notification-hub/scripts/notify.py mute --until "18:00"

# 取消静默
python3 .claude/skills/notification-hub/scripts/notify.py unmute
```

## 输出格式

### 单条通知
```
🔔 Notification
Source: test-runner
Message: Test passed: 1071 tests
Time: 2026-05-11 21:30:00
```

### 聚合通知
```
🔔 Notification (3 messages aggregated)
Source: commit-validator + test-runner + self-healing
Time: 2026-05-11 21:15:00 - 21:30:00

Messages:
1. Lint failed (3 errors)
2. Test passed (1071 tests)
3. Self-healing succeeded (locator fix)
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 发送成功 |
| 1 | 发送失败 |
| 2 | 免打扰中 |
| 3 | 配置错误 |

## 与其他技能集成

在任意技能脚本中添加：

```python
# 调用 notification-hub 发送通知
from pathlib import Path
import subprocess

hub_script = Path(__file__).parent.parent.parent / "notification-hub" / "scripts" / "notify.py"
subprocess.run([
    "python3", str(hub_script), "send",
    "--message", "Error: element not found",
    "--level", "failure",
    "--source", "self-healing-executor"
])
```