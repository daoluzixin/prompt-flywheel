#!/usr/bin/env python3
"""分析 v1.8 (round9-run13) 的 FN 和 FP 具体条目"""
import json, os
from collections import defaultdict

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(os.path.dirname(base_dir))

# Load GT (golden only)
gt = json.load(open(os.path.join(base_dir, 'baseline/ground_truth.json')))
golden_docs = [d for d in gt['documents'] if d['tier'] == 'golden']

# Build GT counts by (contentId, category) for PI and KG
gt_pi_counts = defaultdict(int)
gt_pi_items = []
for d in golden_docs:
    for item in d.get('expected_process_issues', []):
        key = (d['contentId'], item['category'])
        gt_pi_counts[key] += 1
        gt_pi_items.append({**item, 'contentId': d['contentId']})

gt_kg_counts = defaultdict(int)
gt_kg_items = []
for d in golden_docs:
    for item in d.get('expected_knowledge_gaps', []):
        key = (d['contentId'], item['category'])
        gt_kg_counts[key] += 1
        gt_kg_items.append({**item, 'contentId': d['contentId']})

# Load round9-run13 predictions
pred_pi = []
pred_kg = []
run_dir = os.path.join(base_dir, 'runs/round9-run13')
for f in sorted(os.listdir(run_dir)):
    if f.endswith('.json'):
        data = json.load(open(os.path.join(run_dir, f)))
        pred_pi.extend(data.get('process_issues', []))
        pred_kg.extend(data.get('knowledge_gaps', []))

# Build pred counts
pred_pi_counts = defaultdict(int)
for item in pred_pi:
    key = (item['contentId'], item['category'])
    pred_pi_counts[key] += 1

pred_kg_counts = defaultdict(int)
for item in pred_kg:
    key = (item['contentId'], item['category'])
    pred_kg_counts[key] += 1

# Find FN (GT items not matched by predictions)
print('=== PI False Negatives (missed by model) ===')
pi_fn_items = []
all_pi_keys = set(list(gt_pi_counts.keys()) + list(pred_pi_counts.keys()))
for k in sorted(all_pi_keys):
    expected = gt_pi_counts.get(k, 0)
    predicted = pred_pi_counts.get(k, 0)
    if expected > predicted:
        items = [i for i in gt_pi_items if (i['contentId'], i['category']) == k]
        for item in items[predicted:]:
            pi_fn_items.append(item)
            print(f'  [{item["id"]}] {item["contentId"]} | {item["category"]} | diff={item["difficulty"]}')
            print(f'    desc: {item["description"]}')
            print(f'    quote: {item["quote"][:100]}')
            print()

print(f'Total PI FN: {len(pi_fn_items)}')
print()

print('=== KG False Negatives (missed by model) ===')
kg_fn_items = []
all_kg_keys = set(list(gt_kg_counts.keys()) + list(pred_kg_counts.keys()))
for k in sorted(all_kg_keys):
    expected = gt_kg_counts.get(k, 0)
    predicted = pred_kg_counts.get(k, 0)
    if expected > predicted:
        items = [i for i in gt_kg_items if (i['contentId'], i['category']) == k]
        for item in items[predicted:]:
            kg_fn_items.append(item)
            print(f'  [{item["id"]}] {item["contentId"]} | {item["category"]} | diff={item["difficulty"]}')
            print(f'    desc: {item["description"]}')
            print(f'    quote: {item["quote"][:100]}')
            print()

print(f'Total KG FN: {len(kg_fn_items)}')
print()

# Also show FP
print('=== PI False Positives ===')
pi_fp_items = []
for k in sorted(all_pi_keys):
    expected = gt_pi_counts.get(k, 0)
    predicted = pred_pi_counts.get(k, 0)
    if predicted > expected:
        items = [i for i in pred_pi if (i['contentId'], i['category']) == k]
        for item in items[expected:]:
            pi_fp_items.append(item)
            print(f'  {item["contentId"]} | {item["category"]}')
            print(f'    desc: {item["description"]}')
            print(f'    quote: {item["quote"][:100]}')
            print()

print(f'Total PI FP: {len(pi_fp_items)}')
print()

print('=== KG False Positives ===')
kg_fp_items = []
for k in sorted(all_kg_keys):
    expected = gt_kg_counts.get(k, 0)
    predicted = pred_kg_counts.get(k, 0)
    if predicted > expected:
        items = [i for i in pred_kg if (i['contentId'], i['category']) == k]
        for item in items[expected:]:
            kg_fp_items.append(item)
            print(f'  {item["contentId"]} | {item["category"]}')
            print(f'    desc: {item["description"]}')
            print(f'    quote: {item["quote"][:100]}')
            print()

print(f'Total KG FP: {len(kg_fp_items)}')

# Summary
print()
print('=== Summary ===')
tp_pi = sum(min(gt_pi_counts.get(k, 0), pred_pi_counts.get(k, 0)) for k in all_pi_keys)
tp_kg = sum(min(gt_kg_counts.get(k, 0), pred_kg_counts.get(k, 0)) for k in all_kg_keys)
fp_pi = len(pi_fp_items)
fn_pi = len(pi_fn_items)
fp_kg = len(kg_fp_items)
fn_kg = len(kg_fn_items)
print(f'PI: TP={tp_pi}, FP={fp_pi}, FN={fn_pi}, P={tp_pi/(tp_pi+fp_pi):.4f}, R={tp_pi/(tp_pi+fn_pi):.4f}, F1={2*tp_pi/(2*tp_pi+fp_pi+fn_pi):.4f}')
print(f'KG: TP={tp_kg}, FP={fp_kg}, FN={fn_kg}, P={tp_kg/(tp_kg+fp_kg):.4f}, R={tp_kg/(tp_kg+fn_kg):.4f}, F1={2*tp_kg/(2*tp_kg+fp_kg+fn_kg):.4f}')
