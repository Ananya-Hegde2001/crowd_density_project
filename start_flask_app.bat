@echo off
title Crowd Density Monitoring System
echo ====================================
echo   Crowd Density Monitoring System
echo ====================================
echo.
echo Starting Flask application...
echo.
cd /d "%~dp0backend"
echo Current directory: %CD%
echo.
echo Installing/updating requirements...
pip install -r ../requirements.txt
echo.
echo Starting the web server...
echo Open your browser and go to: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python run_flask.py
pause
