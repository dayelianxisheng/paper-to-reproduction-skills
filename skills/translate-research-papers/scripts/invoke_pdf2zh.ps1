param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [ValidateSet("translate", "compare", "crop", "crop-compare")]
    [string]$Endpoint = "compare",

    [string]$ServerUrl = "http://127.0.0.1:8890",
    [string]$TranslatedDirectory = "D:\resource\env\fanyi\server\server\translated",
    [string]$NextService = "siliconflowfree",
    [string]$SourceLanguage = "en",
    [string]$TargetLanguage = "zh-CN",
    [int]$TimeoutSeconds = 1800,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$resolvedSource = (Resolve-Path -LiteralPath $Source).Path
if ([System.IO.Path]::GetExtension($resolvedSource) -ine ".pdf") {
    throw "Source must be a PDF: $resolvedSource"
}

$sourceInfo = Get-Item -LiteralPath $resolvedSource
if ($sourceInfo.Length -lt 5) {
    throw "Source PDF is empty: $resolvedSource"
}

$config = [ordered]@{
    engine                    = "pdf2zh_next"
    service                   = "bing"
    next_service              = $NextService
    sourceLang                = $SourceLanguage
    targetLang                = $TargetLanguage
    skipLastPages             = "0"
    threadNum                 = "4"
    qps                       = "10"
    poolSize                  = "0"
    mono                      = "true"
    dual                      = "true"
    mono_cut                  = "false"
    dual_cut                  = "false"
    crop_compare              = "false"
    compare                   = "false"
    babeldoc                  = "false"
    skipSubsetFonts           = "false"
    fontFile                  = ""
    fontFamily                = "auto"
    dualMode                  = "LR"
    transFirst                = "true"
    ocr                       = "false"
    autoOcr                   = "true"
    noWatermark               = "true"
    saveGlossary              = "false"
    disableGlossary           = "false"
    noDual                    = "false"
    noMono                    = "false"
    skipClean                 = "false"
    disableRichTextTranslate  = "false"
    enhanceCompatibility      = "false"
    translateTableText        = "false"
    onlyIncludeTranslatedPage = "false"
}

if ($DryRun) {
    [pscustomobject]@{
        status = "dry-run"
        source = $resolvedSource
        sourceBytes = $sourceInfo.Length
        endpoint = "$ServerUrl/$Endpoint"
        config = $config
    } | ConvertTo-Json -Depth 5
    exit 0
}

$bytes = [System.IO.File]::ReadAllBytes($resolvedSource)
$payload = [ordered]@{
    fileName = $sourceInfo.Name
    fileContent = "data:application/pdf;base64," + [System.Convert]::ToBase64String($bytes)
}
foreach ($entry in $config.GetEnumerator()) {
    $payload[$entry.Key] = $entry.Value
}

$started = Get-Date
$response = Invoke-RestMethod `
    -Uri "$ServerUrl/$Endpoint" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ($payload | ConvertTo-Json -Compress) `
    -TimeoutSec $TimeoutSeconds

if ($response.status -ne "success" -or -not $response.fileList) {
    throw "PDF2zh returned an unsuccessful response: $($response | ConvertTo-Json -Compress)"
}

$outputs = foreach ($fileName in $response.fileList) {
    $path = Join-Path $TranslatedDirectory $fileName
    $exists = Test-Path -LiteralPath $path
    $header = $null
    $length = $null
    if ($exists) {
        $fileInfo = Get-Item -LiteralPath $path
        $length = $fileInfo.Length
        $stream = [System.IO.File]::OpenRead($path)
        try {
            $buffer = New-Object byte[] 5
            [void]$stream.Read($buffer, 0, 5)
            $header = [System.Text.Encoding]::ASCII.GetString($buffer)
        }
        finally {
            $stream.Dispose()
        }
    }
    [pscustomobject]@{
        fileName = $fileName
        path = $path
        exists = $exists
        bytes = $length
        pdfHeaderValid = ($header -eq "%PDF-")
    }
}

[pscustomobject]@{
    status = $response.status
    endpoint = $Endpoint
    source = $resolvedSource
    elapsedSeconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
    outputFiles = @($outputs)
} | ConvertTo-Json -Depth 5

