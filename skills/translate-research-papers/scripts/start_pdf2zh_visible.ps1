param(
    [string]$ServerDirectory,
    [string]$ConfigPath,
    [string]$SearchRoot,
    [int]$Port = 8890,
    [int]$WaitSeconds = 30,
    [switch]$ForceConda
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot "local_config.ps1")

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

$localConfig = Update-LocalPathConfig `
    -ConfigPath $ConfigPath `
    -ServerDirectory $ServerDirectory `
    -SearchRoot $SearchRoot
$resolvedServer = Get-RequiredLocalPath `
    -Config $localConfig `
    -Key "pdf2zh_server_directory" `
    -Directory

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

$proxyPrefix = ""
foreach ($name in @("ALL_PROXY", "all_proxy")) {
    $value = [Environment]::GetEnvironmentVariable($name)
    if ($value -like "socks://*") {
        $proxyPrefix += 'set "{0}=" && ' -f $name
    }
}
$cmd = (Get-Command cmd.exe -ErrorAction Stop).Source
$uvPath = $localConfig["uv_executable"]
if ($uvPath -and (Test-Path -LiteralPath $uvPath -PathType Leaf) -and -not $ForceConda) {
    $uvCommand = '{0}cd /d "{1}" && set "PYTHONIOENCODING=utf-8" && "{2}" run --python 3.12 --with-requirements requirements.txt server.py --port {3}' -f $proxyPrefix, $resolvedServer, $uvPath, $Port
    $uvProcess = Start-Process -FilePath $cmd -ArgumentList "/k", $uvCommand -WindowStyle Normal -PassThru
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

$condaPath = $localConfig["conda_executable"]
if (-not $condaPath -or -not (Test-Path -LiteralPath $condaPath -PathType Leaf)) {
    throw "Conda was not discovered. Refresh the YAML config or install uv."
}

$legacyScripts = Join-Path $resolvedServer "zotero-pdf2zh-venv\Scripts"
$nextScripts = Join-Path $resolvedServer "zotero-pdf2zh-next-venv\Scripts"
$condaCommand = '{0}cd /d "{1}" && set "PATH={2};{3};%PATH%" && set "PYTHONIOENCODING=utf-8" && "{4}" run -n PDF2zh python server.py --enable_venv false --check_update false --port {5}' -f $proxyPrefix, $resolvedServer, $legacyScripts, $nextScripts, $condaPath, $Port
$condaProcess = Start-Process -FilePath $cmd -ArgumentList "/k", $condaCommand -WindowStyle Normal -PassThru

if (-not (Wait-Pdf2zhPort -LocalPort $Port -Seconds $WaitSeconds)) {
    throw "Conda fallback was launched visibly but port $Port did not start. Inspect the terminal."
}

[pscustomobject]@{
    status = "started"
    port = $Port
    pid = $condaProcess.Id
    method = "conda"
} | ConvertTo-Json -Compress
