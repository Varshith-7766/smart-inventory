@echo off
REM ===========================================================================
REM Smart Inventory — One-Command Setup (Windows)
REM ===========================================================================
echo.
echo ===== Smart Inventory Setup =====
echo.

REM ---- 1. Check Python ----
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed. Install Python 3.11+ first.
    pause
    exit /b 1
)
echo [OK] Python found

REM ---- 2. Check MySQL ----
mysql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] MySQL client not found in PATH. Make sure MySQL is running.
) else (
    echo [OK] MySQL client found
)

REM ---- 3. Install Python dependencies ----
echo.
echo [1/5] Installing Python dependencies...
cd /d "%~dp0..\backend"
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM ---- 4. Set up the database ----
echo.
echo [2/5] Setting up the database...

REM Check if .env exists, if not create from example
if not exist ".env" (
    if exist "..\.env.example" (
        copy "..\.env.example" ".env" >nul
        echo [INFO] Created .env from .env.example — edit it with your MySQL password
    )
)

REM Try to find MySQL password from .env
set DB_PASS=password
if exist ".env" (
    for /f "tokens=2 delims==" %%a in ('type ".env" ^| find "DATABASE_URL"') do set DB_URL=%%a
)
echo [INFO] Running database/schema.sql — you will be prompted for MySQL root password
echo.
mysql -u root -p < "%~dp0..\database\schema.sql"
if %errorlevel% neq 0 (
    echo [WARN] Database setup may have failed. Check your MySQL credentials in .env
) else (
    echo [OK] Database schema created
)

REM ---- 5. Seed sample data ----
echo.
echo [3/5] Seeding sample data...
cd /d "%~dp0..\backend"
python "%~dp0seed_data.py"
if %errorlevel% neq 0 (
    echo [WARN] Seeding skipped or failed
) else (
    echo [OK] Sample data loaded
)

REM ---- 6. Verify .env ----
echo.
echo [4/5] Verifying configuration...
if not exist ".env" (
    echo [WARN] No .env file found. Copy ..\.env.example to .env and edit it.
) else (
    echo [OK] .env found
)

REM ---- 7. Start server ----
echo.
echo [5/5] Starting the server...
echo.
echo =============================================
echo  Server will start at http://localhost:5000
echo  Press Ctrl+C to stop
echo =============================================
echo.
python app.py

pause
