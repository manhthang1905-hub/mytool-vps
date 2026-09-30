# -*- coding: utf-8 -*-
"""Cài VPS TỪ BẢN CLONE — Việc 5.1, `workspace/LO-TRINH-PHAT-HANH-V3.md`.

═══ KHÁC `vm/cai_dat_vps.py` THẾ NÀO ═══

`vm/cai_dat_vps.py` cài từ một GÓI đóng sẵn trên máy nhà (`vm/goi-vps/
tool.zip`), và dựng MyTool thành thư mục SIBLING của `vm/`. Tệp NÀY cài từ
một bản CLONE THẲNG của kho — nghĩa là khi kịch bản này chạy, `vm/` đã nằm
SẴN BÊN TRONG MyTool (`core/`, `ui_qt/`, `tu_chay.py`... đã có đủ, đúng cấu
trúc `vm/VPS-CLAUDE.md` mô tả), chỉ còn thiếu vài bước RIÊNG của VPS:

    1. chạy SETUP.bat (cài requirements.txt gốc — TÁI DÙNG, không viết lại)
    2. cài thêm vm/requirements-vm.txt
    3. ghi vps.json (đánh dấu "đang chạy chế độ VPS")
    4. tạo vm/config.json từ vm/config.example.json (trạm loopback, chế độ phiên)
    5. tạo DONE/ (nơi chứa gói video chờ đăng)
    6. sinh CLAUDE.local.md từ vm/VPS-CLAUDE.md
    7. đăng ký 3 lịch Task Scheduler qua core/lich_tu_chay

Không giống `vm/cai_dat_vps.py` (CẤM import `core.*` — lúc nó chạy, Python có
thể còn chưa cài xong pip), tệp NÀY được phép import `core.*`: tiền đề của cả
luồng cài này là bước 1 (SETUP.bat) đã chạy xong TRƯỚC — `core/` đã dùng
được. Vẫn tránh mọi thứ kéo theo PyQt5 (giao diện chưa chắc mở được ở đây,
và kịch bản này chạy không cửa sổ trong `CAI-DAT-VPS.bat`).

═══ CHẾ ĐỘ `--thu` ═══

In ra CÁC BƯỚC SẼ LÀM mà không làm gì thật — không gọi pip, không ghi tệp,
không gọi `schtasks`. Cùng tinh thần `tu_chay.py --thu`
(`CLAUDE.local.md` luật riêng VPS số 3: "Muốn thử thì dùng --thu").

═══ VÌ SAO `msvc-runtime` QUA PIP THAY VÌ `aka.ms` ═══

`vm/VPS-CLAUDE.md` luật 5: mạng VPS chỉ có IPv6, `aka.ms`/`github.com` đo
KHÔNG vào được (18/09/2026). `SETUP.bat` (không sửa ở đây, TÁI DÙNG nguyên
văn) tự tải `vc_redist.x64.exe` từ `aka.ms` NẾU import PyQt5 thất bại vì
thiếu Visual C++ runtime — trên VPS chỉ-IPv6, nhánh đó treo tới khi hết giờ
(mạng không lỗi ngay, `Invoke-WebRequest` phải hết `timeout` mới chịu thua).
Nên kịch bản này cài TRƯỚC gói PyPI `msvc-runtime` (bọc sẵn các DLL
`vcruntime140`/`msvcp140`, cùng tác dụng, tải qua `pypi.org` — IPv6 dùng
được) rồi MỚI gọi `SETUP.bat`: khi `SETUP.bat` tự kiểm `import PyQt5`, DLL đã
có sẵn và nhánh `aka.ms` không bao giờ bị chạm tới. Cài `msvc-runtime` hỏng
KHÔNG chặn cả lượt cài (best-effort) — máy có VC++ sẵn (phổ biến trên Windows
Server) thì bước này chỉ là thừa, không phải bắt buộc.

═══ VÌ SAO KHÔNG CẦN TỰ SỬA NGUỒN FFMPEG ═══

`requirements.txt` (gốc, `SETUP.bat` cài ở bước 1) đã có sẵn `imageio-ffmpeg`
— gói PyPI mang theo một bản FFmpeg dựng sẵn, và `core.ffmpeg_goi_san.
bao_dam_ffmpeg` đã tự ưu tiên bản NÀY trước khi thử tải `gyan.dev`/
`github.com` (xem docstring đầu tệp đó). Trên VPS chỉ-IPv6, miễn `pip
install -r requirements.txt` chạy xong là đường vòng qua gyan.dev/github
không bao giờ bị chạm — kịch bản này chỉ cần bảo đảm bước 1 chạy, KHÔNG tự ý
gọi `cai_ffmpeg()` (hàm tự tải qua mạng ngoài).

═══ Whisper: KHÔNG TỰ TẢI ĐƯỢC THÌ CHÉP TAY QUA RDP ═══

Mô hình `faster-whisper-small` nằm trên HuggingFace — `vm/VPS-CLAUDE.md` luật
5 liệt kê HuggingFace vào danh sách KHÔNG vào được từ máy chỉ-IPv6. Kịch bản
này THỬ tải (best-effort, không chặn cả lượt cài nếu hỏng) rồi in hướng dẫn
chép tay `models/faster-whisper-small/` từ máy nhà qua RDP khi tải không
được — xem `README-VPS.md`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # MyTool (vm/ nam BEN TRONG)
VM_DIR = os.path.join(GOC, "vm")

#: Trùng `vm/cai_dat_vps.TRAM_VPS` / `core/goi_vps.TRAM_VPS` — trạm luôn cố
#: định ở loopback trên VPS, ba nơi định nghĩa lại vì mỗi nơi có luật import
#: riêng (tệp này với `core.*` được phép, hai tệp kia thì không).
TRAM_VPS = "http://127.0.0.1:8765"

#: Số kênh tối đa mặc định của một VPS — quyết định #17 trong lộ trình v3.0
#: ("trần 5→10 kênh sau Đợt 1-2"). Dùng để điền vào CLAUDE.local.md sinh ra;
#: đổi qua `--so-kenh` nếu chủ dự án muốn ghi số khác cho máy cụ thể này.
SO_KENH_TOI_DA_MAC_DINH = 10

BaoHam = Callable[[str], None]
ChayLenh = Callable[[Sequence[str]], Tuple[int, str]]


def _im_lang(_dong: str) -> None:
    pass


def _chay_that(lenh: Sequence[str], *, timeout: float = 1800) -> Tuple[int, str]:
    try:
        ket = subprocess.run(
            list(lenh), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as loi:
        return 1, str(loi)
    return ket.returncode, (ket.stdout or "") + (ket.stderr or "")


# ── 1. SETUP.bat — TÁI DÙNG, không viết lại ─────────────────────────────────


def chay_setup_bat(goc: str, *, bao: Optional[BaoHam] = None,
                   chay: Optional[ChayLenh] = None, thu: bool = False) -> bool:
    """Gọi `SETUP.bat` gốc (cài `requirements.txt`, kiểm giao diện, khảo sát
    phần cứng...). KHÔNG viết lại logic của nó ở đây — chỉ gọi.

    `< NUL` (qua `stdin=subprocess.DEVNULL` khi tự chạy) để cái `pause` cuối
    `SETUP.bat` không treo cửa sổ chờ người bấm phím — VPS chạy việc này
    không có ai ngồi trước màn hình. Máy có mạng ổn định thì lượt này chỉ mất
    vài phút; máy phải tự tải VC++/Whisper có thể lâu hơn, nên `timeout` để
    rộng (1 giờ) thay vì mặc định 30 phút của các bước khác.
    """
    bao = bao or _im_lang
    duong = os.path.join(goc, "SETUP.bat")
    if not os.path.isfile(duong):
        bao("  !!! Không thấy SETUP.bat ở {0} — bỏ qua bước này.".format(goc))
        return False
    if thu:
        bao("  [thử] sẽ chạy SETUP.bat (cài requirements.txt gốc, kiểm giao "
            "diện, khảo sát phần cứng) — không chạy thật.")
        return True
    bao("  đang chạy SETUP.bat (có thể mất vài phút, lần đầu tải thêm mô "
        "hình Whisper/FFmpeg nếu máy chưa có)...")
    if chay is not None:
        ma, ra = chay(["cmd", "/c", duong])
    else:
        try:
            ket = subprocess.run(
                ["cmd", "/c", duong], cwd=goc, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=3600,
                stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            ma, ra = ket.returncode, (ket.stdout or "") + (ket.stderr or "")
        except (OSError, subprocess.SubprocessError) as loi:
            ma, ra = 1, str(loi)
    if ma != 0:
        bao("  !!! SETUP.bat kết thúc với mã lỗi {0}: {1}".format(ma, (ra or "")[-500:]))
        return False
    bao("  SETUP.bat chạy xong.")
    return True


# ── 2. vm/requirements-vm.txt (+ websocket-client, đã có trong tệp) ─────────


def cai_requirements_vm(python_exe: str, goc: str, *, bao: Optional[BaoHam] = None,
                        chay: Optional[ChayLenh] = None, thu: bool = False) -> bool:
    bao = bao or _im_lang
    chay = chay or _chay_that
    duong = os.path.join(goc, "vm", "requirements-vm.txt")
    if not os.path.isfile(duong):
        bao("  !!! Không thấy vm/requirements-vm.txt — bỏ qua.")
        return False
    if thu:
        bao("  [thử] sẽ chạy: {0} -m pip install -r {1}".format(python_exe, duong))
        return True
    for lan in range(1, 4):
        bao("  đang cài vm/requirements-vm.txt (lần {0}/3)...".format(lan))
        ma, ra = chay([python_exe, "-m", "pip", "install", "-q", "-r", duong])
        if ma == 0:
            bao("  vm/requirements-vm.txt: đã cài xong (có websocket-client — "
                "cần cho máy đăng DOM).")
            return True
    bao("  !!! Cài vm/requirements-vm.txt KHÔNG được sau 3 lần: {0}".format((ra or "")[:200]))
    return False


def cai_msvc_runtime(python_exe: str, *, bao: Optional[BaoHam] = None,
                     chay: Optional[ChayLenh] = None, thu: bool = False) -> bool:
    """`pip install msvc-runtime` — lùi nguồn tải Visual C++ runtime cho máy
    chỉ IPv6 (xem giải thích ở docstring đầu tệp). BEST-EFFORT: hỏng không
    chặn cả lượt cài, chỉ báo — máy vốn đã có VC++ (phổ biến trên Windows
    Server) thì bước này chỉ là thừa."""
    bao = bao or _im_lang
    chay = chay or _chay_that
    if thu:
        bao("  [thử] sẽ chạy: {0} -m pip install msvc-runtime".format(python_exe))
        return True
    bao("  đang cài msvc-runtime (thay cho tải vc_redist.exe từ aka.ms — "
        "máy chỉ IPv6 không vào được aka.ms)...")
    ma, ra = chay([python_exe, "-m", "pip", "install", "-q", "msvc-runtime"])
    if ma == 0:
        bao("  msvc-runtime: đã cài xong.")
        return True
    bao("  - msvc-runtime cài không được (không chặn cả lượt cài): {0}".format((ra or "")[:200]))
    return False


# ── 3. vps.json — đánh dấu chế độ VPS (xem vm/cai_dat_vps.ghi_vps_json) ─────


def ghi_vps_json(goc: str, *, bao: Optional[BaoHam] = None, thu: bool = False) -> str:
    bao = bao or _im_lang
    duong = os.path.join(goc, "vps.json")
    if thu:
        bao("  [thử] sẽ ghi {0} với vm_dir=\"vm\" (đường TƯƠNG ĐỐI — vm/ nằm "
            "ngay trong MyTool ở luồng cài từ bản clone).".format(duong))
        return duong
    du_lieu = {"vm_dir": "vm", "tao_luc": time.time(), "nguon": "clone"}
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du_lieu, tep, ensure_ascii=False, indent=2)
    os.replace(tam, duong)
    bao("  đã ghi vps.json — MyTool nhận ra mình đang chạy CHẾ ĐỘ VPS.")
    return duong


# ── 4. vm/config.json từ vm/config.example.json ─────────────────────────────


def dat_vm_config(goc: str, *, bao: Optional[BaoHam] = None, thu: bool = False) -> Dict[str, object]:
    """`vm/config.json` chưa có thì chép từ `vm/config.example.json`; có rồi
    thì GIỮ NGUYÊN (đây có thể là máy cập nhật lại, không phải cài lần đầu —
    đè lên là mất `kenh`/`cac_kenh`/`chrome` khách đã điền). Dù có sẵn hay
    vừa chép, luôn BẢO ĐẢM hai khoá bắt buộc của chế độ VPS đúng giá trị:
    `che_do_phien=true`, `tram=http://127.0.0.1:8765` — cùng logic
    `vm/cai_dat_vps.bao_dam_tram_loopback`, viết lại ở đây vì tệp đó không
    được `import` (nguyên tắc "chạy trước khi có pip" của chính nó)."""
    bao = bao or _im_lang
    duong = os.path.join(goc, "vm", "config.json")
    duong_mau = os.path.join(goc, "vm", "config.example.json")
    if thu:
        neu_co = "GIỮ NGUYÊN (đã có)" if os.path.isfile(duong) else "chép từ config.example.json"
        bao("  [thử] vm/config.json: {0}; bảo đảm che_do_phien=true, tram={1}."
            .format(neu_co, TRAM_VPS))
        return {}

    if os.path.isfile(duong):
        bao("  vm/config.json đã có sẵn — giữ nguyên nội dung khách đã điền.")
        try:
            with open(duong, encoding="utf-8") as tep:
                cai = json.load(tep)
        except (OSError, ValueError) as loi:
            bao("  !!! vm/config.json đọc lỗi, KHÔNG đụng vào: {0}".format(loi))
            return {}
    else:
        if not os.path.isfile(duong_mau):
            bao("  !!! Không thấy vm/config.example.json — không tạo được vm/config.json.")
            return {}
        with open(duong_mau, encoding="utf-8") as tep:
            cai = json.load(tep)
        bao("  đã tạo vm/config.json từ vm/config.example.json.")

    doi = False
    if cai.get("tram") != TRAM_VPS:
        cai["tram"] = TRAM_VPS
        doi = True
    if not cai.get("che_do_phien"):
        cai["che_do_phien"] = True
        doi = True
    if doi:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(cai, tep, ensure_ascii=False, indent=4)
        os.replace(tam, duong)
        bao("  đã chỉnh vm/config.json: tram=127.0.0.1, che_do_phien=true.")
    else:
        bao("  vm/config.json đã đúng trạm 127.0.0.1 + chế độ phiên từ trước.")
    return cai


# ── 5. DONE/ ─────────────────────────────────────────────────────────────


def tao_thu_muc_done(goc: str, *, bao: Optional[BaoHam] = None, thu: bool = False) -> str:
    bao = bao or _im_lang
    duong = os.path.join(goc, "DONE")
    if thu:
        bao("  [thử] sẽ tạo thư mục {0} (nếu chưa có).".format(duong))
        return duong
    da_co = os.path.isdir(duong)
    os.makedirs(duong, exist_ok=True)
    bao("  DONE/: {0}.".format("đã có sẵn" if da_co else "vừa tạo"))
    return duong


# ── 6. CLAUDE.local.md từ vm/VPS-CLAUDE.md (khuôn có biến) ──────────────────

#: Đoạn văn bản MẶC ĐỊNH trong `vm/VPS-CLAUDE.md` — bản thân tài liệu đã đọc
#: TRÔI CHẢY với đúng các giá trị này (10 kênh, repo đọc từ cap-nhat.json),
#: nên bản cài CŨ (`vm/cai_dat_vps.py`, chép nguyên văn không thay biến) vẫn
#: ra một CLAUDE.local.md đúng ngữ pháp. Ở ĐÂY chỉ thay khi máy cụ thể có số
#: liệu KHÁC mặc định — không có "khuôn kiểu __TOKEN__" nào lộ ra nếu bước
#: thay này không chạy (an toàn hơn cho các đường gọi khác chưa biết tới nó).
_NEO_SO_KENH = "tối đa 10"
_NEO_REPO = "(cấu hình trong `cap-nhat.json` ở gốc MyTool)"


def _doc_repo_cap_nhat(goc: str) -> str:
    """Đọc tên/kho cập nhật từ `cap-nhat.json` ở gốc MyTool — KHÔNG cứng tên
    kho cũ (A17, mục Chặn phát hành trong lộ trình). Tệp này do
    `core/nguon_cap_nhat.py` ghi (việc 5.2, của một phiên khác) — lược đồ
    khoá thật sự tuỳ nơi đó chốt; ở đây chỉ ĐOÁN vài tên khoá hợp lý và LUÔN
    có đường lui khi tệp chưa tồn tại hoặc khoá không khớp, không ném lỗi."""
    duong = os.path.join(goc, "cap-nhat.json")
    try:
        with open(duong, encoding="utf-8") as tep:
            du = json.load(tep)
    except (OSError, ValueError):
        return ""
    if not isinstance(du, dict):
        return ""
    for khoa in ("repo", "kho", "nguon", "dia_chi", "url"):
        gia_tri = du.get(khoa)
        if isinstance(gia_tri, str) and gia_tri.strip():
            return gia_tri.strip()
    return ""


def dat_ho_so_phat_trien(goc: str, *, so_kenh_toi_da: int = SO_KENH_TOI_DA_MAC_DINH,
                         bao: Optional[BaoHam] = None, thu: bool = False) -> None:
    """Chép `vm/VPS-CLAUDE.md` → `MyTool/CLAUDE.local.md` (LUÔN đè — tài liệu
    của TA, không phải nhật ký riêng của máy), điền số kênh tối đa + gợi ý
    kho cập nhật nếu khác mặc định, và dựng `NHAT-KY-PHAT-TRIEN.md` +
    `workspace/ban-va/` cho phiên Claude Code mở thẳng trên VPS này."""
    bao = bao or _im_lang
    nguon = os.path.join(goc, "vm", "VPS-CLAUDE.md")
    dich = os.path.join(goc, "CLAUDE.local.md")
    if thu:
        bao("  [thử] sẽ sinh CLAUDE.local.md từ vm/VPS-CLAUDE.md (số kênh tối "
            "đa={0}, đọc repo cập nhật từ cap-nhat.json nếu có), tạo "
            "NHAT-KY-PHAT-TRIEN.md và workspace/ban-va/ nếu chưa có."
            .format(so_kenh_toi_da))
        return
    if os.path.isfile(nguon):
        with open(nguon, encoding="utf-8") as tep:
            noi_dung = tep.read()
        if so_kenh_toi_da != 10 and _NEO_SO_KENH in noi_dung:
            noi_dung = noi_dung.replace(_NEO_SO_KENH, "tối đa {0}".format(so_kenh_toi_da))
        repo = _doc_repo_cap_nhat(goc)
        if repo and _NEO_REPO in noi_dung:
            noi_dung = noi_dung.replace(_NEO_REPO, "({0})".format(repo))
        with open(dich, "w", encoding="utf-8") as tep:
            tep.write(noi_dung)
        bao("  đã cập nhật CLAUDE.local.md (hướng dẫn Claude Code trên VPS này).")
    else:
        bao("  !!! Không thấy vm/VPS-CLAUDE.md — không sinh được CLAUDE.local.md.")

    duong_nk = os.path.join(goc, "NHAT-KY-PHAT-TRIEN.md")
    if not os.path.isfile(duong_nk):
        with open(duong_nk, "w", encoding="utf-8") as tep:
            tep.write(
                "# Nhật ký phát triển trên VPS này\n\n"
                "Ghi những gì đã đổi / thử / hỏng ngay trên MÁY NÀY — khác "
                "nhật ký chung của tool. Mỗi mục: ngày, việc, kết quả.\n\n")
        bao("  đã tạo NHAT-KY-PHAT-TRIEN.md (lần đầu).")

    os.makedirs(os.path.join(goc, "workspace", "ban-va"), exist_ok=True)


# ── 7. 3 lịch Task Scheduler qua core/lich_tu_chay (chỉ GỌI hàm có sẵn) ──────


def dang_ky_lich(goc: str, *, gio: str = "02:00", phut_canh: int = 5,
                 bao: Optional[BaoHam] = None, thu: bool = False) -> bool:
    """Đăng ký BA việc trong Task Scheduler bằng cách GỌI hai hàm có sẵn của
    `core/lich_tu_chay` — không viết lại logic `schtasks` ở đây:

    * `dang_ky()`                → `ShopAPI-TuChay` (sản xuất hằng ngày)
    * `dang_ky_canh_tram()`      → `ShopAPI-CanhTram` + `ShopAPI-TramLucDangNhap`
      (hàm này tự đăng ký CẢ HAI việc — xem docstring của nó trong
      `core/lich_tu_chay.py`).
    """
    bao = bao or _im_lang
    if thu:
        bao("  [thử] sẽ gọi core.lich_tu_chay.dang_ky(goc, \"{0}\") + "
            "dang_ky_canh_tram(goc, {1}) — đăng ký 3 việc Task Scheduler."
            .format(gio, phut_canh))
        return True
    try:
        from core import lich_tu_chay
    except Exception as loi:  # noqa: BLE001 — core/ chưa sẵn sàng thì báo rõ, không sập cả lượt cài
        bao("  !!! Không nạp được core.lich_tu_chay ({0}) — SETUP.bat có chạy "
            "xong chưa?".format(loi))
        return False

    ok1, msg1 = lich_tu_chay.dang_ky(goc, gio)
    bao("  ShopAPI-TuChay: {0}".format(msg1))
    ok2, msg2 = lich_tu_chay.dang_ky_canh_tram(goc, phut_canh)
    bao("  ShopAPI-CanhTram + ShopAPI-TramLucDangNhap: {0}".format(msg2))
    return ok1 and ok2


# ── Toàn bộ dây chuyền ───────────────────────────────────────────────────────


def cai(*, goc: str = GOC, gio_tu_chay: str = "02:00", phut_canh_tram: int = 5,
       so_kenh_toi_da: int = SO_KENH_TOI_DA_MAC_DINH,
       bao: Optional[BaoHam] = None, chay: Optional[ChayLenh] = None,
       thu: bool = False) -> Dict[str, object]:
    bao = bao or print
    python_exe = sys.executable or "python"

    bao("Bước 1/7 — SETUP.bat (thư viện gốc, kiểm giao diện)")
    b1 = chay_setup_bat(goc, bao=bao, chay=chay, thu=thu)

    bao("Bước 2/7 — msvc-runtime (lùi nguồn cho máy chỉ IPv6)")
    b2 = cai_msvc_runtime(python_exe, bao=bao, chay=chay, thu=thu)

    bao("Bước 3/7 — vm/requirements-vm.txt (gồm websocket-client)")
    b3 = cai_requirements_vm(python_exe, goc, bao=bao, chay=chay, thu=thu)

    bao("Bước 4/7 — vps.json + vm/config.json")
    b4a = ghi_vps_json(goc, bao=bao, thu=thu)
    b4b = dat_vm_config(goc, bao=bao, thu=thu)

    bao("Bước 5/7 — DONE/ + hồ sơ phát triển (CLAUDE.local.md)")
    b5a = tao_thu_muc_done(goc, bao=bao, thu=thu)
    dat_ho_so_phat_trien(goc, so_kenh_toi_da=so_kenh_toi_da, bao=bao, thu=thu)

    bao("Bước 6/7 — đăng ký 3 lịch Task Scheduler")
    b6 = dang_ky_lich(goc, gio=gio_tu_chay, phut_canh=phut_canh_tram, bao=bao, thu=thu)

    bao("Bước 7/7 — kiểm lại máy")
    if thu:
        bao("  [thử] sẽ chạy: python -m core.kiem_may --day-du")
    else:
        bao("  Chạy tay lệnh sau để xem bảng OK/THIẾU: "
            "python -m core.kiem_may --day-du")

    bao("")
    if thu:
        bao("=== CHẾ ĐỘ THỬ — CHƯA LÀM GÌ THẬT ===")
    else:
        bao("=== XONG ===")
        bao("Chạy 'python -m core.kiem_may --day-du' để soát lại toàn bộ.")

    return {
        "setup_bat": b1, "msvc_runtime": b2, "requirements_vm": b3,
        "vps_json": b4a, "vm_config": bool(b4b), "done_dir": b5a,
        "lich": b6,
    }


def main(argv: Optional[List[str]] = None) -> int:
    phan_tich = argparse.ArgumentParser(
        description="Cài VPS từ bản clone (SETUP.bat + thư viện vm/ + vps.json "
                    "+ vm/config.json + DONE/ + CLAUDE.local.md + 3 lịch).")
    phan_tich.add_argument("--thu", action="store_true",
                           help="chỉ in các bước sẽ làm, không làm gì thật")
    phan_tich.add_argument("--gio", default="02:00", help="giờ chạy tu_chay.py --tat-ca mỗi ngày (HH:MM)")
    phan_tich.add_argument("--phut-canh", type=int, default=5, help="nhịp kiểm trạm (phút)")
    phan_tich.add_argument("--so-kenh", type=int, default=SO_KENH_TOI_DA_MAC_DINH,
                           help="số kênh tối đa ghi vào CLAUDE.local.md")
    doi_so = phan_tich.parse_args(argv)
    print("=" * 60)
    print("  MyTool VPS - cai dat tu ban clone")
    print("=" * 60)
    try:
        cai(gio_tu_chay=doi_so.gio, phut_canh_tram=doi_so.phut_canh,
           so_kenh_toi_da=doi_so.so_kenh, thu=doi_so.thu)
    except Exception as loi:  # noqa: BLE001 — báo thật, không để cửa sổ biến mất
        print()
        print("  !!! Lỗi: {0}".format(loi))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
