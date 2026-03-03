@echo off
echo === EchoType Build ===
echo.

REM Install dependencies
echo [1/3] Installing dependencies...
pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

REM Generate icon
echo [2/3] Generating icon...
python generate_icon.py
if errorlevel 1 echo Warning: icon generation failed, using default

REM Build exe using spec file (excludes heavy packages)
echo [3/3] Building executable...
pyinstaller EchoType.spec --clean
if errorlevel 1 goto :error

echo.
echo === Build complete! ===
echo Executable: dist\EchoType.exe
echo.
pause
goto :end

:error
echo.
echo === Build FAILED ===
pause

:end
