<#
Start both backend and frontend in new PowerShell windows.
Usage: Right-click -> "Run with PowerShell" or run from PowerShell:
  & .\start_servers.ps1
#>

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

Start-Process -FilePath "powershell" -ArgumentList "-NoExit","-Command","Set-Location -Path \"$scriptDir\backend\"; python run_server.py" -WindowStyle Normal

Start-Process -FilePath "powershell" -ArgumentList "-NoExit","-Command","Set-Location -Path \"$scriptDir\7_frontend_dashboard\"; node server.js" -WindowStyle Normal

Write-Host "Launched backend and frontend in new PowerShell windows." -ForegroundColor Green
