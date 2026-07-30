param(
    [string]$SourceDirectory = (Join-Path $PSScriptRoot "zotero-bridge"),
    [string]$OutputPath = (Join-Path $PSScriptRoot "pdf2zh-bridge@codex.local.xpi")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$resolvedSource = (Resolve-Path -LiteralPath $SourceDirectory).Path
$manifest = Join-Path $resolvedSource "manifest.json"
$bootstrap = Join-Path $resolvedSource "bootstrap.js"
if (-not (Test-Path -LiteralPath $manifest) -or -not (Test-Path -LiteralPath $bootstrap)) {
    throw "Bridge source is incomplete: $resolvedSource"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$outputDirectory = [System.IO.Path]::GetDirectoryName($resolvedOutput)
if (-not (Test-Path -LiteralPath $outputDirectory)) {
    [void](New-Item -ItemType Directory -Path $outputDirectory)
}
if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput
}

[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $resolvedSource,
    $resolvedOutput,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

$archive = [System.IO.Compression.ZipFile]::OpenRead($resolvedOutput)
try {
    $names = @($archive.Entries | ForEach-Object FullName)
}
finally {
    $archive.Dispose()
}
if ($names -notcontains "manifest.json" -or $names -notcontains "bootstrap.js") {
    throw "Built XPI does not contain root manifest.json and bootstrap.js"
}

[pscustomobject]@{
    status = "built"
    xpi = $resolvedOutput
    bytes = (Get-Item -LiteralPath $resolvedOutput).Length
    entries = $names
} | ConvertTo-Json -Depth 4
