# KirLat – инсталация за Windows с една команда:
#   irm https://raw.githubusercontent.com/NPashofff/KirLat/main/install.ps1 | iex
# Сваля последния KirLat-windows.zip от GitHub Releases в %LOCALAPPDATA%\KirLat, добавя пряк път
# в Start менюто, пита за автостарт и стартира приложението.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repo = "NPashofff/KirLat"
$dir = Join-Path $env:LOCALAPPDATA "KirLat"
$exe = Join-Path $dir "KirLat.exe"
$tmp = Join-Path $env:TEMP "KirLat-install"

Write-Host "KirLat: търся последната версия..."
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases/latest" -Headers @{ "User-Agent" = "KirLat-installer" }
$asset = $release.assets | Where-Object { $_.name -eq "KirLat-windows.zip" } | Select-Object -First 1
if (-not $asset) { throw "В release $($release.tag_name) няма KirLat-windows.zip" }

Get-Process -Name KirLat -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

Write-Host "KirLat: свалям $($release.tag_name)..."
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$zip = Join-Path $tmp "KirLat-windows.zip"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
Unblock-File $zip
Expand-Archive -Path $zip -DestinationPath (Join-Path $tmp "x") -Force

Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Copy-Item -Path (Join-Path $tmp "x\*") -Destination $dir -Recurse -Force
Get-ChildItem $dir -Recurse -File | Unblock-File
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
if (-not (Test-Path $exe)) { throw "KirLat.exe липсва след разархивиране" }

# Пряк път в Start менюто
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $startMenu "KirLat.lnk"))
$lnk.TargetPath = $exe
$lnk.WorkingDirectory = $dir
$lnk.Description = "KirLat – поправя текст, написан на грешна клавиатурна подредба"
$lnk.Save()

# Автостарт при вход – по избор (може да се смени и от настройките на приложението)
$auto = "y"
try { $auto = Read-Host "Да стартира ли KirLat автоматично при вход в Windows? [Y/n]" } catch {}
if ([string]::IsNullOrWhiteSpace($auto) -or $auto -match "^[yYдД]") {
    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "KirLat" -Value "`"$exe`""
    Write-Host "KirLat: автостартът е включен."
} else {
    Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "KirLat" -ErrorAction SilentlyContinue
}

Start-Process -FilePath $exe -WorkingDirectory $dir
Write-Host ""
Write-Host "KirLat $($release.tag_name) е инсталиран в $dir и е стартиран (иконата е в трея)."
Write-Host "Селектирайте текст и натиснете Ctrl+W. Настройки: десен бутон върху иконата."
Write-Host "Ако Windows Defender го спре: приложението е с отворен код, вижте README → 'Windows Defender'."
Write-Host "Деинсталиране: irm https://raw.githubusercontent.com/$repo/main/uninstall.ps1 | iex"
