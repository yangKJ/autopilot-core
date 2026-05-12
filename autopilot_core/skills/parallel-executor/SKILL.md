---
name: parallel-executor
description: |
  ⚡ 并行执行器 - 并行执行多个选中的技能

  触发场景：
  - 说"并行执行技能"
  - 说"同时运行多个任务"
  - skill-chain 中需要并行执行技能时
  - auto-trigger 中需要加速执行时

  功能：
  - 技能并行执行
  - 线程池管理
  - 结果汇总
  - 错误收集

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "并行执行"
  - "parallel executor"
  - "同时运行"
tags: [parallel-executor, concurrent, execution]
---

# ⚡ Parallel Executor v1.0

> 并行执行多个选中的技能，加速自动化流程

## 工作原理

```
[技能映射] → [线程池] → [并行执行] → [结果汇总]
```

## 使用方式

### CLI

```bash
# 从 skill-selector 输出执行
python3 .claude/skills/parallel-executor/scripts/run_parallel.py

# 指定输入文件
python3 .claude/skills/parallel-executor/scripts/run_parallel.py --input result.json

# 控制并行数
python3 .claude/skills/parallel-executor/scripts/run_parallel.py --max-workers 5
```

### 输入格式

```json
{
  "skills": ["test-runner", "commit-validator"],
  "skill_map": {
    "test-runner": ["tests/test_a.py"],
    "commit-validator": ["server.py"]
  }
}
```

## 输出格式

```json
{
  "results": [
    {"skill": "test-runner", "passed": true, "duration": 45.2, "error": ""},
    {"skill": "commit-validator", "passed": false, "duration": 12.3, "error": "Lint errors"}
  ],
  "summary": {
    "passed": 1,
    "total": 2,
    "all_passed": false
  }
}
```

## 在 Skill Chain 中使用

```yaml
chain:
  name: on-change
  steps:
    - name: select-skills
      skill: skill-selector

    - name: execute
      skill: parallel-executor
      if: "select-skills.success"
      config:
        max_workers: 3
```

## 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--max-workers` | 最大并行数 | 3 |
| `--input` | 输入 JSON 文件 | `.skill_selection.json` |
| `--output` | 输出 JSON 文件 | `.parallel_results.json` |

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 所有技能通过 |
| 1 | 有技能失败 |
| 2 | 配置错误 |
| 3 | 超时 |
