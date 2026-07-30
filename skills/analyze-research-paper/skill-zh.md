---
name: analyze-research-paper
description: 将研究论文分析为基于证据的复现规格；提取任务、方法、架构、公式、数据集、训练、推理、指标、结果、资源和缺失信息；联网检索官方项目页、GitHub、Hugging Face、Release、数据集和预训练 checkpoint；将论文主张与项目代码、配置、命令和资源逐项对齐。深度阅读论文、检查是否存在官方或第三方预训练权重、联合分析论文与项目，或制定分阶段复现计划时使用。
---

# 分析研究论文

将论文转换为基于证据、可以实际执行的复现规格。没有项目时完成纯论文分析；
存在项目时联合论文、代码、配置、model card 和 release 证据进行分析。

## 安全与证据规则

- 区分 `VERIFIED`、`INFERRED`、`ESTIMATED` 和 `UNKNOWN`。
- 每项重要结论都要引用论文页码/章节/表格/图/公式，或仓库路径/行号/配置键。
- 保留论文、补充材料、代码、配置、model card 与 README 的冲突，不要静默
  选择其中一个值。
- 优先使用官方出版页、作者、项目、仓库、release 和模型来源；第三方实现和
  checkpoint 必须明确标注。
- 未经用户另行批准，不下载大型数据集或权重，不接受许可证，不登录，不暴露
  token，不安装依赖，也不执行不受信任的项目代码。
- 将内置扫描器视为候选发现工具，而不是最终结论。

## 必需参考资料

记录证据或编写 `reproduction_spec.json` 前阅读
[references/analysis-schema.md](references/analysis-schema.md)。

需要联网检索、查找项目或验证预训练权重时阅读
[references/online-weight-search.md](references/online-weight-search.md)。

仅在分析 VLN、具身智能、导航、仿真器或机器人论文时阅读
[references/vln-analysis.md](references/vln-analysis.md)。

使用 [references/report-template.md](references/report-template.md)
编写最终产物。

## 工作流程

### 1. 确定论文身份与分析范围

确认：

- 准确标题、作者、DOI/arXiv ID、正式发表会议和年份；
- 论文、补充材料、附录、项目主页及各版本之间的关系；
- 目标复现层级：
  - `L0`：理解论文；
  - `L1`：import/模型构建检查；
  - `L2`：使用已发布 checkpoint 推理；
  - `L3`：与论文对应的评测；
  - `L4`：微调或缩减训练；
  - `L5`：完整训练与 benchmark 复现；
- 已有的项目 URL 或本地仓库，以及用户需要的分析深度。

正式发表年份与首次预印本年份不同的时候同时记录。比较代码前确认使用的准确
论文版本。

### 2. 将论文提取为结构化证据

阅读完整论文及相关补充材料，不能只读摘要。提取：

1. 研究问题、任务定义、假设和贡献；
2. 输入、输出、观测、动作和成功条件；
3. 架构模块、数据流、公式、算法和张量作用；
4. 目标函数、loss、reward、优化方法和训练阶段；
5. 数据集、版本、划分、预处理、增强和许可证；
6. 推理、搜索、停止条件、后处理和运行时行为；
7. 指标、评测协议、baseline、随机种子和统计方法；
8. 主实验、消融、鲁棒性、失败案例和局限；
9. 软件、硬件、资源、checkpoint 和计算要求；
10. 缺失细节、模糊参数、冲突和复现风险。

不能把数据集或任务 benchmark 当成模型名称。当操作流程分散在文字、图、公式
和附录中时，可以重建伪代码或数据流，但必须标记为推断。

### 3. 联网检索当前官方来源

允许联网时，使用准确标题、缩写、论文编号、作者和项目名进行搜索。检查：

- 官方论文集、论文页、补充材料和作者项目主页；
- 论文或作者链接的代码仓库；
- 仓库 README、文档、分支、tag、release、issue 和归档状态；
- Hugging Face Models、Datasets 与 Spaces；
- 官方数据集页面、model zoo 和发布存储位置。

对可能变化的信息使用当前的一手来源并给出直接链接。即使论文早于 Hugging
Face Hub，也要进行检索，因为官方机构可能在之后上传了权重。

### 4. 判断预训练权重是否存在

分别识别：

- 通用 backbone/基础模型权重；
- 中间预训练 checkpoint；
- 最终任务或 benchmark checkpoint；
- 微调后的 checkpoint；
- adapter/LoRA/delta 权重；
- 量化、格式转换或第三方衍生权重。

为每个候选项记录发布者、官方身份、平台、URL、revision/commit、文件名、
可见大小、格式、许可证、访问限制、架构和配置兼容性、所需预处理/tokenizer
以及支持证据。

总体状态只能选择：

- `AVAILABLE_VERIFIED`；
- `AVAILABLE_RESTRICTED`；
- `ANNOUNCED_NOT_FOUND`；
- `THIRD_PARTY_ONLY`；
- `BROKEN_OR_REMOVED`；
- `NOT_RELEASED`；
- `UNKNOWN`。

Hugging Face 仓库名称相同不代表官方发布，必须通过论文、作者、项目主页、官方
仓库或机构身份交叉验证。不能把只有 backbone 的权重描述成论文任务 checkpoint。

### 5. 检查项目

存在本地仓库时运行：

```powershell
python "<skill-dir>\scripts\inspect_project_evidence.py" `
  --repo-root "<repository-root>" `
  --output-dir "<repository-root>\artifacts\paper_analysis" `
  --paper-title "<准确论文标题>" `
  --paper-id "<DOI 或 arXiv ID>"
```

在 POSIX 系统上使用 `python3`。检查生成的 `project_evidence.json` 和
`weight_evidence.json`，再回到原始代码行核实候选证据。

还要人工检查：

- 仓库来源、commit、分支、tag、submodule 和 Git LFS；
- 安装/依赖文件和支持的平台；
- 模型定义、forward、loss、trainer、evaluator 和 data loader；
- 配置、默认值、override、随机种子和实验脚本；
- 推理、评测、训练、可视化和部署入口；
- 本地/远程 checkpoint、特征文件、数据和许可证要求。

只有远程仓库时进行只读在线检查。在未访问相关 revision 的源码前，不能声称
已经完成源码级对齐。

### 6. 对齐论文与项目

为每个重要论文模块、算法步骤、数据集、超参数、指标和工作流建立一行映射，
对应到：

- 源码路径和 symbol；
- 配置键与默认值；
- 命令或入口；
- checkpoint 或资源；
- 实现 commit/revision。

每行只能选择：

- `EXACT_MATCH`；
- `IMPLEMENTED_WITH_DIFFERENCES`；
- `PAPER_ONLY`；
- `CODE_ONLY`；
- `NOT_ENOUGH_EVIDENCE`。

说明差异对 checkpoint 加载、推理、指标可比性、评测和训练的实际影响。重点
检查代码默认值与论文表格不同、发表后代码修改、未公开预处理，以及评测脚本中
未说明的假设。

### 7. 建立复现规格

将联合证据转换为：

- 最小输入和所需资源；
- 准确的环境与依赖证据；
- 推理、评测、训练命令，或尚未确定的占位项；
- 预期输出和论文目标指标；
- 资源需求，并区分实测值与估计值；
- 阻塞项、未知项和安全验证步骤；
- 从 `L0` 到用户目标层级的分阶段计划。

不得编造仓库不支持的命令。论文和项目要求确定后，使用
`$evaluate-research-project` 继续评估环境可行性。

### 8. 写入分析产物

在 `artifacts/paper_analysis/` 下写入：

```text
PAPER_ANALYSIS.md
PAPER_PROJECT_ALIGNMENT.md
reproduction_spec.json
project_evidence.json
weight_evidence.json
```

只有检查了项目仓库时才要求 `project_evidence.json`。没有项目时，
`PAPER_PROJECT_ALIGNMENT.md` 可以标记 `NOT_ENOUGH_EVIDENCE`，但仍要完成
纯论文分析。

## 质量门槛

完成前确认：

- 每个数字都有论文或项目位置；
- 正式发表年份与预印本年份已经区分；
- 官方与第三方项目/权重已经分开；
- 权重链接经过近期检查，或明确标为未验证；
- 论文指标定义与评测代码一致，或已经显示冲突；
- 缺少的数据、许可证、checkpoint、配置和硬件已经明确；
- 每个复现层级都有可行、阻塞或未知结论；
- 报告区分事实、推断、估计和未知项。

## 最终回复

先说明论文主要贡献、预训练权重状态、官方项目状态和最高可行复现层级，再报告
最重要的论文—代码差异、阻塞项和产物路径。
