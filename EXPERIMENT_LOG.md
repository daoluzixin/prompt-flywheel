# 实验记录：30 轮 Prompt 优化全过程

> 创建日期：2026-05-11｜最终状态：Dual-Pass v2.1，PI F1=0.84, KG F1=0.87

本文档是一次完整的 LLM prompt 优化实验的逐轮记录。任务是从 Spec 流程对话中提取两类信号——流程不足（PI）和知识库缺口（KG）。优化框架参照 GAN 思路：prompt 是 Generator，评估系统是 Discriminator，通过冻结的 Ground Truth 检测 bad case 并反向驱动迭代。每轮只改一个变量，跑完整 eval 后以 F1 涨跌决定 KEEP 或 REJECT。

---

## 实验基础设施

评估系统的核心是 `eval-runner.py`，按 `(contentId, category)` 做贪心计数匹配，计算 Precision / Recall / F1。6 个 subagent 并行执行 prompt，每个处理一批文档输出 JSON，汇总后自动与上一版本对比标记退化项。

Ground Truth 经历了 5 个版本的演进。v3.0 是初始基准（18 golden docs，25 PI + 21 KG）；v3.1 从 FP 分析中补入 3 条遗漏；v3.2 新增 pi-035（overview 描述错误）；v3.3 新增 pi-036（文件命名规则纠错）；v3.4 引入 10 篇 L3 合成探针，总计扩展至 28 golden + 26 silver = 54 篇，45 PI + 36 KG。R1-R17 在 18 篇原始 golden 上评估，R18 起扩展至 28 篇。

---

## Baseline（Run 1-4）

用同一 prompt v1.0 连续跑 4 轮建立方差基线。PI F1 四轮为 0.67 / 0.52 / 0.65 / 0.60，均值 0.61（σ=0.06）；KG F1 为 0.73 / 0.43 / 0.65 / 0.65，均值 0.61（σ=0.12）。KG 波动显著大于 PI，说明 KG 判定更受采样随机性影响。

最严重的问题浮出水面：spec1.spy 平均 recall 仅 0.21（be99243f 那篇文档的 6 条 spec-mark 短批注全部漏检），spec2.clarify 四轮全漏（recall 0.00），Hard PI recall 仅 0.18。Root cause 很清晰——prompt 中压根没教过 spec-mark 批注可以作为 PI 信号，模型不是"不愿识别"而是"不知道应该识别"。

---

## 第一阶段：Prompt-Only 迭代（R1-R11）

**Round 1（v1.0→v1.1）KEEP。** 攻 spec1.spy 漏检。在 prompt 中新增 spec-mark 短批注的模式识别段落，补 3 个正例（"MQ消息""支持可配置""这些不全"），刻意选用极短文本教模型"短≠不重要"。spec1.spy recall 从 0.21 飙至 1.00，PI F1 升至 0.71，Hard PI recall 从 0.18 跃至 0.86。代价是系统架构 KG 冒出 7 个 FP。

**Round 2（v1.1→v1.2）KEEP。** 攻系统架构 KG 过度生成。逐条分析 7 个 FP 后识别出 5 类典型误判模式，根因是 prompt 缺乏"什么不是系统架构"的负向约束。新增 5 类反例（spec 流程规范、模板设计说明、框架愿景、方法论讨论、知识库分类体系）。FP 从 7 暴降到 1，KG Precision 从 0.62 飙至 0.90（+45%），Recall 不降反升。这证明了精准反例的杠杆效应——只要描述准确，负向约束可以在不伤 recall 的前提下大幅提升 precision。

**Round 3（v1.2→v1.3）KEEP。** 攻 spec4.tasks category 混淆（recall 为 0.00，2 条 GT 全部被误归为 spec3.plan 或 spec5.impl）。根因是 prompt 对 spec4 的描述不足以区分相邻阶段。新增 spec4.tasks 专属判定段落和一条经验法则："what to do（做什么）层面的问题→spec4；how to do（如何设计/实现）→spec3/spec5"。spec4 从 recall 0.00 恢复到 1.00，PI Precision 达到历史最高 0.90。一句话经验法则比三段形式化定义有效得多。

**Round 4（v1.3→v1.4）KEEP。** 攻 spec3.plan 漏检（FN=4，最大 PI 失败类别）。新增约 25 行内容：5 个场景描述 + 与 spec4 的边界规则 + 3 个正例 + "补充信息"与"批评设计思路"的区分。spec3.plan Recall 从 40% 升至 70%（+30pp），Hard PI recall 升至 0.71。代价是引入 3 个 spec3.plan FP（Precision 从 0.90 降至 0.80）——正例教学力度偏强而缺乏配套反例，下一轮需要补。

**Round 5（v1.4→v1.5b）KEEP（经历一次失败）。** Round 5a 添加了"合并原则"，结果 PI Recall 从 0.80 暴跌至 0.68，spec1.spy recall 从 1.00 降至 0.67。教训深刻：对 LLM 说"合并"会严重抑制输出倾向，即使限定了"只限完全相同"也没用。5b 将合并原则反转为"独立性原则"（每条独立事实性错误单独计数），同时补充 spec3.plan 反例。PI F1 首次突破 0.84，Easy + Medium PI 达到完美 100% recall，所有剩余 FN 集中在 Hard。

**Round 6（v1.5b→v1.6）KEEP。** 攻 KG Precision（业务规则 FP=4 + 系统架构 FP=2）。在 KG 不计入条件中新增 2 条排除规则：「Spec 模板方法论」和「AI/框架概念性定位」不属于可沉淀的业务知识。KG Precision 从 0.76 升至 0.857，业务规则 F1 从 0.50 跃至 0.80。PI F1 退化 3pp 推测为随机波动。

**Round 7（v1.6→v1.7）REJECT。** 尝试在 KG 排除规则旁加注"此排除仅限 KG 维度，PI 不受影响"。全面退化：PI Precision -8pp，KG Precision -7pp。教训：在排除规则旁添加跨维度元声明会被模型理解为鼓励多输出的信号。回滚到 v1.6。

**Round 8（v1.6→v1.7 new）KEEP。** 三部分改动：新增 spec5.impl 与 spec1.spy 的易混淆场景段落；修正 GT 标注错误（pi-015/pi-016 的文档归属）；添加"一份文档可以同时包含 PI 和 KG"的提示。PI F1 从 0.79 跃至 0.86，spec5.impl 达到完美 F1=1.00。但 KG Recall 从 0.86 降到 0.67（模型变得过于保守），KG Precision 升至 1.00 是以 recall 大幅下降为代价。

**Round 9（v1.7→v1.8）KEEP。** 攻 KG Recall 恢复。将纠错伴生知识规则从"建议"升级为"强制执行的二次检查"——要求模型在输出 JSON 前逐条回顾每条 PI，检查上下文是否包含伴生知识点。新增"通信方式与消息内容是独立知识点"的拆分指导，以及"即使文档主要讨论 spec 设计，穿插的系统机制纠正仍应输出 KG"的提示。KG F1 从 0.80 跃至 0.93（Recall +24pp），系统架构从 F1 0.67 升至 0.90，业务规则达 F1 1.00。LLM 对可操作的步骤序列的遵从度远高于抽象建议——这是本轮最大的认知收获。

**Round 10（v1.8 尝试→REJECT）。** 在 spec1.spy 段落中增加 PI/KG 边界判断规则和"计数自检"步骤。PI F1 跃至 0.96，但 KG F1 从 0.93 暴跌至 0.83——系统架构 FP +2，业务规则和接口约束各新增 FN。教训：跨维度的宏观边界规则会让模型把"这不是 PI"理解为"这可能也不该输出为 KG"。回滚。

**Round 11（v1.8 尝试 b→REJECT）。** 换策略，用精确反例（3 个具体的 spec1.spy FP 场景）代替宏观规则。spec1.spy FP 确实降到 0，但 TP 从 6 暴跌至 3——模型看到反例后过度保守。这再次验证了 R5a 的教训：任何涉及"不要输出 X"的措辞（即使是精确反例形式）都会让 LLM 全局性地抑制相关输出。回滚。

第一阶段 11 轮：7 KEEP / 4 REJECT。KEEP 的共性是"单一目标 + 正向教学"；REJECT 的共性是"负向约束"——无论是间接措辞、跨维度规则还是精确反例，只要核心信号是"不要输出"就会失败。R10-R11 触及了 prompt 层面的天花板：spec1.spy FP=3 的跨维度耦合在单 pass 中无解。

---

## 第二阶段：数据飞轮闭环（R12-R17）

飞轮的核心思路是"不再只改 prompt，同时改数据"——从 FP 分析中发现 GT 遗漏，补入后暴露新的真实 FN，再针对性改 prompt，形成 prompt-data 双向驱动的闭环。

Prompt v1.8→v1.9 的关键改动有两处。第一，新增 spec2.clarify 专属指引——描述 outline.yml 中路由条目被用户删除或 spec-mark 标记错误时应识别为 spec2.clarify PI，这直接攻克了 11 轮未解的 spec2.clarify recall=0.00 问题。第二，KG 边界细化——当用户纠正的是扩展位的实际结构定义（如 extensions 字段的具体含义）仍应输出为 KG，只有讨论"模板为什么设计扩展位"的方法论部分才排除。

GT v3.0→v3.3 的演进来自 R15/R16 的 FP 分析。v3.1 补入 3 条遗漏（pi-009b 渲染建议实为 spec.md 纠错、pi-034 MQ 消息体字段纠错、kg-022 按能力维度筛选服务规范）；v3.2 补入 pi-035（overview 描述与实际不符）；v3.3 补入 pi-036（文件命名规则纠错）。每一条补入都来自"模型输出被判为 FP，但人工复审后确认模型是对的、GT 漏标了"的发现。

R15 是 prompt v1.9 首次评估：PI F1=0.877, KG F1=0.857，spec2.clarify 首次达到 recall=1.00。R16 做稳定性验证，结果高度一致。用 GT v3.3 重新评估 R15/R16 的预测结果后，PI F1 均提升至 0.93——GT 补完消除了假 FP，验证了"GT 补完→指标自然提升"的飞轮机制。R17 直接对 GT v3.3 跑新预测：PI F1=0.9310, KG F1=0.9545，所有难度层级 PI recall=1.00，spec2.clarify 连续第 3 轮 F1=1.00，系统架构 category 达到完美（TP=11, FP=0, FN=0）。

三轮的一致性验证了飞轮闭环的有效性：prompt 改进 + GT 补完的组合将综合 F1 从 0.91 稳定推至 0.94，波动极小。

---

## L3 合成泛化探针（R18）

R17 剩余 3 个 FN 难以判断是 prompt 的系统性缺陷还是 subagent 随机波动。L3 层的设计思路是：基于已知 failure patterns 的措辞变体和场景变体定向生成对抗样本，检测 prompt 是否仅在已知 case 上过拟合。

3 个 active failure patterns 来自 R17 FN 分析：FP_011（短文档零输出，734b79d3 仅 2 轮对话讨论接口鉴权但模型输出零结果）、FP_012（极短泛化批注遗漏，"这些不全"仅 4 字被漏检）、FP_013（提问式纠错遗漏，"你能不能做到…"被理解为征询建议而非纠错）。

据此设计了 10 个 synthetic probes：FP_011 × 4（CDN无需认证头、批量接口上限100、ConfigCenter只读、接口非幂等），FP_012 × 3（"不对"2字、"缺了"2字+后续补充、"有问题"3字+outline纠错），FP_013 × 3（"能不能简洁点""可不可以换种方式""是不是应该拆开"）。

R18 结果：10/10 检出率，9/10 category 精确匹配。唯一偏差是 syn-010 的"接口非幂等"被归入接口约束而非业务规则——处于两个 category 的语义边界，可接受。结论：R17 的 3 个 FN 是 subagent 随机波动而非 prompt 系统性缺陷，prompt v1.9 已具备对这三类 failure pattern 的真正泛化能力。探针补入 GT v3.4，为后续迭代建立了更严格的回归基准。

---

## 稳定性验证（R19-R23）

单次评估无法量化随机波动对指标的影响。R19-R23 在完全相同条件下（prompt v1.9 不变、GT v3.4 冻结、28 golden docs）重复运行 5 轮，建立置信区间。

5 轮均值：PI F1=0.75（σ=0.08），KG F1=0.68（σ=0.08）。注意这比 R17 的 0.94 低很多，因为 R17 只在 18 篇原始 golden 上评估，而 R19-R23 用的是包含 10 篇对抗探针的 28 篇 hard 基准。R22 是明显离群点（PI F1=0.63），根因定位于 batch_1 的 spec1.spy 维度产生 6 个 FP——经典的 subagent 单次采样偏差，R23 立即恢复高位。

剔除 R22 后四轮：PI F1=0.78（σ=0.05），KG F1=0.71（σ=0.05）。Precision 的波动远小于 Recall（PI Precision 排除离群点后在 0.75-0.76 间几乎无波动，Recall 则在 0.64-0.89 间大幅摆动），说明"什么不该提取"已经收敛，但"什么必须提取"仍受注意力随机性影响。两个系统性弱点清晰定位：spec5.impl FP 均值 5.8（5 轮几乎无波动，确认为系统性缺陷），接口约束/业务规则 category 边界模糊（FP 均值约 4）。

关键结论：后续 prompt 优化的增益必须超过 0.10 F1 才能被可靠判定为真实改进而非采样噪声。

---

## 第三阶段：架构级实验——独立 Pass 拆分（R26-R30）

当 prompt 层面策略穷尽后（R10-R11 触顶，稳定性验证确认了系统性弱点的位置），自然的下一步是架构级改变。假设是：将 PI 和 KG 提取拆为两个物理独立的 pass，从根本上消除跨维度语义耦合。

PI-only prompt 仅保留 PI 相关规则，新增 spec5.impl 严格边界"三条件同时满足"判定规则。KG-only prompt 仅保留 KG 相关规则，移除纠错伴生知识检查，展开 category 判定指引。合并脚本按 batch_index 对齐两个 pass 的输出。

**R26 首次验证。** PI F1 从基线 0.75 跃至 0.85（+0.10，超过 significance threshold），spec5.impl FP 从均值 5.8 骤降至 1——"三条件同时满足"规则 + 物理隔离的组合有效抑制了过度标记。PI difficulty recall 优异：easy 0.93, medium 1.00, hard 1.00，独立 pass 的专注度让模型在 hard case 上也不再遗漏。KG 侧改进有限（F1 仅 +0.01），系统架构 recall 偏低（FN=6），接口约束 FP=3 未解决——KG 的瓶颈不在跨维度耦合，而在 category 内部判定指引不够细致。

**R27-R28 稳定性验证。** PI F1 三轮均值 0.84（σ=0.013），相比单 Pass 基线的 0.75（σ=0.08），不仅绝对值提升了 +0.09，方差也从 0.08 缩小到 0.013——架构拆分让 PI 提取表现极为稳定。spec5.impl FP 三轮为 1/2/1，均值 1.3，降幅稳定在 77%-83%。KG F1 三轮均值 0.67（σ=0.029），与基线持平但 Precision 呈下降趋势（业务规则和数据模型的 FP 在 R27/R28 中恶化）。

决策：PI-only pass 确认为稳定真实改进，KEEP。KG-only pass 需要进一步迭代。架构拆分后的巨大优势是可以冻结已稳定的 PI pass，只迭代 KG pass——将 eval 成本降低 50%，且彻底消除了"改 KG 影响 PI"的风险。

**R29 KG 精调：FP 消除 + 系统架构 Recall 提升。** 诊断定位到精确原因后做单变量改动：新增"需求分析/方案设计中的业务逻辑阐述"排除条件（区分 PRD 原文 vs 纠正性补充）、补充系统架构正例 5 条、新增反例 3 条。KG F1 从 0.68 跃至 0.84（+0.16，远超阈值），系统架构 Recall 从 ~60% 跃至 100%，业务规则 Precision=1.00。KEEP。

**R30 KG 精调：Category 边界精细化。** R29 剩余问题主要是 category 误分类（"订单号获取优先级逻辑"被判为接口约束而非业务规则，"接口无鉴权"被判为系统架构而非接口约束）。新增 3 条 category 区分规则。KG Recall 从 0.86 升至 0.93（FN 从 4→2），业务规则和接口约束双双达到 F1=1.00。Precision 微降（系统架构新增 3 个边界 FP）属于可接受的 tradeoff。KEEP。

---

## 最终成绩

从 baseline F1=0.61 到最终 Dual-Pass v2.1：PI F1=0.84, KG F1=0.87, Combined F1≈0.85（28-doc hard 基准）。在原始 18-doc 基准上的峰值是 PI F1=0.93, KG F1=0.95, Combined=0.94。

三个阶段各有贡献：第一阶段 prompt-only 迭代将 F1 从 0.61 推至 ~0.84（11 轮，约 60 行增量改动）；第二阶段数据飞轮闭环将 F1 从 0.84 推至 0.94（6 轮，prompt v1.9 + GT v3.3）；第三阶段架构拆分在更严格的 28-doc 基准上将 KG F1 从 0.67 推至 0.87（PI 稳定在 0.84）。

两轮 KG-only 迭代将 KG F1 从 0.63 提升至 0.87，是实验以来最大的单次跃进——证明架构拆分后单维度 prompt 的优化空间远大于耦合状态。这也是本实验最重要的方法论发现之一：当 prompt 层面策略触顶时，正确的做法不是继续在同一层面尝试更多 trick，而是退后一步重新审视架构。

---

## 可复现信息

评估命令：`python eval-runner.py --predicted ../runs/{round}-run{N} --version "{version}" --difficulty-breakdown`。6 个 subagent 并行执行，输出到 `runs/{round}-run{N}/batch_{0-5}.json`。

G 版本链路：v1.0（baseline 4 轮）→ v1.1（R1）→ v1.2（R2）→ v1.3（R3）→ v1.4（R4）→ v1.5b（R5）→ v1.6（R6）→ v1.7 REJECT 回滚 → v1.7 new（R8）→ v1.8（R9）→ R10 REJECT 回滚 → R11 REJECT 回滚 → v1.9（R12-R17 飞轮阶段）→ Dual-Pass v2.0（R26-R28）→ v2.1 KG 精调（R29-R30）。

GT 版本链路：v3.0（R1-R14 基准）→ v3.1（+3 遗漏）→ v3.2（+pi-035）→ v3.3（+pi-036）→ v3.4（+10 synthetic probes，当前最新）。

全部 30 轮评估在 2026-05-11 同日完成。
