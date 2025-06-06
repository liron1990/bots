@echo off
setlocal

:: Check if Python 3 is available via the 'py -3' launcher
py -3 --version >NUL 2>&1
if errorlevel 1 (
    echo Python 3 is not installed or 'py -3' is not available.
    pause
    exit /b 1
)

:: Install the package using Python 3
echo Python 3 is available. Installing whatsapp-chatbot-python...
py -3 -m pip install whatsapp-chatbot-python

pause
