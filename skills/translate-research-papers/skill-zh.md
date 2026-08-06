---
name: translate-research-papers
description: 在原生 Windows、原生 Linux 或 WSL 上使用本地 PDF2zh 翻译研究论文 PDF，验证中英双语版的页数、中文文本和对照布局，并可通过受限本地 bridge 将原文与译文导入 Zotero。用户要求 PDF2zh 论文翻译、中英对照 PDF、Zotero 附件导入，或诊断 PDF2zh/Zotero 服务时使用。
---

# 使用 PDF2zh 与 Zotero 翻译研究论文

先完整跑通一篇，再开始批量任务。保持 PDF2zh 服务终端可见。不得打印、复制
或暴露 API key 与 Zotero bridge token。

## 先判断平台

不要因为历史配置是 `D:\...` 就假定当前环境为 Windows。先检查源文件路径、
PowerShell 与 WSL 工具：

- 原生 Windows：使用 PowerShell 脚本，默认源目录为 `D:\download`。
- 原生 Linux：使用 `.sh` 与 `.py` 脚本；默认服务目录为
  `~/resource/env/zotero/zotero-pdf2zh/server`。
- WSL：只有 `powershell.exe` 和 `wslpath` 均存在时才调用 Windows 流程；否则
  按原生 Linux 处理。

用户只要求翻译时，Zotero bridge 缺失不得阻塞 PDF 产出。

## 翻译流程

1. 确认原始 PDF 存在、非空且以 `%PDF-` 开头。
2. 在可见终端中启动或检查 PDF2zh。

   Windows：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   Linux：

   ```bash
   scripts/start_pdf2zh_visible.sh
   ```

   Linux 启动器会依次选择 uv、`PDF2zh` Conda 环境或兼容 Python；若没有图形
   终端则停止，不得悄悄在后台启动而隐藏错误。

3. 提交单篇翻译。

   Windows：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source "D:\download\paper.pdf" -Endpoint compare
   ```

   Linux：

   ```bash
   scripts/invoke_pdf2zh_linux.py \
     --source /path/to/paper.pdf \
     --endpoint compare \
     --delivery /path/to/paper-中英对照.pdf
   ```

   Linux helper 先调用 REST。当 `/compare` 包装层返回
   `CalledProcessError`，但本地 `pdf2zh_next` 可执行文件存在时，只对
   `compare + siliconflowfree` 使用直接 CLI 回退。保留有效的
   `*.no_watermark.zh-CN.dual.pdf`，再复制为 `*.compare.pdf`，不要通过移动
   文件破坏原产物。回退运行期间不得并行提交第二个翻译。

   单段富文本解析失败、占位符过多或翻译结果长度不匹配时，PDF2zh 会降级为
   普通翻译；只要进程最终返回 0 且产物验证通过，应作为警告汇报，而不是把
   整篇标为失败。只读取脱敏后的日志尾部，不得输出可能包含密钥的原始日志。

4. 验证双语 PDF。

   ```bash
   scripts/validate_bilingual_pdf.py \
     --source /path/to/paper.pdf \
     --translated /path/to/paper.compare.pdf \
     --layout lr \
     --render-prefix /tmp/paper-preview
   ```

   必须满足：

   - 原文与译文均为有效 PDF，译文非空；
   - 页数一致，除非任务明确跳过页面；
   - 可提取足量、有意义的中文文本；
   - LR 对照版宽度约为原文两倍，高度近似不变；
   - 首屏目视检查无裁切、半页空白、乱码或字体缺失。

5. 将验证后的文件复制到原文旁边，并保留服务目录中的归档副本。

## 诊断 Linux 代理导入失败

若 `httpx` 在导入 `ollama` 时出现
`ValueError: Unknown scheme for proxy URL URL('socks://…')`，应判定为进程环境
错误，而不是字体或 PDF 错误；自动附加 `--skip-subset-fonts` 的重试无法修复。

- 只检查代理变量名与 scheme，不得打印完整代理 URL、凭据、API key 或 token。
- 检查 8890 监听进程的环境，而不只看当前 shell。图形终端可能继承不同的
  `ALL_PROXY`。
- `scripts/start_pdf2zh_visible.sh` 会在新服务终端内部，仅移除以
  `socks://` 开头的不兼容 `ALL_PROXY`/`all_proxy`，保留有效的
  `HTTP_PROXY` 与 `HTTPS_PROXY`。
- 已运行的服务若继承了错误变量，先解析准确的监听 PID，只停止该 PDF2zh
  进程，再重新运行启动器。不得修改用户的全局代理设置。
- 用仅取消错误变量的导入探针验证 `ollama` 与 `pdf2zh`，然后检查 `/health`。
  如果必须使用 SOCKS，先确认已安装 SOCKS 依赖，再改用当前 `httpx` 支持的
  scheme，例如 `socks5://`。

## 按需归档到 Zotero

安装、鉴权、路径或归档诊断前读取
[references/zotero-bridge.md](references/zotero-bridge.md)。

1. Windows 调用 `invoke_zotero_bridge.ps1 -Action Health`；Linux 调用：

   ```bash
   scripts/invoke_zotero_bridge.py health
   ```

2. bridge 未安装时，只有在用户明确授权后，才通过 Zotero 的
   **Tools → Plugins → 齿轮 → Install Plugin From File** 安装捆绑 XPI。
   把新 XPI 静默复制到 profile 不会构成有效安装，也不得修改
   `extensions.json`。

3. 明确目标 collection。若有多个合理目标，必须让用户选择；主题与唯一集合
   明确对应时可说明判断依据后使用。

4. 原文尚未进入 Zotero 时，Linux 使用受限、幂等的 `prepare`：

   ```bash
   scripts/invoke_zotero_bridge.py prepare \
     --source-path ~/Downloads/paper.pdf \
     --target-collection-id 77 \
     --short-title PaperName
   ```

   `prepare` 只接受允许源目录下的 PDF，并返回 `source.id`。重复调用必须复用
   已存在的 `<shortTitle>-original`，不得创建重复附件。

5. 使用验证后的 `server/translated/*.compare.pdf` 归档：

   ```bash
   scripts/invoke_zotero_bridge.py archive \
     --source-attachment-id 849 \
     --target-collection-id 77 \
     --translated-path /absolute/server/translated/paper.compare.pdf \
     --short-title PaperName \
     --service siliconflowfree
   ```

6. 核对父条目 ID/key、原文与译文附件 ID、路径和 collection：

   - 两个附件必须共享同一文献父条目；
   - 只有父条目属于目标 collection，两个子附件的 collection 为空；
   - 必须对 bridge 返回的 `translated.path` 实体文件重新运行 PDF 验证，不能仅
     凭同名 Zotero 附件记录判定归档成功；
   - 同名附件记录存在但实体文件缺失或为空时，bridge 应重新导入并返回
     `repaired=true`；
   - 重复调用必须返回 `idempotent=true`。

Zotero 运行时不得直接编辑 `zotero.sqlite`。使用 `immutable=1` 打开的 SQLite
可能忽略仍在 WAL 中的最新条目，因此不能把它当作最终存在性判断；优先信任
bridge 返回值，或先完全关闭 Zotero 再执行只读数据库审计。
