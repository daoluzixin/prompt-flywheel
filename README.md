# prompt-flywheel

A GAN-style data flywheel for systematic LLM prompt optimization.

**30 rounds of adversarial iteration, F1 0.61 → 0.94, completed in one day.**

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
