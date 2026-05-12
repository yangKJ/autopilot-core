---
name: learning-recorder
description: |
  📝 学习记录器技能 - 自动捕获错误、纠正、最佳实践，持续进化项目知识

  触发场景：
  - 说"记录这个错误"
  - 说"记住这个教训"
  - 测试失败被修复
  - 用户纠正了错误
  - 发现更好方案
  - 任何"学到了"时刻

  功能：
  - 错误捕获 → 归类 → 存储
  - 纠正记录 → 原因分析 → 规则提取
  - 最佳实践 → 模式识别 → 复用
  - 自动提炼 → 更新到 CLAUDE.md

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "记录这个"
  - "记住这个"
  - "学习到"
  - "这次学到了"
  - "capture"
  - "learning"
tags: [learning, memory, knowledge, self-improvement, capture]
---

# 📝 Learning Recorder v1.0

> 项目自我进化的核心：把每一次错误和纠正都变成知识

## 核心概念

**学习循环**：

```
错误发生 → [学习记录器] → 捕获上下文 → 归类存储
                                        ↓
                              下次遇到类似问题
                                        ↓
                              自动应用已有知识 → 避免重复犯错
```

## 学习类型

| 类型 | 说明 | 存储位置 |
|------|------|---------|
| **ERROR** | 命令/操作失败 | `.learnings/ERRORS.md` |
| **CORRECTION** | 用户纠正 | `.learnings/LEARNINGS.md` (category: correction) |
| **BEST_PRACTICE** | 发现更好方案 | `.learnings/LEARNINGS.md` (category: best_practice) |
| **FEATURE_REQUEST** | 用户请求功能 | `.learnings/FEATURE_REQUESTS.md` |

## 学习条目结构

```markdown
## [标题]
- **日期**: 2026-05-11
- **类别**: ERROR | CORRECTION | BEST_PRACTICE
- **问题**: 描述问题
- **原因**: 分析根本原因
- **解决方案**: 修复方案
- **关键词**: 用于检索
- **应用场景**: 何时使用这个知识
```

## 使用方式

### 手动记录

```bash
# 记录错误
python3 .claude/skills/learning-recorder/scripts/record.py --type error --content "ruff check 失败: unused import" --solution "使用 ruff check --fix"

# 记录纠正
python3 .claude/skills/learning-recorder/scripts/record.py --type correction --content "用户说不要用mock测试数据库" --reason "mock和实际行为不一致"

# 记录最佳实践
python3 .claude/skills/learning-recorder/scripts/record.py --type best-practice --content "使用 contextlib 简化资源清理" --solution "with contextlib"
```

### Python API

```python
from learning_recorder import LearningRecorder

recorder = LearningRecorder()

# 记录错误
recorder.record_error(
    problem="Element not found",
    cause="定位符失效",
    solution="使用 accessibility_label"
)

# 记录纠正
recorder.record_correction(
    original="使用 mock 数据库",
    corrected="使用真实数据库测试",
    reason="mock 和实际行为不一致"
)
```

### 自动触发集成

```python
# 在 self-healing 修复成功后自动调用
result = executor.heal(error, context)
if result.success:
    recorder.record_error(
        problem=error,
        cause=result.strategy_used,
        solution=result.fix_applied
    )
```

## 输出示例

### 记录成功

```
📝 Learning Recorded
==================================================
Type: ERROR
Problem: Element not found: accessibility_id:submit
Cause: 定位符在页面变化后失效
Solution: 使用 accessibility_label 作为备用定位符
Keywords: locator, element_not_found, accessibility

Added to: .learnings/ERRORS.md
==================================================
```

### 查询学习

```bash
python3 .claude/skills/learning-recorder/scripts/query.py --keyword "locator"
```

### 知识提炼

```bash
# 找出重复出现的错误模式，提炼成规则
python3 .claude/skills/learning-recorder/scripts/synthesize.py
```

## 自动化触发

在以下情况自动记录：
1. `self-healing-executor` 修复成功 → 记录修复方案
2. 测试失败后重试成功 → 记录重试策略
3. 用户说 "no", "actually", "应该" → 记录纠正
4. 检测到重复错误 → 触发知识提炼

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 记录成功 |
| 1 | 记录失败 |
| 2 | 参数错误 |

## 文件结构

```
.learnings/
├── ERRORS.md              # 错误记录
├── LEARNINGS.md          # 学习记录（纠正 + 最佳实践）
├── FEATURE_REQUESTS.md   # 功能请求
└── PATTERNS.md          # 提炼的模式规则
```