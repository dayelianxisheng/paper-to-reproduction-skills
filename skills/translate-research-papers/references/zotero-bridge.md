# Restricted Zotero bridge

Use this reference only to install, maintain, or diagnose the local bridge.
Routine calls should use `scripts/invoke_zotero_bridge.ps1` on Windows or
`scripts/invoke_zotero_bridge.py` on Linux.

## Endpoints

- `GET /pdf2zh-bridge/health`
- `POST /pdf2zh-bridge/prepare`
- `POST /pdf2zh-bridge/archive`

Operational endpoints require both headers below. Helpers read the token from
disk and must never print its value.

```text
X-PDF2zh-Bridge-Token: <local token>
Zotero-Allowed-Request: true
```

Default token paths:

- Windows: `D:\software\Professional\Zotero\note\pdf2zh-bridge.token`
- Linux: `~/Zotero/pdf2zh-bridge.token`

## Allowed roots

The bridge accepts only PDF paths below two roots reported by `/health`:

- Source root: `D:\download` on Windows or `~/Downloads` on Linux.
- Translated root: the configured PDF2zh `server/translated` directory.

Override both when launching Zotero with `PDF2ZH_SOURCE_DIRECTORY` and
`PDF2ZH_TRANSLATED_DIRECTORY`. Path checks are case-insensitive only on Windows.

## Prepare contract

Required fields:

- `sourcePath`: original PDF below the allowed source root.
- `targetCollectionID`: existing Zotero collection ID.
- `shortTitle`: stable attachment prefix.

The operation imports `<shortTitle>-original` as a standalone attachment only
when it does not already exist in the target collection or one of its parents.
It returns `source.id` for the archive call and is idempotent by attachment title.

## Archive contract

Required fields:

- `sourceAttachmentID`: existing original PDF attachment.
- `targetCollectionID`: target collection for the bibliographic parent.
- `translatedPath`: validated PDF below the allowed translated root.
- `shortTitle`: stable attachment prefix.

Optional fields include `service`, `templateItemID`, `itemType`, and bounded
bibliographic metadata. The operation is idempotent by parent and attachment
title. It accepts no arbitrary JavaScript, SQL, delete operation, or destination
path.

Title idempotence is backed by a file-presence check. If a matching translated
attachment record points to a missing or empty file, the bridge removes that
invalid child attachment, imports the validated translated PDF again, and
returns `translated.repaired=true`. Always validate the exact returned
`translated.path`; then repeat the archive call and require
`idempotent=true`, `created=false`, and `repaired=false`.

## Installation and maintenance

- Add-on ID: `pdf2zh-bridge@codex.local`
- Source: `scripts/zotero-bridge`
- Windows builder: `scripts/build_zotero_bridge.ps1`
- Linux builder: `scripts/build_zotero_bridge.sh`
- Built XPI: `scripts/pdf2zh-bridge@codex.local.xpi`

For a new installation, use Zotero **Tools → Plugins → gear → Install Plugin
From File**. Silent XPI copying can be ignored by the add-on manager. Never edit
`extensions.json`.

After changing bridge source:

1. Increment both `manifest.json` and `bootstrap.js` versions.
2. Build the XPI with the platform helper.
3. Install or update through Plugins Manager; restart Zotero if requested.
4. Require successful health, prepare idempotence, and archive idempotence tests.

Never edit `zotero.sqlite` directly. While Zotero is running, an immutable
SQLite connection can omit current WAL changes; use bridge responses as the
authoritative live state.
