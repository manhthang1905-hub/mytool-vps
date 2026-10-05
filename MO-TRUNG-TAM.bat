@echo off
rem Mở Trung tâm trực quan MYTOOL (chỉ đọc): bật máy chủ nhỏ 127.0.0.1:8770 nếu chưa chạy, rồi mở trình duyệt.
cd /d "%~dp0"
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri http://127.0.0.1:8770/du-lieu.json -UseBasicParsing -TimeoutSec 5 | Out-Null } catch { Start-Process -FilePath python -ArgumentList '-X','utf8','-m','core.truc_quan' -WindowStyle Hidden; Start-Sleep -Seconds 3 }"
start "" http://127.0.0.1:8770/
