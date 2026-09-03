# KirLat – деинсталация за Windows:
#   irm https://raw.githubusercontent.com/NPashofff/KirLat/main/uninstall.ps1 | iex
$ErrorActionPreference = "SilentlyContinue"

$dir = Join-Path $env:LOCALAPPDATA "KirLat"

# Remove-Item -Recurse в Windows PowerShell 5.1 се проваля с терминираща грешка върху 8.3 кратки
# пътища (напр. LOCAL~1); трием през .NET, с cmd като резервен вариант.
function Remove-Tree([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return }
    try { [System.IO.Directory]::Delete($path, $true); return } catch {}
    try { cmd /c rmdir /s /q "$path" 2>$null } catch {}
}
Get-Process -Name KirLat | Stop-Process -Force
Start-Sleep -Milliseconds 500

Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "KirLat"
Remove-Item -Force (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\KirLat.lnk")
Remove-Tree $dir
Remove-Tree (Join-Path $env:APPDATA "KirLat")   # настройки и дневник

Write-Host "KirLat е премахнат."
