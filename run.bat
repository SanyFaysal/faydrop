@echo off
title Faydrop - Video & Audio Downloader by Faysal
echo ==========================================================
echo Starting Faydrop Video and Audio Downloader...
echo ==========================================================

REM Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found! Please install Python 3.10+ from python.org.
        pause
        exit /b 1
    ) else (
        set PYCMD=python
    )
) else (
    set PYCMD=py
)

%PYCMD% main.py
if %errorlevel% neq 0 (
    echo.
    echo Application stopped with an error code: %errorlevel%
    pause
)

