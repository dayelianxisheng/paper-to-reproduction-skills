---
name: download-research-papers
description: Download and validate research-paper PDFs from a reading list or JSON manifest. Use when saving a verified paper collection with consistent filenames.
---

# Download Research Papers

Prefer official publisher, conference, proceedings, or arXiv PDF URLs.

## Workflow

1. Build a UTF-8 JSON manifest containing `title`, `filename`, and `url`.
   Preserve the requested order; filenames must be plain `.pdf` basenames.
2. Confirm the destination directory, then run:

   ```powershell
   python "<skill-dir>\scripts\download_papers.py" `
     --manifest "<manifest.json>" `
     --output "<download-directory>" `
     --workers 4 --retries 3
   ```

3. Check `download_report.json`. Retry failed items with a verified official
   alternate URL; valid existing PDFs are skipped.
4. Report destination and downloaded/skipped/failed counts.

Use `references/vln-reading-list.json` only for the bundled VLN collection.
