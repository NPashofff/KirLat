# Билд на KirLat.exe за Windows. Резултат: dist\KirLat.exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = $null
$cmd = Get-Command python -ErrorAction SilentlyContinue
if ($cmd -and (& $cmd.Source --version 2>$null)) { $py = $cmd.Source }
if (-not $py) { $py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" }
if (-not (Test-Path $py)) { throw "Python не е намерен. Инсталирайте Python 3.10+ от python.org" }

& $py -m pip install --quiet -r requirements.txt pyinstaller
& $py make_icon.py
& $py -m PyInstaller --noconfirm --clean KirLat.spec
Write-Host "`nГотово: $PSScriptRoot\dist\KirLat.exe"
