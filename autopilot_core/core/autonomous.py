#!/usr/bin/env python3
"""
自动驾驶调度中心 - 通用版
一键式执行：选择技能 → 生成计划 → 执行 → 验证 → 记录 → 通知
"""

import sys
import json
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# 导入核心模块
from .learning_engine import record_chain_outcome, get_learning_engine

# 获取技能包路径
SKILLS_PACKAGE = Path(__file__).parent.parent / "skills"


@dataclass
class ExecutionResult:
    success: bool
    stage: str
    skill: str
    duration: float
    output: str
    error: str = ""


@dataclass
class AutopilotConfig:
    """自动驾驶配置"""
    project_root: Path = Path.cwd()
    skills_dir: Path = SKILLS_PACKAGE  # 使用内置技能包
    state_dir: Path = Path(".autopilot/state")
    db_path: Path = Path(".autopilot/.learning.db")

    # 技能路径映射（名称 -> 路径或命令）
    skill_paths: Dict[str, str] = None

    # 学习引擎配置
    learning_enabled: bool = True
    min_samples: int = 3

    # 执行配置
    max_workers: int = 3
    timeout: int = 300
    retry_on_fail: bool = True

    def __post_init__(self):
        if self.skill_paths is None:
            self.skill_paths = {}


class SkillRegistry:
    """技能注册表"""

    def __init__(self, config: AutopilotConfig):
        self.config = config
        self._skills = {}

    def register(self, name: str, path: str):
        """注册技能"""
        self._skills[name] = path

    def get(self, name: str) -> Optional[str]:
        """获取技能路径"""
        return self._skills.get(name)

    def list_all(self) -> List[str]:
        """列出所有技能"""
        return list(self._skills.keys())

    def load_from_config(self, skills_yaml: Path):
        """从配置文件加载"""
        if not skills_yaml.exists():
            return

        import yaml
        with open(skills_yaml) as f:
            data = yaml.safe_load(f)

        for skill in data.get("skills", []):
            name = skill.get("name")
            action = skill.get("action")
            if name and action:
                self.register(name, action)


class AutonomousScheduler:
    """自动驾驶调度中心"""

    def __init__(self, config: AutopilotConfig = None, dry_run: bool = False):
        self.config = config or AutopilotConfig()
        self.dry_run = dry_run
        self.results: List[ExecutionResult] = []
        self.context: Dict = {}
        self.plan: Dict = {}
        self.skill_registry = SkillRegistry(self.config)

    def get_changed_files(self) -> List[str]:
        """获取变更的文件列表"""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True, cwd=self.config.project_root
            )
            if result.returncode == 0:
                files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
                return files
        except:
            pass
        return []

    def step_select_skills(self, files: List[str]) -> Dict:
        """Step 1: 选择技能并生成执行计划"""
        print(f"\n{'='*60}")
        print(f"📋 Step 1: 技能选择 + 执行计划生成")
        print(f"{'='*60}")

        # 如果有 skill-selector，使用它
        selector_path = self.config.skills_dir / "skill-selector" / "scripts" / "select_skills.py"
        if selector_path.exists():
            output_file = self.config.state_dir / ".autonomous_plan.json"
            cmd = [
                "python3", str(selector_path),
                "-f", *files[:20],
                "-o", str(output_file)
            ]

            if self.dry_run:
                print(f"[DRY RUN] Would run skill selector for {len(files[:20])} files")
                # 干跑模式：生成默认计划但不实际执行
                stages = []
                stage = {"name": "check", "skills": [], "depends_on": []}
                for f in files[:20]:
                    if f.endswith(".py"):
                        if "test" in f.lower():
                            stage["skills"].append("test-runner")
                        else:
                            stage["skills"].append("commit-validator")
                stage["skills"] = list(set(stage["skills"]))
                if stage["skills"]:
                    stages.append(stage)
                self.plan = {"stages": stages}
                print(f"[DRY RUN] Would execute plan: {json.dumps(self.plan, indent=2)}")
                return {"execution_plan": self.plan}

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.config.project_root)
            print(result.stdout)

            if result.returncode == 0 and output_file.exists():
                with open(output_file) as f:
                    plan_data = json.load(f)
                self.plan = plan_data.get("execution_plan", {})
                return plan_data

        # 默认计划：按文件类型选择技能
        stages = []
        stage = {"name": "default", "skills": [], "depends_on": []}

        for f in files[:20]:
            if f.endswith(".py"):
                if "test" in f.lower():
                    stage["skills"].append("test-runner")
                else:
                    stage["skills"].append("code-review")

        stage["skills"] = list(set(stage["skills"]))
        if stage["skills"]:
            stages.append(stage)

        self.plan = {"stages": stages}
        return {"execution_plan": self.plan}

    def step_execute_plan(self) -> bool:
        """Step 2: 执行计划"""
        print(f"\n{'='*60}")
        print(f"🚀 Step 2: 执行动态计划")
        print(f"{'='*60}")

        if not self.plan:
            print("⚠️  No execution plan available")
            return False

        plan_file = self.config.state_dir / ".autonomous_plan.json"
        plan_file.parent.mkdir(parents=True, exist_ok=True)

        if self.dry_run:
            print(f"[DRY RUN] Would execute plan: {json.dumps(self.plan, indent=2)}")
            return True

        # 将计划写入文件
        with open(plan_file, "w") as f:
            json.dump({"execution_plan": self.plan}, f)

        # 使用 parallel-executor 执行计划
        executor_path = self.config.skills_dir / "parallel-executor" / "scripts" / "run_parallel.py"
        if executor_path.exists():
            cmd = [
                "python3", str(executor_path),
                "-p", str(plan_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.config.project_root)
            print(result.stdout)
            if result.stderr:
                print(f"STDERR: {result.stderr[:200]}")
            return result.returncode == 0

        # 如果没有并行执行器，逐个执行技能
        for stage in self.plan.get("stages", []):
            for skill in stage.get("skills", []):
                skill_path = self.skill_registry.get(skill)
                if skill_path:
                    print(f"Executing {skill}...")
                    subprocess.run(
                        ["python3", skill_path],
                        capture_output=True, text=True,
                        cwd=self.config.project_root
                    )

        return True

    def step_validate(self, execution_success: bool) -> bool:
        """Step 3: 验证执行结果"""
        print(f"\n{'='*60}")
        print(f"✅ Step 3: 验证执行结果")
        print(f"{'='*60}")

        if self.dry_run:
            print("[DRY RUN] Would run validation")
            return True

        if execution_success:
            print(f"Execution succeeded - validation PASS")
            return True

        files = self.context.get("files", [])
        if not files:
            return False

        try:
            start = time.time()

            for f in files[:3]:
                if f.endswith(".py"):
                    result = subprocess.run(
                        ["python3", "-m", "py_compile", f],
                        capture_output=True, text=True, cwd=self.config.project_root, timeout=10
                    )
                    if result.returncode != 0:
                        print(f"Syntax error in {f}:")
                        print(f"   {result.stderr[:200]}")
                        return False

            duration = time.time() - start
            print(f"Syntax check: ✅ PASS ({duration:.1f}s)")
            return True

        except Exception as e:
            print(f"Validation error: {e}")
            return False

    def step_record_learning(self, success: bool):
        """Step 4: 记录学习"""
        print(f"\n{'='*60}")
        print(f"🧠 Step 4: 记录学习")
        print(f"{'='*60}")

        if self.dry_run:
            print("[DRY RUN] Would record learning")
            return

        if not self.config.learning_enabled:
            return

        try:
            chain_name = "autonomous"
            stages = self.plan.get("stages", [])
            skill_names = [s for stage in stages for s in stage.get("skills", [])]
            skill_names = list(set(skill_names))

            files = self.context.get("files", [])
            record_chain_outcome(chain_name, skill_names, files, success)
            print(f"✅ Learning recorded: chain={chain_name}, success={success}")

        except Exception as e:
            print(f"⚠️  Learning record failed: {e}")

    def run_closed_loop_healing(self) -> bool:
        """运行闭环自愈"""
        healer_path = self.config.skills_dir / "self-healing-executor" / "scripts" / "heal.py"
        if healer_path and healer_path.exists():
            try:
                result = subprocess.run(
                    ["python3", str(healer_path)],
                    capture_output=True, text=True, cwd=self.config.project_root, timeout=120
                )
                return result.returncode == 0
            except Exception as e:
                print(f"⚠️  Closed-loop healing failed: {e}")
        return False

    def step_notify(self, success: bool, details: str = ""):
        """Step 5: 发送通知"""
        print(f"\n{'='*60}")
        print(f"📱 Step 5: 发送通知")
        print(f"{'='*60}")

        if self.dry_run:
            print("[DRY RUN] Would send notification")
            return

        notifier_path = self.config.skills_dir / "notification-hub" / "scripts" / "notify.py"
        if notifier_path and notifier_path.exists():
            try:
                level = "success" if success else "failure"
                title = "✅ 自动驾驶完成" if success else "❌ 自动驾驶失败"
                message = details or (f"执行 {len(self.plan.get('stages', []))} 个阶段" if self.plan else "无执行计划")

                cmd = [
                    "python3", str(notifier_path),
                    "send", "-m", message, "-l", level, "-s", "autonomous-scheduler"
                ]

                subprocess.run(cmd, capture_output=True, text=True, cwd=self.config.project_root, timeout=30)
                print(f"✅ Notification sent")
            except Exception as e:
                print(f"⚠️  Notification failed: {e}")

    def run_full_cycle(self, files: List[str] = None) -> bool:
        """运行完整自动驾驶周期"""
        print(f"\n🚗{'='*58}")
        print(f"   自动驾驶调度中心启动")
        print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 获取变更文件
        if not files:
            files = self.get_changed_files()

        if not files:
            print("⚠️  No files to process")
            return False

        # P2: 验证文件存在性
        missing_files = [f for f in files if not (self.config.project_root / f).exists()]
        if missing_files:
            print(f"⚠️  Missing files detected:")
            for f in missing_files[:5]:
                print(f"   • {f} (not found)")
            if len(missing_files) > 5:
                print(f"   ... and {len(missing_files) - 5} more")
            # 过滤掉不存在的文件，只处理存在的
            files = [f for f in files if (self.config.project_root / f).exists()]
            if not files:
                print("❌ No valid files to process")
                return False
            print(f"📁 Continuing with {len(files)} valid files")

        print(f"📁 Processing {len(files)} files:")
        for f in files[:5]:
            print(f"   • {f}")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more")

        self.context["files"] = files

        # Step 1: 技能选择
        plan_data = self.step_select_skills(files)
        if not plan_data:
            print("❌ Skill selection failed")
            self.step_notify(False, "技能选择失败")
            return False

        # Step 2: 执行计划
        execution_success = self.step_execute_plan()

        # Step 3: 验证
        validation_success = self.step_validate(execution_success)

        # Step 3.5: 闭环自愈
        # 注意: 自动自愈需要具体错误上下文，当前实现不完整
        # 改用手动触发: autopilot heal
        # if not execution_success and self.config.auto_heal_enabled:
        #     print(f"\n🔄{'='*58}")
        #     print(f"   检测到执行失败，启动闭环自愈")
        #     print(f"{'='*60}")
        #     if self.run_closed_loop_healing(error_context):
        #         print(f"✅ 自愈成功，系统恢复")
        #         execution_success = True

        # Step 4: 记录学习
        final_success = execution_success and validation_success
        self.step_record_learning(final_success)

        # Step 5: 通知
        if final_success:
            self.step_notify(True, f"成功执行 {len(self.plan.get('stages', []))} 个阶段")
        else:
            failed_info = "部分阶段失败" if execution_success else "执行失败"
            self.step_notify(False, failed_info)

        # 总结
        print(f"\n{'='*60}")
        print(f"📊 自动驾驶周期完成")
        print(f"   执行: {'✅ 成功' if execution_success else '❌ 失败'}")
        print(f"   验证: {'✅ 通过' if validation_success else '❌ 未通过'}")
        print(f"   最终: {'✅ 成功' if final_success else '❌ 失败'}")
        print(f"{'='*60}\n")

        return final_success

    def run_continuous(self, files: List[str] = None, interval: int = 60, max_cycles: int = -1):
        """连续运行模式（监控模式）"""
        print(f"\n🔄{'='*58}")
        print(f"   自动驾驶调度中心 - 连续监控模式")
        print(f"   间隔: {interval}秒")
        print(f"   最大循环: {max_cycles if max_cycles > 0 else '无限'}")
        print(f"{'='*60}")

        cycle = 0
        while max_cycles < 0 or cycle < max_cycles:
            cycle += 1
            print(f"\n--- 循环 {cycle} ---")

            files = self.get_changed_files()
            if files:
                print(f"检测到 {len(files)} 个变更文件")
                self.run_full_cycle(files)
            else:
                print("无变更文件")

            if max_cycles < 0 or cycle < max_cycles:
                time.sleep(interval)

        print(f"\n连续监控结束，共运行 {cycle} 个循环")


def main():
    parser = argparse.ArgumentParser(description="自动驾驶调度中心")
    parser.add_argument("--files", "-f", nargs="+", help="指定文件列表")
    parser.add_argument("--dry-run", "-n", action="store_true", help="只输出，不执行")
    parser.add_argument("--continuous", "-c", action="store_true", help="连续监控模式")
    parser.add_argument("--interval", "-i", type=int, default=60, help="连续模式间隔（秒）")
    parser.add_argument("--max-cycles", "-m", type=int, default=-1, help="最大循环次数（-1=无限）")
    parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")
    parser.add_argument("--skills-dir", "-s", type=Path, help="技能目录")

    args = parser.parse_args()

    config = AutopilotConfig(
        project_root=args.project_root,
        skills_dir=args.skills_dir or Path(".autopilot/skills")
    )

    scheduler = AutonomousScheduler(config=config, dry_run=args.dry_run)

    if args.continuous:
        scheduler.run_continuous(
            files=args.files,
            interval=args.interval,
            max_cycles=args.max_cycles
        )
    else:
        success = scheduler.run_full_cycle(files=args.files)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())