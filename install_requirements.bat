@echo off
echo Checking for Python installation...

:: Check if Python is available in PATH
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not found in your system's PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check the option "Add Python to PATH" during installation.
    echo Exiting script.
    pause
    exit /b 1
) else (
    echo Python found. Proceeding with package installation...
)

:: Install packages from requirements.txt
echo Installing required packages from requirements.txt...
python -m pip install -r requirements.txt

:: Check if pip install was successful
if %errorlevel% neq 0 (
    echo There was an error installing the packages. Please check the messages above.
) else (
    echo Packages installed successfully.
)

echo Script finished.
pause