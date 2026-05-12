#!/usr/bin/env python3
import json, os

pred_dir = 'daily-report-optimized/eval/v1.4b-results'
key_docs = ['2757704387-catpaw', '2758031444-catpaw', '2757972453-catpaw', '2757991421-catpaw']

for f in sorted(os.listdir(pred_dir)):
    if f.endswith('.json'):
        data = json.load(open(os.path.join(pred_dir, f)))
        docs_in_batch = set()
        for kg in data.get('knowledge_gaps', []):
            if kg.get('contentId') in key_docs:
                docs_in_batch.add(kg['contentId'])
        for pi in data.get('process_issues', []):
            if pi.get('contentId') in key_docs:
                docs_in_batch.add(pi['contentId'])
        if docs_in_batch:
            print(f'{f}: {docs_in_batch}')

# Also show which batch has these docs based on all items
print("\n=== All KG items for key docs ===")
for f in sorted(os.listdir(pred_dir)):
    if f.endswith('.json'):
        data = json.load(open(os.path.join(pred_dir, f)))
        for kg in data.get('knowledge_gaps', []):
            if kg.get('contentId') in key_docs:
                print(f"  {f} | {kg['contentId']} | {kg['category']} | {kg['description'][:60]}")
