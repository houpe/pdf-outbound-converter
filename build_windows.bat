@echo off
echo ========================================
echo Building Windows executable (EXE)
echo ========================================
echo.

echo Step 1: Converting icon...
python convert_icon.py
if errorlevel 1 (
    echo Warning: Icon conversion failed, building without custom icon.
    goto :build_no_icon
)

echo.
echo Step 2: Building EXE with PyInstaller...
pyinstaller --clean PDF出库单转换_Windows.spec
goto :end

:build_no_icon
pyinstaller --clean --onefile --windowed --name "PDF出库单转换" --add-data "OMS出库.xlsx;." pdf_to_outbound_gui.py

:end
echo.
echo ========================================
echo Build complete! Check the 'dist' folder.
echo ========================================
pause
