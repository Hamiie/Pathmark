@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set PY_CMD=py
) else (
  set PY_CMD=python
)
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements.
  pause
  exit /b 1
)
%PY_CMD% -m streamlit run app\main.py
endlocal
