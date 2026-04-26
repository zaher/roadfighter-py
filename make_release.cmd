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

:: Ensure PyInstaller is available
echo Checking for PyInstaller...
%PYTHON% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    %PYTHON% -m pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller.
        goto :end
    )
)

echo.
echo Locating SDL2 DLLs...
for /f "delims=" %%i in ('%PYTHON% -c "import sdl2dll, pathlib; print(pathlib.Path(sdl2dll.__file__).parent / 'dll')"') do set "SDL2_DLL_DIR=%%i"
if not exist "%SDL2_DLL_DIR%\SDL2.dll" (
    echo WARNING: SDL2 DLLs not found in sdl2dll package.
    set "SDL2_DLL_DIR="
) else (
    echo Found SDL2 DLLs: %SDL2_DLL_DIR%
)

echo.
echo Building executable with PyInstaller...
if defined SDL2_DLL_DIR (
    %PYTHON% -m PyInstaller --clean --noconfirm --name RoadFighter --onedir --windowed --add-binary "%SDL2_DLL_DIR%\*.dll;." main.py
) else (
    %PYTHON% -m PyInstaller --clean --noconfirm --name RoadFighter --onedir --windowed main.py
)
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    goto :end
)

echo.
echo Moving build output to release folder...
mkdir "%RELEASE_DIR%"
xcopy /E /I /Y "dist\RoadFighter\*" "%RELEASE_DIR%\"
if errorlevel 1 (
    echo ERROR: Failed to copy dist files.
    goto :end
)

echo.
echo Copying game assets into release...
xcopy /E /I /Y "graphics" "%RELEASE_DIR%\graphics\" >nul
xcopy /E /I /Y "sound" "%RELEASE_DIR%\sound\" >nul
xcopy /E /I /Y "maps" "%RELEASE_DIR%\maps\" >nul
xcopy /E /I /Y "fonts" "%RELEASE_DIR%\fonts\" >nul
xcopy /E /I /Y "controller" "%RELEASE_DIR%\controller\" >nul
xcopy /E /I /Y "source" "%RELEASE_DIR%\source\" >nul
copy /Y "RoadFighter.cfg" "%RELEASE_DIR%\" >nul
copy /Y "README.md" "%RELEASE_DIR%\" >nul
copy /Y "LICENSE" "%RELEASE_DIR%\" >nul

echo.
echo Ensuring SDL2 DLLs are in release root...
if defined SDL2_DLL_DIR (
    copy /Y "%SDL2_DLL_DIR%\SDL2.dll" "%RELEASE_DIR%\" >nul
    copy /Y "%SDL2_DLL_DIR%\SDL2_image.dll" "%RELEASE_DIR%\" >nul
    copy /Y "%SDL2_DLL_DIR%\SDL2_mixer.dll" "%RELEASE_DIR%\" >nul
    copy /Y "%SDL2_DLL_DIR%\SDL2_ttf.dll" "%RELEASE_DIR%\" >nul
    copy /Y "%SDL2_DLL_DIR%\SDL2_gfx.dll" "%RELEASE_DIR%\" >nul
)

echo.
echo Cleaning up PyInstaller build files...
rmdir /S /Q "build" 2>nul
rmdir /S /Q "dist" 2>nul
del /Q "RoadFighter.spec" 2>nul

echo.
echo ==========================================
echo  Release build completed successfully!
echo ==========================================
echo.
echo Output folder: %RELEASE_DIR%
echo Executable:    %RELEASE_DIR%\RoadFighter.exe
echo.
echo Distribute the entire %RELEASE_DIR% folder.
echo The user runs RoadFighter.exe to play.
echo.

:end
pause
endlocal
