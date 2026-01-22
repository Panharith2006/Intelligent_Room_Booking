@echo off
REM Quick start script for Room Booking Analytics Dashboard

echo ========================================
echo Room Booking Analytics Dashboard
echo ========================================
echo.

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Running globally...
)

REM Check if streamlit is installed
python -c "import streamlit" 2>NUL
if errorlevel 1 (
    echo.
    echo ERROR: Streamlit is not installed!
    echo Please run: pip install streamlit pandas plotly
    echo.
    pause
    exit /b 1
)

echo Starting Analytics Dashboard...
echo.
echo Dashboard will open in your default browser
echo Press Ctrl+C to stop the server
echo.

streamlit run dashboard_analytics.py

pause
