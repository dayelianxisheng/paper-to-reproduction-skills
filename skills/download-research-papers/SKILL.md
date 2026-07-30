---
name: download-research-papers
description: Batch-download research-paper PDFs from a user-provided reading list or URL manifest, apply consistent filenames, validate that responses are real PDFs, retry transient failures, skip already valid files, and produce a machine-readable report. Use for literature-review collections, paper reading lists, conference PDF archives, or repeatable PDF corpus downloads.
---

# Download Research Papers

Turn a paper list into a verified local PDF collection with
`scripts/download_papers.py`. Prefer official publisher, conference, proceedings,
or arXiv PDF URLs.

## Workflow

1. Extract every requested paper into a UTF-8 JSON manifest:

   ```json
   [
     {
       "title": "Paper title",
       "filename": "01_2025_Short_Name_Venue.pdf",
       "url": "https://example.org/paper.pdf"
     }
   ]
   ```

2. Preserve the user's requested ordering and naming convention. Make every
   filename a plain basename ending in `.pdf`; never allow directory traversal.
3. Confirm the output directory is in scope. Create it if needed.
4. Run:

   ```powershell
   python "<skill-dir>\scripts\download_papers.py" `
     --manifest "<manifest.json>" `
     --output "<download-directory>" `
     --workers 4 `
     --retries 3
   ```

5. Read the generated `download_report.json`. Treat the run as incomplete if
   any item is `failed`; an HTTP success containing HTML is still a failure.
6. For failures, verify the citation and locate an authoritative alternate PDF
   URL if internet lookup is allowed, update the manifest, and rerun. Valid
   existing PDFs are skipped, so reruns are cheap.
7. Report the destination, downloaded/skipped/failed counts, manifest path,
   report path, and any unresolved papers.

## Script behavior

- Download concurrently with a browser-like user agent and bounded retries.
- Write to `.part` files and atomically rename only after validation.
- Accept a PDF marker within the first 1,024 bytes and require at least 1 KiB.
- Record byte size and SHA-256 for every valid PDF.
- Never overwrite a valid existing PDF. Replace an existing invalid file only
  after a valid replacement has downloaded.
- Exit nonzero when any paper fails.

## Bundled VLN list

For the 24-paper VLN collection, use
`references/vln-reading-list.json`. Load that reference only when the user asks
to download, reproduce, or update this specific collection.
