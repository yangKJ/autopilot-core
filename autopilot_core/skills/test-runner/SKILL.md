---
name: test-runner
description: |
  🧪 测试运行器技能 - 执行测试套件、解析结果、格式化报告

  触发场景：
  - 说"运行测试"
  - 说"执行测试套件"
  - 说"跑一下测试"
  - 说"测试通过了吗"
  - cron 定时测试验证
  - pre-commit hook 调用

  功能：
  - 运行 pytest（可配置范围）
  - 解析测试结果（passed/failed/skipped）
  - 格式化输出（简洁/详细）
  - 失败时发送系统通知
  - 支持并行执行

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "运行测试"
  - "执行测试套件"
  - "跑一下测试"
  - "测试通过了吗"
  - "运行 pytest"
tags: [testing, pytest, test-runner, automation]
---

# 🧪 Test Runner v1.0

> 通用测试执行技能，适用于任何 Python 项目

## 使用方式

### 手动触发

```bash
# 快速模式（默认）
python .claude/skills/test-runner/scripts/run_tests.py

# 完整模式（所有测试）
python .claude/skills/test-runner/scripts/run_tests.py --mode full

# 指定文件/目录
python .claude/skills/test-runner/scripts/run_tests.py --path tests/ai_self_healing/

# 并行执行
python .claude/skills/test-runner/scripts/run_tests.py --parallel 4

# 带覆盖率
python .claude/skills/test-runner/scripts/run_tests.py --coverage
```

### 程序化调用

```python
from test_runner import TestRunner

runner = TestRunner()
result = runner.run()
if result.passed:
    print("All tests passed!")
else:
    print(f"Failed: {result.failures}")
```

## 配置

在 `scripts/config.py` 中修改默认配置：

```python
DEFAULT_CONFIG = {
    "mode": "quick",           # quick / full
    "parallel": 1,             # 并行进程数
    "coverage": False,         # 是否生成覆盖率
    "notify_on_failure": True, # 失败是否通知
    "timeout": 300,            # 超时秒数
    "fail_fast": False,        # 遇错即停
}
```

## 输出格式

### 简洁模式（默认）

```
✅ 1071 passed (1m40s)
```

### 详细模式（--verbose）

```
============================= test session starts ==============================
platform darwin -- Python 3.12.0, pytest-9.0.2

tests/ai_self_healing/test_llm_interface.py::TestOllamaClient::test_generate_success PASSED
tests/ai_self_healing/test_fix_strategies.py::TestFixStrategies::test_circuit_breaker_recovery PASSED

================================ 1071 passed in 100.50s ================================
```

### 失败时

```
❌ 3 failed, 1068 passed (1m40s)

FAILED tests/test_a.py::TestA::test_one
FAILED tests/test_b.py::TestB::test_two

查看详情: python -m pytest tests/ --tb=short
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 全部通过 |
| 1 | 有测试失败 |
| 2 | 测试执行错误 |
| 3 | 超时 |

## Cron 安装

```bash
# 每小时验证测试状态（失败才通知）
(crontab -l 2>/dev/null; echo "0 * * * * cd /path/to/project && python3 .claude/skills/test-runner/scripts/run_tests.py --mode quick --notify") | crontab -
```

## Pre-commit Hook 集成

在 `.git/hooks/pre-commit` 中添加：

```bash
#!/bin/bash
python3 .claude/skills/test-runner/scripts/run_tests.py --mode quick --fail-fast
```

## 跨项目复用

复制到目标项目：

```bash
cp -r .claude/skills/test-runner /path/to/project/.claude/skills/
```

修改 `scripts/config.py` 中的项目路径即可。