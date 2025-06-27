@echo off
echo.
echo 🏦 Customer Loan Management App v1.0 - Simple Deploy
echo ===============================================
echo.

REM Stop any existing containers
echo 🛑 Stopping any running containers...
docker-compose down 2>nul

echo.
echo 🐳 Starting application...
echo 🌐 App will be available at: http://localhost:8501
echo.

REM Start the application
docker-compose up --build

echo.
echo 📝 Press any key to close...
pause >nul
