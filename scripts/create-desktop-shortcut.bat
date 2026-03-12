@echo off
REM Creates a desktop shortcut for ag3ntwerk Command Center
REM Run this once to create the shortcut

echo Creating desktop shortcut for ag3ntwerk Command Center...

set SCRIPT_PATH=F:\Projects\ag3ntwerk\start-ag3ntwerk.bat
set SHORTCUT_NAME=ag3ntwerk Command Center
set DESKTOP=%USERPROFILE%\Desktop

REM Create VBS script to make shortcut (Windows native method)
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = "%DESKTOP%\%SHORTCUT_NAME%.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%SCRIPT_PATH%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "F:\Projects\ag3ntwerk" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "Launch ag3ntwerk AI Command Center" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.IconLocation = "cmd.exe,0" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"

cscript //nologo "%TEMP%\CreateShortcut.vbs"
del "%TEMP%\CreateShortcut.vbs"

echo.
echo Desktop shortcut created: %DESKTOP%\%SHORTCUT_NAME%.lnk
echo.
echo You can now double-click the shortcut to start ag3ntwerk!
echo.
pause
