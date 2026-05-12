---
name: self-healing-executor
description: |
  🔧 Self-Healing 执行器技能 - 自动诊断错误、选择修复策略、执行修复、验证结果

  触发场景：
  - 测试失败时自动触发
  - 说"自动修复"
  - 说"运行 Self-Healing"
  - 说"诊断并修复"
  - 自动化管道中的错误恢复

  功能：
  - 错误分类（8 类错误）
  - 策略选择（7 种修复策略）
  - 修复执行
  - 结果验证
  - 闭环报告

version: 2.0.0
author: mcp agent
trigger_patterns:
  - "自动修复"
  - "运行 Self-Healing"
  - "诊断并修复"
  - "self-healing"
tags: [self-healing, error-recovery, automation, fix-strategy]
---

# 🔧 Self-Healing Executor v2.0

> 自动驾驶核心技能：诊断 → 修复 → 验证
>
> **版本变更**：v2.0 整合评审结论，新增修复域判定、三态验证、分层金字塔、LLM 降级路径、安全关键操作限制

## 工作流程

```
[错误发生]
    ↓
┌─────────────────────────────────────┐
│ 0. 修复域判定（前置）                │
│    元素级 → 进入修复循环             │
│    业务级 → 降级报告（停止）         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 1. Error Classification             │
│    8 类错误分类                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Strategy Selection               │
│    7 种修复策略                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Fix Execution                   │
│    应用选中的修复策略                 │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. Verification                    │
│    分层验证金字塔（L1-L4）           │
│    三态结果：CONFIRMED/UNCERTAIN/FAILED │
└─────────────────────────────────────┘
    ↓
[结果报告]
```

## 0. 修复域判定（前置）

修复域判定是 Self-Healing 的第一道关卡，决定是否进入自动修复循环。

### 修复域分类

| 域 | 故障类型 | 处理策略 |
|---|---|---|
| **元素级** | 定位器失效、UI 属性变化、可见性状态、元素遮挡 | 自动修复（最多 3 轮 L1-L3 降级） |
| **业务级** | 逻辑错误、数据不一致、权限问题、状态机异常 | 降级报告（记录日志、通知人工、停止自动修复） |

### 判定逻辑

```python
async def run(self, workflow, initial_error, context):
    # 前置判定：修复域分类
    classified = self.error_analyzer.classify(str(initial_error), context)

    # 业务级故障 → 直接降级报告
    if self._is_business_level_failure(classified):
        logger.warning("Business-level failure, skipping auto-fix")
        return LoopResult(
            success=False,
            attempts=0,
            error="Business-level failure requires manual intervention",
            state=LoopState.FAILED,
        )

    # 元素级故障 → 进入修复循环
    return await self._run_fix_loop(...)
```

### 安全关键操作限制

以下操作属于 **Critical 级别**，必须用户二次确认，拒绝自动修复：

| 操作 | 危险等级 | 处理方式 |
|------|---------|---------|
| `grant_permission` | 🔴 Critical | 必须用户显式授权，禁止自动修复 |
| `revoke_permission` | 🔴 Critical | 必须用户显式授权，禁止自动修复 |
| `delete_data` | 🔴 Critical | 必须用户显式授权，禁止自动修复 |

```python
CRITICAL_OPERATIONS = {
    "grant_permission",
    "revoke_permission",
    "delete_data",
}

def is_critical_operation(self, operation_name: str) -> bool:
    return operation_name in self.CRITICAL_OPERATIONS
```

## 错误分类（8 类）

| Category | 说明 | 示例 | 修复域 |
|----------|------|------|-------|
| `LocatorNotFound` | 元素定位失败 | `NoSuchElementException` | 元素级 |
| `Timeout` | 操作超时 | `Timeout waiting for element` | 元素级 |
| `AssertionFailed` | 断言失败 | `Expected true but was false` | 业务级 |
| `NetworkError` | 网络错误 | `Connection refused` | 元素级 |
| `PermissionDenied` | 权限错误 | `Access denied to X` | 业务级 |
| `InvalidState` | 状态错误 | `Element not clickable` | 元素级 |
| `CrashDetected` | 应用崩溃 | `App crashed` | 元素级 |
| `UnknownError` | 未知错误 | fallback | 需判定 |

## 三态 VerificationResult

验证结果从二态（bool）升级为三态，提供更精细的状态表达：

```python
class VerificationStatus(Enum):
    CONFIRMED = "confirmed"    # 验证通过，元素存在且可用
    UNCERTAIN = "uncertain"    # 验证不确定，需降级到更高成本验证
    FAILED = "failed"          # 验证明确失败

@dataclass
class VerificationResult:
    status: VerificationStatus  # 三态替代 passed: bool
    message: str
    element_exists: bool = False
    element_visible: bool = False
    suggestion: str | None = None  # 修复建议
```

| 状态 | 含义 | 下一步行动 |
|------|------|-----------|
| `CONFIRMED` | 验证通过，修复成功 | 退出修复循环 |
| `UNCERTAIN` | 验证不确定，降级到更高层级验证 | 进入 L3/L4 验证 |
| `FAILED` | 验证失败，修复无效 | 尝试下一个策略 |

## 分层验证金字塔

验证采用分层策略，从低成本到高成本逐层验证：

```
         ┌─────────────┐
         │   L4: 业务流验证   │  高成本 → 仅在 L3 失败时触发
         │  (异步，完整路径)   │
         └──────┬──────┘
                │ UNCERTAIN
         ┌──────▼──────┐
         │   L3: 轻量功能验证  │  中成本 → 元素可操作性验证
         │  (异步，交互测试)   │
         └──────┬──────┘
                │ UNCERTAIN
         ┌──────▼──────┐
         │   L2: 元素可操作性  │  低成本 → enabled/visible/interactive
         │  (同步，<100ms)    │
         └──────┬──────┘
                │ UNCERTAIN
         ┌──────▼──────┐
         │   L1: 元素存在性   │  最低成本 → 查询元素是否存在
         │  (同步，<100ms)    │
         └─────────────┘
```

| 层级 | 验证内容 | 执行方式 | 超时 | 适用场景 |
|------|---------|---------|------|---------|
| **L1** | 元素存在于 UI 树中 | 同步 | < 100ms | 快速确认元素存在 |
| **L2** | 元素 enabled/visible/interactive | 同步 | < 100ms | 确认元素可交互 |
| **L3** | 轻量功能验证（tap/swipe 交互） | 异步 | 5s | 验证元素真实可用 |
| **L4** | 完整业务流验证（多步骤操作） | 异步 | 30s | L3 失败后的最终确认 |

### 验证递归保护

防止验证递归导致的无限循环：

```python
@dataclass
class LoopConfig:
    max_retries: int = 3
    max_verification_depth: int = 5  # 验证嵌套深度保护
    verify_timeout: int = 60

async def _verify_with_depth_protection(self, locator, context):
    self._verify_depth += 1
    if self._verify_depth > self.config.max_verification_depth:
        logger.error("Verification depth exceeded, stopping recursive loop")
        return VerificationResult(
            status=VerificationStatus.FAILED,
            message="Max verification depth exceeded"
        )
    try:
        result = await self.fix_verifier.verify(locator, context)
        return result
    finally:
        self._verify_depth -= 1
```

## 修复策略（7 层）

| Level | 策略 | 适用场景 | 超时 | 降级路径 |
|-------|------|---------|------|---------|
| L1 | QuickRetry | 瞬时错误 | 1s | → L2 |
| L2 | AlternativeLocator | 定位符问题 | 3s | → L3 |
| L3 | ScrollRetry | 需滚动 | 5s | → L4 |
| L4 | AISuggestion | 复杂场景 | 10s | → L5 |
| L5 | VisualMatch | 视觉相似 | 15s | → L6 |
| L6 | SemanticFallback | 语义推断 | 20s | → L7 |
| L7 | ReportFailure | 所有失败 | - | 终止 |

## LLM 失败降级路径

当 AI 修复策略（CODE_VALIDATE）失败时，自动降级到确定性策略：

```python
class StrategyFailureType(Enum):
    NOT_APPLICABLE = "not_applicable"
    EXECUTION_FAILED = "execution_failed"
    LLM_UNAVAILABLE = "llm_unavailable"

def apply_strategy(self, strategy, context) -> FixResult:
    try:
        result = strategy.action(context)
        return FixResult(success=True, strategy_name=strategy.name, ...)
    except Exception as e:
        # AI 修复失败 → 回退到确定性修复
        if strategy.strategy_type == FixStrategyType.CODE_VALIDATE:
            return self._fallback_deterministic_fix(strategy, context)
        return FixResult(success=False, strategy_name=strategy.name, ...)

def _fallback_deterministic_fix(self, strategy, context):
    """降级到确定性修复策略：CODE_VALIDATE → APP_RESTART"""
    restart_strategy = FixStrategy(
        name="fallback_restart",
        strategy_type=FixStrategyType.APP_RESTART,
        action=self._restart_app,
    )
    try:
        restart_strategy.action(context)
        return FixResult(success=True, strategy_name="fallback_restart", ...)
    except:
        return FixResult(
            success=False,
            strategy_name="fallback_restart",
            failure_type=StrategyFailureType.EXECUTION_FAILED
        )
```

**降级路径**：
```
CODE_VALIDATE (LLM) 失败
    ↓
APP_RESTART (确定性)
    ↓
若再失败 → ReportFailure (L7)
```

## 使用方式

### 手动触发

```bash
python3 .claude/skills/self-healing-executor/scripts/heal.py --error "Element not found" --context "accessibility_id:submit"
```

### Python API

```python
from self_healing_executor import SelfHealingExecutor

executor = SelfHealingExecutor()
result = executor.heal(
    error="Element not found",
    context={"locator": "accessibility_id:submit"}
)

# v2.0 结果检查方式
if result.verification_result.status == VerificationStatus.CONFIRMED:
    print(f"Fixed with {result.strategy_used}")
elif result.verification_result.status == VerificationStatus.UNCERTAIN:
    print("Verification uncertain, needs higher-level validation")
else:
    print(f"Failed after {result.attempts} attempts")
```

### 自动化集成

```python
# 在测试失败时自动调用
try:
    element.click()
except Exception as e:
    executor = SelfHealingExecutor()
    result = executor.heal(str(e), get_context())

    # 安全关键操作检查
    if result.requires_user_confirmation:
        # 暂停等待用户授权
        wait_for_user_confirmation(result.critical_operations)
```

## 输出示例

### 成功修复（CONFIRMED）

```
🔧 Self-Healing Executing...
├── 🔍 Domain Check: Element-level failure (proceed to fix)
├── 📊 Classify: LocatorNotFound (confidence: 95%)
├── 🎯 Strategy: L2 Alternative Locator
├── ⚡ Attempt 1: accessibility_id:submit → accessibility_id:submit_button
│   └── ✅ L1 Verify: CONFIRMED (element exists)
│   └── ✅ L2 Verify: CONFIRMED (element interactive)
└── ✅ Fixed in 2.1s

Strategy: L2 Alternative Locator
Attempts: 1
Duration: 2.1s
Verification: CONFIRMED
```

### 降级报告（业务级故障）

```
🔧 Self-Healing Executing...
├── 🔍 Domain Check: Business-level failure (escalate)
├── 📊 Classify: PermissionDenied (confidence: 88%)
└── ⚠️  Stopping auto-fix: business-level failure

Needs human review: permission denied
Reason: Security-critical operation requires user confirmation
```

### LLM 降级

```
🔧 Self-Healing Executing...
├── 📊 Classify: AssertionFailed (confidence: 75%)
├── 🎯 Strategy: L4 AI Suggestion (CODE_VALIDATE)
├── ⚡ LLM validate... FAILED (LLM unavailable)
├── 🔄 Fallback: APP_RESTART
├── ⚡ Restart app... SUCCESS
└── ✅ Fixed via fallback strategy

Strategy: fallback_restart (APP_RESTART)
Attempts: 2
Duration: 8.3s
```

## 配置

在 `scripts/config.py` 中修改：

```python
CONFIG = {
    "max_attempts": 3,
    "max_verification_depth": 5,        # v2.0 新增
    "verify_timeout": 60,
    "escalate_on_fail": True,
    "use_ai_for_complex": True,
    "verify_after_fix": True,
    "notify_on_escalation": True,

    # v2.0 新增：安全关键操作
    "critical_operations": [
        "grant_permission",
        "revoke_permission",
        "delete_data",
    ],
    "require_user_confirmation": True,
}
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 修复成功（CONFIRMED） |
| 1 | 修复失败，需人工（FAILED after all strategies） |
| 2 | 配置错误 |
| 3 | 超时 |
| 4 | 业务级故障降级（无需修复） |

## 与其他技能的协作

```
test-runner 失败 → self-healing-executor → 成功 → 继续
                            ↓
                         失败 → notification-hub → 通知

self-healing-executor 失败 → notification-hub → 统一通知
```

```
project-health-monitor 检测到熔断器 OPEN → self-healing-executor 尝试恢复
```

## 评审结论来源

本技能文档 v2.0 整合自 Agent Council 评审结论：
- **评审文件**: `.claude/skills/agent-council/history/self_healing_review.md`
- **参与 Agent**: Software Architect, Security Engineer, Code Reviewer
- **评审日期**: 2026/05/11

### 核心改进点

| 改进项 | 来源 | 优先级 |
|--------|------|--------|
| 修复域判定前置 | Software Architect | P0 |
| 三态 VerificationResult | Code Reviewer | P0 |
| 分层验证金字塔 | Software Architect | P0 |
| LLM 失败降级路径 | Code Reviewer | P0 |
| 安全关键操作限制 | Security Engineer | P0 |
| 验证递归保护 | Code Reviewer | P1 |
| 审计日志机制（HMAC-SHA256 防篡改） | Security Engineer | P0 |

## 审计日志机制

Self-Healing 执行过程全程审计记录，采用防篡改设计确保日志完整性。

### 日志结构

```python
@dataclass
class AuditLogEntry:
    timestamp: str              # ISO 8601 格式
    event_type: str             # FIX_ATTEMPT / VERIFICATION / DOMAIN_CHECK
    level: str                  # P0 / P1 / P2
    operation: str              # 操作名称
    status: str                 # SUCCESS / FAILURE / UNCERTAIN
    details: dict               # 详细信息
    hmac_signature: str          # HMAC-SHA256 防篡改签名
```

### HMAC-SHA256 防篡改

每条日志包含基于内容计算的 HMAC 签名，检测任何篡改行为：

```python
import hmac
import hashlib

class AuditLogger:
    def __init__(self, secret_key: str):
        self._secret = secret_key.encode()

    def _sign(self, entry: AuditLogEntry) -> str:
        """计算 HMAC-SHA256 签名"""
        message = f"{entry.timestamp}:{entry.event_type}:{entry.operation}:{entry.status}"
        return hmac.new(self._secret, message.encode(), hashlib.sha256).hexdigest()

    def verify(self, entry: AuditLogEntry) -> bool:
        """验证日志完整性"""
        expected = self._sign(entry)
        return hmac.compare_digest(entry.hmac_signature, expected)
```

### P0/P1 异常检测

| 级别 | 触发条件 | 处理方式 |
|------|---------|---------|
| **P0** | 安全关键操作被拒绝、修复循环超过最大次数、业务级故障降级 | 立即通知 + 记录严重事件 |
| **P1** | LLM 降级发生、验证深度超过阈值、连续 3 次修复失败 | 记录警告 + 定时汇总 |

```python
class P0Alert(Exception):
    """P0 级别异常：需要立即处理"""
    pass

class P1Warning(Exception):
    """P1 级别异常：需要关注但不紧急"""
    pass

def _classify_alert_level(event_type: str, attempts: int, domain: str) -> str:
    if domain == "business" or attempts > 5:
        return "P0"
    elif event_type in ("LLM_FALLBACK", "VERIFICATION_DEPTH_EXCEEDED"):
        return "P1"
    return "P2"
```

### 审计日志输出示例

```
2026-05-12T10:30:45.123Z | FIX_ATTEMPT | P1 | ios_button_click | SUCCESS
  └── strategy: L2 Alternative Locator
  └── locator: accessibility_id:submit → accessibility_id:submit_btn
  └── verification: CONFIRMED
  └── signature: a1b2c3d4e5f6...

2026-05-12T10:30:48.456Z | DOMAIN_CHECK | P0 | grant_permission | FAILURE
  └── reason: Critical operation requires user confirmation
  └── action: Skip auto-fix, escalate to human
  └── signature: f6e5d4c3b2a1...
```

### 日志存储

审计日志存储在 `.claude/logs/self-healing-audit.log`，按日期轮转：

```
.claude/logs/
└── self-healing-audit.log
    ├── 2026-05-10.log
    ├── 2026-05-11.log
    └── 2026-05-12.log
```

### 与 notification-hub 集成

P0 级别事件自动触发通知：

```python
# P0 事件立即通知
if alert_level == "P0":
    notification_hub.send_urgent(
        title="Self-Healing P0 Alert",
        message=f"Critical failure in {operation}: {reason}",
        channel="security"
    )

# P1 事件批量汇总通知
elif alert_level == "P1":
    pending_warnings.append({
        "operation": operation,
        "reason": reason,
        "timestamp": timestamp
    })
```

### 审计日志完整性验证

定期验证历史日志是否被篡改：

```python
def verify_audit_log(log_file: Path) -> list[VerificationResult]:
    """验证日志文件完整性，返回被篡改的条目"""
    tampered = []
    with open(log_file) as f:
        for line in f:
            entry = parse_log_line(line)
            if not audit_logger.verify(entry):
                tampered.append(entry)
    return tampered
```