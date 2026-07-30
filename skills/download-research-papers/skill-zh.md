---
name: download-research-papers
description: 根据用户提供的阅读清单或 URL 清单批量下载研究论文 PDF，统一文件名，验证响应确实是 PDF，重试暂时性失败，跳过已有有效文件，并生成机器可读报告。适用于文献综述、论文阅读清单、会议 PDF 归档或可重复执行的论文语料下载。
---

# 下载研究论文

使用 `scripts/download_papers.py` 将论文清单转换为经过验证的本地 PDF
集合。优先使用出版方、会议、论文集或 arXiv 的官方 PDF 地址。

## 工作流程

1. 将所有待下载论文整理成 UTF-8 JSON 清单：

   ```json
   [
     {
       "title": "论文标题",
       "filename": "01_2025_Short_Name_Venue.pdf",
       "url": "https://example.org/paper.pdf"
     }
   ]
   ```

2. 保留用户要求的排序和命名规则。每个 `filename` 必须是以 `.pdf`
   结尾的普通文件名，禁止目录穿越。
3. 确认输出目录位于任务授权范围内；必要时创建目录。
4. 运行：

   ```powershell
   python "<skill-dir>\scripts\download_papers.py" `
     --manifest "<manifest.json>" `
     --output "<download-directory>" `
     --workers 4 `
     --retries 3
   ```

5. 读取生成的 `download_report.json`。只要有任何条目为 `failed`，就将
   本次下载视为未完成；HTTP 请求成功但内容实际为 HTML 时仍属于失败。
6. 对失败项核对论文信息；若允许联网，则查找权威的备用 PDF 地址，更新清单
   后重新运行。有效的现有 PDF 会被跳过，因此重复运行成本较低。
7. 汇报下载目录、成功/跳过/失败数量、清单路径、报告路径及尚未解决的论文。

## 脚本行为

- 使用接近浏览器的 User-Agent 并发下载，并限制重试次数。
- 先写入 `.part` 文件，验证通过后再原子重命名。
- 允许 PDF 标记出现在前 1,024 字节内，并要求文件至少为 1 KiB。
- 为每个有效 PDF 记录文件大小和 SHA-256。
- 不覆盖已有有效 PDF；只有在有效替代文件下载完成后才替换无效文件。
- 任意论文下载失败时返回非零退出码。

## 内置 VLN 清单

处理 24 篇 VLN 论文合集时，使用
`references/vln-reading-list.json`。仅当用户要求下载、复现或更新该特定
合集时加载此参考文件。
