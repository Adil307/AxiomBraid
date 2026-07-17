@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo AxiomBraid 2.0.0 - Doxygen Documentation Generator
echo ============================================================

echo.
where doxygen >nul 2>&1
if errorlevel 1 (
    echo ERROR: Doxygen was not found on PATH.
    echo Install it with:
    echo   winget install --id DimitriVanHeesch.Doxygen -e
    echo Then reopen the terminal.
    exit /b 1
)

where dot >nul 2>&1
if errorlevel 1 (
    echo WARNING: Graphviz dot was not found on PATH.
    echo Install it with:
    echo   winget install --id Graphviz.Graphviz -e
    echo Documentation can still build, but diagrams may be missing.
)

if not exist "src\axiombraid" (
    echo ERROR: src\axiombraid was not found.
    echo Run this file from the AxiomBraid project root.
    exit /b 1
)

if not exist "docs\doxygen" mkdir "docs\doxygen"

echo.
echo Generating documentation...
doxygen Doxyfile
if errorlevel 1 (
    echo ERROR: Doxygen generation failed.
    exit /b 1
)

if not exist "docs\doxygen\html\index.html" (
    echo ERROR: Expected index file was not generated.
    exit /b 1
)

echo.
echo SUCCESS: Documentation generated.
echo Main page:
echo   %CD%\docs\doxygen\html\index.html
start "" "%CD%\docs\doxygen\html\index.html"
endlocal
