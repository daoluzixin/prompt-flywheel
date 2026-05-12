# Baseline 标注规范

本目录存放 L1 固定基准数据集——经人工标注的对话文档及其 ground truth。每轮 prompt 迭代后都用这份数据做回归验证，确保改进不引入退化。

## 目录结构

```
baseline/
├── docs/              # 对话文档原文（从日报系统导出的 .md 文件）
├── ground_truth.json  # 人工标注的正确识别结果
└── README.md
```

## 标注流程

1. 从近一周的日报输出中挑选 15-25 篇对话文档（覆盖各种 case 类型）
2. 将文档原文复制到 `docs/` 目录
3. 人工逐篇阅读，标注每篇应该识别出的 process_issues 和 knowledge_gaps
4. 将标注结果写入 `ground_truth.json`

## ground_truth.json 格式

```json
{
  "version": "1.0",
  "annotator": "anonymous",
  "annotated_at": "2026-05-10",
  "documents": [
    {
      "contentId": "xxx",
      "file": "docs/xxx.md",
      "expected_process_issues": [
        {
          "category": "spec3.plan",
          "description": "用户指出方案遗漏了缓存失效场景",
          "quote": "你这个方案没考虑缓存过期的情况",
          "note": "可选，标注者备注为什么判定为正例"
        }
      ],
      "expected_knowledge_gaps": [
        {
          "category": "接口约束",
          "description": "订单服务的限流规则",
          "quote": "这个接口有限流，QPS 上限 200",
          "note": ""
        }
      ],
      "expected_negatives": [
        {
          "quote": "我想加个导出功能",
          "reason": "新增需求，不属于流程不足也不属于知识缺口",
          "type": "neither"
        }
      ]
    }
  ]
}
```

`expected_negatives` 字段记录那些「看起来像但不应该被识别」的用户发言，用于检测误报。

## 选取原则

基准集应覆盖以下分布：

- 至少包含 3 篇「无任何可识别条目」的正常对话（测试误报率）
- process_issues 的 5 个 category 各至少覆盖 1 例
- knowledge_gaps 的 6 个 category 各至少覆盖 1 例
- 包含 2-3 篇「纠错伴生知识」的边界 case（同一发言同时命中两个指标）
- 包含 2 篇「AI 运行环境问题」的反例（不应被识别为 process_issues）
