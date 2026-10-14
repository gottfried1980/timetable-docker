$ErrorActionPreference = 'Stop'
$taskName = 'TodoListe-TimeTree-Sync'
$pythonPath = (& python -c 'import sys; print(sys.executable)').Trim()
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Python wurde nicht gefunden.' }
$taskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$wrapper = Join-Path $PSScriptRoot 'run-sync-task.ps1'
$arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -PythonPath "{1}"' -f $wrapper, $pythonPath
$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument $arguments -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 15)
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUser
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($trigger, $logonTrigger) -Principal $principal -Settings $settings -Description 'TimeTree alle 15 Minuten über den lokalen JSON-Server synchronisieren.' -Force | Out-Null
Write-Output "Aufgabe eingerichtet: $taskName (alle 15 Minuten und bei Anmeldung)."
Write-Output 'Benutzer muss angemeldet sein; JSON-Server muss laufen. Protokoll: sync-task.log'
