@echo off
title March Madness Web Application
color 0A

:: Change to the project directory
cd /d %~dp0

:: Check if virtual environment exists and activate it
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found at venv\Scripts\activate.bat
    echo The application may not run correctly if dependencies aren't installed.
    pause
)

:: Start the Django development server on port 8080, accessible from network
echo Starting Django server on 0.0.0.0:8080...
python manage.py runserver 0.0.0.0:8080

:: Keep console open if there's an error
pause
