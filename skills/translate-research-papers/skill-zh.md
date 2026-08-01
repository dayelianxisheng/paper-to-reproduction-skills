---
name: translate-research-papers
description: 使用本地 Zotero PDF2zh 服务翻译研究论文 PDF，保持服务终端可见；uv 可用时优先尝试，失败时回退到 PDF2zh Conda 环境；无需 GUI 点击即可调用 PDF2zh 和带鉴权的 Zotero REST bridge；验证双语输出，并把原文与译文 PDF 挂到正确的 Zotero 文献父条目下。用户要求使用 PDF2zh 翻译论文、自动化 Zotero 双语 PDF 工作流、将译文导入 Zotero，或诊断 Windows PDF2zh 服务/API 配置时使用。
---

# 使用 PDF2zh 与 Zotero 翻译研究论文

在允许批量翻译前，先完整跑通一篇论文。保持 PDF2zh 服务窗口可见，以便用户
查看进度和错误。

## 本地配置

- 原始 PDF：`D:\download`
- 服务目录：`D:\resource\env\fanyi\server\server`
- 服务 URL：`http://127.0.0.1:8890`
- Conda 激活脚本：`D:\resource\env\miniconda3\Scripts\activate.bat`
- Conda 环境：`PDF2zh`
- Zotero 数据目录：`D:\software\Professional\Zotero\note`
- Zotero bridge URL：`http://127.0.0.1:23119/pdf2zh-bridge`
- Zotero bridge token：`D:\software\Professional\Zotero\note\pdf2zh-bridge.token`
- Zotero bridge 插件 ID：`pdf2zh-bridge@codex.local`
- 默认引擎/服务：`pdf2zh_next` 与 `siliconflowfree`
- 双语对照 endpoint：`/compare`

不得打印、复制或暴露 API key 与 bridge token。Zotero 运行时不得直接编辑
`zotero.sqlite`。常规工作流中不要使用 PDF2zh 右键菜单或 Zotero 的
Run JavaScript 窗口。

## 工作流程

1. 检查原始 PDF、目标 Zotero collection、已有文献父条目和附件。确定原文
   附件 ID 与目标 collection ID。若已存在有效译文则跳过，除非用户要求替换。
2. 确认 Zotero 正在运行，且受限 bridge 能正常响应：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_zotero_bridge.ps1 `
     -Action Health
   ```

   成功响应必须包含 `status=ok`、Zotero 版本、token 路径和允许导入的根
   目录。若失败，启动 Zotero 或重启一次；不要回退到 GUI 自动化。

3. 启动或检查 PDF2zh 服务：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   若 8890 端口已监听，脚本会立即返回。只有 uv 已安装时才会先尝试 uv；
   否则在可见终端中启动已知 Conda 配置。若 uv 已安装但服务未能监听，检查
   可见终端，再使用 `-ForceConda` 重新运行。

4. 通过 PDF2zh REST API 翻译：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source "D:\download\paper.pdf" `
     -Endpoint compare
   ```

   返回 `status=success` 和 `outputFiles` 后仍需完成 PDF 验证，才能视为最终
   成功。REST 请求为同步请求，可能持续数分钟；需要保持交互响应时，在后台
   进程中执行并轮询日志。

5. 验证生成的 PDF：

   - 确认文件存在、非空，并以 `%PDF-` 开头。
   - 除非有意跳过页面，否则页数应与原文一致。
   - 提取文本并确认包含有意义的中文内容。
   - 条件允许时，目视检查代表性页面的双语布局。

6. 通过带鉴权的 Zotero bridge 归档：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_zotero_bridge.ps1 `
     -Action Archive `
     -SourceAttachmentID 849 `
     -TargetCollectionID 80 `
     -TranslatedPath "D:\resource\env\fanyi\server\server\translated\paper.compare.pdf" `
     -ShortTitle "R2R" `
     -Service "siliconflowfree" `
     -TemplateItemID 695
   ```

   `TemplateItemID` 为可选参数，仅在必须新建文献父条目时使用。bridge 会把
   父条目放入目标 collection，将原文命名为 `<shortTitle>-original`，将双语
   附件命名为 `<shortTitle>-<service>-compare`，并移除子附件自身的 collection
   归属。重复发送相同请求时必须返回 `idempotent=true`，不得创建重复条目。

7. 核对返回的父条目 ID/key、两个子附件 ID、存储路径、页数和 collection
   归属。父条目的 collection 列表必须包含目标 collection；两个子附件的
   collection 列表必须为空。汇报耗时、回退情况和所有警告。

bridge 仅提供健康检查、更新元数据和受约束的归档操作。它要求本地 token，
只接受 `server\translated` 下的译文 PDF，且不开放任意 JavaScript 或 SQL
执行。只有维护或诊断 bridge 时才读取
[references/zotero-bridge.md](references/zotero-bridge.md)。

## 失败处理

- 8890 端口不可用时，先检查可见服务终端，再考虑切换环境。
- uv 不可用或来自其他电脑时，使用 Conda 回退方案，并附加
  `--enable_venv false --check_update false`；同时把两个内置 PDF2zh 虚拟
  环境的 `Scripts` 目录加入 `PATH` 前部。
- bridge 健康检查失败时，确认 Zotero 正在运行、持久化插件位于当前 profile，
  且 token 文件可读。插件更新后重启 Zotero 一次。
- 归档返回 `UNAUTHORIZED` 时，不要把 token 粘贴到命令或对话中；让
  `invoke_zotero_bridge.ps1` 自行读取 token 文件。
- 归档返回 `PATH_OUTSIDE_ALLOWED_ROOT` 时，把已经验证的输出保留在
  `server\translated`，并使用该绝对路径重试。
- 服务返回成功但文件不存在时，检查 `server\translated`、可见终端及
  `fileList` 中的准确文件名。
- Zotero storage 副本创建完成且 PDF 验证通过之前，不删除服务输出。
