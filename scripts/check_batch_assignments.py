#!/usr/bin/env python3
"""检查文档分配在哪个 batch，以及GT标注一致性"""
import json, os

gt = json.load(open('daily-report-optimized/eval/baseline/ground_truth.json'))
pred_dir = 'daily-report-optimized/eval/v1.4b-results'

# Check which batch each doc is in
print("=== 文档-batch 映射 ===")
for f in sorted(os.listdir(pred_dir)):
    if f.endswith('.json'):
        data = json.load(open(os.path.join(pred_dir, f)))
        cid = data.get('contentId', 'unknown')
        print(f"  {f}: contentId={cid}")

# Check if 2758031444 and 2757704387 are in same batch
print("\n=== 重点文档检查 ===")
key_docs = ['2757704387-catpaw', '2758031444-catpaw', '2757972453-catpaw', '2757991421-catpaw']
for f in sorted(os.listdir(pred_dir)):
    if f.endswith('.json'):
        data = json.load(open(os.path.join(pred_dir, f)))
        cid = data.get('contentId', '')
        if cid in key_docs:
            print(f"  {cid} -> {f}")
            print(f"    KG count: {len(data.get('knowledge_gaps', []))}")
            for kg in data.get('knowledge_gaps', []):
                print(f"      {kg['category']}: {kg['description'][:60]}")

# Check GT for these docs
print("\n=== GT 标注检查 ===")
for d in gt['documents']:
    if d['contentId'] in key_docs:
        print(f"  {d['contentId']}:")
        for kg in d.get('expected_knowledge_gaps', []):
            print(f"    {kg['category']}: {kg['description'][:60]}")
        print()
