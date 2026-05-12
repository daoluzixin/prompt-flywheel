# Synthetic 泛化探针

存放手工构造的边界 case，用于检测 prompt 是否对已知 Hard Pool case 过拟合。

这些 case 不来自真实对话，而是根据 Error Taxonomy 中的失败模式族，人工构造的「变体」——保持同一失败模式的核心结构，但更换具体领域/措辞/上下文。如果 prompt 对已知 case 做了过于具体的规则修补（相当于 overfit），这些变体就会暴露泛化失败。

## probes.json 格式

```json
{
  "probes": [
    {
      "id": "syn-001",
      "target_failure_mode": "FM-01",
      "created_at": "2026-05-10",
      "conversation_snippet": "用户：'Jarvis 插件现在连不上，换个方式吧'",
      "expected_output": "不应输出到 process_issues",
      "rationale": "FM-01 变体：换了工具名称和措辞，本质仍是环境问题"
    }
  ]
}
```

## 使用时机

每次 prompt 修改通过 baseline 回归验证后，额外跑一遍 synthetic probes。如果某个 probe 开始失败（之前通过），说明改动引入了过拟合倾向——改动可能过于针对特定措辞而非根本逻辑。
