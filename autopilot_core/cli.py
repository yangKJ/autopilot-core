#!/usr/bin/env python3
"""
Autopilot CLI - 统一入口
autopilot - 一站式自动驾驶模式管理
"""

import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional

VERSION = "0.2.0"


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path.cwd()


def run_autopilot(args) -> int:
    """运行自动驾驶"""
    from .core.autonomous import AutonomousScheduler, AutopilotConfig

    config = AutopilotConfig(project_root=get_project_root())
    scheduler = AutonomousScheduler(config=config, dry_run=args.dry_run)

    files = args.files if args.files else None

    if args.continuous:
        scheduler.run_continuous(files=files, interval=args.interval or 60, max_cycles=args.max_cycles or -1)
        # continuous 模式没有返回值，假设正常
        return 0
    else:
        success = scheduler.run_full_cycle(files=files)
        return 0 if success else 1


def cmd_init(args) -> int:
    """初始化项目"""
    from .core.config import ConfigLoader

    project_root = args.project or Path.cwd()
    loader = ConfigLoader(project_root)

    if loader.init_project_config(force=args.force):
        print(f"✅ Autopilot 项目初始化完成")
        print(f"   配置文件: {loader.project_config_path}")
        print(f"   技能目录: {project_root / '.autopilot' / 'skills'}")
        print(f"\n下一步:")
        print(f"   1. 编辑 .autopilot.yaml 配置技能")
        print(f"   2. 运行 'autopilot run' 启动自动驾驶")
    else:
        return 1

    return 0


def cmd_config(args) -> int:
    """配置管理"""
    from .core.config import ConfigLoader, AutopilotSettings

    project_root = args.project or Path.cwd()
    loader = ConfigLoader(project_root)

    if args.show or (not args.set and not args.reset):
        settings = loader.load()
        print(f"\n📋 Autopilot 配置")
        print(f"{'='*60}")

        config_dict = settings.to_dict()
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print(f"{'  ' * indent}📁 {key}:")
                    print_dict(value, indent + 1)
                else:
                    print(f"{'  ' * indent}• {key}: {value}")

        print_dict(config_dict)
        print()

    elif args.set:
        key, value = args.set[0], args.set[1]

        # 转换值类型
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        settings = loader.load()
        keys = key.split(".")
        config_dict = settings.to_dict()
        current = config_dict
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value
        settings = AutopilotSettings.from_dict(config_dict)

        if args.local:
            loader.save_local(settings)
        else:
            loader.save_project(settings)

    elif args.reset:
        settings = loader.load()
        if args.local:
            loader.save_local(settings)
        else:
            loader.save_project(settings)

    return 0


def cmd_dashboard(args) -> int:
    """监控面板"""
    from .core.dashboard import get_dashboard_data, format_dashboard

    project_root = get_project_root()

    if args.json:
        import json
        data = get_dashboard_data(project_root)
        print(json.dumps({
            "chain_stats": data.chain_stats,
            "recent_runs": data.recent_runs,
            "health_status": data.health_status,
            "predictions": data.predictions,
            "notification_history": data.notification_history
        }, indent=2))
    else:
        data = get_dashboard_data(project_root)
        print(format_dashboard(data))

    return 0


def cmd_predict(args) -> int:
    """预测分析"""
    from .core.learning_engine import predict_success_rate, get_prediction_report

    if args.report:
        report = get_prediction_report(days_ahead=args.ahead or 3)
        print(f"\n📈 预测报告 (生成于: {report['generated_at'][:19]})")
        print(f"   预测范围: 未来{args.ahead or 3}天")
        print(f"\n   高风险链条: {', '.join(report['high_risk_chains']) or '无'}")
        print(f"   推荐链条: {', '.join(report['recommended_chains']) or '无'}")
        print("\n   详细预测:")
        for p in report["predictions"]:
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p["risk"], "⚪")
            print(f"   {emoji} {p['chain']}: {p['predicted_success_rate']:.0%} (置信度: {p['confidence']:.0%})")
        print()
    else:
        result = predict_success_rate(
            chain_name=args.chain,
            days_history=args.days or 14,
            days_ahead=args.ahead or 3
        )

        if args.json:
            import json
            print(json.dumps(result, indent=2))
        else:
            print(f"\n📊 预测结果 (链条: {result.get('chain', 'all')})")
            print(f"   预测成功率: {result['prediction']:.1%}")
            print(f"   置信度: {result['confidence']:.0%}")
            print(f"   趋势斜率: {result['trend_slope']}")
            print(f"   风险等级: {result['risk']}")
            print(f"   建议: {result['recommendation']}")
            print()

    return 0


def cmd_health(args) -> int:
    """健康检查"""
    from .core.dashboard import get_health_status

    project_root = get_project_root()
    health = get_health_status(project_root)

    print(f"\n🏥{'='*58}")
    print(f"   Autopilot 健康检查")
    print(f"{'='*60}\n")

    print(f"   整体状态: {health.get('overall', 'unknown')}")
    print(f"   过去24小时失败: {health.get('recent_failures', 0)}次")

    if health.get("checks"):
        print("\n   关键检查:")
        for check, status in health.get("checks", {}).items():
            print(f"     {status} {check}")

    print()
    return 0


def cmd_heal(args) -> int:
    """闭环自愈"""
    from .core.auto_heal import ClosedLoopHealer

    healer = ClosedLoopHealer(max_cycles=args.cycles or 3)
    result = healer.run_healing_cycle(check_name=args.check)

    return 0 if result.healed else 1


def cmd_status(args) -> int:
    """显示状态"""
    print(f"\n🚗{'='*58}")
    print(f"   Autopilot 状态")
    print(f"{'='*60}\n")

    project_root = get_project_root()

    # 检查关键组件
    components = {
        "core/autonomous.py": "自动驾驶调度",
        "core/learning_engine.py": "学习引擎",
        "core/config.py": "配置系统",
        "core/dashboard.py": "监控面板",
        "core/auto_heal.py": "闭环自愈",
        "core/daemon.py": "持续监控",
        "core/scheduler.py": "定时任务",
        "core/nlp.py": "自然语言",
        "core/git_hooks.py": "Git Hooks",
    }

    print("📜 核心模块:")
    for path, desc in components.items():
        full_path = Path(__file__).parent / path
        status = "✅" if full_path.exists() else "❌"
        print(f"   {status} {desc}")

    # 检查配置
    print("\n📋 配置状态:")
    config_files = [
        Path("~/.autopilot/config.yaml").expanduser(),
        project_root / ".autopilot.yaml",
        project_root / ".autopilot.local.yaml",
    ]

    for cf in config_files:
        status = "✅" if cf.exists() else "-"
        print(f"   {status} {cf}")

    # 数据库状态
    db_path = project_root / ".autopilot" / ".learning.db"
    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT COUNT(*) as count FROM file_runs")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"\n📊 数据库记录: {count} 条")
    else:
        print(f"\n📊 数据库记录: 无")

    print()
    return 0


def cmd_daemon(args) -> int:
    """持续监控模式"""
    from .core.daemon import ContinuousMonitor

    config = {
        "debounce_seconds": args.debounce or 10,
        "max_batch_size": args.max_batch or 30,
        "check_interval": args.interval or 5,
    }

    monitor = ContinuousMonitor(config)
    monitor.start()

    return 0


def cmd_scheduler(args) -> int:
    """定时任务调度"""
    from .core.scheduler import TaskScheduler

    project_root = get_project_root()
    scheduler = TaskScheduler(project_root=project_root)

    if args.list:
        scheduler.list_tasks()
    elif args.run:
        scheduler.run_pending()
    elif args.report:
        print(scheduler.generate_report(args.days or 7))
    else:
        scheduler.list_tasks()

    return 0


def cmd_git_hooks(args) -> int:
    """Git Hooks 管理"""
    from .core.git_hooks import install_hooks, uninstall_hooks, list_hooks

    project_root = get_project_root()

    if args.list:
        hooks = list_hooks()
        print("\n📋 Git Hooks 状态:")
        for name, installed in hooks.items():
            status = "✅ 已安装" if installed else "❌ 未安装"
            print(f"   {status} {name}")
        return 0

    if args.install:
        print("🚀 安装 Git Hooks...")
        success = install_hooks(dry_run=False)
        if success:
            print("\n✅ Git Hooks 安装完成")
            print("\n可用 hooks:")
            print("   pre-commit: 提交前检查 (ruff + 语法)")
            print("   post-commit: 提交后检查")
            print("   pre-push: 推送前检查")
        return 0 if success else 1

    if args.uninstall:
        print("🗑️  卸载 Git Hooks...")
        success = uninstall_hooks(dry_run=False)
        return 0 if success else 1

    # 默认显示状态
    hooks = list_hooks()
    print("\n📋 Git Hooks 状态:")
    for name, installed in hooks.items():
        status = "✅ 已安装" if installed else "❌ 未安装"
        print(f"   {status} {name}")

    print("\n使用 --install 安装，--uninstall 卸载，--list 查看状态")

    return 0


def cmd_nlp(args) -> int:
    """自然语言接口"""
    from .core.nlp import main as nlp_main

    if not args.command:
        print("❌ 需要提供指令")
        return 1

    sys.argv = ["nlp"] + args.command
    if args.dry_run:
        sys.argv.append("--dry-run")

    return nlp_main()


def cmd_workflow(args) -> int:
    """工作流管理"""
    from .core.workflow_runner import (
        workflow_list, workflow_show, workflow_run,
        workflow_history, workflow_validate
    )

    project_root = args.project or Path.cwd()
    output_json = getattr(args, 'json', False)

    if args.workflow_command == "list":
        return workflow_list(project_root, json_output=output_json)
    elif args.workflow_command == "show":
        if not args.name:
            print("❌ 需要提供工作流名称")
            return 1
        return workflow_show(args.name, project_root, json_output=output_json)
    elif args.workflow_command == "run":
        if not args.name:
            print("❌ 需要提供工作流名称")
            return 1
        return workflow_run(args.name, project_root, verbose=args.verbose, json_output=output_json)
    elif args.workflow_command == "history":
        if not args.name:
            print("❌ 需要提供工作流名称")
            return 1
        limit = getattr(args, 'limit', 10)
        return workflow_history(args.name, project_root, limit=limit, json_output=output_json)
    elif args.workflow_command == "validate":
        return workflow_validate(project_root, json_output=output_json)

    print("❌ 未知的 workflow 子命令")
    return 1


def cmd_exec(args) -> int:
    """执行外部命令"""
    from .core.exec_runner import exec_command

    if not args.cmd_args:
        print("❌ 需要提供要执行的命令")
        return 1

    project_root = args.project or Path.cwd()
    output_json = getattr(args, 'json', False)

    # 跳过 -- 分隔符
    cmd_args = args.cmd_args
    if cmd_args and cmd_args[0] == "--":
        cmd_args = cmd_args[1:]

    if not cmd_args:
        print("❌ 需要提供要执行的命令")
        return 1

    return exec_command(
        cmd_args,
        cwd=str(project_root),
        timeout=args.timeout or 300,
        verbose=args.verbose,
        json_output=output_json,
    )


def main():
    parser = argparse.ArgumentParser(
        description="🚗 Autopilot - 自动驾驶模式管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s init                    # 初始化项目
  %(prog)s run                     # 运行自动驾驶
  %(prog)s run -f file1.py file2.py  # 指定文件
  %(prog)s run --continuous        # 持续监控模式
  %(prog)s dashboard               # 查看监控面板
  %(prog)s predict                 # 预测分析
  %(prog)s health                  # 健康检查
  %(prog)s heal                    # 闭环自愈
  %(prog)s config show            # 显示配置
  %(prog)s status                  # 查看状态
        """
    )

    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {VERSION}")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run - 运行自动驾驶
    run_parser = subparsers.add_parser("run", help="运行自动驾驶")
    run_parser.add_argument("-f", "--files", nargs="+", help="文件列表")
    run_parser.add_argument("-n", "--dry-run", action="store_true", help="干跑")
    run_parser.add_argument("-c", "--continuous", action="store_true", help="连续模式")
    run_parser.add_argument("-i", "--interval", type=int, help="检查间隔（秒）")
    run_parser.add_argument("-m", "--max-cycles", type=int, help="最大循环次数")

    # init - 初始化项目
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.add_argument("-p", "--project", type=Path, help="项目路径")
    init_parser.add_argument("-f", "--force", action="store_true", help="强制覆盖")

    # config - 配置管理
    config_parser = subparsers.add_parser("config", help="配置管理")
    config_parser.add_argument("command", nargs="?", choices=["show", "set", "reset"], help="子命令")
    config_parser.add_argument("--set", nargs=2, help="设置配置 key value")
    config_parser.add_argument("--local", "-l", action="store_true", help="保存到本地配置")
    config_parser.add_argument("-p", "--project", type=Path, help="项目路径")

    # dashboard - 监控面板
    dash_parser = subparsers.add_parser("dashboard", help="监控面板")
    dash_parser.add_argument("--json", action="store_true", help="JSON输出")
    dash_parser.add_argument("--refresh", "-r", type=int, help="自动刷新间隔（秒）")

    # predict - 预测
    predict_parser = subparsers.add_parser("predict", help="预测分析")
    predict_parser.add_argument("-c", "--chain", help="链条名称")
    predict_parser.add_argument("--days", type=int, default=14, help="历史天数")
    predict_parser.add_argument("--ahead", type=int, default=3, help="预测天数")
    predict_parser.add_argument("--report", "-r", action="store_true", help="预测报告")
    predict_parser.add_argument("--json", action="store_true", help="JSON输出")

    # health - 健康检查
    health_parser = subparsers.add_parser("health", help="健康检查")

    # heal - 闭环自愈
    heal_parser = subparsers.add_parser("heal", help="闭环自愈")
    heal_parser.add_argument("-c", "--check", help="检查项")
    heal_parser.add_argument("-n", "--cycles", type=int, default=3, help="最大循环")

    # status - 状态
    subparsers.add_parser("status", help="查看状态")

    # daemon - 持续监控
    daemon_parser = subparsers.add_parser("daemon", help="持续监控模式")
    daemon_parser.add_argument("-d", "--debounce", type=int, default=10, help="防抖时间")
    daemon_parser.add_argument("-m", "--max-batch", type=int, default=30, help="最大批量")
    daemon_parser.add_argument("--interval", type=int, default=5, help="检查间隔")

    # scheduler - 定时任务
    scheduler_parser = subparsers.add_parser("scheduler", help="定时任务调度")
    scheduler_parser.add_argument("--list", "-l", action="store_true", help="列出任务")
    scheduler_parser.add_argument("--run", "-r", action="store_true", help="运行待执行任务")
    scheduler_parser.add_argument("--report", action="store_true", help="生成报告")
    scheduler_parser.add_argument("--days", "-d", type=int, help="报告天数")

    # git-hooks - Git Hooks
    hooks_parser = subparsers.add_parser("git-hooks", help="Git Hooks管理")
    hooks_parser.add_argument("--install", "-i", action="store_true", help="安装")
    hooks_parser.add_argument("--uninstall", "-u", action="store_true", help="卸载")
    hooks_parser.add_argument("--list", "-l", action="store_true", help="列出已安装的 hooks")

    # nlp - 自然语言
    nlp_parser = subparsers.add_parser("nlp", help="自然语言接口")
    nlp_parser.add_argument("command", nargs="*", help="自然语言指令")
    nlp_parser.add_argument("--dry-run", "-n", action="store_true", help="干跑")

    # workflow - 外部工作流
    workflow_parser = subparsers.add_parser("workflow", help="外部工作流管理")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command", help="workflow子命令")

    # workflow list
    wf_list = workflow_subparsers.add_parser("list", help="列出所有工作流")
    wf_list.add_argument("-p", "--project", type=Path, help="项目路径")
    wf_list.add_argument("--json", action="store_true", help="JSON输出")

    # workflow show
    wf_show = workflow_subparsers.add_parser("show", help="显示工作流详情")
    wf_show.add_argument("name", help="工作流名称")
    wf_show.add_argument("-p", "--project", type=Path, help="项目路径")
    wf_show.add_argument("--json", action="store_true", help="JSON输出")

    # workflow run
    wf_run = workflow_subparsers.add_parser("run", help="运行工作流")
    wf_run.add_argument("name", help="工作流名称")
    wf_run.add_argument("-p", "--project", type=Path, help="项目路径")
    wf_run.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    wf_run.add_argument("--json", action="store_true", help="JSON输出")

    # workflow history
    wf_history = workflow_subparsers.add_parser("history", help="查看工作流历史")
    wf_history.add_argument("name", help="工作流名称")
    wf_history.add_argument("-p", "--project", type=Path, help="项目路径")
    wf_history.add_argument("--limit", type=int, default=10, help="显示条数")
    wf_history.add_argument("--json", action="store_true", help="JSON输出")

    # workflow validate
    wf_validate = workflow_subparsers.add_parser("validate", help="校验工作流配置")
    wf_validate.add_argument("-p", "--project", type=Path, help="项目路径")
    wf_validate.add_argument("--json", action="store_true", help="JSON输出")

    # exec - 外部命令执行
    exec_parser = subparsers.add_parser("exec", help="执行外部命令")
    exec_parser.add_argument("cmd_args", nargs=argparse.REMAINDER, help="要执行的命令")
    exec_parser.add_argument("-p", "--project", type=Path, help="项目路径")
    exec_parser.add_argument("-t", "--timeout", type=int, help="超时时间(秒)")
    exec_parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    exec_parser.add_argument("--json", action="store_true", help="JSON输出")

    args = parser.parse_args()

    # 分发命令
    commands = {
        "run": run_autopilot,
        "init": cmd_init,
        "config": cmd_config,
        "dashboard": cmd_dashboard,
        "predict": cmd_predict,
        "health": cmd_health,
        "heal": cmd_heal,
        "status": cmd_status,
        "daemon": cmd_daemon,
        "scheduler": cmd_scheduler,
        "git-hooks": cmd_git_hooks,
        "nlp": cmd_nlp,
        "workflow": cmd_workflow,
        "exec": cmd_exec,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            print(f"❌ 执行错误: {e}")
            return 1
    else:
        print(f"❌ 未知命令: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())