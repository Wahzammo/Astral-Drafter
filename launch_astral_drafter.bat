@echo off
:: ============================================================================
:: Astral Drafter - One-Click Launcher
:: ============================================================================
:: This script starts the required servers and opens the user interface.
:: IMPORTANT: You MUST edit the file paths below to match your system.
:: ============================================================================

:: --- CONFIGURATION - EDIT THESE PATHS ---

:: 1. Set the path to the folder where your llama-server.exe is located.
set LLAMA_CPP_DIR=C:\Users\aaron\llama.cpp\build\bin\release

:: 2. Set the full path to your Mistral Nemo model file.
set MODEL_PATH=F:\OllamaModels\mistral-nemo-instruct-2407-Q4_K_M.gguf

:: 3. Set the path to YOUR Astral-Drafter project folder.
set DRAFTER_DIR=C:\Users\aaron\Astral-Drafter

:: ============================================================================
:: --- LAUNCH SEQUENCE - DO NOT EDIT BELOW THIS LINE ---
:: ============================================================================

echo.
echo [1/3] Starting llama.cpp server...
cd /d %LLAMA_CPP_DIR%
start "Llama.cpp Server" llama-server.exe -m "%MODEL_PATH%" -c 65536 --n-gpu-layers 35 --threads 8

:: Give the first server a moment to start up.
timeout /t 5 >nul

echo.
echo [2/3] Starting Python Bridge server...
cd /d %DRAFTER_DIR%
start "Astral Drafter Bridge" python llama_cpp_server_bridge.py

:: Give the second server a moment to start up.
timeout /t 5 >nul

echo.
echo [3/3] Launching Astral Drafter GUI in your default browser...
start "" "%DRAFTER_DIR%\gui\astral_nexus_drafter.html"

echo.
echo All components launched! You can close this window.
exit
