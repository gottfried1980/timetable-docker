param([Parameter(Mandatory=$true)][string]$PythonPath)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$syncLog = Join-Path $PSScriptRoot 'sync-task.log'
try {
    "Start: $(Get-Date -Format o)" | Set-Content -LiteralPath $syncLog -Encoding UTF8
    & $PythonPath (Join-Path $PSScriptRoot 'timetree_sync.py') sync --live 2>&1 |
        Out-File -LiteralPath $syncLog -Append -Encoding UTF8
    exit $LASTEXITCODE
} catch {
    'Synchronisierung konnte nicht gestartet werden. Python-Pfad und Server prüfen.' |
        Out-File -LiteralPath $syncLog -Append -Encoding UTF8
    exit 1
}
