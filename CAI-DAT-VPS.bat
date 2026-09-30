@echo off
REM ===========================================================================
REM  QUAN TRONG CHO NGUOI SUA FILE NAY (cung luat voi scripts\SETUP.bat):
REM  File .bat PHAI la thuan ASCII, khong dau, khong ky tu ke khung.
REM  cmd.exe doc file batch theo tung byte va nho vi tri dang doc; mot ky tu
REM  nhieu byte (chu co dau, dau gach ke) se lam no doc lech va bam nat lenh.
REM  Chu tieng Viet co dau chi duoc nam trong file .py, khong nam o day.
REM  TUYET DOI khong dung "setlocal enabledelayedexpansion" (an dau !).
REM ===========================================================================
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
title MyTool - CAI DAT VPS (tu ban clone)
echo ============================================================
echo    MyTool VPS - cai dat tu ban clone
echo ============================================================
echo.
echo   Cai ngay tren ban clone git nay. Huong dan day du: README.md
echo.

REM --- [0] Dang chay trong file ZIP? (cung bay voi scripts\SETUP.bat) ---------------
set "HERE=%~dp0"
echo "%HERE%" | find /i "\AppData\Local\Temp\" >nul
if not errorlevel 1 goto :in_zip
echo "%HERE%" | find /i "\Temp1_" >nul
if not errorlevel 1 goto :in_zip
echo "%HERE%" | find /i "\INetCache\" >nul
if errorlevel 1 goto :place_ok

:in_zip
echo   !!! DANG CHAY TU BEN TRONG FILE NEN (.zip) - giai nen het ra roi chay lai.
pause
exit /b 1

:place_ok

REM --- [1] scripts\SETUP.bat - TAI DUNG nguyen van, khong viet lai ------------
REM
REM  "< NUL": scripts\SETUP.bat ket bang lenh "pause" cho nguoi bam phim. May VPS
REM  khong co ai ngoi truoc man hinh - doc stdin tu thiet bi NUL de "pause"
REM  troi qua ngay thay vi treo cua so mai mai.
REM  --thu: chi in cac buoc se lam - khong chay SETUP.bat that.
if /i "%~1"=="--thu" (
  echo [1/2] --thu: bo qua scripts\SETUP.bat ^(khong cai gi that^).
  goto :tim_python
)
if not exist "%~dp0scripts\SETUP.bat" (
  echo   !!! Khong thay scripts\SETUP.bat - dang o dung thu muc goc MyTool khong?
  pause
  exit /b 1
)
echo [1/2] Dang chay scripts\SETUP.bat (cai thu vien goc, kiem giao dien)...
echo       - co the mat vai phut lan dau, dung tat cua so nay.
call "%~dp0scripts\SETUP.bat" < NUL
cd /d "%~dp0"
echo       - scripts\SETUP.bat da chay xong (xem loi mau do o tren neu co).
echo.

:tim_python
REM --- Tim python de goi buoc rieng cua VPS -----------------------------------
REM Cung thu tu uu tien voi scripts\SETUP.bat: .venv cua thu muc tool truoc (SETUP
REM vua tao/dung no o buoc tren), roi moi lui ve "python"/"py -3" he thong.
set "PYEXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not defined PYEXE (
  python --version >nul 2>&1
  if not errorlevel 1 set "PYEXE=python"
)
if not defined PYEXE (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PYEXE=py -3"
)
if not defined PYEXE (
  echo   !!! Khong tim thay Python sau khi chay scripts\SETUP.bat - xem loi o buoc [1/2].
  pause
  exit /b 1
)

REM --- [2] vm\cai_dat_tu_kho.py - rieng cua VPS -------------------------------
REM %* chuyen tiep nguyen doi so dong lenh (vd "--thu") sang kich ban Python.
echo [2/2] Dang chay buoc rieng cua VPS (vm\cai_dat_tu_kho.py)...
echo       - thu vien vm\, vps.json, vm\config.json, DONE\, CLAUDE.local.md, 5 lich.
%PYEXE% -m vm.cai_dat_tu_kho %*
set "MA_LOI=%errorlevel%"
echo.

if not "%MA_LOI%"=="0" (
  echo ============================================================
  echo    !!! CAI DAT CHUA XONG - xem loi mau do o tren.
  echo ============================================================
  pause
  exit /b 1
)

echo ============================================================
echo    XONG! Kiem lai bang lenh:
echo      %PYEXE% -m core.kiem_may --day-du
echo    Doc them: README.md
echo ============================================================
pause
