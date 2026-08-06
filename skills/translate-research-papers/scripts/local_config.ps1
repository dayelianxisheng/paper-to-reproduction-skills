Set-StrictMode -Version Latest

function Get-LocalConfigPath {
    param([string]$ConfigPath)

    if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
        return [System.IO.Path]::GetFullPath($ConfigPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:PDF2ZH_SKILL_CONFIG)) {
        return [System.IO.Path]::GetFullPath($env:PDF2ZH_SKILL_CONFIG)
    }
    $base = $env:LOCALAPPDATA
    if ([string]::IsNullOrWhiteSpace($base)) {
        $base = $env:APPDATA
    }
    if ([string]::IsNullOrWhiteSpace($base)) {
        $base = $env:USERPROFILE
    }
    if ([string]::IsNullOrWhiteSpace($base)) {
        throw "No user configuration directory is available; set PDF2ZH_SKILL_CONFIG."
    }
    return Join-Path (Join-Path $base "translate-research-papers") "local-paths.yaml"
}

function Read-LocalPathConfig {
    param([Parameter(Mandatory = $true)][string]$ConfigPath)

    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        return @{}
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $ConfigPath -Encoding UTF8) {
        if ($line -match '^\s*([A-Za-z0-9_]+):\s*(.+?)\s*$') {
            $key = $Matches[1]
            $raw = $Matches[2]
            try {
                $values[$key] = $raw | ConvertFrom-Json
            }
            catch {
                $values[$key] = $raw.Trim('"', "'")
            }
        }
    }
    return $values
}

function Get-PythonLauncher {
    foreach ($name in @("python3", "python", "py")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }
    throw "Python is required to discover and refresh local PDF2zh paths."
}

function Update-LocalPathConfig {
    param(
        [string]$ConfigPath,
        [string]$Source,
        [string]$ServerDirectory,
        [string]$TranslatedDirectory,
        [string]$ZoteroDataDirectory,
        [string]$TokenPath,
        [string]$SearchRoot
    )

    $resolvedConfig = Get-LocalConfigPath -ConfigPath $ConfigPath
    $resolver = Join-Path $PSScriptRoot "local_config.py"
    if (-not (Test-Path -LiteralPath $resolver -PathType Leaf)) {
        throw "Local path resolver is missing: $resolver"
    }
    $python = Get-PythonLauncher
    $arguments = @($resolver, "refresh", "--config", $resolvedConfig)
    if (-not [string]::IsNullOrWhiteSpace($Source)) {
        $arguments += @("--source", $Source)
    }
    if (-not [string]::IsNullOrWhiteSpace($ServerDirectory)) {
        $arguments += @("--server-directory", $ServerDirectory)
    }
    if (-not [string]::IsNullOrWhiteSpace($TranslatedDirectory)) {
        $arguments += @("--translated-directory", $TranslatedDirectory)
    }
    if (-not [string]::IsNullOrWhiteSpace($ZoteroDataDirectory)) {
        $arguments += @("--zotero-data-directory", $ZoteroDataDirectory)
    }
    if (-not [string]::IsNullOrWhiteSpace($TokenPath)) {
        $arguments += @("--token-path", $TokenPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($SearchRoot)) {
        $arguments += @("--search-root", $SearchRoot)
    }
    if ([System.IO.Path]::GetFileNameWithoutExtension($python) -eq "py") {
        $arguments = @("-3") + $arguments
    }
    & $python @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Local path discovery failed with exit code $LASTEXITCODE."
    }
    return Read-LocalPathConfig -ConfigPath $resolvedConfig
}

function Get-RequiredLocalPath {
    param(
        [Parameter(Mandatory = $true)][hashtable]$Config,
        [Parameter(Mandatory = $true)][string]$Key,
        [switch]$Directory
    )

    $value = $Config[$Key]
    if ([string]::IsNullOrWhiteSpace([string]$value)) {
        throw "$Key is missing from the local YAML config. Refresh discovery with an explicit hint."
    }
    $pathType = if ($Directory) { "Container" } else { "Leaf" }
    if (-not (Test-Path -LiteralPath $value -PathType $pathType)) {
        throw "$Key is stale or has the wrong type: $value"
    }
    return (Resolve-Path -LiteralPath $value).Path
}
