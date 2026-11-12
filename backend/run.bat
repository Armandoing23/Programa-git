@echo off
chcp 65001 >nul
title Biomedical Research AI - Backend Server
echo ========================================
echo Biomedical Research AI
echo Backend Server
echo ========================================
echo.
echo [1/3] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instala Python 3.10+ desde python.org
    pause
    exit /b 1
)
echo Python encontrado.
echo.
echo [2/3] Verificando Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo ADVERTENCIA: Ollama no parece estar corriendo en http://localhost:11434
    echo Inicia Ollama y asegurate de tener el modelo "llama3" descargado.
    echo El sistema funcionara en modo fallback (solo base de conocimiento).
    echo.
) else (
    echo Ollama detectado.
)
echo.
echo [3/3] Instalando dependencias...
pip install -r requirements.txt
echo.
echo Iniciando servidor en http://localhost:8000
echo Abre frontend/index.html en tu navegador.
echo.
python main.py
pause
