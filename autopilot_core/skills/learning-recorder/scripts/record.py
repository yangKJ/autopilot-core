#!/usr/bin/env python3
"""
学习记录器脚本 v2.0
集成 self-improving-agent 标准格式
"""

import subprocess
import sys
import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional
import random
import string

# ============ 配置 ============
PROJECT_ROOT = Path.cwd()
LEARNINGS_DIR = PROJECT_ROOT / ".learnings"

# ============ 辅助函数 ============

def ensure_learnings_dir():
    """确保学习目录存在"""
    LEARNINGS_DIR.mkdir(exist_ok=True)


def get_timestamp() -> str:
    """获取 ISO-8601 时间戳"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


def get_date_id() -> str:
    """获取日期 ID 如 20260511"""
    return datetime.now().strftime("%Y%m%d")


def generate_id(prefix: str) -> str:
    """生成标准 ID 如 ERR-20260511-A3F"""
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{prefix}-{get_date_id()}-{chars}"


def extract_keywords(text: str) -> list:
    """提取关键词"""
    words = re.findall(r'\b[a-z_]+[a-z0-9_]+\b', text.lower())
    stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'for', 'of', 'and', 'or', 'in', 'on', 'at', 'by'}
    keywords = [w for w in words if w not in stopwords and len(w) > 2][:5]
    return keywords


def check_duplicate(problem: str, filename: str) -> Optional[str]:
    """检查是否已存在相似条目，返回相似条目的 ID"""
    filepath = LEARNINGS_DIR / filename
    if not filepath.exists():
        return None

    with open(filepath) as f:
        content = f.read()

    # 简单匹配：检查问题前100字符是否已存在
    problem_prefix = problem[:100].lower()
    matches = re.findall(r'## \[(\w+-\w+-\w+)\]', content)
    for match_id in matches:
        if problem_prefix in content.lower():
            return match_id
    return None


# ============ 格式模板 (self-improving-agent 标准) ============

def format_error_entry(entry: dict) -> str:
    """错误条目标准格式"""
    return f"""
## [{entry['id']}] {entry['title']}

**Logged**: {entry['logged']}
**Priority**: {entry.get('priority', 'high')}
**Status**: {entry.get('status', 'pending')}
**Area**: {entry.get('area', 'backend')}

### Summary
{entry['problem']}

### Error
```
{entry.get('error', entry['problem'])}
```

### Context
- Command/operation attempted: {entry.get('context', 'N/A')}
- Input or parameters used: {entry.get('params', 'N/A')}

### Suggested Fix
{entry.get('solution', 'Investigate and resolve')}

### Metadata
- Reproducible: {entry.get('reproducible', 'unknown')}
- Related Files: {entry.get('related_files', 'N/A')}
- See Also: {entry.get('see_also', 'N/A')}

---
"""


def format_learning_entry(entry: dict) -> str:
    """学习条目标准格式"""
    category = entry.get('category', 'correction')
    return f"""
## [{entry['id']}] {entry['title']}

**Logged**: {entry['logged']}
**Priority**: {entry.get('priority', 'medium')}
**Status**: {entry.get('status', 'pending')}
**Area**: {entry.get('area', 'backend')}

### Summary
{entry['problem']}

### Details
{entry.get('details', entry['problem'])}

### Suggested Action
{entry.get('solution', 'N/A')}

### Metadata
- Source: {entry.get('source', 'conversation')}
- Related Files: {entry.get('related_files', 'N/A')}
- Tags: {entry.get('tags', ', '.join(entry.get('keywords', [])))}
- See Also: {entry.get('see_also', 'N/A')}
- Pattern-Key: {entry.get('pattern_key', '')}
- Recurrence-Count: {entry.get('recurrence_count', '1')}
- First-Seen: {entry.get('first_seen', entry['logged'][:10])}
- Last-Seen: {entry.get('last_seen', entry['logged'][:10])}

---
"""


def format_feature_entry(entry: dict) -> str:
    """功能请求条目标准格式"""
    return f"""
## [{entry['id']}] {entry['title']}

**Logged**: {entry['logged']}
**Priority**: {entry.get('priority', 'medium')}
**Status**: {entry.get('status', 'pending')}
**Area**: {entry.get('area', 'frontend')}

### Requested Capability
{entry['problem']}

### User Context
{entry.get('context', 'N/A')}

### Complexity Estimate
{entry.get('complexity', 'unknown')}

### Suggested Implementation
{entry.get('solution', 'N/A')}

### Metadata
- Frequency: {entry.get('frequency', 'first_time')}
- Related Features: {entry.get('related_features', 'N/A')}

---
"""


# ============ 记录函数 ============

def record_error(
    problem: str,
    error: str = None,
    solution: str = None,
    context: str = None,
    params: str = None,
    related_files: str = None,
    priority: str = "high",
    area: str = "backend"
) -> tuple:
    """记录错误"""
    ensure_learnings_dir()

    entry = {
        "id": generate_id("ERR"),
        "title": problem[:60],
        "logged": get_timestamp(),
        "priority": priority,
        "status": "pending",
        "area": area,
        "problem": problem,
        "error": error or problem,
        "solution": solution or "Investigate and resolve",
        "context": context or "N/A",
        "params": params or "N/A",
        "related_files": related_files or "N/A",
        "reproducible": "unknown"
    }

    # 检查重复
    duplicate = check_duplicate(problem, "ERRORS.md")
    if duplicate:
        return False, f"Duplicate of {duplicate}"

    filepath = LEARNINGS_DIR / "ERRORS.md"
    with open(filepath, "a") as f:
        f.write(format_error_entry(entry))

    return True, entry["id"]


def record_learning(
    problem: str,
    solution: str = None,
    details: str = None,
    category: str = "correction",
    reason: str = None,
    source: str = "conversation",
    related_files: str = None,
    keywords: list = None,
    pattern_key: str = None,
    priority: str = "medium",
    area: str = "backend"
) -> tuple:
    """记录学习（纠正或最佳实践）"""
    ensure_learnings_dir()

    entry = {
        "id": generate_id("LRN"),
        "title": problem[:60],
        "logged": get_timestamp(),
        "priority": priority,
        "status": "pending",
        "area": area,
        "category": category,
        "problem": problem,
        "details": details or problem,
        "solution": solution or "N/A",
        "source": source,
        "related_files": related_files or "N/A",
        "keywords": keywords or extract_keywords(problem),
        "pattern_key": pattern_key or ""
    }

    filename = "LEARNINGS.md"
    duplicate = check_duplicate(problem, filename)
    if duplicate:
        return False, f"Duplicate of {duplicate}"

    filepath = LEARNINGS_DIR / filename
    with open(filepath, "a") as f:
        f.write(format_learning_entry(entry))

    return True, entry["id"]


def record_correction(original: str, corrected: str, reason: str, **kwargs) -> tuple:
    """记录纠正"""
    problem = f"原方案: {original}"
    details = f"原方案: {original}\n纠正为: {corrected}"
    return record_learning(
        problem=problem,
        solution=corrected,
        details=details,
        category="correction",
        reason=reason,
        source="user_feedback",
        **kwargs
    )


def record_best_practice(content: str, practice: str, reason: str = None, **kwargs) -> tuple:
    """记录最佳实践"""
    return record_learning(
        problem=content,
        solution=practice,
        details=f"内容: {content}\n最佳实践: {practice}",
        category="best_practice",
        source="best_practice",
        **kwargs
    )


def record_feature_request(request: str, context: str = None, complexity: str = "unknown", **kwargs) -> tuple:
    """记录功能请求"""
    ensure_learnings_dir()

    entry = {
        "id": generate_id("FEAT"),
        "title": request[:60],
        "logged": get_timestamp(),
        "priority": "medium",
        "status": "pending",
        "area": "frontend",
        "problem": request,
        "context": context or "N/A",
        "complexity": complexity,
        "frequency": "first_time"
    }

    duplicate = check_duplicate(request, "FEATURE_REQUESTS.md")
    if duplicate:
        return False, f"Duplicate of {duplicate}"

    filepath = LEARNINGS_DIR / "FEATURE_REQUESTS.md"
    with open(filepath, "a") as f:
        f.write(format_feature_entry(entry))

    return True, entry["id"]


# ============ 查询函数 ============

def query_learnings(keyword: str) -> list:
    """查询学习记录"""
    ensure_learnings_dir()

    results = []
    for md_file in LEARNINGS_DIR.glob("*.md"):
        if md_file.name.startswith("."):
            continue
        with open(md_file) as f:
            content = f.read()
        if keyword.lower() in content.lower():
            # 提取匹配的 ID
            ids = re.findall(r'## \[(\w+-\w+-\w+)\]', content)
            results.append({
                "file": md_file.name,
                "keyword": keyword,
                "ids": ids
            })

    return results


def list_learnings() -> dict:
    """列出所有学习记录"""
    ensure_learnings_dir()

    summary = {}
    for md_file in LEARNINGS_DIR.glob("*.md"):
        if md_file.name.startswith("."):
            continue
        with open(md_file) as f:
            lines = f.readlines()
        count = sum(1 for line in lines if line.startswith("## ["))
        if count > 0:
            summary[md_file.name] = count

    return summary


def get_pending_count() -> int:
    """获取待处理学习数量"""
    ensure_learnings_dir()

    total = 0
    for md_file in LEARNINGS_DIR.glob("*.md"):
        with open(md_file) as f:
            content = f.read()
        total += content.count("**Status**: pending")

    return total


# ============ CLI 入口 ============

def main():
    parser = argparse.ArgumentParser(description="Learning Recorder v2.0 (self-improving-agent format)")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # record 命令
    record_parser = subparsers.add_parser("record", help="记录学习")
    record_parser.add_argument("--type", "-t", required=True,
                            choices=["error", "correction", "best-practice", "feature"],
                            help="学习类型")
    record_parser.add_argument("--content", "-c", required=True, help="问题/内容")
    record_parser.add_argument("--solution", "-s", help="解决方案")
    record_parser.add_argument("--reason", "-r", help="原因/说明")
    record_parser.add_argument("--context", help="上下文")
    record_parser.add_argument("--priority", "-p", default="medium", choices=["low", "medium", "high", "critical"])
    record_parser.add_argument("--area", "-a", default="backend", choices=["frontend", "backend", "infra", "tests", "docs", "config"])

    # query 命令
    query_parser = subparsers.add_parser("query", help="查询学习")
    query_parser.add_argument("--keyword", "-k", required=True, help="搜索关键词")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有学习记录")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看学习状态")

    args = parser.parse_args()

    if args.command == "record":
        recorded = False
        msg = ""

        if args.type == "error":
            recorded, msg = record_error(
                problem=args.content,
                solution=args.solution,
                context=args.context,
                priority=args.priority,
                area=args.area
            )
        elif args.type == "correction":
            if not args.solution or not args.reason:
                print("Error: --solution and --reason required for correction type")
                return 1
            recorded, msg = record_correction(
                original=args.content,
                corrected=args.solution,
                reason=args.reason,
                priority=args.priority,
                area=args.area
            )
        elif args.type == "best-practice":
            if not args.solution:
                print("Error: --solution required for best-practice type")
                return 1
            recorded, msg = record_best_practice(
                content=args.content,
                practice=args.solution,
                reason=args.reason,
                priority=args.priority,
                area=args.area
            )
        elif args.type == "feature":
            recorded, msg = record_feature_request(
                request=args.content,
                context=args.context,
                priority=args.priority,
                area=args.area
            )

        if recorded:
            print(f"📝 Learning Recorded")
            print(f"   ID: {msg}")
            print(f"   Type: {args.type}")
            print(f"   Priority: {args.priority}")
            return 0
        else:
            print(f"⚠️  {msg}")
            return 0

    elif args.command == "query":
        results = query_learnings(args.keyword)
        if results:
            print(f"🔍 Found {len(results)} files matching '{args.keyword}':")
            for r in results:
                print(f"  {r['file']}: {len(r['ids'])} entries")
        else:
            print(f"No matches for '{args.keyword}'")
        return 0

    elif args.command == "list":
        summary = list_learnings()
        if not summary:
            print("📚 No learning records yet")
            return 0
        print("📚 Learning Records:")
        for filename, count in summary.items():
            print(f"  {filename}: {count} entries")
        return 0

    elif args.command == "status":
        pending = get_pending_count()
        summary = list_learnings()
        total = sum(summary.values())
        print("📊 Learning Status:")
        print(f"  Total entries: {total}")
        print(f"  Pending: {pending}")
        if summary:
            for filename, count in summary.items():
                print(f"  {filename}: {count}")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())