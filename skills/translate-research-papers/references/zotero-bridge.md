# Restricted Zotero bridge

Use this reference only to maintain or diagnose the local bridge. Routine translation should call `scripts/invoke_zotero_bridge.ps1`.

## Endpoints

- `GET http://127.0.0.1:23119/pdf2zh-bridge/health`
- `POST http://127.0.0.1:23119/pdf2zh-bridge/archive`

Both operational endpoints require:

```text
X-PDF2zh-Bridge-Token: <token read from the Zotero data directory>
Zotero-Allowed-Request: true
```

The bridge binds through Zotero's localhost server. The token is stored at `D:\software\Professional\Zotero\note\pdf2zh-bridge.token`; never print or copy its full value.

## Archive contract

Required JSON fields:

- `sourceAttachmentID`: Zotero ID of an existing PDF attachment.
- `targetCollectionID`: Zotero collection ID for the bibliographic parent.
- `translatedPath`: absolute path to a validated PDF below `D:\resource\env\fanyi\server\server\translated`.
- `shortTitle`: stable attachment-name prefix.

Optional fields:

- `service`, default `siliconflowfree`.
- `templateItemID`, used to copy metadata and creators when creating a parent.
- `itemType`, default `conferencePaper`.
- `metadata`: supported bibliographic fields and creators.

The operation is idempotent by parent and attachment title. It never accepts arbitrary JavaScript, SQL, destination paths, or delete commands.

## Installation and maintenance

- Add-on ID: `pdf2zh-bridge@codex.local`
- Source: `scripts/zotero-bridge`
- Build script: `scripts/build_zotero_bridge.ps1`
- Built XPI: `scripts/pdf2zh-bridge@codex.local.xpi`

Zotero 9.0.6 requires `applications.zotero.update_url` in the manifest. Use an HTTPS URL so update-security checks do not mark the unsigned local add-on as application-disabled. The configured HTTPS loopback URL intentionally has no remote dependency; the bridge returns local update metadata over its HTTP endpoint but performs no self-update.

After changing bridge source:

1. Increment both manifest and bootstrap versions.
2. Run `scripts/build_zotero_bridge.ps1`.
3. Replace only the exact installed XPI in the active Zotero profile.
4. Restart Zotero cleanly.
5. Require a successful health response and an idempotent archive test.

Do not edit `extensions.json` or `zotero.sqlite` directly. Do not add a general-purpose code-execution endpoint.
