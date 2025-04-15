@echo off
setlocal

:: Set the paths
set SCRIPT_NAME=BD2pineViewer.pyw
set ICON_NAME=icon.ico
set SHORTCUT_NAME=Brown Dust II Spine Viewer.lnk

:: Get the current directory
set "CURRENT_DIR=%~dp0"
set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"

:: Get the desktop path
set "DESKTOP_PATH=%USERPROFILE%\Desktop"

:: Check if the script exists
if not exist "%CURRENT_DIR%\%SCRIPT_NAME%" (
    echo Error: %SCRIPT_NAME% not found in current directory.
    pause
    exit /b 1
)

:: Create the shortcut
set "VBS_SCRIPT=%TEMP%\CreateShortcut.vbs"

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBS_SCRIPT%"
echo sLinkFile = "%DESKTOP_PATH%\%SHORTCUT_NAME%" >> "%VBS_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBS_SCRIPT%"
echo oLink.TargetPath = "%CURRENT_DIR%\%SCRIPT_NAME%" >> "%VBS_SCRIPT%"
echo oLink.WorkingDirectory = "%CURRENT_DIR%" >> "%VBS_SCRIPT%"

:: Only set icon if it exists
if exist "%CURRENT_DIR%\%ICON_NAME%" (
    echo oLink.IconLocation = "%CURRENT_DIR%\%ICON_NAME%, 0" >> "%VBS_SCRIPT%"
)

echo oLink.Save >> "%VBS_SCRIPT%"

cscript //nologo "%VBS_SCRIPT%"
del "%VBS_SCRIPT%"

echo Shortcut created successfully on your desktop.
exit /b