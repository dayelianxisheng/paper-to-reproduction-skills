---
name: translate-research-papers
description: Translate research-paper PDFs with a local PDF2zh service on native Windows, native Linux, or WSL; discover and cache verified local paths in YAML; validate bilingual layout and Chinese text; and optionally archive attachments in Zotero through a restricted local bridge. Use for PDF2zh translation, bilingual/compare PDFs, Zotero attachment import, local path discovery, or PDF2zh/Zotero diagnostics.
---

# Translate Research Papers

Translate one paper successfully before starting a batch. Keep the PDF2zh server
terminal visible. Never expose API keys, proxy URLs, or the Zotero bridge token.

## Discover local paths first

Do not embed machine-specific paths in commands, documentation, or source. At
the start of every use, refresh the local YAML cache:

```bash
scripts/local_config.py refresh --source "$SOURCE_PDF"
```

The resolver uses explicit arguments and environment variables first, then
searches at limited depth by file signature. It writes only paths that currently
exist. Its default YAML location follows the operating system's user-config
directory; override it with `PDF2ZH_SKILL_CONFIG` or `--config`. Never commit
this generated YAML.

Use `local_config.py get KEY` when a path is needed. The Linux and PowerShell
helpers refresh and read the YAML automatically. If discovery misses a path,
rerun `refresh` with an explicit `--server-directory`, `--source-directory`,
`--translated-directory`, `--zotero-data-directory`, `--token-path`, or
`--search-root`. A missing or stale required path must stop the workflow.

Choose the platform only after discovery:

- Native Windows: use the PowerShell helpers.
- Native Linux: use the shell and Python helpers.
- WSL: use Windows PowerShell only when the discovered PowerShell and `wslpath`
  executables both exist; otherwise use the native-Linux flow.

Missing Zotero paths must not block a translation-only request.

## Translate

1. Confirm that the source exists, is non-empty, and starts with `%PDF-`.
2. Start PDF2zh in a visible terminal. Both launchers refresh the YAML first.

   Windows:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_pdf2zh_visible.ps1
   ```

   Linux:

   ```bash
   scripts/start_pdf2zh_visible.sh
   ```

3. Translate with the `compare` endpoint.

   Windows:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/invoke_pdf2zh.ps1 `
     -Source $SourcePdf -Endpoint compare
   ```

   Linux:

   ```bash
   scripts/invoke_pdf2zh_linux.py \
     --source "$SOURCE_PDF" \
     --endpoint compare \
     --delivery "$DELIVERY_PDF"
   ```

   The Linux helper tries REST first. If `/compare` returns a wrapper-level
   `CalledProcessError`, it runs the same `pdf2zh_next` CLI directly, preserves
   the valid LR dual PDF, and copies it to `*.compare.pdf`. Do not start a second
   translation while this fallback runs. Treat rich-text fallback messages as
   warnings only when the process exits successfully and emits a valid PDF.

4. Validate before delivery or archive.

   ```bash
   scripts/validate_bilingual_pdf.py \
     --source "$SOURCE_PDF" \
     --translated "$TRANSLATED_PDF" \
     --layout lr \
     --render-prefix "$PREVIEW_PREFIX"
   ```

   Require a valid PDF header, matching page count, meaningful Chinese text,
   expected LR geometry, and a visually correct first-page preview.

## Diagnose Linux proxy import failures

Treat `ValueError: Unknown scheme for proxy URL URL('socks://…')` from
`httpx` while importing `ollama` as an environment failure, not a font or PDF
failure. The retry with `--skip-subset-fonts` cannot fix it.

- Inspect only proxy variable names and schemes; never print full values.
- Check the environment of the port-8890 listener, because a graphical terminal
  can inherit a different `ALL_PROXY` than the current shell.
- The Linux launcher removes only an unsupported `ALL_PROXY`/`all_proxy` value
  beginning with `socks://` inside the new server terminal. It preserves valid
  HTTP/HTTPS proxy variables and never changes global proxy settings.
- If an existing server inherited the bad value, resolve its exact listener PID,
  stop only that process, rerun the launcher, probe the imports, and check
  `/health`. Use `socks5://` only when the installed HTTP client and SOCKS
  dependency support it.

## Archive in Zotero when requested

Read `references/zotero-bridge.md` before installation, authorization, or
archive work.

1. Require the YAML keys for the source directory, translated directory, Zotero
   data directory, and bridge token path. The helper reads the token file but
   never prints its contents.
2. Launch Zotero with `PDF2ZH_SKILL_CONFIG` pointing to the generated YAML. The
   bridge reads the cached source and translated directories when needed.
   Explicit `PDF2ZH_SOURCE_DIRECTORY` and `PDF2ZH_TRANSLATED_DIRECTORY` values
   may override the YAML; the bridge has no machine-specific fallback roots.
3. Check health with `invoke_zotero_bridge.ps1 -Action Health` on Windows or
   `invoke_zotero_bridge.py health` on Linux.
4. Install the bundled XPI through Zotero's Plugins Manager only after user
   authorization. Never copy it silently into a profile or edit
   `extensions.json`.
5. Resolve an unambiguous target collection. Prepare and archive with variables,
   not literal local paths:

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

6. Validate the exact returned attachment path. Confirm that the original and
   bilingual attachments share one bibliographic parent, only the parent belongs
   to the target collection, repair is reported explicitly, and a repeated call
   is idempotent without duplicates.

Never edit `zotero.sqlite` directly. While Zotero is running, an immutable
SQLite connection can ignore the live WAL; prefer bridge results or close
Zotero before a read-only audit.
