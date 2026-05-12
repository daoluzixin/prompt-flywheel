# prompt-flywheel

A GAN-style data flywheel for systematic LLM prompt optimization.

**30 rounds of adversarial iteration, F1 0.61 → 0.94, completed in one day.**

[English](#why-i-built-this) | [中文](#为什么做这个)

---

## Why I Built This

Most prompt engineering today is still "vibes-based" — tweak a word, eyeball the output, hope it gets better. When I was tasked with optimizing an LLM prompt for signal extraction (identifying user corrections and knowledge gaps from AI-human conversations), I realized that without a rigorous evaluation framework, I'd just be guessing.

So instead of jumping into prompt tweaking, I designed and implemented a complete optimization system from scratch: human-annotated ground truth, automated evaluation pipelines, variance baselines, structured failure pattern tracking, and a three-layer data flywheel that co-evolves the prompt and evaluation data together.

This repository is the full, unedited record of that experiment — every eval run, every prompt version, every KEEP and REJECT decision, and the methodology that emerged from 30 rounds of systematic iteration. It's not a polished library or framework; it's a working laboratory that demonstrates the approach and proves it works.

**This is entirely my original work** — from problem formulation, evaluation system design, ground truth annotation, prompt iteration, data flywheel protocol design, to the final dual-pass architecture. The methodology, the tooling, and all experimental results were produced independently in a single day.

---

## What's Inside

The core contribution is not the optimized prompt itself, but the **reusable methodology** for systematic prompt optimization with minimal labeled data (46→81 annotations drove F1 from 0.61 to 0.94). The key insight: prompt and evaluation data should co-evolve, not be optimized independently — this is what makes it a "flywheel" rather than just "iteration."

### The Three-Layer Data Flywheel

```
┌─────────────────────────────────────────────────────────────┐
│  L1: Fixed Baseline Regression (never regress)              │
│       ↓ all pass                                            │
│  L2: Hard Pool Iteration (failure-pattern-driven)           │
│       ↓ converged                                           │
│  L3: Adversarial Probes (generalization verification)       │
└─────────────────────────────────────────────────────────────┘

Prompt improves → exposes GT gaps → GT补完 exposes true prompt weakness
    → adversarial probes verify generalization → repeat
```

### Key Findings (from 30 rounds)

**What works:**

- Positive examples solve "doesn't know to extract" (recall 0.21→1.00 in one round)
- Precise counter-examples solve "over-generates" (precision +45%)
- One-sentence heuristics beat multi-paragraph definitions for category disambiguation
- Upgrading "advisory rules" to "mandatory checklist steps" gives order-of-magnitude gains
- Physical pass separation eliminates cross-dimension semantic coupling

**What fails (verified anti-patterns):**

- Any restrictive phrasing ("merge", "reduce", "don't output") gets over-generalized by LLMs
- Meta-declarations about rule scope ("this only applies to X dimension") backfire
- Cross-dimension boundary rules cause both dimensions to degrade
- Precise counter-examples on high-recall categories suppress true positives

**Engineering discipline:**

- Establish variance baseline BEFORE any optimization (σ=0.08~0.12)
- Single-variable changes only — otherwise you can't attribute effects
- Backup before every change; 4 REJECTs were zero-cost rollbacks
- When prompt-level strategies plateau, go architectural (dual-pass)

---

## Results

| Metric | Baseline | After Flywheel (18-doc) | Dual-Pass (28-doc hard) |
|--------|----------|------------------------|------------------------|
| PI F1 | 0.61 | 0.93 | 0.84 |
| KG F1 | 0.61 | 0.95 | 0.87 |
| Combined F1 | 0.61 | 0.94 | 0.85 |

The 18-doc and 28-doc numbers use different evaluation benchmarks (the latter includes 10 adversarial synthetic probes designed to be harder). Both represent substantial improvements from the same baseline.

---

## Repository Structure

```
├── BEST_PRACTICES.md              # Reusable strategy handbook (the methodology)
├── EXPERIMENT_LOG.md              # Complete 30-round experiment record
├── DUAL_PASS_EXPERIMENT.md        # Architecture-level split experiment
├── PROMPT_OPTIMIZATION_AGENT.md   # The flywheel protocol definition (GAN-style)
├── changelog.md                   # Per-round change attribution
├── metrics.json                   # All quantitative metrics
├── baseline/                      # Frozen evaluation data (28 golden docs + GT v3.4)
│   ├── ground_truth.json
│   └── docs/                      # 54 conversation documents
├── dataset/                       # Failure patterns, adversarial probes, criteria
├── scripts/                       # Evaluation tooling
│   ├── eval-runner.py             # Core evaluator (greedy count matching)
│   ├── merge-dual-pass.py         # Dual-pass output merger
│   └── run-dual-pass-eval.sh      # End-to-end dual-pass evaluation
├── runs/                          # Raw results from all 30 evaluation rounds
│   ├── baseline/run{1-4}/         # Variance baseline (4 identical runs)
│   ├── round{1-25}-run*/          # Single-pass iterations
│   └── round{26-30}-dual/        # Dual-pass architecture runs
└── backup/                        # Prompt version history (supports rollback)
```

---

## How to Use This

**If you want to understand the methodology:** Start with `BEST_PRACTICES.md` — it's a distilled handbook of what works and what doesn't when optimizing LLM prompts for extraction/classification tasks.

**If you want to see the full experiment:** Read `EXPERIMENT_LOG.md` for the complete narrative of 30 rounds, including root cause analyses, decision rationale, and lessons from each REJECT.

**If you want to adapt the framework to your own task:** Use `PROMPT_OPTIMIZATION_AGENT.md` as the protocol template. Replace the task-specific prompt (G) and ground truth, keep the three-layer flywheel structure and engineering discipline.

**If you want to reproduce a run:**

```bash
# Merge dual-pass outputs
python3 scripts/merge-dual-pass.py \
  --pi-dir runs/round30-dual/pi \
  --kg-dir runs/round30-dual/kg \
  --output-dir runs/round30-dual/merged

# Evaluate
python3 scripts/eval-runner.py \
  --predicted runs/round30-dual/merged \
  --version v3.4 \
  --difficulty-breakdown
```

---

## Comparison with Existing Approaches

| | DSPy / OPRO | This Flywheel |
|--|-------------|---------------|
| Data requirement | Hundreds to thousands of labels | 46→81 labels sufficient |
| Optimization | Automated search (black-box) | Human-driven, explainable per round |
| Data evolution | Fixed dataset | Prompt and GT co-evolve |
| Failure understanding | Limited interpretability | Structured failure pattern signatures |
| Architecture decisions | Not addressed | Flywheel naturally surfaces architectural ceilings |
| Best for | Large labeled datasets, clear objectives | Small data, need to understand failure modes |

The ideal end-state is combining both: use this flywheel to bootstrap high-quality evaluation data and initial prompt understanding, then hand off to automated frameworks for fine-grained search at scale.

---

## Author

**Yunhao Feng** ([@daoluzixin](https://github.com/daoluzixin))

This work was completed during my internship, motivated by a practical need to systematically improve LLM prompt quality beyond trial-and-error. The methodology draws inspiration from adversarial training (GAN), active learning (prioritizing informative samples), and experimental science (variance baselines, single-variable control, reproducibility).

---

## License

MIT

---

---

# prompt-flywheel（中文版）

基于 GAN 式对抗思路的数据飞轮，用于系统化 LLM Prompt 优化。

**30 轮对抗迭代，F1 从 0.61 提升至 0.94，一天内完成。**

---

## 为什么做这个

当前大多数 prompt engineering 仍然是"玄学调参"——改个措辞、肉眼看看输出、期望有提升。当我接到一个任务：优化用于信号提取的 LLM Prompt（从人机对话中识别用户纠正和知识盲区）时，我意识到如果没有严谨的评估框架，所谓优化不过是猜测。

所以我没有直接去调 prompt，而是从头设计并实现了一套完整的优化系统：人工标注的 Ground Truth、自动化评估流水线、方差基线、结构化失败模式追踪、以及一个让 prompt 与评估数据共同进化的三层数据飞轮。

这个仓库是那次实验的完整未删节记录——每一轮评估、每一版 prompt、每一次 KEEP 和 REJECT 决策，以及从 30 轮系统迭代中提炼出的方法论。它不是一个精雕细琢的开源库或框架；它是一个真实的实验室，展示了方法并证明了它有效。

**这完全是我的原创工作**——从问题定义、评估系统设计、Ground Truth 标注、Prompt 迭代策略、数据飞轮协议设计，到最终的双通道架构。方法论、工具链和所有实验结果均在一天之内独立完成。

---

## 核心内容

核心贡献不是那个优化后的 prompt 本身，而是一套**可复用的方法论**：如何用极少的标注数据（46→81 条标注驱动 F1 从 0.61 升至 0.94）实现系统化 prompt 优化。关键洞察：prompt 和评估数据应该共同进化，而非独立优化——这才是"飞轮"而非"迭代"。

### 三层数据飞轮

```
┌─────────────────────────────────────────────────────────────┐
│  L1: 固定基线回归（永不退化）                                  │
│       ↓ 全部通过                                             │
│  L2: 困难样本池迭代（失败模式驱动）                             │
│       ↓ 收敛                                                │
│  L3: 对抗探针（泛化性验证）                                    │
└─────────────────────────────────────────────────────────────┘

Prompt 提升 → 暴露 GT 缺陷 → GT 补完暴露 Prompt 真正的短板
    → 对抗探针验证泛化性 → 循环
```

### 关键发现（30 轮提炼）

**有效策略：**

- 正例样本解决"不知道要提取"（recall 一轮从 0.21→1.00）
- 精确反例解决"过度生成"（precision +45%）
- 一句话启发式规则胜过多段定义（用于类别消歧）
- 将"建议性规则"升级为"强制检查步骤"获得数量级提升
- 物理通道分离消除跨维度语义耦合

**验证过的反模式：**

- 任何限制性措辞（"合并""减少""不要输出"）都会被 LLM 过度泛化
- 关于规则适用范围的元声明（"这只适用于 X 维度"）会适得其反
- 跨维度边界规则导致两个维度同时退化
- 在高召回类别上使用精确反例会压制真阳性

**工程纪律：**

- 优化前先建立方差基线（σ=0.08~0.12）
- 每次只改一个变量——否则无法归因
- 每次修改前备份；4 次 REJECT 实现零成本回滚
- 当 prompt 级策略触顶时，升级到架构层（双通道）

---

## 实验结果

| 指标 | 基线 | 飞轮优化后（18 篇） | 双通道（28 篇困难集） |
|------|------|-------------------|---------------------|
| PI F1 | 0.61 | 0.93 | 0.84 |
| KG F1 | 0.61 | 0.95 | 0.87 |
| 综合 F1 | 0.61 | 0.94 | 0.85 |

18 篇和 28 篇使用不同的评估基准（后者包含 10 条对抗合成探针，难度更高）。两者均从相同基线出发获得了显著提升。

---

## 如何使用

**想了解方法论：** 从 `BEST_PRACTICES.md` 开始——它是关于 LLM Prompt 提取/分类任务优化中什么有效、什么无效的精炼手册。

**想看完整实验过程：** 阅读 `EXPERIMENT_LOG.md`，包含 30 轮的完整叙事、根因分析、决策理由，以及每次 REJECT 的教训。

**想把框架应用到自己的任务：** 使用 `PROMPT_OPTIMIZATION_AGENT.md` 作为协议模板。替换任务相关的 prompt（G）和 Ground Truth，保留三层飞轮结构和工程纪律。

**想复现一次评估：**

```bash
# 合并双通道输出
python3 scripts/merge-dual-pass.py \
  --pi-dir runs/round30-dual/pi \
  --kg-dir runs/round30-dual/kg \
  --output-dir runs/round30-dual/merged

# 评估
python3 scripts/eval-runner.py \
  --predicted runs/round30-dual/merged \
  --version v3.4 \
  --difficulty-breakdown
```

---

## 与已有方案的对比

| | DSPy / OPRO | 本飞轮 |
|--|-------------|--------|
| 数据需求 | 数百到数千条标注 | 46→81 条标注即可 |
| 优化方式 | 自动搜索（黑盒） | 人驱动、每轮可解释 |
| 数据演化 | 固定数据集 | Prompt 和 GT 共同进化 |
| 失败理解 | 可解释性有限 | 结构化失败模式签名 |
| 架构决策 | 未涉及 | 飞轮自然暴露架构天花板 |
| 适合场景 | 大量标注、目标明确 | 小数据、需要理解失败模式 |

理想的终态是两者结合：用本飞轮快速 bootstrap 高质量评估数据和初始 prompt 理解，再交给自动化框架做大规模精细搜索。

---

## 作者

**冯云浩** ([@daoluzixin](https://github.com/daoluzixin))

这项工作在实习期间完成，动机是想把 LLM Prompt 优化从"试错+运气"提升为一套可复现的系统方法。方法论灵感来自对抗训练（GAN）、主动学习（优先标注最有信息量的样本）和实验科学（方差基线、单变量控制、可复现性）。

---

## License

MIT
