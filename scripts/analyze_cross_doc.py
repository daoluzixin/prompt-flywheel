#!/usr/bin/env python3
"""分析跨文档错位：同一知识点在不同doc被FP/FN"""
import json, os
from collections import defaultdict

gt = json.load(open('daily-report-optimized/eval/baseline/ground_truth.json'))
pred_dir = 'daily-report-optimized/eval/v1.4b-results'

gt_kg = []
for d in gt['documents']:
    for i in d.get('expected_knowledge_gaps', []):
        gt_kg.append(dict(i, contentId=d['contentId']))

pred_kg = []
for f in sorted(os.listdir(pred_dir)):
    if f.endswith('.json'):
        pred_kg.extend(json.load(open(os.path.join(pred_dir, f))).get('knowledge_gaps', []))

# Find cases where same description appears in both FP (wrong doc) and FN (right doc)
print("=== 跨文档错位分析 ===")
print("找 FP 和 FN 中描述高度相似但 contentId 不同的条目\n")

# Collect FP and FN
gt_counts = defaultdict(int)
for i in gt_kg:
    gt_counts[(i['contentId'], i['category'])] += 1
pred_counts = defaultdict(int)
for i in pred_kg:
    pred_counts[(i['contentId'], i['category'])] += 1

all_keys = set(list(gt_counts.keys()) + list(pred_counts.keys()))
fp_items = []
fn_items = []
for k in sorted(all_keys):
    e = gt_counts.get(k, 0)
    p = pred_counts.get(k, 0)
    if p > e:
        items = [i for i in pred_kg if (i['contentId'], i['category']) == k]
        for item in items[e:]:
            fp_items.append(item)
    if e > p:
        items = [i for i in gt_kg if (i['contentId'], i['category']) == k]
        for item in items[p:]:
            fn_items.append(item)

# Check cross-doc matches (same category, similar desc, different doc)
print("--- 同 category + 描述相似 + 不同 doc ---")
matches = []
for fp in fp_items:
    for fn in fn_items:
        if fp['category'] == fn['category'] and fp['contentId'] != fn['contentId']:
            # keyword overlap
            fp_kw = set(fp['description'].replace('，', ' ').replace('、', ' ').replace('：', ' ').split())
            fn_kw = set(fn['description'].replace('，', ' ').replace('、', ' ').replace('：', ' ').split())
            overlap = fp_kw & fn_kw
            if len(overlap) >= 4:
                matches.append((fp, fn, len(overlap)))

matches.sort(key=lambda x: -x[2])
for fp, fn, ol in matches:
    print(f"  [{fp['category']}] overlap={ol}")
    print(f"    FP doc={fp['contentId']}: {fp['description'][:80]}")
    print(f"    FN doc={fn['contentId']}: {fn['description'][:80]}")
    print()

# Check SAME doc, different category (category misclassification)
print("=== 同文档跨 category 错位 ===")
print("--- 同 doc + 不同 category + 描述相似 ---")
for fp in fp_items:
    for fn in fn_items:
        if fp['contentId'] == fn['contentId'] and fp['category'] != fn['category']:
            fp_kw = set(fp['description'].replace('，', ' ').replace('、', ' ').replace('：', ' ').split())
            fn_kw = set(fn['description'].replace('，', ' ').replace('、', ' ').replace('：', ' ').split())
            overlap = fp_kw & fn_kw
            if len(overlap) >= 3:
                print(f"  DOC={fp['contentId']}")
                print(f"    FP [{fp['category']}]: {fp['description'][:80]}")
                print(f"    FN [{fn['category']}]: {fn['description'][:80]}")
                print()

# Now check: 2758031444 FP vs 2757704387 FN (same content diff doc)
print("=== 重点：2758031444 vs 2757704387 ===")
fp_2758031444 = [i for i in fp_items if i['contentId'] == '2758031444-catpaw']
fn_2757704387 = [i for i in fn_items if i['contentId'] == '2757704387-catpaw']
print(f"2758031444 FP ({len(fp_2758031444)}):")
for i in fp_2758031444:
    print(f"  {i['category']}: {i['description'][:80]}")
print(f"\n2757704387 FN ({len(fn_2757704387)}):")
for i in fn_2757704387:
    print(f"  {i['category']}: {i['description'][:80]}")
