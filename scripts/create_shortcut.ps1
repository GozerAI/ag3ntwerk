# Create Desktop Shortcut for C-Suite Command Center

$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "C-Suite Command Center.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "F:\Projects\c-suite\C-Suite.bat"
$Shortcut.WorkingDirectory = "F:\Projects\c-suite"
$Shortcut.Description = "Launch C-Suite AI Command Center"
$Shortcut.Save()

Write-Host "Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
