#!/usr/bin/env python3
"""
Spec 日报 Prompt 评估脚本 V3

用法：
  python3 eval-runner.py --predicted <batch_*.json 目录> --version v3.0
  python3 eval-runner.py --predicted <目录> --version v3.0 --include-silver
  python3 eval-runner.py --predicted <目录> --version v3.0 --difficulty-breakdown

功能：
  1. 加载 baseline/ground_truth.json (V3 schema) 中的人工标注
  2. 加载指定目录下的 batch_*.json（prompt 实际输出）
  3. 按 contentId + category 做匹配，计算 TP/FP/FN
  4. 输出 Precision/Recall/F1，按 category 和 difficulty 细分
  5. 检测 confusing_fp（命中 expected_negatives 的误报）
  6. 将结果追加到 metrics.json
  7. 对比上一版本，高亮退化指标

V3 新特性：
  - 支持 tier 过滤（默认只跑 golden，--include-silver 加入 silver）
  - difficulty breakdown（按 easy/medium/hard 分析召回率）
  - confusing_fp 检测（命中 expected_negatives 的 FP 单独统计）
  - schema 版本兼容性检查
"""

import argparse
import json
import hashlib
import os
import sys
from datetime import date
from pathlib import Path
from collections import defaultdict

EVAL_DIR = Path(__file__).parent
BASELINE_FILE = EVAL_DIR / "baseline" / "ground_truth.json"
METRICS_FILE = EVAL_DIR / "metrics.json"

SUPPORTED_SCHEMAS = ["2.0", "3.0"]


def load_ground_truth(include_silver=False):
    """加载人工标注的 ground truth，支持 tier 过滤"""
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    schema = data.get("schema", "1.0")
    if schema not in SUPPORTED_SCHEMAS:
        print(f"⚠️  GT schema {schema} 未经测试，建议升级 eval-runner")

    documents = data["documents"]

    # V3: tier 过滤
    if not include_silver:
        documents = [d for d in documents if d.get("tier", "golden") == "golden"]

    return documents, data


def load_predictions(predicted_dir: Path):
    """加载 batch_*.json 文件，合并为统一结构"""
    all_process_issues = []
    all_knowledge_gaps = []

    # 支持 batch_*.json 和 batch-*.json 两种命名
    batch_files = sorted(list(predicted_dir.glob("batch_*.json")) + list(predicted_dir.glob("batch-*.json")))
    if not batch_files:
        print(f"⚠️  未找到 batch 文件: {predicted_dir}")
        return [], []

    for batch_file in batch_files:
        with open(batch_file, "r", encoding="utf-8") as f:
            batch = json.load(f)
        all_process_issues.extend(batch.get("process_issues", []))
        all_knowledge_gaps.extend(batch.get("knowledge_gaps", []))

    return all_process_issues, all_knowledge_gaps


def match_items(expected_list, predicted_list, match_fields=("contentId", "category")):
    """
    匹配逻辑：
    - 两条记录的 contentId 和 category 完全一致视为匹配（TP）
    - predicted 中有但 expected 中无的视为 FP
    - expected 中有但 predicted 中无的视为 FN

    注意：同一 contentId + category 可能有多条（同篇文档同一 category 多个识别），
    此时按数量做贪心匹配。
    """
    expected_counts = defaultdict(int)
    for item in expected_list:
        key = tuple(item.get(f, "") for f in match_fields)
        expected_counts[key] += 1

    predicted_counts = defaultdict(int)
    for item in predicted_list:
        key = tuple(item.get(f, "") for f in match_fields)
        predicted_counts[key] += 1

    tp = 0
    fp = 0
    fn = 0

    all_keys = set(list(expected_counts.keys()) + list(predicted_counts.keys()))
    for key in all_keys:
        e = expected_counts.get(key, 0)
        p = predicted_counts.get(key, 0)
        matched = min(e, p)
        tp += matched
        fp += max(0, p - e)
        fn += max(0, e - p)

    return tp, fp, fn


def calc_metrics(tp, fp, fn):
    """计算 Precision, Recall, F1"""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


def category_breakdown(expected_list, predicted_list, categories, match_fields=("contentId", "category")):
    """按 category 细分统计"""
    breakdown = {}
    for cat in categories:
        exp_filtered = [x for x in expected_list if x.get("category") == cat]
        pred_filtered = [x for x in predicted_list if x.get("category") == cat]
        tp, fp, fn = match_items(exp_filtered, pred_filtered, match_fields)
        p, r, f = calc_metrics(tp, fp, fn)
        breakdown[cat] = {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}
    return breakdown


def difficulty_breakdown(expected_list, predicted_list, match_fields=("contentId", "category")):
    """
    按 difficulty 分析召回率：
    对于每个 difficulty 级别，统计有多少 expected 被 matched（recall）。
    注意：predicted 没有 difficulty 字段，所以只能从 expected 侧分析 FN 分布。
    """
    difficulties = ["easy", "medium", "hard"]
    breakdown = {}

    predicted_counts = defaultdict(int)
    for item in predicted_list:
        key = tuple(item.get(f, "") for f in match_fields)
        predicted_counts[key] += 1

    for diff in difficulties:
        diff_items = [x for x in expected_list if x.get("difficulty") == diff]
        total = len(diff_items)
        if total == 0:
            breakdown[diff] = {"total": 0, "recalled": 0, "missed": 0, "recall": 0.0}
            continue

        # 对于每个 difficulty，统计有多少能被 predicted 匹配
        # 这里用简化逻辑：按 key 分组后做贪心
        expected_by_key = defaultdict(int)
        for item in diff_items:
            key = tuple(item.get(f, "") for f in match_fields)
            expected_by_key[key] += 1

        recalled = 0
        for key, count in expected_by_key.items():
            matched = min(count, predicted_counts.get(key, 0))
            recalled += matched

        missed = total - recalled
        recall = recalled / total if total > 0 else 0.0
        breakdown[diff] = {
            "total": total,
            "recalled": recalled,
            "missed": missed,
            "recall": round(recall, 4)
        }

    return breakdown


def detect_confusing_fps(documents, predicted_list, item_type="process_issues"):
    """
    检测 confusing FP：predicted 命中了 expected_negatives 中定义的 category。
    这类 FP 是"可预期的误报"，有助于 prompt 改进。
    """
    confusing_fps = []

    for doc in documents:
        negatives = doc.get("expected_negatives", [])
        neg_type = "confusing_pi" if item_type == "process_issues" else "confusing_kg"
        relevant_negs = [n for n in negatives if n.get("type") == neg_type]

        if not relevant_negs:
            continue

        content_id = doc["contentId"]
        neg_categories = {n["category"] for n in relevant_negs}

        # 检查 predicted 中是否有命中这些 negative categories 的
        for pred in predicted_list:
            if pred.get("contentId") == content_id and pred.get("category") in neg_categories:
                confusing_fps.append({
                    "contentId": content_id,
                    "predicted_category": pred.get("category"),
                    "neg_id": next((n["id"] for n in relevant_negs if n["category"] == pred.get("category")), "unknown"),
                    "reason": next((n.get("description", "") for n in relevant_negs if n["category"] == pred.get("category")), "")
                })

    return confusing_fps


def compute_prompt_hash(prompt_path: Path) -> str:
    """计算 prompt 文件的 MD5 hash，用于标识版本"""
    if prompt_path.exists():
        content = prompt_path.read_bytes()
        return hashlib.md5(content).hexdigest()[:12]
    return "unknown"


def print_comparison(current, previous):
    """对比当前与上一版本，高亮退化"""
    print("\n" + "=" * 60)
    print("📊 与上一版本对比")
    print("=" * 60)

    for metric_type in ["process_issues", "knowledge_gaps"]:
        print(f"\n  [{metric_type}]")
        curr = current[metric_type]
        prev = previous[metric_type]

        for field in ["precision", "recall", "f1"]:
            c_val = curr.get(field, 0) or 0
            p_val = prev.get(field, 0) or 0
            delta = c_val - p_val
            indicator = "✅" if delta >= 0 else "❌ 退化"
            print(f"    {field}: {p_val:.4f} → {c_val:.4f} ({delta:+.4f}) {indicator}")


def main():
    parser = argparse.ArgumentParser(description="Spec 日报 Prompt 评估 V3")
    parser.add_argument("--predicted", required=True, help="包含 batch_*.json 的目录路径")
    parser.add_argument("--version", required=True, help="本次评估的版本号，如 v3.0")
    parser.add_argument("--note", default="", help="本次评估的备注")
    parser.add_argument("--prompt-file", default=None,
                        help="analyze-batch-prompt.md 路径，用于计算 hash")
    parser.add_argument("--include-silver", action="store_true",
                        help="包含 silver tier 文档（默认只评估 golden）")
    parser.add_argument("--difficulty-breakdown", action="store_true",
                        help="输出按 difficulty 分级的召回率分析")
    parser.add_argument("--subset-only", action="store_true",
                        help="只评估预测和 ground_truth 都覆盖的 contentId 子集")
    parser.add_argument("--detect-confusing", action="store_true",
                        help="检测命中 expected_negatives 的 confusing FP")
    args = parser.parse_args()

    predicted_dir = Path(args.predicted)
    if not predicted_dir.exists():
        print(f"❌ 目录不存在: {predicted_dir}")
        sys.exit(1)

    if not BASELINE_FILE.exists():
        print(f"❌ baseline 文件不存在: {BASELINE_FILE}")
        sys.exit(1)

    # 加载数据
    documents, gt_data = load_ground_truth(include_silver=args.include_silver)
    if not documents:
        print("❌ ground_truth.json 中没有标注数据")
        sys.exit(1)

    tier_label = "golden+silver" if args.include_silver else "golden-only"
    print(f"  [tier] 评估模式: {tier_label} ({len(documents)} 篇)")

    pred_process_issues, pred_knowledge_gaps = load_predictions(predicted_dir)

    # 规范化 contentId：预测结果可能缺少 -catpaw 后缀
    gt_id_map = {}
    for doc in documents:
        full_id = doc["contentId"]
        if "-catpaw" in full_id:
            short_id = full_id.split("-catpaw")[0]
            gt_id_map[short_id] = full_id
        gt_id_map[full_id] = full_id

    def normalize_content_id(cid):
        return gt_id_map.get(cid, cid)

    for item in pred_process_issues:
        item["contentId"] = normalize_content_id(item.get("contentId", ""))
    for item in pred_knowledge_gaps:
        item["contentId"] = normalize_content_id(item.get("contentId", ""))

    # subset-only 模式
    if args.subset_only:
        predicted_ids = set(
            x.get("contentId", "") for x in pred_process_issues + pred_knowledge_gaps
        )
        documents = [d for d in documents if d["contentId"] in predicted_ids]
        print(f"  [subset-only] 只评估预测覆盖的 {len(documents)} 篇文档")

    # 提取 ground truth（展平为列表）
    gt_process_issues = []
    gt_knowledge_gaps = []
    for doc in documents:
        for item in doc.get("expected_process_issues", []):
            enriched = dict(item)
            enriched["contentId"] = doc["contentId"]
            gt_process_issues.append(enriched)
        for item in doc.get("expected_knowledge_gaps", []):
            enriched = dict(item)
            enriched["contentId"] = doc["contentId"]
            gt_knowledge_gaps.append(enriched)

    # 计算整体指标
    pi_tp, pi_fp, pi_fn = match_items(gt_process_issues, pred_process_issues)
    kg_tp, kg_fp, kg_fn = match_items(gt_knowledge_gaps, pred_knowledge_gaps)

    pi_precision, pi_recall, pi_f1 = calc_metrics(pi_tp, pi_fp, pi_fn)
    kg_precision, kg_recall, kg_f1 = calc_metrics(kg_tp, kg_fp, kg_fn)

    # 按 category 细分
    pi_categories = ["spec1.spy", "spec2.clarify", "spec3.plan", "spec4.tasks", "spec5.impl"]
    kg_categories = ["系统架构", "业务规则", "技术栈", "组织流程", "接口约束", "数据模型"]

    pi_cat_breakdown = category_breakdown(gt_process_issues, pred_process_issues, pi_categories)
    kg_cat_breakdown = category_breakdown(gt_knowledge_gaps, pred_knowledge_gaps, kg_categories)

    # 计算 prompt hash
    prompt_path = Path(args.prompt_file) if args.prompt_file else (
        EVAL_DIR.parent / "scripts" / "analyze-batch-prompt.md"
    )
    prompt_hash = compute_prompt_hash(prompt_path)

    # 组装结果
    result = {
        "version": args.version,
        "date": date.today().isoformat(),
        "prompt_hash": prompt_hash,
        "note": args.note,
        "tier": tier_label,
        "gt_schema": gt_data.get("schema", "unknown"),
        "documents_evaluated": len(documents),
        "process_issues": {
            "total_expected": len(gt_process_issues),
            "total_predicted": len(pred_process_issues),
            "true_positives": pi_tp,
            "false_positives": pi_fp,
            "false_negatives": pi_fn,
            "precision": pi_precision,
            "recall": pi_recall,
            "f1": pi_f1
        },
        "knowledge_gaps": {
            "total_expected": len(gt_knowledge_gaps),
            "total_predicted": len(pred_knowledge_gaps),
            "true_positives": kg_tp,
            "false_positives": kg_fp,
            "false_negatives": kg_fn,
            "precision": kg_precision,
            "recall": kg_recall,
            "f1": kg_f1
        },
        "category_breakdown": {
            "process_issues": {cat: {"tp": v["tp"], "fp": v["fp"], "fn": v["fn"]}
                              for cat, v in pi_cat_breakdown.items()},
            "knowledge_gaps": {cat: {"tp": v["tp"], "fp": v["fp"], "fn": v["fn"]}
                              for cat, v in kg_cat_breakdown.items()}
        }
    }

    # V3: difficulty breakdown
    if args.difficulty_breakdown:
        pi_diff = difficulty_breakdown(gt_process_issues, pred_process_issues)
        kg_diff = difficulty_breakdown(gt_knowledge_gaps, pred_knowledge_gaps)
        result["difficulty_breakdown"] = {
            "process_issues": pi_diff,
            "knowledge_gaps": kg_diff
        }

    # V3: confusing FP 检测
    confusing_pi_fps = []
    confusing_kg_fps = []
    if args.detect_confusing:
        confusing_pi_fps = detect_confusing_fps(documents, pred_process_issues, "process_issues")
        confusing_kg_fps = detect_confusing_fps(documents, pred_knowledge_gaps, "knowledge_gaps")
        result["confusing_fps"] = {
            "process_issues": confusing_pi_fps,
            "knowledge_gaps": confusing_kg_fps
        }

    # 输出到终端
    print("=" * 60)
    print(f"📋 Spec 日报 Prompt 评估结果 — {args.version}")
    print(f"   Prompt Hash: {prompt_hash}")
    print(f"   GT Schema: {gt_data.get('schema', 'unknown')}")
    print(f"   基准集文档数: {len(documents)} ({tier_label})")
    print("=" * 60)

    print(f"\n  [process_issues]")
    print(f"    Expected: {len(gt_process_issues)}, Predicted: {len(pred_process_issues)}")
    print(f"    TP={pi_tp}, FP={pi_fp}, FN={pi_fn}")
    print(f"    Precision: {pi_precision:.4f}")
    print(f"    Recall:    {pi_recall:.4f}")
    print(f"    F1:        {pi_f1:.4f}")

    print(f"\n  [knowledge_gaps]")
    print(f"    Expected: {len(gt_knowledge_gaps)}, Predicted: {len(pred_knowledge_gaps)}")
    print(f"    TP={kg_tp}, FP={kg_fp}, FN={kg_fn}")
    print(f"    Precision: {kg_precision:.4f}")
    print(f"    Recall:    {kg_recall:.4f}")
    print(f"    F1:        {kg_f1:.4f}")

    print(f"\n  [category 细分 - P/R/F1]")
    for cat, stats in pi_cat_breakdown.items():
        if stats["tp"] + stats["fp"] + stats["fn"] > 0:
            print(f"    {cat}: TP={stats['tp']} FP={stats['fp']} FN={stats['fn']} | P={stats['precision']:.2f} R={stats['recall']:.2f} F1={stats['f1']:.2f}")
    for cat, stats in kg_cat_breakdown.items():
        if stats["tp"] + stats["fp"] + stats["fn"] > 0:
            print(f"    {cat}: TP={stats['tp']} FP={stats['fp']} FN={stats['fn']} | P={stats['precision']:.2f} R={stats['recall']:.2f} F1={stats['f1']:.2f}")

    # difficulty breakdown 输出
    if args.difficulty_breakdown:
        print(f"\n  [difficulty 召回分析]")
        print(f"    Process Issues:")
        for diff, stats in pi_diff.items():
            if stats["total"] > 0:
                print(f"      {diff}: {stats['recalled']}/{stats['total']} recalled (R={stats['recall']:.2f}), {stats['missed']} missed")
        print(f"    Knowledge Gaps:")
        for diff, stats in kg_diff.items():
            if stats["total"] > 0:
                print(f"      {diff}: {stats['recalled']}/{stats['total']} recalled (R={stats['recall']:.2f}), {stats['missed']} missed")

    # confusing FP 输出
    if args.detect_confusing and (confusing_pi_fps or confusing_kg_fps):
        print(f"\n  [confusing FP 检测]")
        for cfp in confusing_pi_fps:
            print(f"    ⚠️  PI: {cfp['contentId']} → {cfp['predicted_category']} (原因: {cfp['reason'][:60]})")
        for cfp in confusing_kg_fps:
            print(f"    ⚠️  KG: {cfp['contentId']} → {cfp['predicted_category']} (原因: {cfp['reason'][:60]})")

    # 追加到 metrics.json
    if METRICS_FILE.exists():
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)
    else:
        metrics_data = {"schema_version": "3.0", "description": "Eval iterations", "iterations": []}

    # 与上一版本对比
    if metrics_data["iterations"]:
        last = metrics_data["iterations"][-1]
        if last.get("process_issues", {}).get("precision") is not None:
            print_comparison(result, last)

    metrics_data["iterations"].append(result)

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 结果已追加到 {METRICS_FILE}")

    # 退化检测
    has_regression = False
    if len(metrics_data["iterations"]) >= 2:
        prev = metrics_data["iterations"][-2]
        for metric_type in ["process_issues", "knowledge_gaps"]:
            prev_f1 = prev.get(metric_type, {}).get("f1")
            curr_f1 = result[metric_type]["f1"]
            if prev_f1 is not None and curr_f1 < prev_f1 - 0.05:
                has_regression = True
                print(f"\n⚠️  警告：{metric_type} F1 下降超过 5%，建议回滚！")

    if has_regression:
        sys.exit(2)  # 退出码 2 表示检测到退化


if __name__ == "__main__":
    main()
