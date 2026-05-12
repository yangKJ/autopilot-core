---
name: skill-chain
description: |
  🔗 技能编排技能 - 声明式定义技能执行链条，实现复杂自动化流程

  触发场景：
  - 说"设置技能链条"
  - 说"配置 chain"
  - 说"创建工作流"
  - CI/CD 或复杂自动化流程中

  功能：
  - 声明式链条定义（YAML/JSON）
  - 条件执行（if/then/else）
  - 并行/串行执行
  - 错误处理和升级
  - 结果传递

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "设置技能链条"
  - "配置 chain"
  - "创建工作流"
  - "skill chain"
  - "技能编排"
tags: [skill-chain, orchestration, workflow, automation]
---

# 🔗 Skill Chain v1.0

> 声明式技能编排，实现复杂自动化流程

## 核心概念

```
Chain = 技能的有序组合 + 条件逻辑 + 错误处理
```

## 声明式配置示例

```yaml
# .claude/skills/skill-chain/chains/on-commit.yaml
chain:
  name: on-commit
  description: "Git commit 时的完整检查流程"

  steps:
    - name: lint
      skill: commit-validator
      config:
        mode: quick

    - name: test
      skill: test-runner
      config:
        mode: quick

    - name: self-heal
      skill: self-healing-executor
      if: "test.failed"
      config:
        max_attempts: 3

    - name: record
      skill: learning-recorder
      if: "self-heal.success"
      config:
        type: best-practice
```

## 预定义链条

| 链条 | 触发 | 说明 |
|------|------|------|
| `on-commit` | git commit | lint → test → self-heal → record |
| `on-change` | 文件变更 | 检测 → 触发对应技能 |
| `on-deploy` | 部署前 | dependency → env → security → test → deploy |
| `hourly-check` | cron | health → self-heal → notify |

## 使用方式

### CLI

```bash
# 运行预定义链条
python3 .claude/skills/skill-chain/scripts/run.py on-commit
python3 .claude/skills/skill-chain/scripts/run.py on-change --files server.py
python3 .claude/skills/skill-chain/scripts/run.py on-deploy

# 运行自定义链条
python3 .claude/skills/skill-chain/scripts/run.py --config /path/to/chain.yaml

# 列出所有链条
python3 .claude/skills/skill-chain/scripts/run.py list
```

### Python API

```python
from skill_chain import ChainRunner

runner = ChainRunner()
result = runner.run("on-commit")

if result.success:
    print("Chain completed successfully")
else:
    print(f"Chain failed at step: {result.failed_step}")
```

## 输出示例

```
🔗 Running chain: on-commit
==================================================

Step 1/4: lint
🚀 commit-validator
├── ❌ Lint: FAIL (3 errors)

Step 1 failed, checking conditions...
Condition: lint.failed = true → skip to self-heal
Step 2/4: self-heal
🚀 self-healing-executor
├── ✅ Fixed in 2.1s
Step 3/4: record
🚀 learning-recorder
├── 📝 Learning recorded

Step 4/4: test (retry)
🚀 test-runner
├── ✅ PASS (1071 tests)

==================================================
✅ Chain completed (3/4 steps executed)
Duration: 125s
```

## 条件表达式

| 表达式 | 说明 | 示例 |
|--------|------|------|
| `step.failed` | 上一步失败 | `if: "lint.failed"` |
| `step.success` | 上一步成功 | `if: "test.success"` |
| `result.code == 0` | 返回码判断 | `if: "result.code == 0"` |
| `output contains "error"` | 输出匹配 | `if: "output contains 'error'"` |

## 错误处理

```yaml
chain:
  name: robust-chain
  on_error: continue  # 继续执行还是中断

  steps:
    - name: risky-step
      skill: deployment-checker
      on_error: continue  # 失败后继续

    - name: cleanup
      skill: learning-recorder
      on_error: halt      # 失败后停止
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 链条执行成功 |
| 1 | 链条执行失败 |
| 2 | 配置错误 |
| 3 | 超时 |