@echo off
REM Customer Loan Management App - Docker Deployment Script (Windows)

echo.
echo 🏦 Customer Loan Management App v1.0
echo ====================================
echo 📍 Current directory: %CD%
echo ⏰ Started at: %DATE% %TIME%
echo.

REM Check if Docker is installed
echo 🔍 Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Docker is not installed or not running
    echo.
    echo 📥 Please install Docker Desktop first:
    echo    https://docs.docker.com/desktop/windows/
    echo.
    echo 💡 After installation, make sure Docker Desktop is running
    echo    (you should see Docker icon in system tray)
    echo.
    pause
    exit /b 1
)

echo ✅ Docker is installed and available
echo.

REM Check if Docker daemon is running
echo 🔍 Checking if Docker daemon is running...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Docker daemon is not running
    echo.
    echo 💡 Please start Docker Desktop and wait for it to fully start
    echo    (you should see Docker whale icon in system tray)
    echo.
    pause
    exit /b 1
)

echo ✅ Docker daemon is running
echo.

REM Check if Excel file exists
echo 🔍 Checking for Excel file...
if not exist "Customer_Loan_2025_06_07.xlsx" (
    echo.
    echo ❌ ERROR: Excel file not found
    echo.
    echo 📁 Expected file: Customer_Loan_2025_06_07.xlsx
    echo 📍 Current directory: %CD%
    echo.
    echo 💡 Please copy your Excel file to this directory and try again
    echo.
    pause
    exit /b 1
)

echo ✅ Excel file found: Customer_Loan_2025_06_07.xlsx
echo.

REM Check required files
echo 🔍 Checking required files...
if not exist "app.py" (
    echo ❌ ERROR: app.py not found
    pause
    exit /b 1
)
if not exist "Dockerfile" (
    echo ❌ ERROR: Dockerfile not found
    pause
    exit /b 1
)
if not exist "BRAND_KEYWORDS" (
    echo ❌ ERROR: BRAND_KEYWORDS folder not found
    pause
    exit /b 1
)

echo ✅ All required files found
echo.

echo 🐳 Starting application with Docker Compose...
echo 🚀 Building and running containers...
echo ⏳ This may take a few minutes on first run...
echo.
echo 🌐 The app will be available at: http://localhost:8501
echo 💡 Your browser should open automatically in 30 seconds
echo.

REM Start browser opening in background
start /b powershell -command "Start-Sleep 30; Start-Process 'http://localhost:8501'"

REM Start the application
docker-compose up --build

echo.
echo 🏁 Application stopped
echo.
echo 🌐 If you want to restart, just run this script again
echo � The app was available at: http://localhost:8501
echo.

echo 📝 Press any key to close this window...
pause >nul
