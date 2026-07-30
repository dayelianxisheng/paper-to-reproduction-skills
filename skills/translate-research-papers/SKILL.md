---
name: translate-research-papers
description: Translate research-paper PDFs with the local Zotero PDF2zh server, keep the server terminal visible, try uv when available and fall back to the PDF2zh Conda environment, call the PDF2zh and authenticated Zotero REST bridges without GUI clicks, validate bilingual outputs, and attach original and translated PDFs under the correct Zotero bibliographic parent. Use when asked to translate PDFs with PDF2zh, automate Zotero bilingual-PDF workflows, import translated PDFs into Zotero, or diagnose this Windows PDF2zh server/API setup.
---

# Translate Research Papers with PDF2zh and Zotero

Run one paper end to end before authorizing a batch. Keep the PDF2zh server window visible so the user can inspect progress and errors.

## Local configuration

- Source PDFs: `D:\download`
- Server directory: `D:\resource\env\fanyi\server\server`
- Server URL: `http://127.0.0.1:8890`
- Conda activation script: `D:\resource\env\miniconda3\Scripts\activate.bat`
- Conda environment: `PDF2zh`
- Zotero data directory: `D:\software\Professional\Zotero\note`
- Zotero bridge URL: `http://127.0.0.1:23119/pdf2zh-bridge`
- Zotero bridge token: `D:\software\Professional\Zotero\note\pdf2zh-bridge.token`
- Zotero bridge add-on ID: `pdf2zh-bridge@codex.local`
- Default engine/service: `pdf2zh_next` with `siliconflowfree`
- Bilingual side-by-side endpoint: `/compare`

Do not print, copy, or expose API keys or the bridge token. Do not edit `zotero.sqlite` directly while Zotero is running. Do not use the PDF2zh context menu or Zotero's Run JavaScript window for the routine workflow.

## Workflow

1. Inspect the source PDF, intended Zotero collection, existing parent, and attachments. Resolve the source attachment ID and target collection ID. Skip an already valid translation unless the user requests replacement.
2. Confirm Zotero is running and its restricted bridge responds:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_zotero_bridge.ps1 `
     -Action Health
   ```

   A successful response must report `status=ok`, the Zotero version, token path, and allowed import root. If it fails, start Zotero or restart it once; do not fall back to GUI scripting.

3. Start or check the PDF2zh server:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   The script returns immediately if port 8890 is already listening. It tries uv only when installed; otherwise it launches the known Conda configuration in a visible terminal. If an installed uv path fails to listen, inspect its visible terminal and rerun with `-ForceConda`.

4. Translate through the PDF2zh REST API:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source "D:\download\paper.pdf" `
     -Endpoint compare
   ```

   Treat the returned `status=success` and `outputFiles` as provisional until PDF validation passes. The REST request is synchronous and can take several minutes; run it in a background process and poll logs when interactive responsiveness is required.

5. Validate the generated PDF:

   - Confirm the file exists, is non-empty, and starts with `%PDF-`.
   - Confirm its page count matches the source unless pages were intentionally skipped.
   - Extract text and confirm that meaningful Chinese text is present.
   - Confirm the bilingual layout visually on representative pages when feasible.

6. Archive through the authenticated Zotero bridge:

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

   `TemplateItemID` is optional and is used only when a bibliographic parent must be created. The bridge places the parent in the target collection, names the source `<shortTitle>-original`, names the bilingual attachment `<shortTitle>-<service>-compare`, and removes direct collection membership from child attachments. Repeating the same request must return `idempotent=true` without creating duplicates.

7. Verify the returned parent ID/key, both child attachment IDs, stored paths, page counts, and collection membership. Parent collections must contain the target collection; both child collection lists must be empty. Report elapsed time and any fallback or warning.

The bridge exposes only health, update metadata, and the constrained archive operation. It requires a local token, accepts translated PDFs only below `server\translated`, and does not expose arbitrary JavaScript or SQL execution. Read [references/zotero-bridge.md](references/zotero-bridge.md) only when maintaining or diagnosing the bridge.

## Failure handling

- If port 8890 is unavailable, inspect the visible server terminal before changing environments.
- If uv is unavailable or belongs to another computer, use the Conda fallback with `--enable_venv false --check_update false` and prepend both bundled PDF2zh virtual-environment `Scripts` directories to `PATH`.
- If bridge health fails, confirm Zotero is running, the persistent add-on exists in the active profile, and the token file is readable. Restart Zotero once after an add-on update.
- If archive returns `UNAUTHORIZED`, do not paste the token into commands or chat; let `invoke_zotero_bridge.ps1` read the token file.
- If archive returns `PATH_OUTSIDE_ALLOWED_ROOT`, leave the validated output in `server\translated` and retry with that absolute path.
- If the server returns success but no file exists, inspect `server\translated`, the visible terminal, and the exact filename in `fileList`.
- Preserve server outputs until the Zotero storage copy and PDF validation have both succeeded.
