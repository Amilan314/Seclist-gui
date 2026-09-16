@echo off
rem ============================================================
rem  SecLists GUI launcher  (ASCII only: cmd.exe mis-parses
rem  non-ASCII batch files after a codepage switch)
rem ============================================================
setlocal
title SecLists GUI

set "HERE=%~dp0"
set "PY="

for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\pythonw3.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\pythonw3.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
  "%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"
  "C:\Python313\pythonw.exe"
  "C:\Python312\pythonw.exe"
  "C:\Python311\pythonw.exe"
  "C:\Python310\pythonw.exe"
) do if not defined PY if exist "%%~fP" set "PY=%%~fP"

if not defined PY for /f "delims=" %%P in ('where pythonw 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where pythonw3 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where python3 2^>nul') do if not defined PY set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('where python 2^>nul') do if not defined PY set "PY=%%P"

if not defined PY goto :nopython

start "" "%PY%" "%HERE%SecListsAssistant.pyw" %*
exit /b 0

:nopython
echo.
echo [x] Python 3 was not found on this computer.
echo     Install Python 3.10 or newer from https://www.python.org/downloads/windows/
echo     and tick "Add python.exe to PATH".
echo.
pause
exit /b 1
