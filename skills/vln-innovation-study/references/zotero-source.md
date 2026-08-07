# Zotero VLN Source

## Local identity

- Data directory: `/home/zq/Zotero`
- Active database: `/home/zq/Zotero/zotero.sqlite`
- Attachment storage: `/home/zq/Zotero/storage`
- Collection name: `VLN`
- Collection key: `QETYZLNY`
- Library: personal library (`users/0` in the local API)

Include the root collection and every descendant collection. Treat collection counts and numeric SQLite IDs as transient; resolve by the stable collection key or case-insensitive name.

## Safe access order

1. If the focal title is known, search attachment filenames under `/home/zq/Zotero/storage` with `rg --files` and a distinctive title fragment.
2. If collection enumeration or metadata lookup is needed, prefer Zotero's read-only local API at `http://127.0.0.1:23119/api/`.
3. If the local API returns `403`, tell the user to enable Zotero Settings → Advanced → “Allow other applications on this computer to communicate with Zotero”. Do not change this preference silently.
4. If Zotero is closed, allow read-only SQLite access with `mode=ro` and `PRAGMA query_only=ON`.
5. If the database is locked, stop the SQLite query. Never bypass an active rollback journal with `immutable=1`, and never write directly to `zotero.sqlite`.

Use the official local API collection endpoints with API version 3:

```text
/api/users/0/collections/QETYZLNY
/api/users/0/collections/QETYZLNY/collections
/api/users/0/collections/<child-key>/items/top
/api/users/0/items/<item-key>/children
/api/users/0/items/<attachment-key>/file/view/url
```

Recurse through subcollections because collection item endpoints do not imply conceptual lineage order.

## Attachment resolution

For known-title filesystem search:

1. Keep only PDF candidates whose normalized title matches the focal paper.
2. Run `pdfinfo` and hash candidates before choosing one.
3. Collapse byte-identical duplicates.
4. Prefer the original-language, original-pagination PDF.
5. Treat filenames containing `compare`, `dual`, `bilingual`, `translated`, or language suffixes as reading aids, not the page-anchor authority.
6. Record the selected absolute PDF path in the paper note's `source` field.
7. Use the original PDF's printed/page sequence consistently for evidence anchors.

Do not assume the largest PDF is the original; bilingual or merged outputs are often larger and may double the page count.

## Metadata and evidence boundary

- Use Zotero metadata to identify and locate a paper.
- Use the focal PDF for `AUTHOR` claims, equations, figures, tables, and page anchors.
- Use the official paper page to verify title, authors, revision, venue, or DOI when needed.
- Do not treat a Zotero abstract, note, tag, or generated full-text cache as a substitute for the paper.
- Do not edit collections, items, tags, notes, or attachments unless the user explicitly asks for Zotero changes.

## Duplicate and transformed attachments

Keep multiple attachments visible when their roles differ, but select exactly one anchor PDF for the persistent note. A compare/translated copy may help comprehension; verify every technical claim and page reference against the anchor PDF before writing it as `AUTHOR` evidence.
