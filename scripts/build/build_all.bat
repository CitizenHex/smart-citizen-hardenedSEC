@echo off
echo ========================================
echo SC Localization Editor - Build Script
echo ========================================
echo.

echo Step 1: Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo   - Old builds removed
echo.

echo Step 2: Installing PyInstaller (if needed)...
.venv\Scripts\python.exe -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo WARNING: Could not install PyInstaller
    echo Please install manually: .venv\Scripts\pip install pyinstaller
    pause
)
echo   - PyInstaller ready
echo.

echo Step 3: Building executable...
.venv\Scripts\python.exe scripts\build\build_exe.py
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)
echo   - Executable created
echo.

echo Step 4: Testing executable...
if exist "dist\SCLocalizationEditor-v*.exe" (
    echo   - Executable exists: OK
) else (
    echo   - ERROR: Executable not found!
    pause
    exit /b 1
)
echo.

echo Step 5: Creating installer (requires Inno Setup)...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    if errorlevel 1 (
        echo WARNING: Installer creation failed
        echo You can create it manually with Inno Setup
    ) else (
        echo   - Installer created successfully!
    )
) else (
    echo WARNING: Inno Setup not found at default location
    echo Skipping installer creation
    echo You can install Inno Setup from: https://jrsoftware.org/isdl.php
    echo Or create the installer manually by opening installer.iss
)
echo.

echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Outputs:
for %%f in (dist\SCLocalizationEditor-v*.exe) do (
    echo   [OK] Executable: %%f
)
echo.
echo Next steps:
echo   1. Test the executable: dist\SCLocalizationEditor-v*.exe
echo   2. Create installer with Inno Setup (if not already done)
echo   3. Upload to GitHub releases!
echo.
pause
