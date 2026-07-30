param(
    [string]$ServerDirectory = "D:\resource\env\fanyi\server\server",
    [int]$Port = 8890,
    [int]$WaitSeconds = 30,
    [switch]$ForceConda
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Test-Pdf2zhPort {
    param([int]$LocalPort)
    return [bool](Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Pdf2zhPort {
    param([int]$LocalPort, [int]$Seconds)
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        if (Test-Pdf2zhPort -LocalPort $LocalPort) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

$resolvedServer = (Resolve-Path -LiteralPath $ServerDirectory).Path

if (Test-Pdf2zhPort -LocalPort $Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen |
        Select-Object -First 1
    [pscustomobject]@{
        status = "already-running"
        port = $Port
        pid = $listener.OwningProcess
        method = "existing"
    } | ConvertTo-Json -Compress
    exit 0
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv -and -not $ForceConda) {
    $uvCommand = 'cd /d "{0}" && set "PYTHONIOENCODING=utf-8" && uv run --python 3.12 --with-requirements requirements.txt server.py' -f $resolvedServer
    $uvProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $uvCommand -WindowStyle Normal -PassThru
    if (Wait-Pdf2zhPort -LocalPort $Port -Seconds $WaitSeconds) {
        [pscustomobject]@{
            status = "started"
            port = $Port
            pid = $uvProcess.Id
            method = "uv"
        } | ConvertTo-Json -Compress
        exit 0
    }
    throw "uv was launched visibly but port $Port did not start. Inspect that terminal, then rerun with -ForceConda."
}

$condaActivate = "D:\resource\env\miniconda3\Scripts\activate.bat"
if (-not (Test-Path -LiteralPath $condaActivate)) {
    throw "Conda activation script not found: $condaActivate"
}

$legacyScripts = Join-Path $resolvedServer "zotero-pdf2zh-venv\Scripts"
$nextScripts = Join-Path $resolvedServer "zotero-pdf2zh-next-venv\Scripts"
$condaCommand = 'cd /d "{0}" && call "{1}" PDF2zh && set "PATH={2};{3};%PATH%" && set "PYTHONIOENCODING=utf-8" && python server.py --enable_venv false --check_update false' -f $resolvedServer, $condaActivate, $legacyScripts, $nextScripts
$condaProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $condaCommand -WindowStyle Normal -PassThru

if (-not (Wait-Pdf2zhPort -LocalPort $Port -Seconds $WaitSeconds)) {
    throw "Conda fallback was launched visibly but port $Port did not start. Inspect the terminal."
}

[pscustomobject]@{
    status = "started"
    port = $Port
    pid = $condaProcess.Id
    method = "conda"
} | ConvertTo-Json -Compress

