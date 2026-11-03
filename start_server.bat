@echo off
title Skelion Local Control Plane (Port 8003)
cd /d "%~dp0"
echo ===================================================
echo   Skelion Control Plane & AI Engine (Port 8003)
echo ===================================================
echo Running on http://127.0.0.1:8003
echo Admin dashboard: http://127.0.0.1:8003/admin
echo.
python run_control_plane.py
pause
