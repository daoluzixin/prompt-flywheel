#!/usr/bin/env python3
"""分析 KG 的 FP 和 FN 条目"""
import json, os
from collections import defaultdict

gt = json.load(open('daily-report-optimized/eval/baseline/ground_truth.json'))
pred_dir = 'daily-report-optimized/eval/v1.4b-results'

# Load GT KG
gt_kg = []
for d in gt['documents']:
    for i in d.get('expected_knowledge_gaps', []):
        gt_kg.append(dict(i, contentId=d['contentId']))

# Load predicted KG
pred_kg = []
for f in sorted(os.listdir(pred_dir)):
    if f.endswith('.json'):
        pred_kg.extend(json.load(open(os.path.join(pred_dir, f))).get('knowledge_gaps', []))

# Match by (contentId, category)
gt_counts = defaultdict(int)
for i in gt_kg:
    gt_counts[(i['contentId'], i['category'])] += 1

pred_counts = defaultdict(int)
for i in pred_kg:
    pred_counts[(i['contentId'], i['category'])] += 1

all_keys = set(list(gt_counts.keys()) + list(pred_counts.keys()))

print('=== KG FP (predicted but not in GT) ===')
for k in sorted(all_keys):
    e = gt_counts.get(k, 0)
    p = pred_counts.get(k, 0)
    if p > e:
        items = [i for i in pred_kg if (i['contentId'], i['category']) == k]
        for item in items[e:]:
            print(f'  {k[0]} | {k[1]} | {item["description"][:70]}')

print()
print('=== KG FN (in GT but not predicted) ===')
for k in sorted(all_keys):
    e = gt_counts.get(k, 0)
    p = pred_counts.get(k, 0)
    if e > p:
        items = [i for i in gt_kg if (i['contentId'], i['category']) == k]
        for item in items[p:]:
            print(f'  {k[0]} | {k[1]} | {item["description"][:70]}')
