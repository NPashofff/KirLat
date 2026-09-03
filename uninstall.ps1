# KirLat – деинсталация за Windows:
#   irm https://raw.githubusercontent.com/NPashofff/KirLat/main/uninstall.ps1 | iex
$ErrorActionPreference = "SilentlyContinue"

$dir = Join-Path $env:LOCALAPPDATA "KirLat"
Get-Process -Name KirLat | Stop-Process -Force
Start-Sleep -Milliseconds 500

Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "KirLat"
Remove-Item -Force (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\KirLat.lnk")
Remove-Item -Recurse -Force $dir
Remove-Item -Recurse -Force (Join-Path $env:APPDATA "KirLat")   # настройки и дневник

Write-Host "KirLat е премахнат."
