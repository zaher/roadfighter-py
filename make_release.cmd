@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo  Road Fighter - Release Build Script
echo ==========================================
echo.

set "RELEASE_DIR=release\RoadFighter"
set "PYTHON=python"

:: Check if release folder already exists
if exist "%RELEASE_DIR%" (
    echo Release folder already exists: %RELEASE_DIR%
    set /p OVERWRITE="Overwrite existing release? (Y/N): "
    if /I "!OVERWRITE!"=="Y" (
        echo Removing old release folder...
        rmdir /S /Q "%RELEASE_DIR%"
    ) else (
        echo Aborted.
        goto :end
    )
)

echo.
echo Creating release directory structure...
mkdir "%RELEASE_DIR%\source"
mkdir "%RELEASE_DIR%\graphics"
mkdir "%RELEASE_DIR%\sound"
mkdir "%RELEASE_DIR%\maps"
mkdir "%RELEASE_DIR%\fonts"
mkdir "%RELEASE_DIR%\controller"

echo.
echo Copying game files...
copy /Y "main.py" "%RELEASE_DIR%\" >nul
copy /Y "requirements.txt" "%RELEASE_DIR%\" >nul
copy /Y "RoadFighter.cfg" "%RELEASE_DIR%\" >nul
copy /Y "README.md" "%RELEASE_DIR%\" >nul
copy /Y "LICENSE" "%RELEASE_DIR%\" >nul

xcopy /E /I /Y "source\*" "%RELEASE_DIR%\source\" >nul
xcopy /E /I /Y "graphics\*" "%RELEASE_DIR%\graphics\" >nul
xcopy /E /I /Y "sound\*" "%RELEASE_DIR%\sound\" >nul
xcopy /E /I /Y "maps\*" "%RELEASE_DIR%\maps\" >nul
xcopy /E /I /Y "fonts\*" "%RELEASE_DIR%\fonts\" >nul
xcopy /E /I /Y "controller\*" "%RELEASE_DIR%\controller\" >nul

echo.
echo Creating Python virtual environment...
%PYTHON% -m venv "%RELEASE_DIR%\.venv"
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    goto :end
)

echo.
echo Installing dependencies into virtual environment...
"%RELEASE_DIR%\.venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"%RELEASE_DIR%\.venv\Scripts\pip.exe" install -r "%RELEASE_DIR%\requirements.txt"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    goto :end
)

echo.
echo Creating launcher scripts...
(
    echo @echo off
    echo setlocal
    echo cd /d "%%~dp0"
    echo call ".venv\Scripts\activate.bat"
    echo start pythonw main.py
    echo endlocal
) > "%RELEASE_DIR%\RoadFighter.cmd"

(
    echo @echo off
    echo setlocal
    echo cd /d "%%~dp0"
    echo call ".venv\Scripts\activate.bat"
    echo python main.py %%*
    echo endlocal
) > "%RELEASE_DIR%\RoadFighter-Console.cmd"

echo.
echo ==========================================
echo  Release build completed successfully!
echo ==========================================
echo.
echo Output folder: %RELEASE_DIR%
echo.
echo Launchers created:
echo   - RoadFighter.cmd        (no console window)
echo   - RoadFighter-Console.cmd (with console, accepts arguments)
echo.

:end
pause
endlocal
