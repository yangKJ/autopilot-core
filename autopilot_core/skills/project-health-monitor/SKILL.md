---
name: project-health-monitor
description: |
  🏥 项目健康监控技能 - 定时检查项目状态、自动发现问题、触发修复流程

  触发场景：
  - 说"检查项目健康"
  - 说"运行健康检查"
  - 说"监控项目状态"
  - 说"定时健康检查"
  - 说"设置每小时检查"
  - Cron 定时任务触发

  功能：
  - 运行测试套件
  - 检查熔断器状态
  - 验证工具注册表
  - 检查 lint 问题
  - 报告最近提交
  - 失败时发送系统通知

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "检查项目健康"
  - "运行健康检查"
  - "监控项目状态"
  - "定时健康检查"
  - "设置每小时检查"
tags: [health-check, monitoring, testing, circuit-breaker, lint]
---

# 🏥 Project Health Monitor v1.0

> 通用项目健康监控技能，适用于任何 Python 项目

## 核心能力

1. **测试验证** — 运行 pytest 检查测试状态
2. **熔断器检查** — 验证熔断器机制可用
3. **工具注册表** — 检查工具数量一致性
4. **Lint 检查** — 运行 ruff 检查代码规范
5. **提交追踪** — 检查最近 git 提交
6. **告警通知** — 失败时发送系统通知

## 配置

```yaml
health_checks:
  - name: "测试"
    check: test
    command: "python3 -m pytest tests/ --tb=no -q 2>&1 | tail -20"
    pass_if: "returncode == 0"

  - name: "熔断器"
    check: circuit_breaker
    command: "python3 -c 'from template_engine.circuit_breaker import CircuitBreakerRegistry; print(\"OK\")'"
    pass_if: "output contains OK"

  - name: "Lint"
    check: lint
    command: "ruff check . --select E,F,W --ignore PGH,INP"
    pass_if: "returncode == 0"
```

## 使用方式

### 手动触发

```bash
python .claude/skills/project-health-monitor/scripts/health_check.py
```

### 定时执行

设置 cron 任务每小时运行：

```bash
# 安装 cron 任务
(crontab -l 2>/dev/null; echo "0 * * * * cd /path/to/project && python .claude/skills/project-health-monitor/scripts/health_check.py") | crontab -
```

## 输出格式

```
==================================================
📊 项目健康检查
⏰ 2026-05-11 20:00:00
==================================================

✅ 测试: 1071 passed
✅ 熔断器: CircuitBreakerRegistry available
✅ 工具注册表: 96 tools
✅ Lint: OK
✅ 最近提交: 3 commits

==================================================
✅ 项目健康，一切正常
```

## 失败告警

当检查失败时，发送 macOS 系统通知：

```python
import subprocess
subprocess.run([
    "osascript", "-e",
    'display notification "项目健康检查失败" with title "MCP Health Alert"'
])
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 全部通过 |
| 1 | 有问题需要关注 |

## 自定义检查

添加自定义检查项：

```python
def check_custom() -> dict:
    """自定义检查"""
    output, code = run_cmd("your command here")
    return {
        "status": "pass" if code == 0 else "fail",
        "output": output[-500:]
    }
```

在 `checks` 字典中添加即可。

## 跨项目复用

本技能设计为通用模板，复制到任意项目后：
1. 修改 PROJECT_ROOT 路径
2. 自定义 checks 列表
3. 安装 cron 任务

无需修改核心逻辑。