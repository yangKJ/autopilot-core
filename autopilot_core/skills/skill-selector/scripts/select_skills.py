#!/usr/bin/env python3
"""
技能选择器
根据文件变更类型、内容和学习历史选择要执行的技能
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Optional

# 获取项目根目录（当前工作目录）
PROJECT_ROOT = Path.cwd()
SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"

# 技能选择规则
SKILL_RULES = {
    "*.py": ["test-runner", "commit-validator"],
    "tests/**/*.py": ["test-runner"],
    "tests/test_*.py": ["test-runner"],
    "tests/**/test_*.py": ["test-runner"],
    "server.py": ["project-health-monitor"],
    "template_engine/**": ["commit-validator"],
    "ai_self_healing/**": ["self-healing-executor"],
    "ios_automation_core/**": ["commit-validator"],
    "*.json": ["deployment-checker"],
    ".claude/skills/**": ["learning-recorder"],
    "scripts/*.py": ["commit-validator"],
    "*.md": ["learning-recorder"],
}

# 文件 -> 技能映射（优先级）
FILE_SKILL_PRIORITY = {
    "*.py": ["test-runner", "commit-validator"],
    "tests/**/*.py": ["test-runner"],
    "server.py": ["project-health-monitor", "commit-validator"],
    "template_engine/**": ["commit-validator"],
    "ai_self_healing/**": ["self-healing-executor", "commit-validator"],
    "ios_automation_core/**": ["commit-validator"],
    "*.json": ["deployment-checker"],
    "scripts/*.py": ["commit-validator"],
    "*.md": ["learning-recorder"],
}

# 技能依赖关系定义
SKILL_DEPENDENCIES = {
    "commit-validator": [],
    "test-runner": ["commit-validator"],
    "self-healing-executor": [],
    "deployment-checker": [],
    "learning-recorder": [],
    "notification-hub": [],
    "project-health-monitor": [],
}

# 高风险文件模式
HIGH_RISK_PATTERNS = [
    "server.py",
    "template_engine/dispatcher.py",
    "template_engine/executor.py",
    "ai_self_healing/fix_strategies.py",
    "ai_self_healing/loop_controller.py",
]

# 敏感操作模式
SENSITIVE_PATTERNS = [
    "server.py",
    "template_engine/template_engine.py",
]

# 并行技能组
PARALLEL_GROUPS = [
    {"name": "check", "skills": ["commit-validator", "deployment-checker", "project-health-monitor"]},
    {"name": "test", "skills": ["test-runner"]},
    {"name": "heal", "skills": ["self-healing-executor"]},
    {"name": "meta", "skills": ["learning-recorder", "notification-hub"]},
]


def match_pattern(filename: str, pattern: str) -> bool:
    """匹配文件名模式"""
    import re
    regex_pattern = pattern.replace(".", r"\.").replace("**/", ".*/").replace("**", ".*").replace("*", "[^/]*")
    return bool(re.match(f"^{regex_pattern}$", filename))


def get_skills_for_file(filename: str) -> List[str]:
    """获取文件应该触发的技能列表"""
    skills = set()
    for pattern, skill_list in SKILL_RULES.items():
        if match_pattern(filename, pattern):
            skills.update(skill_list)
    return list(skills)


def get_skills_for_files(filenames: List[str]) -> Dict[str, List[str]]:
    """获取多个文件应触发的技能映射"""
    skill_map = {}
    for filename in filenames:
        skills = get_skills_for_file(filename)
        for skill in skills:
            if skill not in skill_map:
                skill_map[skill] = []
            if filename not in skill_map[skill]:
                skill_map[skill].append(filename)
    return skill_map


def analyze_code_changes(files: List[str]) -> Dict[str, any]:
    """分析代码变更特征"""
    analysis = {
        "total_files": len(files),
        "by_type": {},
        "skills_needed": [],
        "high_priority": [],
    }
    skills_needed_set = set()

    for f in files:
        ext = Path(f).suffix
        analysis["by_type"][ext] = analysis["by_type"].get(ext, 0) + 1

        if any(p in f for p in ["server.py", "template_engine/", "ai_self_healing/"]):
            analysis["high_priority"].append(f)
            skills_needed_set.add("self-healing-executor")

    analysis["skills_needed"] = list(skills_needed_set)
    return analysis


def select_skills_with_learning(context: Dict = None, use_learning: bool = True) -> Dict:
    """选择要执行的技能"""
    files = context.get("files", []) if context else []

    if not files:
        return {
            "selected_skills": ["commit-validator"],
            "skill_map": {},
            "analysis": {"total_files": 0},
            "learning": {"enabled": False, "reason": "no_files"}
        }

    skill_map = get_skills_for_files(files)
    analysis = analyze_code_changes(files)

    selected_skills = list(skill_map.keys()) if skill_map else ["commit-validator"]

    return {
        "selected_skills": selected_skills,
        "skill_map": skill_map,
        "analysis": analysis,
        "learning": {"enabled": False},
        "files": files,
        "execution_plan": generate_execution_plan(files, skill_map, analysis),
    }


def generate_execution_plan(files: List[str], skill_map: Dict[str, List[str]], analysis: Dict, predictions: Dict = None) -> Dict:
    """生成执行计划"""

    risk_level = "low"
    risk_files = []

    for f in files:
        is_high_risk = any(pattern in f for pattern in HIGH_RISK_PATTERNS)
        is_sensitive = any(pattern in f for pattern in SENSITIVE_PATTERNS)

        if is_high_risk:
            risk_level = "high"
            risk_files.append(f)
        elif is_sensitive and risk_level != "high":
            risk_level = "medium"

    stages = []

    # Stage 1: 基础检查
    check_skills = [s for s in skill_map.keys() if s in ["commit-validator", "deployment-checker", "project-health-monitor"]]
    if check_skills:
        stages.append({
            "name": "check",
            "skills": check_skills,
            "depends_on": []
        })

    # Stage 2: 测试
    if "test-runner" in skill_map:
        stages.append({
            "name": "test",
            "skills": ["test-runner"],
            "depends_on": ["check"]
        })

    # Stage 3: 自愈（仅当用户明确需要时）
    # 注意: self-healing 需要具体错误上下文，不应在规划阶段自动添加
    # 用户可通过 autopilot heal 手动触发自愈
    pass  # 自愈已禁用自动触发

    # Stage 4: 元操作
    meta_skills = [s for s in skill_map.keys() if s in ["learning-recorder", "notification-hub"]]
    if meta_skills:
        stages.append({
            "name": "meta",
            "skills": meta_skills,
            "depends_on": ["check", "test"]
        })

    return {
        "stages": stages,
        "risk_level": risk_level,
        "risk_files": risk_files,
        "total_files": len(files),
        "prediction": predictions if predictions else {}
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="技能选择器")
    parser.add_argument("-f", "--files", nargs="+", help="文件列表")
    parser.add_argument("-o", "--output", help="输出文件")

    args = parser.parse_args()

    files = args.files if args.files else []

    result = select_skills_with_learning({"files": files})

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"✅ 计划已保存到 {output_path}")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())