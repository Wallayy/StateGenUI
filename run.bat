@echo off
title XInjector StateGenerator
echo Starting StateGenerator...
python launcher.py
if errorlevel 1 (
    echo.
    echo Failed to start. Make sure Python is installed and dependencies are set up:
    echo   pip install -e .
    echo.
    pause
)
