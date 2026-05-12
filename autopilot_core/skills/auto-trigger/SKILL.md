---
name: auto-trigger
description: |
  ⚡ 自动触发器技能 - 基于文件变更类型自动判定并触发对应技能

  触发场景：
  - 说"设置自动触发"
  - 说"配置 auto-trigger"
  - 说"当文件变更时自动执行"
  - git hook 或 CI/CD 中调用

  功能：
  - 文件变更检测
  - 变更类型判定（.py, .md, .json 等）
  - 技能选择和触发
  - 结果汇总报告

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "设置自动触发"
  - "配置 auto-trigger"
  - "当文件变更时"
  - "file change trigger"
tags: [auto-trigger, event-driven, automation, file-change]
---

# ⚡ Auto Trigger v1.0

> 文件变更自动触发对应技能，真正的"自动驾驶"

## 工作原理

```
[文件变更]
    ↓
[变更类型判定]
    ↓
┌─────────────────────────────────────────┐
│ .py 文件     → test-runner + commit-validator │
│ .md 文件     → self-improving-agent (如有更新)  │
│ .json 文件   → deployment-checker              │
│ server.py   → project-health-monitor         │
│ tests/      → test-runner                   │
│ .git/hooks  → commit-validator              │
└─────────────────────────────────────────┘
    ↓
[触发技能] → [结果汇总] → [通知]
```

## 触发规则

| 文件模式 | 触发技能 | 说明 |
|---------|---------|------|
| `*.py` | test-runner + commit-validator | Python 文件变更 |
| `tests/**/*.py` | test-runner | 测试文件变更 |
| `*.md` | learning-recorder (检查) | 文档变更 |
| `server.py` | project-health-monitor | 核心文件变更 |
| `template_engine/**` | commit-validator | 模板引擎变更 |
| `ai_self_healing/**` | self-healing-executor | 自愈模块变更 |
| `.json` | deployment-checker | 配置变更 |
| `.git/hooks/*` | commit-validator | Hook 配置变更 |
| `**/test_*.py` | test-runner | 测试文件变更 |

## 使用方式

### Git Hook 集成

```bash
# 在 .git/hooks/post-commit 中添加
python3 .claude/skills/auto-trigger/scripts/trigger.py --changed-files "$(git diff --name-only HEAD~1)"

# 或在 .git/hooks/pre-push 中
python3 .claude/skills/auto-trigger/scripts/trigger.py --changed-files "$(git diff --name-only origin/$(git branch --show-current))"
```

### CI/CD 集成

```yaml
# .github/workflows/auto-trigger.yml
- name: Auto Trigger
  run: |
    python3 .claude/skills/auto-trigger/scripts/trigger.py \
      --changed-files "${{ github.changed-files }}"
```

### CLI

```bash
# 触发所有技能
python3 .claude/skills/auto-trigger/scripts/trigger.py

# 触发特定文件
python3 .claude/skills/auto-trigger/scripts/trigger.py --files tests/test_a.py server.py

# 增量触发（仅变更文件）
python3 .claude/skills/auto-trigger/scripts/trigger.py --diff
```

## 输出示例

```
⚡ Auto Trigger
==================================================

Changed files:
- server.py
- tests/test_a.py

Triggering skills:
🚀 test-runner → tests/test_a.py
🚀 commit-validator → lint + test
🚀 project-health-monitor → full check

Results:
✅ test-runner: 10 passed (5s)
✅ commit-validator: PASS
✅ project-health-monitor: OK

Summary: 3/3 skills passed
Duration: 120s
==================================================
```

## 配置

```python
# scripts/config.py
CONFIG = {
    "parallel": True,              # 并行执行技能
    "max_parallel_skills": 3,    # 最多并行 3 个技能
    "fail_fast": False,           # 遇错即停
    "notify_on_complete": True,   # 完成时通知
    "rules": {
        "*.py": ["test-runner", "commit-validator"],
        "tests/**/*.py": ["test-runner"],
        "server.py": ["project-health-monitor"],
        "ai_self_healing/**": ["self-healing-executor"],
        "*.json": ["deployment-checker"],
    }
}
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 全部技能通过 |
| 1 | 有技能失败 |
| 2 | 配置错误 |
| 3 | 超时 |