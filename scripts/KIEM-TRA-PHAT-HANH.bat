@echo off
REM ===========================================================================
REM  File .bat PHAI thuan ASCII - xem ghi chu dau SETUP.bat.
REM ===========================================================================
REM
REM  Kiem phat hanh v3.0 (Viec 5.3, workspace\LO-TRINH-PHAT-HANH-V3.md):
REM  xuat mot ban sao SACH cua cay lam viec hien tai ra ngoai thu muc nay,
REM  quet bi mat / du lieu kenh that / duong tuyet doi C:\Users / tep lon,
REM  roi (neu may du RAM va khong dang san xuat o khau nang) chay pytest
REM  TREN BAN SAO do - khong dung tren kho dang sua.
REM
REM  Bao cao ghi o workspace\kiem-phat-hanh\<ngay>.md. File nay KHONG sua gi
REM  trong thu muc tool - chi doc dia va ghi ra ngoai + ghi bao cao.
chcp 65001 >nul
REM Tep nay nam trong scripts\ - thu muc goc MyTool la thu muc cha.
cd /d "%~dp0.."
set "GOC=%CD%\"
set PYTHONUTF8=1
title My Tool - Kiem phat hanh

REM --- Tim Python THAT (khong phai ban gia Microsoft Store) - xem CHAY-QT.bat
set "PYEXE="
if exist "%GOC%.venv\Scripts\python.exe" set PYEXE="%GOC%.venv\Scripts\python.exe"
if not defined PYEXE if exist "%GOC%venv\Scripts\python.exe" set PYEXE="%GOC%venv\Scripts\python.exe"
if not defined PYEXE for /d %%d in ("%LocalAppData%\Python\pythoncore-*") do if not defined PYEXE if exist "%%d\python.exe" set PYEXE="%%d\python.exe"
if not defined PYEXE for /d %%d in ("%LocalAppData%\Programs\Python\Python3*") do if not defined PYEXE if exist "%%d\python.exe" set PYEXE="%%d\python.exe"
if defined PYEXE goto :co_python
python -c "import sys" >nul 2>&1
if errorlevel 1 goto :thu_py
python -c "import sys; print(sys.executable)" 2>nul | find /i "\WindowsApps\" >nul
if errorlevel 1 (
  set "PYEXE=python"
  goto :co_python
)

:thu_py
if defined PYEXE goto :co_python
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"

:co_python
if not defined PYEXE (
  echo.
  echo   !!! KHONG TIM THAY PYTHON THAT. Chay CAI-DAT-VPS.bat mot lan roi thu lai.
  echo.
  pause
  exit /b 1
)

echo ============================================================
echo    Kiem phat hanh v3.0
echo ============================================================
echo Dung Python: %PYEXE%
echo.

%PYEXE% -m core.kiem_phat_hanh %*

echo.
echo ============================================================
echo    Xong. Xem bao cao trong workspace\kiem-phat-hanh\
echo ============================================================
pause
