# KirLat – инсталация за Windows с една команда:
#   irm https://raw.githubusercontent.com/NPashofff/KirLat/main/install.ps1 | iex
# Сваля последния KirLat.exe от GitHub Releases в %LOCALAPPDATA%\KirLat, добавя пряк път
# в Start менюто, включва автостарт и стартира приложението.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo = "NPashofff/KirLat"
$dir = Join-Path $env:LOCALAPPDATA "KirLat"
$exe = Join-Path $dir "KirLat.exe"

Write-Host "KirLat: търся последната версия..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers @{ "User-Agent" = "KirLat-installer" }
$asset = $release.assets | Where-Object { $_.name -eq "KirLat.exe" } | Select-Object -First 1
if (-not $asset) { throw "В release $($release.tag_name) няма KirLat.exe" }

New-Item -ItemType Directory -Force -Path $dir | Out-Null
Get-Process -Name KirLat -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

Write-Host "KirLat: свалям $($release.tag_name)..."
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $exe -UseBasicParsing

# Пряк път в Start менюто
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $startMenu "KirLat.lnk"))
$lnk.TargetPath = $exe
$lnk.WorkingDirectory = $dir
$lnk.Description = "KirLat – поправя текст, написан на грешна клавиатурна подредба"
$lnk.Save()

# Автостарт при вход
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "KirLat" -Value "`"$exe`""

Start-Process -FilePath $exe
Write-Host ""
Write-Host "KirLat $($release.tag_name) е инсталиран в $dir и е стартиран (иконата е в трея)."
Write-Host "Селектирайте текст и натиснете Ctrl+W. Настройки: десен бутон върху иконата."
Write-Host "Деинсталиране: irm https://raw.githubusercontent.com/$repo/main/uninstall.ps1 | iex"
