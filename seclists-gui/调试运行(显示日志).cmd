@echo off
rem Debug launcher: keeps a console window so Python errors are visible.
setlocal
title SecLists GUI - debug

set "HERE=%~dp0"
set "PY="

for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\python3.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python3.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "C:\Python313\python.exe"
  "C:\Python312\python.exe"
  "C:\Python311\python.exe"
) do if not defined PY if exist "%%~fP" set "PY=%%~fP"

if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where python3 2^>nul') do if not defined PY set "PY=%%P"

if not defined PY goto :nopython

"%PY%" "%HERE%SecListsAssistant.pyw" %*
set "RC=%ERRORLEVEL%"
echo.
echo [exit code %RC%]
if not "%RC%"=="0" echo See data\error.log for details.
pause
exit /b %RC%

:nopython
echo [x] Python 3 was not found. Install Python 3.10+ first.
pause
exit /b 1
