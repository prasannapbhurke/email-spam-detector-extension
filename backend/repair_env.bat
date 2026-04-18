@echo off
echo --- SYSTEM REPAIR START ---
echo 1. Checking Python version...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit
)

echo 2. Installing/Upgrading essential libraries...
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn pydantic slowapi bleach scikit-learn pandas numpy joblib

echo 3. Verifying installation...
python -c "import fastapi; import slowapi; import bleach; print('--- ALL LIBRARIES VERIFIED ---')"
if %errorlevel% neq 0 (
    echo [ERROR] Some libraries failed to install.
)

echo 4. Starting Server...
python main.py
pause
