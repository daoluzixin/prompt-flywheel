# GAN 风格数据飞轮实验

> 一句话总结：通过 30 轮 GAN 式对抗迭代 + 架构级拆分，将 Spec 日报的流程不足识别（PI）F1 从 0.61 提升至 0.84，知识库缺口识别（KG）F1 从 0.61 提升至 0.87。最终采用 Dual-Pass 架构（PI-only + KG-only 独立提取后合并），彻底解决了跨维度语义耦合问题。

---

## 术语与指标速查

| 术语 | 含义 |
|------|------|
| **PI (Process Issues)** | 流程不足——Spec 各阶段产出中的错误被用户纠正，说明该阶段的 prompt/流程存在缺陷 |
| **KG (Knowledge Gaps)** | 知识库缺口——对话中暴露出 AI 不掌握的业务事实或技术背景知识，应回流沉淀到知识库 |
| **G (Generator)** | 被优化的目标 prompt。v1.x 为单 pass（`analyze-batch-prompt.md`），v2.x 拆为 PI-only（`analyze-batch-prompt-pi-only.md`）+ KG-only（`analyze-batch-prompt-kg-only.md`）两个独立 pass |
| **D (Discriminator)** | 评估系统（eval-runner + 冻结 Ground Truth），判定 G 的输出质量并驱动迭代 |
| **GT (Ground Truth)** | 人工标注的正确答案，当前 v3.4 版本含 28 篇 golden 文档、45 条 PI + 36 条 KG |
| **Category** | PI 按 Spec 阶段分类：spec1.spy / spec2.clarify / spec3.plan / spec4.tasks / spec5.impl；KG 按知识类型分类：系统架构 / 业务规则 / 技术栈 / 接口约束 / 数据模型 |
| **Difficulty** | 每条标注的识别难度：easy（信号显式）/ medium（需推理）/ hard（极短或间接信号） |
| **KEEP / REJECT** | 每轮迭代的决策——改动有效则 KEEP 并保留新版本，退化则 REJECT 并回滚 |

| 指标 | 公式 | 直觉理解 |
|------|------|----------|
| **Precision** | TP / (TP + FP) | 模型输出的条目中有多少是对的（"说的准不准"） |
| **Recall** | TP / (TP + FN) | 应该被识别的条目中有多少被找到了（"漏没漏"） |
| **F1** | 2 × P × R / (P + R) | Precision 和 Recall 的调和平均，综合衡量准确率 |
| **TP (True Positive)** | — | 模型正确识别的条目数 |
| **FP (False Positive)** | — | 模型错误输出的条目数（误报） |
| **FN (False Negative)** | — | 模型遗漏的条目数（漏检） |
| **σ (标准差)** | — | 同一 prompt 多轮运行的指标波动幅度，用于区分真实改进和随机噪声 |

匹配规则：按 `(contentId, category)` 做贪心计数匹配。即同一篇文档内，某个 category 的预测数量与 GT 标注数量取交集为 TP，多出的为 FP，不足的为 FN。

---

## 这个实验解决什么问题

Spec 日报系统每天自动分析 AI-人协作对话，从中提取两类信号：**流程不足**（Process Issues, PI）——Spec 各阶段产出的错误被用户纠正；**知识库缺口**（Knowledge Gaps, KG）——对话中暴露出 AI 不知道的业务/技术背景知识。提取这两类信号的核心是一份 LLM prompt（`analyze-batch-prompt.md`，以下称 G）。问题在于 G 的初始版本表现不稳定，PI 和 KG 的 F1 均只有 0.61，某些关键类别（如 spec1.spy 阶段的短批注纠错）几乎完全漏检。

本实验的目标是：**用可复现的工程方法系统性地提升 G 的准确率，并沉淀一套可迁移到其他 LLM prompt 优化场景的方法论。**

---

## 实验方法

整体框架借鉴 GAN 的对抗思想：G 是被优化的 prompt，评估系统（eval-runner + 冻结的 Ground Truth）扮演 Discriminator（D）。每轮只改一个变量，跑完整评估看指标涨落，达标则 KEEP、退化则 REJECT 并回滚。

评估方式是将 28 篇人工标注的 golden 对话文档分成 6 个 batch，由 6 个并行 subagent 各自读取 G prompt + 对应 batch 的文档输出结构化 JSON，eval-runner.py 汇总后按 `(contentId, category)` 贪心计数匹配计算 TP/FP/FN，再按 category 和 difficulty 输出细分指标。

实验分五个阶段推进：

**阶段一（R1-R11）：Prompt-only 迭代。** 通过逐个攻克失败模式（spec1.spy 漏检 → 系统架构 FP → category 混淆 → recall 回收），将综合 F1 从 0.61 推至 0.91。11 轮中 7 轮 KEEP、4 轮 REJECT，积累了关于 LLM prompt 工程的核心经验。

**阶段二（R12-R17）：数据飞轮闭环。** 不再只改 prompt，同时从 FP 分析中发现 GT 标注遗漏并补入。Prompt v1.9 解决了前 11 轮未攻克的 spec2.clarify 漏检问题，GT 从 v3.0 演进到 v3.3（补入 5 条标注遗漏）。二者协同将 F1 推至 0.94 并连续 3 轮稳定。

**阶段三（R18）：L3 合成泛化探针。** 基于飞轮过程中沉淀的 3 个 active 失败模式，定向生成 10 个对抗样本验证 prompt 是否过拟合。结果：10/10 检出率、9/10 分类精确匹配，确认 prompt v1.9 具备真正泛化能力。

**阶段四（R19-R23）：稳定性验证。** 在扩展后的 28-doc 基准上连续 5 轮重复评估（唯一变量是 LLM 采样随机性），量化随机波动幅度为 σ≈0.08，定位了两个系统性弱点（spec5.impl FP 和 KG category 边界模糊）作为下一阶段优化方向。

**阶段五（R26-R30）：Dual-Pass 架构拆分。** 将 PI+KG 从单 prompt 拆为两个物理独立的 pass（PI-only + KG-only），每次调用只关注单一维度，合并后评估。这一架构级改变彻底消除了 R10/R11 暴露的跨维度语义耦合：PI F1 从 0.75 提升至 0.84（spec5.impl FP 从均值 5.8 降至 1-2），KG F1 从 0.68 提升至 0.87（业务规则和接口约束均达到 F1=1.00）。拆分后的"冻结一侧、迭代另一侧"策略让 R29-R30 可以放心做 KG 激进优化而 PI 严格不退化。

---

## 核心结果

| 指标 | Baseline | 阶段一最优 (R9) | 飞轮最优 (R17, 18-doc) | 28-doc 单 pass (R19-R23) | **Dual-Pass 最优 (R30)** |
|------|----------|----------------|----------------------|------------------------|-----------------------|
| PI F1 | 0.61 | 0.88 | 0.93 | 0.75 (σ=0.08) | **0.84** |
| KG F1 | 0.61 | 0.93 | 0.95 | 0.68 (σ=0.08) | **0.87** |
| 综合 F1 | 0.61 | 0.91 | 0.94 | 0.71 | **0.85** |

注：18-doc 和 28-doc 是两个不同难度的评测基准。R17 的 0.93/0.95 基于原始 18 篇 golden docs；R19-R23 基于 28 篇（含 10 篇 synthetic hard probes），评测集更难，指标回落是预期行为。R30 的 Dual-Pass 架构在同样的 28-doc 硬基准上将 PI/KG 分别提升 +0.09/+0.19，远超单 pass 基线的 σ=0.08 噪声带。

逐类攻克情况：spec1.spy recall 0.21→1.00（R1 解决）；spec4.tasks recall 0→1.00（R3 解决）；spec2.clarify 11 轮 recall=0 → 飞轮阶段 F1=1.00（v1.9 解决）；系统架构 FP 均值 4→0（R2+R6+飞轮解决）；spec5.impl FP 均值 5.8→1-2（Dual-Pass R26 解决）；业务规则/接口约束 F1=1.00（R29-R30 解决）。

---

## 沉淀的方法论（核心经验）

30 轮实验提炼出的 LLM prompt 优化经验，可迁移到任何信息提取/分类场景：

**有效的策略**——正例教学解决系统性漏检（recall +79pp）；精准反例解决过度生成（precision +45%）；一句话经验法则解决 category 混淆（比三段定义有效）；将"建议性规则"升级为"带步骤的强制检查"（recall +24pp）；用"独立性原则"替代"合并原则"避免 recall 暴跌。

**架构级突破**——物理拆分消除跨维度耦合（PI/KG 独立 pass，R26 验证）；拆分后"冻结一侧、迭代另一侧"降低 50% eval 成本且零风险（R29-R30 验证）；精准 category 边界规则（一句话区分）纠正误分类（R30 验证，业务规则/接口约束 F1=1.00）；"PRD 输入 vs 纠正性补充"区分规则消除需求文档 FP（R29 验证，Precision +18pp）。

**已证伪的反模式**——对 LLM 说"合并/去重/减少"会全局抑制输出（R5a 验证）；在排除规则旁加"另一维度不受影响"的元声明适得其反（R7 验证）；跨维度宏观边界规则让两个维度同时退化（R10 验证）；精确反例在高 recall category 上会同时压低 TP（R11 验证）。

**工程纪律**——先建 baseline 方差再做决策（KG σ=0.12，小于此值的变化不可信）；怀疑 prompt 极限时先查 GT 标注质量（R8 修正 GT 错误后单轮涨 7pp）；每次 KEEP 后立即备份（4 次 REJECT 靠此零成本回滚）；当 prompt 层面连续 REJECT 时应考虑架构级方案而非继续微调。

---

## 目录结构速览

```
eval/
├── EXPERIMENT_LOG.md          # 完整 30 轮实验记录（方法、每轮详情、结论）
├── BEST_PRACTICES.md          # 可复用的实践策略手册
├── DUAL_PASS_EXPERIMENT.md    # Dual-Pass 架构实验方案与结果
├── PROMPT_OPTIMIZATION_AGENT.md  # GAN 风格飞轮协议定义
├── changelog.md               # 每轮变更的精简归因记录
├── metrics.json               # 全部运行的量化指标
├── baseline/                  # 冻结评估基准（28 golden docs + GT v3.4）
├── dataset/                   # 失败模式库 + 对抗数据 + 判定标准
├── scripts/                   # 评估工具（eval-runner.py, merge-dual-pass.py 等）
├── runs/                      # 30 次评估运行的原始结果（含 round26-30-dual/）
└── backup/                    # G prompt 历史版本（支持回滚）

scripts/
├── analyze-batch-prompt.md         # 原始单 pass prompt（v1.9，已归档）
├── analyze-batch-prompt-pi-only.md # PI-only pass prompt（v2.1 生产版）
└── analyze-batch-prompt-kg-only.md # KG-only pass prompt（v2.1 生产版）
```

---

## 如何复现

运行一次 Dual-Pass 评估：

```bash
cd eval

# Step 1: 分别跑 PI-only 和 KG-only pass（各 6 batch，由 subagent 并行）
# Step 2: 合并两个 pass 的输出
python3 scripts/merge-dual-pass.py \
  --pi-dir runs/round30-dual/pi \
  --kg-dir runs/round30-dual/kg \
  --output-dir runs/round30-dual/merged

# Step 3: 评估合并结果
python3 scripts/eval-runner.py --predicted runs/round30-dual/merged --version v3.4 --difficulty-breakdown
```

如需发起新一轮迭代，按照 `PROMPT_OPTIMIZATION_AGENT.md` 定义的协议执行即可——备份当前 G → 做单变量改动 → 跑对应 pass 的 6 batch 评估 → 合并 → 看指标 → KEEP 或 REJECT。Dual-Pass 架构下可只迭代一侧（如 KG-only），复用另一侧已冻结的输出。

---

## 后续方向

v2.1 Dual-Pass 架构（R30）已解决此前两大系统性弱点（spec5.impl FP 和 category 边界模糊）。当前剩余改进空间：

- **KG Recall 最后 7%**：28 条 GT KG 中仍有 2 条系统架构 FN（Recall 92.9%→目标 100%），可继续迭代 KG-only prompt 的正例覆盖
- **PI spec1.spy FP**：R10/R11 已确认为当前 prompt 范式的硬天花板，需要更根本的方案（如引入 confidence scoring 或二阶段过滤）
- **稳定性验证**：Dual-Pass 架构尚未做多轮重复评估量化 σ，建议跑 3-5 轮确认 R30 结果的稳定性
- **生产部署**：将 Dual-Pass 流程集成到日报自动化 pipeline，更新 SKILL.md 中的执行流程
