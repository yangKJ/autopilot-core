#!/usr/bin/env python3
"""
多链条并行执行器
同时运行多个技能链条
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============ 配置 ============

PROJECT_ROOT = Path.cwd()
CHAIN_SCRIPT = PROJECT_ROOT / ".claude" / "skills" / "skill-chain" / "scripts" / "run.py"


@dataclass
class ChainResult:
    name: str
    success: bool
    duration: float
    output: str


def run_chain(chain_name: str, context: Dict = None, timeout: int = 600) -> ChainResult:
    """运行单个链条"""
    import time
    start = time.time()

    cmd = ["python3", str(CHAIN_SCRIPT), "run", chain_name]

    if context and context.get("files"):
        cmd.extend(["--files"] + context["files"][:20])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT
        )
        duration = time.time() - start

        return ChainResult(
            name=chain_name,
            success=result.returncode == 0,
            duration=duration,
            output=result.stdout + result.stderr
        )
    except subprocess.TimeoutExpired:
        return ChainResult(
            name=chain_name,
            success=False,
            duration=timeout,
            output="Timeout"
        )
    except Exception as e:
        return ChainResult(
            name=chain_name,
            success=False,
            duration=0,
            output=str(e)
        )


def run_chains_parallel(chain_names: List[str], context: Dict = None, max_workers: int = 3) -> List[ChainResult]:
    """并行运行多个链条"""
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_chain, chain_name, context): chain_name
            for chain_name in chain_names
        }

        for future in as_completed(futures):
            chain_name = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(ChainResult(
                    name=chain_name,
                    success=False,
                    duration=0,
                    output=str(e)
                ))

    return results


def main():
    parser = argparse.ArgumentParser(description="Parallel Chain Runner")
    parser.add_argument("--chains", "-c", nargs="+", required=True, help="要运行的链条列表")
    parser.add_argument("--files", "-f", nargs="+", help="文件列表")
    parser.add_argument("--max-workers", "-w", type=int, default=3, help="最大并行数")
    parser.add_argument("--timeout", "-t", type=int, default=600, help="单个链条超时（秒）")
    parser.add_argument("--json", "-j", action="store_true", help="JSON 输出")

    args = parser.parse_args()

    context = {"files": args.files} if args.files else None

    print(f"🚀 Running {len(args.chains)} chains in parallel (max_workers={args.max_workers})")
    print("=" * 60)

    results = run_chains_parallel(args.chains, context, args.max_workers)

    # 汇总
    passed = sum(1 for r in results if r.success)
    total = len(results)
    total_duration = sum(r.duration for r in results)

    print(f"\n{'=' * 60}")
    print(f"📊 Summary: {passed}/{total} chains passed")
    print(f"⏱️  Total duration: {total_duration:.1f}s")

    for result in results:
        emoji = "✅" if result.success else "❌"
        print(f"\n{emoji} {result.name}: {'PASS' if result.success else 'FAIL'} ({result.duration:.1f}s)")
        if not result.success and result.output:
            print(f"   Output: {result.output[:200]}...")

    if args.json:
        output = {
            "chains": [r.name for r in results],
            "passed": passed,
            "total": total,
            "results": [
                {"name": r.name, "success": r.success, "duration": r.duration}
                for r in results
            ]
        }
        print(json.dumps(output, indent=2))

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
