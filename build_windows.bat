@echo off
echo ========================================
echo Building Windows executable (EXE)
echo ========================================
echo.

echo Step 1: Converting icon...
python src/convert_icon.py
if errorlevel 1 (
    echo Warning: Icon conversion failed, building without custom icon.
    goto :build_no_icon
)

echo.
echo Step 2: Building EXE with PyInstaller...
pyinstaller --clean PDF出库单转换_Windows.spec
goto :end

:build_no_icon
pyinstaller --clean --onedir --windowed --name "PDF出库单转换" ^
    --add-data "templates/OMS出库.xlsx;templates" ^
    --add-data "templates/黎明屯铁锅炖模板.xlsx;templates" ^
    --add-data "templates/欢乐牧场模板.xlsx;templates" ^
    src/main.py

:end
echo.
echo ========================================
echo Build complete! Check the 'dist' folder.
echo ========================================
pause
