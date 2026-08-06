---
name: translate-research-papers
description: Translate research-paper PDFs with a local PDF2zh service on native Windows, native Linux, or WSL; validate bilingual layout and Chinese text; and optionally prepare and archive original plus translated attachments in Zotero through a restricted local bridge. Use for PDF2zh paper translation, bilingual/compare PDFs, Zotero attachment import, or PDF2zh/Zotero service diagnostics.
---

# Translate Research Papers

Translate one paper successfully before starting a batch. Keep the PDF2zh server
terminal visible. Never expose API keys or the Zotero bridge token.

## Choose the platform first

Do not assume Windows from the historical paths. Inspect the source path and the
available shell:

- Native Windows: use the PowerShell helpers and `D:\download` defaults.
- Native Linux: use the `.sh` and `.py` helpers. The default server is
  `~/resource/env/zotero/zotero-pdf2zh/server`.
- WSL: use Windows PowerShell only when `powershell.exe` and `wslpath` exist;
  otherwise treat the environment as native Linux.

Missing Zotero bridge support must not block a translation-only request.

## Translate

1. Confirm that the source exists, starts with `%PDF-`, and is non-empty.
2. Start PDF2zh in a visible terminal.

   Windows:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   Native Linux:

   ```bash
   scripts/start_pdf2zh_visible.sh
   ```

3. Translate with the `compare` endpoint.

   Windows:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source "D:\download\paper.pdf" -Endpoint compare
   ```

   Native Linux:

   ```bash
   scripts/invoke_pdf2zh_linux.py \
     --source /path/to/paper.pdf \
     --endpoint compare \
     --delivery /path/to/paper-中英对照.pdf
   ```

   The Linux helper tries REST first. If `/compare` returns a wrapper-level
   `CalledProcessError`, it runs the same `pdf2zh_next` CLI directly, preserves
   the valid LR dual PDF, and copies it to `*.compare.pdf`. Do not start a second
   translation while this fallback is running. Treat per-paragraph rich-text
   fallback warnings as warnings when the process exits successfully and emits
   a valid PDF.

4. Validate before delivery or archive.

   ```bash
   scripts/validate_bilingual_pdf.py \
     --source /path/to/paper.pdf \
     --translated /path/to/paper.compare.pdf \
     --layout lr \
     --render-prefix /tmp/paper-preview
   ```

   Require a valid PDF header, matching page count, meaningful Chinese text,
   and expected LR geometry. Visually inspect the rendered first page for
   clipping, blank halves, broken fonts, or reversed content.

## Diagnose Linux proxy import failures

Treat `ValueError: Unknown scheme for proxy URL URL('socks://…')` from
`httpx` while importing `ollama` as an environment failure, not a font or PDF
failure. The automatic retry with `--skip-subset-fonts` cannot fix it.

- Inspect only proxy variable names and schemes; never print complete proxy
  URLs, credentials, API keys, or tokens.
- Check the environment of the process listening on port 8890, not only the
  current shell. A graphical terminal can inherit a different `ALL_PROXY`.
- `scripts/start_pdf2zh_visible.sh` removes only an unsupported
  `ALL_PROXY`/`all_proxy` value beginning with `socks://` inside the new server
  terminal. It leaves valid `HTTP_PROXY` and `HTTPS_PROXY` values unchanged.
- If an existing server inherited the bad value, resolve its exact listener
  PID, stop only that PDF2zh process, and rerun the launcher. Do not change the
  user's global proxy configuration.
- Verify the repair with an import probe that unsets only the invalid variable,
  followed by `/health`. If SOCKS is required instead, use a scheme supported
  by the installed `httpx` version, such as `socks5://`, only after confirming
  the SOCKS dependency is installed.

## Archive in Zotero when requested

Read `references/zotero-bridge.md` before bridge installation, authorization,
path, or archive work.

1. Check bridge health. Use `invoke_zotero_bridge.ps1 -Action Health` on
   Windows or `invoke_zotero_bridge.py health` on Linux.
2. If the bridge is absent, install the bundled XPI through Zotero's
   **Tools → Plugins → gear → Install Plugin From File** only after the user
   authorizes installation. Silent profile copying is not a valid new install.
3. Ensure the target collection is known. Do not choose an ambiguous collection.
4. On Linux, prepare a source that is not yet in Zotero:

   ```bash
   scripts/invoke_zotero_bridge.py prepare \
     --source-path ~/Downloads/paper.pdf \
     --target-collection-id 77 \
     --short-title PaperName
   ```

5. Archive the validated bilingual PDF with the returned source attachment ID:

   ```bash
   scripts/invoke_zotero_bridge.py archive \
     --source-attachment-id 849 \
     --target-collection-id 77 \
     --translated-path /absolute/server/translated/paper.compare.pdf \
     --short-title PaperName
   ```

6. Confirm the original and bilingual attachments share the bibliographic
   parent and only the parent belongs to the target collection. Validate the
   PDF at the exact `translated.path` returned by the bridge; a matching Zotero
   attachment title is insufficient when its backing file is missing. The
   bridge repairs a missing or empty matching attachment and reports
   `repaired=true`. A subsequent call must return `idempotent=true` without
   duplicates.

Never edit `zotero.sqlite` or `extensions.json` directly. Do not treat an
`immutable=1` SQLite query as authoritative while Zotero is running: it can
ignore the live WAL. Prefer bridge results or shut Zotero down before a
read-only database audit.
