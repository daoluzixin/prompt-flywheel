# Hard Pool

存放当前 prompt 版本无法正确处理的 Bad Cases。每条记录包含对话片段、实际输出、期望输出、失败模式分类。

当某条 case 在新版本 prompt 中被正确处理且通过回归验证后，从此目录移入 `baseline/` 作为回归保护。

## cases.json 格式

```json
{
  "cases": [
    {
      "id": "hp-001",
      "added_at": "2026-05-10",
      "source_contentId": "原始文档ID",
      "failure_mode": "边界误判-环境问题误识为流程不足",
      "conversation_snippet": "用户原话...",
      "actual_output": {
        "type": "process_issues",
        "category": "spec5.impl",
        "description": "模型的错误输出"
      },
      "expected_output": "不应输出 / 应为 knowledge_gaps",
      "error_type": "FP",
      "priority": 1,
      "resolved_in": null,
      "note": "用户在说 MCP tool 不可用，是环境问题不是流程设计问题"
    }
  ]
}
```

## 失败模式族（Error Taxonomy）

随着 Bad Cases 积累，按以下维度聚类：

| 模式族 ID | 名称 | 描述 | 当前频次 |
|-----------|------|------|----------|
| FM-01 | 边界误判-环境问题 | 把 AI 运行环境问题（MCP不可用/脚本报错）误识为 spec 流程不足 | 0 |
| FM-02 | 边界误判-需求补充 | 把用户新增需求误识为流程不足 | 0 |
| FM-03 | 证据不足强行输出 | quote 无法直接支撑 description，需要推理补全 | 0 |
| FM-04 | category 归类错误 | 识别到了正确的条目但 category 标错 | 0 |
| FM-05 | 知识库缺口误扩 | 把一次性故障/临时安排误识为可沉淀知识 | 0 |
| FM-06 | 纠错型漏检 | 用户明确纠正了 Agent 错误但未被识别 | 0 |
| FM-07 | 伴生知识漏检 | 纠错同时附带了背景事实，只输出了一侧 | 0 |
| FM-08 | AI标记漏检 | 对话中有 [知识盲区] 标记但未被捕获 | 0 |

新发现的模式族追加到此表，保持 ID 连续。
