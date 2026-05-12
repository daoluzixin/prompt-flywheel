#!/usr/bin/env python3
"""
合并独立 Pass（PI-only + KG-only）的输出为 eval-runner 兼容格式。

用法：
  python3 merge-dual-pass.py \
    --pi-dir <PI-only pass 输出目录> \
    --kg-dir <KG-only pass 输出目录> \
    --output-dir <合并后的输出目录>

说明：
  独立 Pass 实验中，PI-only pass 输出的 batch_*.json 只包含 process_issues，
  KG-only pass 输出的 batch_*.json 只包含 knowledge_gaps。
  本脚本将两者按 batch_index 对齐合并，输出 eval-runner 期望的格式：
  每个 batch_*.json 同时包含 process_issues 和 knowledge_gaps。

  如果某个 batch 文件只在一侧存在，另一侧补空数组。
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="合并 PI-only 和 KG-only pass 输出")
    parser.add_argument("--pi-dir", required=True, help="PI-only pass 的 batch_*.json 目录")
    parser.add_argument("--kg-dir", required=True, help="KG-only pass 的 batch_*.json 目录")
    parser.add_argument("--output-dir", required=True, help="合并输出目录")
    return parser.parse_args()


def load_batches(directory: Path) -> dict:
    """加载目录下所有 batch_*.json，返回 {batch_index: data} 的映射"""
    batches = {}
    for f in sorted(directory.glob("batch_*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            batch_idx = data.get("batch_index", int(f.stem.split("_")[1]))
            batches[batch_idx] = data
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  WARNING: 无法解析 {f}: {e}")
    return batches


def main():
    args = parse_args()
    pi_dir = Path(args.pi_dir)
    kg_dir = Path(args.kg_dir)
    output_dir = Path(args.output_dir)

    if not pi_dir.exists():
        print(f"ERROR: PI 目录不存在: {pi_dir}")
        sys.exit(1)
    if not kg_dir.exists():
        print(f"ERROR: KG 目录不存在: {kg_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    pi_batches = load_batches(pi_dir)
    kg_batches = load_batches(kg_dir)

    all_indices = sorted(set(list(pi_batches.keys()) + list(kg_batches.keys())))

    if not all_indices:
        print("ERROR: 未找到任何 batch 文件")
        sys.exit(1)

    print(f"  PI batches: {len(pi_batches)}, KG batches: {len(kg_batches)}")
    print(f"  合并 batch indices: {all_indices}")

    total_pi = 0
    total_kg = 0

    for idx in all_indices:
        pi_data = pi_batches.get(idx, {})
        kg_data = kg_batches.get(idx, {})

        process_issues = pi_data.get("process_issues", [])
        knowledge_gaps = kg_data.get("knowledge_gaps", [])

        total_pi += len(process_issues)
        total_kg += len(knowledge_gaps)

        merged = {
            "batch_index": idx,
            "process_issues": process_issues,
            "knowledge_gaps": knowledge_gaps
        }

        output_file = output_dir / f"batch_{idx}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"\n  合并完成:")
    print(f"    Total process_issues: {total_pi}")
    print(f"    Total knowledge_gaps: {total_kg}")
    print(f"    输出目录: {output_dir}")
    print(f"    输出文件数: {len(all_indices)}")


if __name__ == "__main__":
    main()
