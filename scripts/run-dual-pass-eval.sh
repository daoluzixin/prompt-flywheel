#!/bin/bash
# ============================================================
# 独立 Pass 实验执行脚本
# 
# 用法：本脚本不直接执行分析（分析由 subagent 完成），
# 它提供了实验流程的完整命令参考。
#
# 实际执行时，主 Agent 应：
# 1. 为 PI-only pass 启动 6 个 subagent（使用 pi-only prompt）
# 2. 为 KG-only pass 启动 6 个 subagent（使用 kg-only prompt）
# 3. 合并两个 pass 的输出
# 4. 运行 eval-runner.py 评估
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_DIR="$(dirname "$SCRIPT_DIR")"
SKILL_DIR="$(dirname "$EVAL_DIR")"
RUNS_DIR="${EVAL_DIR}/runs/round26-dual"

echo "============================================================"
echo "  独立 Pass 拆分实验 (R26)"
echo "============================================================"
echo ""
echo "  Prompt 文件:"
echo "    PI-only: ${SKILL_DIR}/scripts/analyze-batch-prompt-pi-only.md"
echo "    KG-only: ${SKILL_DIR}/scripts/analyze-batch-prompt-kg-only.md"
echo ""
echo "  输出目录:"
echo "    PI runs: ${RUNS_DIR}/pi/"
echo "    KG runs: ${RUNS_DIR}/kg/"
echo "    Merged:  ${RUNS_DIR}/merged/"
echo ""

# Step 3: 合并（在 PI 和 KG 两轮 subagent 都完成后执行）
echo "--- Step 3: 合并两个 pass 的输出 ---"
echo ""
echo "  python3 ${SCRIPT_DIR}/merge-dual-pass.py \\"
echo "    --pi-dir ${RUNS_DIR}/pi \\"
echo "    --kg-dir ${RUNS_DIR}/kg \\"
echo "    --output-dir ${RUNS_DIR}/merged"
echo ""

# Step 4: 评估
echo "--- Step 4: 运行 eval-runner ---"
echo ""
echo "  python3 ${SCRIPT_DIR}/eval-runner.py \\"
echo "    --predicted ${RUNS_DIR}/merged \\"
echo "    --version v2.0-dual-pass \\"
echo "    --note '独立Pass拆分实验R26' \\"
echo "    --prompt-file ${SKILL_DIR}/scripts/analyze-batch-prompt-pi-only.md \\"
echo "    --detect-confusing \\"
echo "    --difficulty-breakdown"
echo ""
echo "============================================================"
echo "  注意：实际分析由主 Agent 调度 subagent 完成，本脚本仅供参考"
echo "============================================================"
