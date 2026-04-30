@echo off
title BlueBot License API - Local Simulation
echo ============================================
echo  BlueBot License API - Ambiente Local
echo ============================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Docker nao esta rodando!
    echo Por favor, inicie o Docker Desktop e tente novamente.
    pause
    exit /b 1
)

echo [1/4] Parando containers antigos (se houver)...
docker compose down -v 2>nul

echo [2/4] Iniciando PostgreSQL e API...
docker compose up -d --build

echo Aguardando API ficar pronta...
:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 goto wait_loop

echo [3/4] Rodando seed de dados de teste...
docker compose exec api python -m app.seed

echo.
echo [4/4] Ambiente pronto!
echo.
echo ============================================
echo  🌐 API:        http://localhost:8000
echo  📖 Swagger:    http://localhost:8000/docs
echo  🗄️  Admin:     http://localhost/admin/
echo ============================================
echo.
echo  🔑 Licencas de teste:
echo     APRO-TEST-AAAA-BBBB  (basic, valida)
echo     APRO-TEST-PRO-CCCC   (pro, valida)
echo     APRO-TEST-EXP-DDDD   (basic, expirada)
echo     APRO-TEST-INA-EEEE   (basic, inativa)
echo.
echo  👤 Admin: admin / admin123
echo.
echo  Pressione qualquer tecla para abrir o Swagger...
pause >nul
start http://localhost:8000/docs
