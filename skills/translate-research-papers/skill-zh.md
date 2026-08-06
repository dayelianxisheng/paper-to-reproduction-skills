---
name: translate-research-papers
description: 在原生 Windows、原生 Linux 或 WSL 上使用本地 PDF2zh 翻译研究论文 PDF，自动发现本机所需路径并将已验证路径缓存到 YAML，验证中英双语布局和中文文本，并可通过受限本地 bridge 归档 Zotero 附件。用户要求 PDF2zh 翻译、中英对照 PDF、Zotero 附件导入、本地路径发现或 PDF2zh/Zotero 故障诊断时使用。
---

# 使用 PDF2zh 与 Zotero 翻译研究论文

先完整跑通一篇，再开始批量任务。保持 PDF2zh 服务终端可见。不得暴露 API
key、完整代理 URL 或 Zotero bridge token。

## 使用前先发现本地路径

不得在命令、文档或源码中写入机器专属路径。每次使用技能时先刷新本地 YAML：

```bash
scripts/local_config.py refresh --source "$SOURCE_PDF"
```

解析器优先使用显式参数和环境变量，再按文件特征做有限深度搜索；只有当前真实
存在的路径才会写入 YAML。默认位置遵循操作系统的用户配置目录，也可通过
`PDF2ZH_SKILL_CONFIG` 或 `--config` 覆盖。生成的 YAML 不得提交到仓库。

需要路径时调用 `local_config.py get KEY`。Linux 与 PowerShell helper 会自动
刷新并读取 YAML。自动发现遗漏时，使用 `--server-directory`、
`--source-directory`、`--translated-directory`、`--zotero-data-directory`、
`--token-path` 或 `--search-root` 提供线索。必需路径缺失或失效时必须停止。

完成发现后再选择平台：

- 原生 Windows：使用 PowerShell helper；
- 原生 Linux：使用 shell 与 Python helper；
- WSL：仅当 YAML 中发现 PowerShell 与 `wslpath` 两个可执行文件时调用
  Windows 流程，否则使用原生 Linux 流程。

用户只要求翻译时，Zotero 路径缺失不得阻塞 PDF 产出。

## 翻译流程

1. 确认原始 PDF 存在、非空且以 `%PDF-` 开头。
2. 在可见终端中启动 PDF2zh；两个启动器都会先刷新 YAML。

   Windows：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   Linux：

   ```bash
   scripts/start_pdf2zh_visible.sh
   ```

3. 提交单篇 `compare` 翻译。

   Windows：

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source $SourcePdf -Endpoint compare
   ```

   Linux：

   ```bash
   scripts/invoke_pdf2zh_linux.py \
     --source "$SOURCE_PDF" \
     --endpoint compare \
     --delivery "$DELIVERY_PDF"
   ```

   Linux helper 先调用 REST。若 `/compare` 包装层返回
   `CalledProcessError`，则用同一 `pdf2zh_next` CLI 回退，保留有效的 LR 双语
   PDF 并复制为 `*.compare.pdf`。回退期间不得并行提交第二篇。仅当进程返回 0
   且产物有效时，富文本降级信息才可按警告处理。

4. 交付或归档前验证：

   ```bash
   scripts/validate_bilingual_pdf.py \
     --source "$SOURCE_PDF" \
     --translated "$TRANSLATED_PDF" \
     --layout lr \
     --render-prefix "$PREVIEW_PREFIX"
   ```

   必须验证 PDF 头、页数、有效中文文本、LR 页面几何，并目视检查首屏无裁切、
   空白半页、乱码或字体缺失。

## 诊断 Linux 代理导入失败

若 `httpx` 在导入 `ollama` 时出现
`ValueError: Unknown scheme for proxy URL URL('socks://…')`，应判定为进程环境
错误，而不是字体或 PDF 错误；`--skip-subset-fonts` 重试无法修复。

- 只检查代理变量名与 scheme，不打印完整值；
- 检查 8890 监听进程的环境，因为图形终端可能继承不同的 `ALL_PROXY`；
- Linux 启动器只在新服务终端内部移除以 `socks://` 开头的不兼容
  `ALL_PROXY`/`all_proxy`，保留有效 HTTP/HTTPS 代理，不改全局设置；
- 旧服务继承错误变量时，只停止准确的监听进程，再重新启动、验证导入并检查
  `/health`；仅在 HTTP 客户端与 SOCKS 依赖支持时使用 `socks5://`。

## 按需归档到 Zotero

安装、鉴权或归档前读取
[references/zotero-bridge.md](references/zotero-bridge.md)。

1. 要求 YAML 中已有原文目录、译文目录、Zotero 数据目录和 bridge token 文件
   路径。helper 只读取 token 文件，不得打印内容。
2. 设置 `PDF2ZH_SKILL_CONFIG` 指向生成的 YAML 后启动 Zotero；bridge 会按需
   读取缓存的原文与译文目录。也可用 `PDF2ZH_SOURCE_DIRECTORY` 和
   `PDF2ZH_TRANSLATED_DIRECTORY` 覆盖 YAML；bridge 不包含机器专属回退目录。
3. Windows 使用 `invoke_zotero_bridge.ps1 -Action Health`，Linux 使用
   `invoke_zotero_bridge.py health` 检查 bridge。
4. 只有获得用户授权后，才通过 Zotero Plugins Manager 安装捆绑 XPI。不得
   静默复制到 profile，也不得修改 `extensions.json`。
5. 明确唯一目标 collection，并仅用变量传递路径：

   ```bash
   scripts/invoke_zotero_bridge.py prepare \
     --source-path "$SOURCE_PDF" \
     --target-collection-id "$COLLECTION_ID" \
     --short-title "$SHORT_TITLE"

   scripts/invoke_zotero_bridge.py archive \
     --source-attachment-id "$ATTACHMENT_ID" \
     --target-collection-id "$COLLECTION_ID" \
     --translated-path "$TRANSLATED_PDF" \
     --short-title "$SHORT_TITLE"
   ```

6. 对 bridge 返回的准确附件路径重新验证。原文与双语附件必须共享同一文献父
   条目，只有父条目属于目标 collection；修复必须显式报告，重复调用必须幂等
   且不得创建重复附件。

不得直接编辑 `zotero.sqlite`。Zotero 运行时 immutable SQLite 可能忽略实时
WAL；应优先信任 bridge 返回，或关闭 Zotero 后再做只读审计。
