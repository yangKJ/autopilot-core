#!/usr/bin/env python3
"""
并行执行器
并行执行多个选中的技能
"""

import sys
import json
import subprocess
import time
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = Path.cwd()
SKILLS_DIR = Path(__file__).parent.parent.parent

SKILL_PATHS = {
    "test-runner": "test-runner/scripts/run_tests.py",
    "commit-validator": "commit-validator/scripts/validate.py",
    "self-healing-executor": "self-healing-executor/scripts/heal.py",
    "project-health-monitor": "project-health-monitor/scripts/health_check.py",
    "deployment-checker": "deployment-checker/scripts/check.py",
    "learning-recorder": "learning-recorder/scripts/record.py",
    "notification-hub": "notification-hub/scripts/notify.py",
}


@dataclass
class SkillResult:
    skill: str
    passed: bool
    duration: float
    output: str
    error: str = ""


def run_skill_sync(skill: str, files: List[str] = None) -> SkillResult:
    import time
    start = time.time()

    skill_path = SKILL_PATHS.get(skill)
    if not skill_path:
        return SkillResult(skill=skill, passed=False, duration=0, output="", error="Unknown skill")

    script = SKILLS_DIR / skill_path
    if not script.exists():
        return SkillResult(skill=skill, passed=False, duration=0, output="", error=f"Script not found: {script}")

    cmd = ["python3", str(script)]

    if skill == "test-runner" and files:
        cmd.extend(["--path", "tests/"])
    elif skill == "deployment-checker":
        cmd.append("--quick")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        duration = time.time() - start
        output = result.stdout + result.stderr
        return SkillResult(
            skill=skill,
            passed=result.returncode == 0,
            duration=duration,
            output=output[:500] if output else "",
            error=""
        )
    except subprocess.TimeoutExpired:
        return SkillResult(skill=skill, passed=False, duration=300, output="", error="Timeout")
    except Exception as e:
        return SkillResult(skill=skill, passed=False, duration=time.time() - start, output="", error=str(e))


def run_parallel(skill_map: Dict[str, List[str]], max_workers: int = 3) -> List[SkillResult]:
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for skill, files in skill_map.items():
            future = executor.submit(run_skill_sync, skill, files)
            futures[future] = skill

        for future in as_completed(futures):
            skill = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(SkillResult(skill=skill, passed=False, duration=0, output="", error=str(e)))

    return results


def run_stages(stages: List[Dict], max_workers: int = 3, adaptive_config: Dict = None) -> Dict[str, any]:
    stage_results = {}
    all_skill_results = []

    adaptive = adaptive_config or {}
    retry_config = adaptive.get("retry_config", {"max_attempts": 1, "backoff_factor": 1.0})
    max_attempts = retry_config.get("max_attempts", 1)
    backoff_factor = retry_config.get("backoff_factor", 1.0)

    for idx, stage in enumerate(stages):
        stage_num = stage.get("stage", idx + 1)
        stage_name = stage.get("name", f"stage_{stage_num}")
        skills = stage["skills"]
        depends_on = stage.get("depends_on", [])
        allow_failure = stage.get("allow_failure", False)
        files = stage.get("files", [])

        # 同时用 stage_num 和 stage_name 作为 key，方便依赖查找
        stage_key = stage_num

        if depends_on:
            # 支持 stage name 和 stage num 两种依赖格式
            failed_deps = []
            for d in depends_on:
                # 检查是否是 stage name
                if d in [s.get("name") for s in stages[:idx]]:
                    # 通过 stage name 查找对应的 stage_num
                    for i, s in enumerate(stages[:idx]):
                        if s.get("name") == d:
                            d = s.get("stage", i + 1)
                            break
                # 检查依赖是否失败（支持 name 或 num 作为 key）
                if not stage_results.get(d, True):
                    failed_deps.append(d)
            if failed_deps and not allow_failure:
                print(f"⏭️  Skip Stage {stage_num}: {stage_name} (failed deps: {failed_deps})")
                continue

        print(f"\n📦 Stage {stage_num}: {stage_name}")
        print(f"   Skills: {', '.join(skills)}")
        if max_attempts > 1:
            print(f"   🔄 Adaptive retry: max_attempts={max_attempts}, backoff={backoff_factor}")

        skill_map = {s: files for s in skills}
        stage_success = False

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                sleep_time = backoff_factor * (attempt - 1)
                print(f"   🔄 Retry {attempt}/{max_attempts} (backoff {sleep_time}s)...")
                time.sleep(sleep_time)

            results = run_parallel(skill_map, max_workers=max_workers)
            all_skill_results.extend(results)

            stage_success = all(r.passed for r in results)

            if stage_success:
                break

        stage_results[stage_num] = stage_success
        stage_results[stage_name] = stage_success  # 同时用 name 作为 key，支持 name 依赖查找

        emoji = "✅" if stage_success else "❌"
        print(f"   {emoji} Stage {stage_num}: {'PASS' if stage_success else 'FAIL'}")

    return {
        "stage_results": stage_results,
        "skill_results": all_skill_results,
        "success": all(stage_results.values()) if stage_results else True,
        "adaptive": {
            "retry_config": retry_config,
            "total_attempts": max_attempts
        }
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Executor")
    parser.add_argument("--input", "-i", help="技能选择 JSON 文件")
    parser.add_argument("--max-workers", "-w", type=int, default=3, help="最大并行数")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--plan", "-p", help="执行计划 JSON 文件（阶段执行模式）")

    args = parser.parse_args()

    if args.plan:
        with open(args.plan) as f:
            plan_data = json.load(f)

        execution_plan = plan_data.get("execution_plan", plan_data)
        adaptive_config = execution_plan.get("adaptive", {})

        print(f"🚀 Running execution plan")
        print(f"   Risk: {execution_plan.get('risk_level', 'unknown')}, Priority: {execution_plan.get('priority', 50)}")
        print(f"   Stages: {execution_plan.get('total_stages', 0)}")
        if adaptive_config:
            print(f"   ⚙️  Adaptive: {adaptive_config}")

        result = run_stages(
            execution_plan.get("stages", []),
            max_workers=args.max_workers,
            adaptive_config=adaptive_config
        )

        print(f"\n{'='*50}")
        print(f"📊 Result: {'SUCCESS' if result['success'] else 'FAILURE'}")

        if args.output:
            with open(args.output, "w") as f:
                json.dump({
                    "success": result["success"],
                    "stages": result["stage_results"],
                    "total_stages": len(execution_plan.get("stages", []))
                }, f, indent=2)

        return 0 if result["success"] else 1

    input_file = args.input
    if not input_file:
        input_file = ".autopilot/state/.skill_selection.json"

    if not Path(input_file).exists():
        print("❌ No skill selection found. Run skill-selector first.")
        return 1

    with open(input_file) as f:
        selection = json.load(f)

    skill_map = selection.get("skill_map", {})
    if not skill_map:
        print("⚠️ No skills to execute")
        return 0

    print(f"🚀 Executing {len(skill_map)} skills in parallel (max_workers={args.max_workers})")
    print("=" * 50)

    results = run_parallel(skill_map, args.max_workers)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    print(f"\n{'=' * 50}")
    print(f"✅ Results: {passed}/{total} skills passed")

    for result in results:
        emoji = "✅" if result.passed else "❌"
        print(f"{emoji} {result.skill}: {'PASS' if result.passed else 'FAIL'} ({result.duration:.1f}s)")
        if result.error:
            print(f"   Error: {result.error}")

    output_data = {
        "results": [
            {"skill": r.skill, "passed": r.passed, "duration": r.duration, "error": r.error}
            for r in results
        ],
        "summary": {"passed": passed, "total": total, "all_passed": passed == total}
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
    else:
        output_file = PROJECT_ROOT / ".autopilot" / "state" / ".parallel_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
