#!/usr/bin/env python3
"""详细分析 KG FP/FN 错误模式：重叠检测、类别交叉分析"""
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
        data = json.load(open(os.path.join(pred_dir, f)))
        for i in data.get('knowledge_gaps', []):
            pred_kg.append(i)

# Match by (contentId, category)
gt_counts = defaultdict(int)
for i in gt_kg:
    gt_counts[(i['contentId'], i['category'])] += 1
pred_counts = defaultdict(int)
for i in pred_kg:
    pred_counts[(i['contentId'], i['category'])] += 1

all_keys = set(list(gt_counts.keys()) + list(pred_counts.keys()))

# Collect FP and FN items
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

print(f'Total FP: {len(fp_items)}, Total FN: {len(fn_items)}')
print()

# Category breakdown
print('=== FP by Category ===')
fp_cats = defaultdict(int)
for i in fp_items:
    fp_cats[i['category']] += 1
for cat, cnt in sorted(fp_cats.items(), key=lambda x: -x[1]):
    print(f'  {cat}: {cnt}')

print()
print('=== FN by Category ===')
fn_cats = defaultdict(int)
for i in fn_items:
    fn_cats[i['category']] += 1
for cat, cnt in sorted(fn_cats.items(), key=lambda x: -x[1]):
    print(f'  {cat}: {cnt}')

# Cross-check: FP items that semantically match GT items with different category
print()
print('=== Cross-Category Overlap (FP desc similar to FN desc) ===')
print('--- FP items that might be category misclassification of FN items ---')
for fp in fp_items:
    for fn in fn_items:
        if fp['contentId'] == fn['contentId']:
            # Simple text overlap check
            fp_words = set(fp['description'][:50].split())
            fn_words = set(fn['description'][:50].split())
            if len(fp_words & fn_words) >= 3:
                print(f'  DOC: {fp["contentId"]}')
                print(f'    FP [{fp["category"]}]: {fp["description"][:80]}')
                print(f'    FN [{fn["category"]}]: {fn["description"][:80]}')
                print()

# Group FP by document to see noisy docs
print()
print('=== FP by Document ===')
fp_docs = defaultdict(list)
for i in fp_items:
    fp_docs[i['contentId']].append(f'{i["category"]}: {i["description"][:50]}')
for doc, items in sorted(fp_docs.items(), key=lambda x: -len(x[1])):
    print(f'  {doc} ({len(items)} FP):')
    for it in items:
        print(f'    {it}')

print()
print('=== FN by Document ===')
fn_docs = defaultdict(list)
for i in fn_items:
    fn_docs[i['contentId']].append(f'{i["category"]}: {i["description"][:50]}')
for doc, items in sorted(fn_docs.items(), key=lambda x: -len(x[1])):
    print(f'  {doc} ({len(items)} FN):')
    for it in items:
        print(f'    {it}')
