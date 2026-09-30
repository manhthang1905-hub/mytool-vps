@echo off
REM ===========================================================================
REM  QUAN TRONG CHO NGUOI SUA FILE NAY (cung luat voi SETUP.bat):
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
echo   Viec 5.1, workspace\LO-TRINH-PHAT-HANH-V3.md. Khac CAI-DAT-VM.bat cu
echo   (cai tu goi vm\goi-vps\ dong san tren may nha): file nay cai NGAY TREN
echo   ban clone git dang dung - vm\ da nam san trong thu muc nay.
echo.

REM --- [0] Dang chay trong file ZIP? (cung bay voi SETUP.bat) ---------------
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

REM --- [1] SETUP.bat - TAI DUNG nguyen van, khong viet lai --------------------
REM
REM  "< NUL": SETUP.bat ket bang lenh "pause" cho nguoi bam phim. May VPS
REM  khong co ai ngoi truoc man hinh - doc stdin tu thiet bi NUL de "pause"
REM  troi qua ngay thay vi treo cua so mai mai.
if not exist "%~dp0SETUP.bat" (
  echo   !!! Khong thay SETUP.bat canh file nay - dang o dung thu muc goc MyTool khong?
  pause
  exit /b 1
)
echo [1/2] Dang chay SETUP.bat (cai thu vien goc, kiem giao dien)...
echo       - co the mat vai phut lan dau, dung tat cua so nay.
call "%~dp0SETUP.bat" < NUL
echo       - SETUP.bat da chay xong (xem loi mau do o tren neu co).
echo.

REM --- Tim python de goi buoc rieng cua VPS -----------------------------------
REM Cung thu tu uu tien voi SETUP.bat: .venv cua thu muc tool truoc (SETUP.bat
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
  echo   !!! Khong tim thay Python sau khi chay SETUP.bat - xem loi o buoc [1/2].
  pause
  exit /b 1
)

REM --- [2] vm\cai_dat_tu_kho.py - rieng cua VPS -------------------------------
REM %* chuyen tiep nguyen doi so dong lenh (vd "--thu") sang kich ban Python.
echo [2/2] Dang chay buoc rieng cua VPS (vm\cai_dat_tu_kho.py)...
echo       - thu vien vm\, vps.json, vm\config.json, DONE\, CLAUDE.local.md, 3 lich.
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
echo    Doc them: README-VPS.md
echo ============================================================
pause
