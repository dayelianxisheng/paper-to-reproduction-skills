param(
    [ValidateSet("Health", "Archive")]
    [string]$Action = "Health",

    [string]$ServerUrl = "http://127.0.0.1:23119",
    [string]$TokenPath = "D:\software\Professional\Zotero\note\pdf2zh-bridge.token",
    [int]$SourceAttachmentID,
    [int]$TargetCollectionID,
    [Parameter()]
    [string]$TranslatedPath,
    [Parameter()]
    [string]$ShortTitle,
    [string]$Service = "siliconflowfree",
    [int]$TemplateItemID,
    [string]$ItemType = "conferencePaper",
    [string]$Title,
    [string]$Date,
    [string]$DOI,
    [string]$ProceedingsTitle,
    [string]$Url,
    [string]$Pages,
    [string]$CreatorsJson
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

$token = (Get-Content -LiteralPath $TokenPath -Raw -Encoding UTF8).Trim()
if ($token -notmatch "^[A-Za-z0-9]{48,128}$") {
    throw "Bridge token file is invalid: $TokenPath"
}

$headers = @{
    "X-PDF2zh-Bridge-Token" = $token
    "Zotero-Allowed-Request" = "true"
}
$common = @{
    Headers = $headers
    UserAgent = "Codex-PDF2zh-Bridge/0.1"
    TimeoutSec = 120
}

if ($Action -eq "Health") {
    $response = Invoke-RestMethod `
        -Uri "$ServerUrl/pdf2zh-bridge/health" `
        -Method Get `
        @common
    $response | ConvertTo-Json -Depth 8
    exit 0
}

if ($SourceAttachmentID -le 0) {
    throw "SourceAttachmentID is required for Archive"
}
if ($TargetCollectionID -le 0) {
    throw "TargetCollectionID is required for Archive"
}
if ([string]::IsNullOrWhiteSpace($TranslatedPath)) {
    throw "TranslatedPath is required for Archive"
}
if ([string]::IsNullOrWhiteSpace($ShortTitle)) {
    throw "ShortTitle is required for Archive"
}

$metadata = [ordered]@{}
foreach ($entry in @{
    title = $Title
    date = $Date
    DOI = $DOI
    proceedingsTitle = $ProceedingsTitle
    url = $Url
    pages = $Pages
}.GetEnumerator()) {
    if (-not [string]::IsNullOrWhiteSpace($entry.Value)) {
        $metadata[$entry.Key] = $entry.Value
    }
}
if (-not [string]::IsNullOrWhiteSpace($CreatorsJson)) {
    $metadata.creators = @($CreatorsJson | ConvertFrom-Json)
}

$body = [ordered]@{
    sourceAttachmentID = $SourceAttachmentID
    targetCollectionID = $TargetCollectionID
    translatedPath = (Resolve-Path -LiteralPath $TranslatedPath).Path
    shortTitle = $ShortTitle
    service = $Service
    itemType = $ItemType
    metadata = $metadata
}
if ($TemplateItemID -gt 0) {
    $body.templateItemID = $TemplateItemID
}

$response = Invoke-RestMethod `
    -Uri "$ServerUrl/pdf2zh-bridge/archive" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ($body | ConvertTo-Json -Depth 8 -Compress) `
    @common
$response | ConvertTo-Json -Depth 8
