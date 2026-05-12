#!/usr/bin/env python3
"""
智能学习引擎 v2
基于 SQLite 持久化存储历史数据
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

# ============ 配置 ============

PROJECT_ROOT = Path.cwd()
STATE_DIR = PROJECT_ROOT / ".skills-state"
DB_PATH = PROJECT_ROOT / ".claude" / "skills" / ".learning.db"

logger = logging.getLogger("skill_chain.learning")

# 权重配置
WEIGHTS = {
    "recent_runs_decay": 0.7,
    "high_failure_threshold": 0.3,
    "consecutive_failure_weight": 2.0,
    "file_success_min_samples": 3,
}


class LearningEngine:
    """智能学习引擎（SQLite 持久化）"""

    def __init__(self):
        self._init_db()
        self.pattern_stats_cache = {}

    def _init_db(self):
        """初始化数据库"""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # 创建表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_stats (
                file TEXT PRIMARY KEY,
                success INTEGER DEFAULT 0,
                fail INTEGER DEFAULT 0,
                last_run TEXT
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_stats (
                skill TEXT PRIMARY KEY,
                success INTEGER DEFAULT 0,
                fail INTEGER DEFAULT 0
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS pattern_stats (
                pattern TEXT PRIMARY KEY,
                success INTEGER DEFAULT 0,
                fail INTEGER DEFAULT 0
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file TEXT,
                chain TEXT,
                skill TEXT,
                success INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS file_runs (
                file TEXT,
                chain TEXT,
                success INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (file, chain, timestamp)
            )
        """)

        self.conn.commit()

    def record_outcome(self, chain_name: str, skills: List[str], files: List[str], success: bool):
        """记录执行结果"""
        timestamp = datetime.now().isoformat()

        try:
            # 更新技能统计
            for skill in skills:
                self.conn.execute(
                    "INSERT INTO skill_stats (skill, success, fail) VALUES (?, ?, ?) "
                    "ON CONFLICT(skill) DO UPDATE SET "
                    "success = success + CASE WHEN ? THEN 1 ELSE 0 END, "
                    "fail = fail + CASE WHEN ? THEN 1 ELSE 0 END",
                    (skill, 1 if success else 0, 0 if success else 1, success, not success)
                )

            # 更新文件统计
            for file in files:
                self.conn.execute(
                    "INSERT INTO file_stats (file, success, fail, last_run) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(file) DO UPDATE SET "
                    "success = success + CASE WHEN ? THEN 1 ELSE 0 END, "
                    "fail = fail + CASE WHEN ? THEN 1 ELSE 0 END, "
                    "last_run = ?",
                    (file, 1 if success else 0, 0 if success else 1, timestamp, success, not success, timestamp)
                )

                # 记录历史
                self.conn.execute(
                    "INSERT INTO file_runs (file, chain, success, timestamp) VALUES (?, ?, ?, ?)",
                    (file, chain_name, 1 if success else 0, timestamp)
                )

            # 更新模式统计
            patterns = self._extract_patterns(files)
            for pattern in patterns:
                self.conn.execute(
                    "INSERT INTO pattern_stats (pattern, success, fail) VALUES (?, ?, ?) "
                    "ON CONFLICT(pattern) DO UPDATE SET "
                    "success = success + CASE WHEN ? THEN 1 ELSE 0 END, "
                    "fail = fail + CASE WHEN ? THEN 1 ELSE 0 END",
                    (pattern, 1 if success else 0, 0 if success else 1, success, not success)
                )

            self.conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record outcome: {e}")

    def _extract_patterns(self, files: List[str]) -> List[str]:
        """提取文件模式"""
        patterns = set()
        for f in files:
            if "tests/" in f:
                patterns.add("tests_file")
            elif f.endswith(".py"):
                patterns.add("python_file")
            elif any(dangerous in f for dangerous in ["server.py", "template_engine/", "ai_self_healing/"]):
                patterns.add("high_risk_file")
        return list(patterns)

    def get_file_success_rate(self, file: str) -> Tuple[float, int]:
        """获取文件成功率"""
        cursor = self.conn.execute(
            "SELECT success, fail FROM file_stats WHERE file = ?", (file,)
        )
        row = cursor.fetchone()

        if not row:
            return 0.5, 0

        total = row["success"] + row["fail"]
        if total < WEIGHTS["file_success_min_samples"]:
            return 0.5, total

        rate = row["success"] / total

        # 检查连续失败
        recent_runs = self._get_recent_runs(file)
        consecutive_failures = 0
        for run in reversed(recent_runs):
            if not run["success"]:
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= 2:
            rate = rate * (1 / WEIGHTS["consecutive_failure_weight"])

        return rate, total

    def _get_recent_runs(self, file: str, limit: int = 5) -> List[Dict]:
        """获取文件的最近运行记录"""
        cursor = self.conn.execute(
            "SELECT success, timestamp FROM file_runs WHERE file = ? ORDER BY timestamp DESC LIMIT ?",
            (file, limit)
        )
        return [{"success": bool(row["success"]), "timestamp": row["timestamp"]} for row in cursor.fetchall()]

    def get_skill_success_rate(self, skill: str) -> float:
        """获取技能成功率"""
        cursor = self.conn.execute(
            "SELECT success, fail FROM skill_stats WHERE skill = ?", (skill,)
        )
        row = cursor.fetchone()

        if not row:
            return 0.5

        total = row["success"] + row["fail"]
        if total == 0:
            return 0.5

        return row["success"] / total

    def get_high_risk_files(self, files: List[str]) -> List[str]:
        """获取高风险文件列表"""
        high_risk = []
        for file in files:
            rate, samples = self.get_file_success_rate(file)
            if samples >= WEIGHTS["file_success_min_samples"] and rate < WEIGHTS["high_failure_threshold"]:
                high_risk.append(file)
        return high_risk

    def get_recommended_skills(self, files: List[str], base_skills: List[str]) -> List[str]:
        """获取基于历史加权的推荐技能"""
        recommended = list(base_skills)

        high_risk = self.get_high_risk_files(files)
        if high_risk:
            if "self-healing-executor" not in recommended:
                recommended.insert(0, "self-healing-executor")

        skill_rates = [(s, self.get_skill_success_rate(s)) for s in recommended]
        skill_rates.sort(key=lambda x: x[1], reverse=True)

        return [s[0] for s in skill_rates]

    def predict_failure_risk(self, files: List[str]) -> Dict:
        """预测失败风险"""
        risk_level = "low"
        risk_files = []
        predictions = []

        for file in files:
            rate, samples = self.get_file_success_rate(file)

            if samples >= WEIGHTS["file_success_min_samples"]:
                if rate < 0.3:
                    risk_level = "high"
                    risk_files.append(file)
                    predictions.append({
                        "file": file,
                        "risk": "high",
                        "success_rate": rate,
                        "recommendation": "preempt_self_healing"
                    })
                elif rate < 0.5:
                    risk_level = "medium"
                    if file not in risk_files:
                        risk_files.append(file)
                    predictions.append({
                        "file": file,
                        "risk": "medium",
                        "success_rate": rate,
                        "recommendation": "add_monitoring"
                    })

        return {
            "risk_level": risk_level,
            "risk_files": risk_files,
            "predictions": predictions,
            "files_analyzed": len(files)
        }

    def get_trend_analysis(self, chain_name: str = None, days: int = 7) -> Dict:
        """获取趋势分析（时间序列）"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        if chain_name:
            cursor = self.conn.execute(
                """SELECT DATE(timestamp) as date, AVG(success) as avg_success, COUNT(*) as count
                   FROM file_runs WHERE chain = ? AND timestamp >= ?
                   GROUP BY DATE(timestamp) ORDER BY date""",
                (chain_name, cutoff)
            )
        else:
            cursor = self.conn.execute(
                """SELECT DATE(timestamp) as date, AVG(success) as avg_success, COUNT(*) as count
                   FROM file_runs WHERE timestamp >= ?
                   GROUP BY DATE(timestamp) ORDER BY date""",
                (cutoff,)
            )

        rows = cursor.fetchall()
        if not rows:
            return {"trend": "no_data", "data_points": 0}

        success_rates = [row["avg_success"] for row in rows]
        dates = [row["date"] for row in rows]

        # 简单趋势计算
        if len(success_rates) >= 2:
            recent_avg = sum(success_rates[-3:]) / min(len(success_rates[-3:]), 3)
            older_avg = sum(success_rates[:3]) / min(len(success_rates[:3]), 3)

            if recent_avg > older_avg + 0.1:
                trend = "improving"
            elif recent_avg < older_avg - 0.1:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "dates": dates,
            "success_rates": success_rates,
            "data_points": len(rows)
        }


# 全局实例
_learning_engine: Optional[LearningEngine] = None


def get_learning_engine() -> LearningEngine:
    """获取学习引擎单例"""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine()
    return _learning_engine


def record_chain_outcome(chain_name: str, skills: List[str], files: List[str], success: bool):
    """记录链条执行结果"""
    engine = get_learning_engine()
    engine.record_outcome(chain_name, skills, files, success)


def get_recommended_skills_for_files(files: List[str], base_skills: List[str] = None) -> List[str]:
    """获取文件的推荐技能"""
    engine = get_learning_engine()

    if base_skills is None:
        from skill_selector_scripts import get_skills_for_files
        skill_map = get_skills_for_files(files)
        base_skills = list(skill_map.keys())

    return engine.get_recommended_skills(files, base_skills)


def predict_failure_for_files(files: List[str]) -> Dict:
    """预测文件的失败风险"""
    engine = get_learning_engine()
    return engine.predict_failure_risk(files)


def get_trend_analysis(chain_name: str = None, days: int = 7) -> Dict:
    """获取趋势分析"""
    engine = get_learning_engine()
    return engine.get_trend_analysis(chain_name, days)


# ============ 时间序列预测 ============

def predict_success_rate(chain_name: str = None, days_history: int = 14, days_ahead: int = 3) -> Dict:
    """预测未来成功率（简单线性回归 + 移动平均）"""
    engine = get_learning_engine()
    conn = engine.conn

    cutoff = (datetime.now() - timedelta(days=days_history)).isoformat()

    if chain_name:
        cursor = conn.execute(
            """SELECT DATE(timestamp) as date, AVG(success) as avg_success, COUNT(*) as count
               FROM file_runs WHERE chain = ? AND timestamp >= ?
               GROUP BY DATE(timestamp) ORDER BY date""",
            (chain_name, cutoff)
        )
    else:
        cursor = conn.execute(
            """SELECT DATE(timestamp) as date, AVG(success) as avg_success, COUNT(*) as count
               FROM file_runs WHERE timestamp >= ?
               GROUP BY DATE(timestamp) ORDER BY date""",
            (cutoff,)
        )

    rows = cursor.fetchall()
    if not rows or len(rows) < 3:
        return {
            "status": "insufficient_data",
            "message": "需要至少3天数据",
            "prediction": 0.5,
            "confidence": 0.0,
            "chain": chain_name or "all",
            "risk": "unknown",
            "recommendation": "暂无足够数据",
            "trend_slope": 0,
            "data_points": 0
        }

    # 提取时间序列
    dates = [row["date"] for row in rows]
    rates = [row["avg_success"] for row in rows]
    counts = [row["count"] for row in rows]

    # 简单移动平均预测
    recent_window = min(5, len(rates))
    recent_avg = sum(rates[-recent_window:]) / recent_window

    # 加权平均（越近的权重越大）
    weights = list(range(1, len(rates) + 1))
    weighted_sum = sum(r * w for r, w in zip(rates, weights))
    weighted_avg = weighted_sum / sum(weights)

    # 线性回归斜率
    n = len(rates)
    if n >= 2:
        x_mean = (n - 1) / 2
        y_mean = sum(rates) / n
        numerator = sum((i - x_mean) * (rates[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0
    else:
        slope = 0

    # 预测未来值
    last_idx = n - 1
    predicted_rate = weighted_avg + slope * (last_idx + days_ahead)

    # 限制在 0-1 范围内
    predicted_rate = max(0.0, min(1.0, predicted_rate))

    # 置信度（基于数据量和趋势一致性）
    consistency = 1.0 - min(1.0, abs(slope) * 10)  # 斜率越小越一致
    sample_confidence = min(1.0, n / 14)  # 14天数据为满分
    confidence = (consistency + sample_confidence) / 2

    # 风险评估
    if predicted_rate < 0.3:
        risk = "high"
        recommendation = "考虑使用更安全的链条或添加额外验证"
    elif predicted_rate < 0.5:
        risk = "medium"
        recommendation = "建议启用 self-healing 预防机制"
    else:
        risk = "low"
        recommendation = "可以正常执行"

    return {
        "status": "ok",
        "chain": chain_name or "all",
        "prediction": round(predicted_rate, 3),
        "confidence": round(confidence, 2),
        "trend_slope": round(slope, 4),
        "risk": risk,
        "recommendation": recommendation,
        "data_points": n,
        "prediction_days_ahead": days_ahead,
        "historical_avg": round(sum(rates) / len(rates), 3),
        "recent_avg": round(recent_avg, 3),
        "dates": dates[-7:],  # 最近7天
        "rates": [round(r, 3) for r in rates[-7:]]
    }


def get_prediction_report(chain_names: List[str] = None, days_ahead: int = 3) -> Dict:
    """获取多个链条的预测报告"""
    if chain_names is None:
        # 全部链条
        results = {}
        conn = get_learning_engine().conn
        cursor = conn.execute("SELECT DISTINCT chain FROM file_runs")
        chain_names = [row["chain"] for row in cursor.fetchall()]

    predictions = []
    for chain in chain_names:
        pred = predict_success_rate(chain, days_ahead=days_ahead)
        predictions.append({
            "chain": chain,
            "predicted_success_rate": pred["prediction"],
            "confidence": pred["confidence"],
            "risk": pred["risk"],
            "recommendation": pred["recommendation"]
        })

    # 按风险排序
    risk_order = {"high": 0, "medium": 1, "low": 2}
    predictions.sort(key=lambda x: risk_order.get(x["risk"], 2))

    return {
        "generated_at": datetime.now().isoformat(),
        "prediction_days_ahead": days_ahead,
        "predictions": predictions,
        "high_risk_chains": [p["chain"] for p in predictions if p["risk"] == "high"],
        "recommended_chains": [p["chain"] for p in predictions if p["risk"] == "low"]
    }


# CLI 入口
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Learning Engine CLI")
    parser.add_argument("--predict", "-p", action="store_true", help="预测成功率")
    parser.add_argument("--chain", "-c", help="链条名称")
    parser.add_argument("--days", "-d", type=int, default=14, help="历史天数")
    parser.add_argument("--ahead", "-a", type=int, default=3, help="预测天数")
    parser.add_argument("--report", "-r", action="store_true", help="预测报告")
    args = parser.parse_args()

    if args.predict:
        result = predict_success_rate(args.chain, args.days, args.ahead)
        print(f"\n📊 预测结果 (链条: {result.get('chain', 'all')})")
        print(f"   预测成功率: {result['prediction']:.1%}")
        print(f"   置信度: {result['confidence']:.0%}")
        print(f"   趋势斜率: {result['trend_slope']}")
        print(f"   风险等级: {result['risk']}")
        print(f"   建议: {result['recommendation']}")
        print()

    if args.report:
        report = get_prediction_report(days_ahead=args.ahead)
        print(f"\n📈 预测报告 (生成于: {report['generated_at'][:19]})")
        print(f"   预测范围: 未来{args.ahead}天")
        print(f"\n   高风险链条: {', '.join(report['high_risk_chains']) or '无'}")
        print(f"   推荐链条: {', '.join(report['recommended_chains']) or '无'}")
        print("\n   详细预测:")
        for p in report["predictions"]:
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p["risk"], "⚪")
            print(f"   {emoji} {p['chain']}: {p['predicted_success_rate']:.0%} (置信度: {p['confidence']:.0%})")
        print()
