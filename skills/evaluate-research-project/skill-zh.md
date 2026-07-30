---
name: evaluate-research-project
description: 审计机器学习、机器人、VLN、ROS、仿真器或其他研究代码项目能否在当前机器运行；识别硬依赖与软依赖；评估 CUDA、PyTorch、ROS、仿真器、数据集、checkpoint、GUI、无界面运行、推理、评测、训练及云端资源要求；生成基于证据的本地就绪报告。在安装或复现论文项目前、诊断环境兼容性时，或判断需要本机还是服务器时使用。
---

# 评估研究项目

在不改变项目和当前环境的前提下审计代码仓库与机器。根据直接证据得出结论，
明确区分事实与推断，并保留未知项。

## 安全边界

- 在安装、卸载、升级或降级任何软件之前先完成审计。
- 不使用 `sudo`，不修改项目源码，不改变当前环境。
- 不下载数据集、checkpoint、容器、仿真器或大型资源。
- 不启动完整训练、完整评测或交互式仿真器。
- 在编译、打开 GUI、执行长时间测试、明显占用 GPU，或运行可能改变状态的
  命令之前征得用户同意。
- 只允许检查仓库、检查主机、运行低成本只读命令，以及在指定审计输出目录
  下写入文件。
- 不暴露 token、密码、API key、凭据值或许可证密钥；只报告是否需要凭据
  以及凭据是否存在。

## 必需参考资料

在分类依赖证据前阅读
[references/dependency-evidence-schema.md](references/dependency-evidence-schema.md)。

仅当仓库涉及 VLN、具身智能、ROS、机器人、仿真、三维感知或自定义 CUDA
算子时，阅读
[references/robotics-vln-readiness.md](references/robotics-vln-readiness.md)。

编写最终报告时使用
[references/report-template.md](references/report-template.md)。

## 审计工作流

### 1. 确定范围与来源

确定仓库根目录、目标复现层级、操作系统和预期工作流。若 Git 可用，记录当前
commit、分支、remote、工作树状态、submodule、tag 和 Git LFS 使用情况。

根据论文、项目主页、作者、发布元数据和仓库历史，判断该仓库是官方实现、持续
维护的 fork，还是第三方实现。不能仅凭仓库名称推断其官方身份。

划分目标复现层级：

- `L0`：仅静态检查；
- `L1`：导入与低成本测试；
- `L2`：使用已发布 checkpoint 推理或运行 demo；
- `L3`：与论文对应的评测；
- `L4`：微调或缩减训练；
- `L5`：完整训练与 benchmark 复现。

### 2. 运行非破坏性探测

运行：

```powershell
python "<skill-dir>\scripts\audit_env.py" `
  --repo-root "<repository-root>" `
  --output-dir "<repository-root>\artifacts\local_readiness"
```

在 POSIX 系统上使用 `python3`。探测脚本必须生成：

- `environment_probe.json`；
- `dependency_evidence.json`；
- `commands_to_verify.sh`；
- `commands_to_verify.ps1`。

将探测输出视为原始证据。使用之前检查命令退出码、截断标记、扫描限制和警告。

### 3. 核对仓库要求

检查并交叉核对以下证据：

- README 和项目文档；
- `requirements*.txt`、constraints 和 Conda 环境文件；
- `pyproject.toml`、`setup.py`、`setup.cfg`、Poetry、uv 和 Pipenv 文件；
- Dockerfile、Compose、devcontainer 和 CI workflow；
- 安装与构建脚本；
- 源码 import、运行时断言和版本检查；
- ROS manifest、`.repos`、rosdep、CMake 和 colcon 文件；
- 仿真器配置、launch 文件和渲染选项；
- CUDA/C++ 扩展构建文件；
- 数据集、checkpoint、凭据、许可证和资源说明。

对每项重要依赖保留：

- 组件与版本约束；
- 来源路径和行号或章节；
- 证据类型；
- `hard`、`recommended`、`optional` 或 `unknown` 分类；
- 置信度；
- 分类理由及冲突证据。

只有强证据支持时才把版本视为硬约束，例如精确版本约束或锁文件、运行时断言、
编译 ABI、ROS/Ubuntu 配对、仿真器/插件耦合、官方 CI/容器镜像、checkpoint
架构或必需 API。README 中的示例命令默认视为推荐环境，除非有其他证据印证。

### 4. 与当前机器比较

分别比较，不能混为一谈：

- `nvidia-smi` 报告的 NVIDIA 驱动 CUDA 能力；
- `nvcc` 报告的已安装 CUDA toolkit；
- PyTorch 编译时使用的 CUDA 版本；
- PyTorch 运行时 CUDA 可用性和设备 compute capability。

评估操作系统、架构、WSL/容器状态、CPU、内存、swap、磁盘、Python
解释器、环境管理器、编译器、构建工具、GPU/显存、cuDNN 迹象、ROS、容器、
仿真器、渲染栈、数据集、checkpoint、许可证和凭据。

无法安全确认的要求标记为 `UNKNOWN`。程序未出现在 `PATH` 中，不等于它在
机器其他位置一定没有安装。

### 5. 只运行低成本验证

从语法检查、import/版本检查、配置解析和不需要外部资源的单元测试开始。只有
在资源已经存在且操作明显低成本时，才运行模型构建、checkpoint 加载、单个
episode/batch 或无界面渲染；其他情况先征得用户同意。

为每条命令记录：

- 完整命令和工作目录；
- 开始时间、持续时间、退出码和超时；
- 简洁的 stdout 和 stderr；
- 结果属于已验证、推断还是无法确定。

不得隐藏失败，也不能用笼统总结代替失败信息。

### 6. 分别给出各工作流结论

独立评估：

1. import 与单元测试；
2. 已发布 checkpoint 推理；
3. 单 episode 或小数据划分评测；
4. 完整 benchmark 评测；
5. 完整训练；
6. 交互式仿真器可视化；
7. 无界面训练、评测和渲染；
8. ROS 或真机部署。

仅使用以下结论：

- `PASS`；
- `PASS_WITH_LIMITS`；
- `BLOCKED`；
- `UNKNOWN`；
- `NOT_APPLICABLE`。

每项结论都必须附带证据，不能把所有工作流合并成一个笼统的“能/不能”。

### 7. 分析 GUI 与无界面运行

将每个适用工作流分类为：

- `NATIVE_HEADLESS`；
- `EGL_OR_OSMESA`；
- `XVFB`；
- `GUI_REQUIRED`；
- `UNKNOWN`。

说明训练、评测和渲染能否在没有桌面环境时运行；云端训练的 checkpoint 能否
复制回本机推理；以及推理需要完整仿真器还是只依赖模型环境。

### 8. 判断是否需要云端资源

只有当本机硬件、操作系统耦合、运行时间或缺失依赖确实需要时，才推荐云端或
服务器。分别判断：

- 本地推理可行性；
- 本地评测可行性；
- 本地完整训练可行性。

必要时提供：

- 最低烟雾测试配置；
- 推荐复现配置；
- 完整训练配置。

为每种配置说明操作系统、CPU 核数、内存、GPU 和显存、磁盘、驱动/toolkit
约束、显示环境要求，以及是否适合 spot/preemptible 实例。未实测的显存或
时间数据必须标记为估计值，并说明估计依据。

### 9. 写入审计产物

在 `artifacts/local_readiness/` 下写入：

```text
environment_probe.json
dependency_evidence.json
LOCAL_READINESS_REPORT.md
commands_to_verify.sh
commands_to_verify.ps1
```

使用报告模板，并保留指向准确证据的引用。添加用于解决未知项的安全验证命令，
不要把这些命令写成安装脚本。

最终分类只能选择一项：

- `READY_LOCAL`；
- `READY_LOCAL_WITH_LIMITS`；
- `READY_HEADLESS_SERVER`；
- `CLOUD_RECOMMENDED_FOR_TRAINING`；
- `BLOCKED_BY_HARD_DEPENDENCY`；
- `INSUFFICIENT_EVIDENCE`。

## 最终回复

先给出最终分类，然后只报告：

- 最主要的阻塞项；
- 已验证的硬依赖版本；
- 是否需要云端资源；
- 无界面训练和本地推理是否可行；
- 审计产物路径。

除非用户另外批准安装或修复方案，否则不安装或更改任何内容。
