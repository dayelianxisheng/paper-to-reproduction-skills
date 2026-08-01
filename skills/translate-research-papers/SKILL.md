---
name: translate-research-papers
description: Translate research-paper PDFs with the local PDF2zh service and attach validated bilingual PDFs to Zotero. Use for the configured Windows PDF2zh/Zotero workflow.
---

# Translate Research Papers

Translate one paper successfully before starting a batch. Keep the PDF2zh server
terminal visible. Never expose API keys or the Zotero bridge token.

## Local setup

- PDFs: `D:\download`
- Server: `D:\resource\env\fanyi\server\server`
- PDF2zh: `http://127.0.0.1:8890`
- Zotero bridge: `http://127.0.0.1:23119/pdf2zh-bridge`
- Conda fallback: `PDF2zh`

## Workflow

1. Check Zotero bridge health:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_zotero_bridge.ps1 -Action Health
   ```

2. Start PDF2zh:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   Use uv when available; use `-ForceConda` if uv fails.

3. Translate:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source "D:\download\paper.pdf" -Endpoint compare
   ```

4. Verify the output exists, starts with `%PDF-`, has the expected page count,
   and contains meaningful Chinese text.
5. Archive with `invoke_zotero_bridge.ps1 -Action Archive`, using the source
   attachment ID, target collection ID, translated path, and short title.
6. Confirm the original and bilingual attachments share the correct parent and
   no duplicate was created.

Read `references/zotero-bridge.md` only when health, authorization, path, or
archive diagnostics are needed.
