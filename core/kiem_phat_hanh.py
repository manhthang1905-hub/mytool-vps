# -*- coding: utf-8 -*-
"""core/kiem_phat_hanh.py — kiểm phát hành v3.0 (Việc 5.3 lộ trình).

`workspace/LO-TRINH-PHAT-HANH-V3.md`, tiêu chí "Sẵn sàng v3.0" mục 1 và 2:

    1. clone sạch pytest 0 failed/0 error, skip ≤20 có lý do,
       test_khong_ghi_du_lieu_that đạt
    2. không lọt bí mật/dữ liệu/đường C:\\Users/CLAUDE.local.md

═══ BA BƯỚC, THEO ĐÚNG THỨ TỰ ═══

1. `xuat_cay_sach` — chép đúng những tệp một `git clone` MỚI sẽ có (theo dõi +
   chưa theo dõi nhưng KHÔNG bị `.gitignore` chặn) ra một thư mục tạm NGOÀI
   MyTool. Đọc từ ĐĨA (không qua `git show`/`git archive` một commit), vì mã
   mới nhất thường chưa commit lúc kiểm — và vì `.gitignore` có lỗ (vá E1,
   29/09/2026: `CLAUDE.local.md` vẫn đang bị Git THEO DÕI dù đã lên danh sách
   chặn — chỉ `git ls-files -c` mới thấy được ca này, `--exclude-standard`
   không gỡ một tệp ĐÃ theo dõi).
2. `quet_cay_sach` — soi cây sạch: bí mật (tên tệp lẫn nội dung), dữ liệu kênh
   THẬT lọt qua `.gitignore`, đường tuyệt đối `C:\\Users`, chính
   `CLAUDE.local.md`, tệp > 5MB. Mọi phát hiện đều vào danh sách CHẶN — đây là
   lớp kiểm THỨ HAI, không tin rằng `.gitignore` luôn đúng.
3. `san_sang_chay_pytest` + `chay_pytest_cay_sach` — chạy `pytest` TRÊN CÂY
   SẠCH, KHÔNG PHẢI trên kho đang sửa dở (nhiều phiên agent có thể đang sửa
   file cùng lúc). Chỉ chạy khi RAM trống đủ VÀ máy không đang giữ khe "nang"
   (`.khoa-may`) hay có lượt sản xuất ở khâu `phu-de`/`dung` — luật
   "VPS không chạy nặng song song" (`CLAUDE.local.md`). Không đủ điều kiện thì
   TỰ HOÃN, không tự ép chạy.

`main()` nối cả ba bước và ghi báo cáo `workspace/kiem-phat-hanh/<ngày>.md`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

from .auto import DANG as _KHAU_DANG
from .ghi_dia import ghi_chu
from .khe import pid_con_song, ram_gb

#: Lớp chặn bí mật theo TÊN tệp (trước ở `core/goi_vps.py`, bỏ 01/10/2026 cùng luồng cài ZIP).
_MAU_BI_MAT = re.compile(
    r"secret|cookie|credential|(?:^|[-_.])token(?:[-_.]|$)|api[-_]?key|"
    r"-rieng\.json$|\.key$|\.pem$", re.IGNORECASE)

__all__ = [
    "KiemPhatHanhError", "CaySach", "PhatHien", "KetQuaPytest",
    "GOC", "NGUONG_RAM_TRONG_GB", "NGUONG_TEP_LON_MB",
    "xuat_cay_sach", "don_cay_cu", "quet_cay_sach",
    "san_sang_chay_pytest", "chay_pytest_cay_sach",
    "viet_bao_cao", "duong_bao_cao", "main",
]

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Dưới ngưỡng này thì KHÔNG chạy pytest, dù không có lượt sản xuất nào —
#: cùng con số với luật CLAUDE.md "chỉ chạy khi RAM trống ≥ 6GB".
NGUONG_RAM_TRONG_GB = 6.0

#: Tệp lớn hơn ngưỡng này (MB) trong cây sạch bị coi là đáng ngờ — mã nguồn
#: bình thường không có tệp .py/.json/.md nào to cỡ này; hay gặp nhất là ai đó
#: lỡ track một model/whisper hay một gói .zip.
NGUONG_TEP_LON_MB = 5

_THU_MUC_XUAT_MAC_DINH = "shopapi-kiem-phat-hanh"

#: Đuôi tệp có thể chứa văn bản đọc được — chỉ những đuôi này mới bị quét NỘI
#: DUNG tìm bí mật/đường tuyệt đối. Đuôi nhị phân (ảnh, mp3, exe…) không quét
#: nội dung, đỡ tốn thời gian và tránh báo giả trên byte ngẫu nhiên.
_DUOI_VAN_BAN = (".py", ".json", ".yaml", ".yml", ".md", ".txt", ".js",
                  ".ini", ".cfg", ".csv", ".bat", ".vbs", ".ps1", ".xml",
                  ".env", ".example")

#: Quét nội dung tối đa từng này byte mỗi tệp — đủ cho mọi tệp mã/cấu hình
#: thật, tránh đọc trọn một CSV vài chục MB lỡ lọt qua bộ lọc đuôi.
_KICH_TOI_DA_QUET_NOI_DUNG = 2 * 1024 * 1024

#: Mẫu bí mật DẠNG GIÁ TRỊ trong nội dung tệp — bổ sung cho `_MAU_BI_MAT` (chỉ
#: soi TÊN tệp). Vế `[:=]` bắt cả JSON (`"khoa": "..."`) lẫn .env/.py
#: (`KHOA=...`); giá trị phải đủ dài để không bắt nhầm placeholder rỗng như
#: `"mat_khau": ""` hay `"mat_khau": "xxx"` (đặt sàn ký tự cho từng loại).
_MAU_NOI_DUNG_BI_MAT: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("khoá dạng sk_live_...", re.compile(r"sk_live_[A-Za-z0-9]{10,}")),
    ("token Telegram (số:chuỗi)",
     re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_-]{30,}(?!\w)")),
    ("client_secret Google OAuth (GOCSPX-...)",
     re.compile(r"GOCSPX-[A-Za-z0-9_-]{10,}")),
    ("client_secret",
     re.compile(r"client_secret[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']", re.I)),
    ("mật khẩu",
     re.compile(r"(?:mat_khau|password|passwd)[\"']?\s*[:=]\s*"
                r"[\"'][^\"'\s]{4,}[\"']", re.I)),
    ("cookie",
     re.compile(r"cookie[\"']?\s*[:=]\s*[\"'][^\"'\r\n]{10,}[\"']", re.I)),
)

#: Đường tuyệt đối riêng của máy đóng gói — không được lọt vào mã đi kèm tool,
#: máy khác không có `C:\Users\<tên máy nhà>\...`.
#: Chỗ điền MẪU sau `Users\` (vá 30/09/2026, kho chung): `...`, `…`, `{user}`,
#: `<ten>`, `%USERNAME%`, `$env`, `x\` — là ví dụ trong tài liệu/test, không
#: phải đường thật của máy nào; không chặn.
_MAU_DUONG_TUYET_DOI = re.compile(
    r"[A-Za-z]:\\+Users\\+(?!\\|\.\.\.|…|\{|<|%|\$|x\\)", re.IGNORECASE)
_DUOI_QUET_DUONG_TUYET_DOI = (".yaml", ".yml", ".json", ".md", ".py")


class KiemPhatHanhError(RuntimeError):
    """Không dựng được cây sạch (không phải Git, hoặc `git` lỗi)."""


@dataclass
class CaySach:
    """Kết quả `xuat_cay_sach`: nơi cây sạch nằm + hai danh sách tệp.

    `tep` — MỌI tệp đã chép (theo dõi + chưa theo dõi nhưng không bị
    `.gitignore` chặn), đường dẫn tương đối dùng `/`.
    `theo_doi` — tập con CHỈ những tệp Git đang THEO DÕI (đã `git add`/commit
    ít nhất một lần) — dùng cho các kiểm chỉ có nghĩa với mã đã qua review
    (đường tuyệt đối, `CLAUDE.local.md`).
    """

    duong: str
    tep: Tuple[str, ...]
    theo_doi: FrozenSet[str]


@dataclass
class PhatHien:
    """Một dòng trong danh sách CHẶN."""

    loai: str      # "bi_mat" | "du_lieu_kenh" | "duong_tuyet_doi" | "claude_local_md" | "tep_lon"
    duong: str     # đường tương đối trong cây sạch, dùng "/"
    ghi_chu: str = ""


@dataclass
class KetQuaPytest:
    da_chay: bool
    ma_thoat: Optional[int] = None
    ly_do_hoan: str = ""
    stdout: str = ""
    stderr: str = ""


# ── Bước 1: cây sạch ─────────────────────────────────────────────────────────


def _chay_git(goc: str, tham_so: Sequence[str]) -> bytes:
    try:
        ket = subprocess.run(
            ["git", *tham_so], cwd=goc, capture_output=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as loi:
        raise KiemPhatHanhError(
            "Không gọi được git ({0}): {1}".format(" ".join(tham_so), loi)) from loi
    if ket.returncode != 0:
        raise KiemPhatHanhError(
            "git {0} lỗi:\n{1}".format(
                " ".join(tham_so), ket.stderr.decode("utf-8", "replace")))
    return ket.stdout


def _danh_sach_tep(goc: str, tham_so: Sequence[str]) -> List[str]:
    thoat = _chay_git(goc, tham_so)
    return [p.decode("utf-8", "surrogateescape").replace("\\", "/")
            for p in thoat.split(b"\0") if p]


def _thu_muc_xuat_mac_dinh() -> str:
    goc_tam = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return os.path.join(goc_tam, _THU_MUC_XUAT_MAC_DINH)


def don_cay_cu(goc_tam: Optional[str] = None, *, giu_ngay: float = 3.0,
               log: Callable[[str], None] = lambda s: None) -> int:
    """Xoá các cây sạch cũ (> `giu_ngay` ngày) trong `goc_tam` — đĩa VPS có
    trần (`vm/KE-HOACH.md`, van đĩa <15GB), một chỗ kiểm chạy hằng ngày mà
    không tự dọn là để lại rác vĩnh viễn. Trả về số thư mục đã xoá."""
    goc_tam = goc_tam or _thu_muc_xuat_mac_dinh()
    if not os.path.isdir(goc_tam):
        return 0
    han = time.time() - giu_ngay * 86400
    so_xoa = 0
    for ten in os.listdir(goc_tam):
        duong = os.path.join(goc_tam, ten)
        try:
            if os.path.isdir(duong) and os.path.getmtime(duong) < han:
                shutil.rmtree(duong, ignore_errors=True)
                so_xoa += 1
        except OSError:
            continue
    if so_xoa:
        log("  đã dọn {0} cây sạch cũ (>{1:g} ngày) trong {2}".format(
            so_xoa, giu_ngay, goc_tam))
    return so_xoa


def xuat_cay_sach(goc: str = GOC, *, thu_muc_dich: Optional[str] = None,
                   log: Callable[[str], None] = lambda s: None) -> CaySach:
    """Chép cây làm việc HIỆN TẠI (gồm thay đổi chưa commit) ra một thư mục
    tạm NGOÀI `goc`, đúng những gì một `git clone` mới sẽ nhận.

    Đọc danh sách qua `git ls-files -co --exclude-standard` rồi CHÉP TỪ ĐĨA
    (không phải từ một commit `git archive`): đây là lựa chọn có chủ đích —
    kiểm phát hành phải soi đúng trạng thái đĩa NGAY LÚC GỌI, kể cả khi nhiều
    phiên agent khác đang sửa `core/tu_chay.py`, `core/auto_khau.py`,
    `vm/agent.py`… cùng lúc.
    """
    if not os.path.isdir(os.path.join(goc, ".git")):
        raise KiemPhatHanhError(
            "{0} không phải một Git worktree (.git không có) — kiểm phát hành "
            "cần Git để biết đúng tệp nào đi kèm bản phát hành.".format(goc))

    day_du = _danh_sach_tep(goc, ["ls-files", "-co", "--exclude-standard", "-z"])
    theo_doi = frozenset(_danh_sach_tep(goc, ["ls-files", "-c", "-z"]))
    log("  {0} tệp sẽ có trong bản phát hành ({1} tệp đang theo dõi Git)."
        .format(len(day_du), len(theo_doi)))

    if thu_muc_dich is None:
        thu_muc_dich = os.path.join(
            _thu_muc_xuat_mac_dinh(), time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(thu_muc_dich, exist_ok=True)

    da_chep: List[str] = []
    for rel in day_du:
        nguon = os.path.join(goc, *rel.split("/"))
        if not os.path.isfile(nguon):
            continue  # tệp đã theo dõi nhưng đã bị xoá trên đĩa — không có gì để chép
        dich = os.path.join(thu_muc_dich, *rel.split("/"))
        os.makedirs(os.path.dirname(dich), exist_ok=True)
        try:
            shutil.copy2(nguon, dich)
        except OSError as loi:
            log("  ! bỏ qua {0} (không đọc được: {1})".format(rel, loi))
            continue
        da_chep.append(rel)

    log("  đã chép {0} tệp sang {1}".format(len(da_chep), thu_muc_dich))
    return CaySach(duong=thu_muc_dich, tep=tuple(da_chep),
                    theo_doi=theo_doi & frozenset(da_chep))


# ── Bước 2: quét cây sạch ────────────────────────────────────────────────────


def _la_du_lieu_kenh_that(rel: str) -> Optional[str]:
    """`rel` có phải dữ liệu kênh THẬT (không phải khuôn) lọt qua
    `.gitignore` không? Trả về câu lý do, hoặc `None` nếu sạch.

    Danh sách khớp mục "Chặn phát hành" E trong lộ trình v3."""
    phan = rel.split("/")
    if phan[0] == "CHANNEL" and len(phan) >= 3:
        muc = phan[2]
        if muc == "nghien-cuu" and len(phan) >= 4 and phan[3] != "tuyen.csv":
            return "CHANNEL/*/nghien-cuu/* (dữ liệu đối thủ thật, trừ tuyen.csv)"
        if muc.startswith("chi-so"):
            return "CHANNEL/*/chi-so* (số liệu kênh thật)"
        if muc == "ho-so-video":
            return "CHANNEL/*/ho-so-video (dữ liệu video thật)"
        if muc == "can-ghim.md":
            return "CHANNEL/*/can-ghim.md (dữ liệu kênh thật)"
        if muc == "NHAT-KY-KENH.md":
            return "CHANNEL/*/NHAT-KY-KENH.md (nhật ký kênh thật)"
    # `vm/tien-ich/*/` = riêng THƯ MỤC CON theo mã kênh (khớp .gitignore); các
    # tệp .js/.json khuôn nằm THẲNG trong vm/tien-ich/ (không thư mục con) vẫn
    # là mã nguồn — cần ÍT NHẤT 4 phần (vm/tien-ich/<k>/<tệp>) mới tính.
    if phan[0] == "vm" and len(phan) >= 4 and phan[1] == "tien-ich":
        return "vm/tien-ich/<kênh>/ (cấu hình tiện ích riêng máy)"
    if phan[0] == "vm" and len(phan) >= 2 and phan[1] == "logs":
        return "vm/logs (nhật ký máy thật)"
    return None


def _doc_dau_tep(duong: str, kich_toi_da: int) -> str:
    try:
        with open(duong, "rb") as tep:
            tho = tep.read(kich_toi_da)
    except OSError:
        return ""
    return tho.decode("utf-8", "replace")


def quet_cay_sach(cay: CaySach) -> List[PhatHien]:
    """Soi cây sạch, trả về danh sách CHẶN (rỗng = sạch).

    Lớp kiểm THỨ HAI — không tin rằng `.gitignore` luôn lọc
    đúng (đã có tiền lệ, mục E của lộ trình v3: `CLAUDE.local.md` bị Git theo
    dõi dù đã lên `.gitignore`)."""
    phat_hien: List[PhatHien] = []
    for rel in cay.tep:
        duong_that = os.path.join(cay.duong, *rel.split("/"))
        ten = rel.rsplit("/", 1)[-1]
        duoi = os.path.splitext(ten)[1].lower()

        if ten == "CLAUDE.local.md":
            phat_hien.append(PhatHien("claude_local_md", rel,
                                       "CLAUDE.local.md không được đi kèm bản phát hành."))

        ly_do_kenh = _la_du_lieu_kenh_that(rel)
        if ly_do_kenh:
            phat_hien.append(PhatHien("du_lieu_kenh", rel, ly_do_kenh))

        # Chặn theo TÊN dành cho tệp DỮ LIỆU (secrets.json, cookies.txt…). Tệp
        # mã `.py` (vd `core/secrets.py` — bộ quản lý khoá) vẫn bị soi NỘI DUNG
        # bên dưới, nhưng tên thôi không đủ để chặn (vá 30/09/2026, kho chung).
        if duoi != ".py" and _MAU_BI_MAT.search(ten):
            phat_hien.append(PhatHien("bi_mat", rel, "tên tệp trông giống chứa bí mật."))

        try:
            kich = os.path.getsize(duong_that)
        except OSError:
            kich = 0
        if kich > NGUONG_TEP_LON_MB * 1024 * 1024:
            phat_hien.append(PhatHien(
                "tep_lon", rel, "{0:.1f}MB > ngưỡng {1}MB.".format(
                    kich / 1024 / 1024, NGUONG_TEP_LON_MB)))

        # Chỉ đọc nội dung MỘT lần mỗi tệp, cho cả hai kiểm dưới — tệp lớn hoặc
        # đuôi nhị phân thì không đọc gì cả.
        can_quet_bi_mat = duoi in _DUOI_VAN_BAN and kich <= _KICH_TOI_DA_QUET_NOI_DUNG
        can_quet_duong = (rel in cay.theo_doi and duoi in _DUOI_QUET_DUONG_TUYET_DOI
                           and kich <= _KICH_TOI_DA_QUET_NOI_DUNG)
        noi_dung = (_doc_dau_tep(duong_that, _KICH_TOI_DA_QUET_NOI_DUNG)
                    if (can_quet_bi_mat or can_quet_duong) else "")

        if can_quet_bi_mat and noi_dung:
            for ten_mau, mau in _MAU_NOI_DUNG_BI_MAT:
                if mau.search(noi_dung):
                    phat_hien.append(PhatHien(
                        "bi_mat", rel, "nội dung khớp mẫu \"{0}\".".format(ten_mau)))
                    break  # một dòng CHẶN mỗi tệp là đủ, khỏi lặp mẫu

        if can_quet_duong and noi_dung and _MAU_DUONG_TUYET_DOI.search(noi_dung):
            phat_hien.append(PhatHien(
                "duong_tuyet_doi", rel, "chứa đường tuyệt đối kiểu C:\\Users\\..."))

    return phat_hien


# ── Bước 3: pytest trên cây sạch ─────────────────────────────────────────────


def _khoa_nang_dang_giu(goc: str) -> str:
    """'' nếu khe "nang" (`.khoa-may`) đang trống; câu lý do nếu có người giữ
    còn sống — ĐÚNG đường `core/tu_chay.TEN_TEP_KHOA_MAY` / `core/khe.py`."""
    duong = os.path.join(goc, "workspace", "tu-chay", ".khoa-may")
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            goi = json.load(tep)
    except (OSError, ValueError):
        return ""
    if not isinstance(goi, dict):
        return ""
    try:
        pid = int(goi.get("pid", 0))
    except (TypeError, ValueError):
        pid = 0
    if pid and pid_con_song(pid):
        return "khe \"nang\" (.khoa-may) đang giữ bởi PID {0} còn sống.".format(pid)
    return ""


def _luot_dang_o_khau_nang(goc: str) -> str:
    """'' nếu không có lượt AUTO nào đang ở khâu `phu-de`/`dung` (lớp "nang",
    xem `core/auto.LOP_KHAU`); câu lý do nếu có."""
    goc_auto = os.path.join(goc, "PROJECTS", "AUTO")
    if not os.path.isdir(goc_auto):
        return ""
    try:
        ma_kenh_list = os.listdir(goc_auto)
    except OSError:
        return ""
    for ma_kenh in ma_kenh_list:
        thu_muc_kenh = os.path.join(goc_auto, ma_kenh)
        try:
            ma_luot_list = os.listdir(thu_muc_kenh)
        except OSError:
            continue
        for ma_luot in ma_luot_list:
            duong_tt = os.path.join(thu_muc_kenh, ma_luot, "trang-thai.json")
            try:
                with open(duong_tt, "r", encoding="utf-8") as tep:
                    goi = json.load(tep)
            except (OSError, ValueError):
                continue
            khau = goi.get("khau") if isinstance(goi, dict) else None
            if not isinstance(khau, dict):
                continue
            for ma in ("phu-de", "dung"):
                muc = khau.get(ma)
                if isinstance(muc, dict) and muc.get("trang_thai") == _KHAU_DANG:
                    return "kênh {0} lượt {1} đang ở khâu \"{2}\".".format(
                        ma_kenh, ma_luot, ma)
    return ""


def san_sang_chay_pytest(goc: str = GOC) -> Tuple[bool, str]:
    """`(sẵn_sàng, lý_do)`. Luật CLAUDE.md/CLAUDE.local.md: RAM trống ≥
    `NGUONG_RAM_TRONG_GB`, và không có ai đang giữ khe "nang"/ở khâu
    dựng-phụ đề — "VPS không chạy nặng song song"."""
    ram_trong, _ = ram_gb()
    if ram_trong is None:
        return False, "không đo được RAM trống trên máy này — hoãn cho an toàn."
    if ram_trong < NGUONG_RAM_TRONG_GB:
        return False, "RAM trống {0:.1f}GB < ngưỡng {1:g}GB.".format(
            ram_trong, NGUONG_RAM_TRONG_GB)
    ly_do = _khoa_nang_dang_giu(goc) or _luot_dang_o_khau_nang(goc)
    if ly_do:
        return False, ly_do
    return True, ""


def chay_pytest_cay_sach(cay: CaySach, *,
                          bien_moi_truong_them: Optional[Dict[str, str]] = None,
                          log: Callable[[str], None] = lambda s: None) -> KetQuaPytest:
    """Chạy `python -m pytest tests/` TRÊN CÂY SẠCH, tiến trình con ưu tiên
    thấp (`IDLE_PRIORITY_CLASS`) để không giành CPU của việc sản xuất đang
    chạy trên máy này.

    Gọi hàm này TRƯỚC PHẢI qua `san_sang_chay_pytest` — hàm này TỰ NÓ không
    kiểm RAM/khoá, chỉ lo phần chạy tiến trình con."""
    moi_truong = dict(os.environ)
    # `SHOPAPI_VM_GOC` — Việc 0.2 của lộ trình v3 (`vm/agent.py` cô lập test).
    # Ghi vô hại nếu module chưa đọc biến này: chỉ là một biến môi trường thừa.
    moi_truong["SHOPAPI_VM_GOC"] = cay.duong
    if bien_moi_truong_them:
        moi_truong.update(bien_moi_truong_them)

    co = 0
    if os.name == "nt":
        co = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
              | getattr(subprocess, "IDLE_PRIORITY_CLASS", 0))

    log("  chạy pytest trên cây sạch {0} (ưu tiên thấp)...".format(cay.duong))
    ket = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-p", "no:cacheprovider", "-q"],
        cwd=cay.duong, env=moi_truong, capture_output=True, text=True,
        encoding="utf-8", errors="replace", creationflags=co)
    return KetQuaPytest(da_chay=True, ma_thoat=ket.returncode,
                         stdout=ket.stdout, stderr=ket.stderr)


# ── Báo cáo ──────────────────────────────────────────────────────────────────


def duong_bao_cao(goc: str = GOC, *, ngay: Optional[str] = None) -> str:
    ngay = ngay or time.strftime("%Y-%m-%d")
    return os.path.join(goc, "workspace", "kiem-phat-hanh", "{0}.md".format(ngay))


def viet_bao_cao(cay: CaySach, phat_hien: Sequence[PhatHien],
                  ket_qua_pytest: KetQuaPytest, *, goc: str = GOC,
                  ngay: Optional[str] = None) -> str:
    """Ghi `workspace/kiem-phat-hanh/<ngày>.md`, trả về đường tệp đã ghi."""
    if phat_hien:
        tong = "CHẶN"
    elif not ket_qua_pytest.da_chay:
        tong = "CẢNH BÁO"
    elif ket_qua_pytest.ma_thoat not in (0, None):
        tong = "CHẶN"
    else:
        tong = "OK"

    dong = [
        "# Kiểm phát hành — {0}".format(time.strftime("%Y-%m-%d %H:%M")),
        "",
        "Kết luận: **{0}**".format(tong),
        "",
        "Cây sạch: `{0}` ({1} tệp, {2} tệp đang theo dõi Git).".format(
            cay.duong, len(cay.tep), len(cay.theo_doi)),
        "",
        "## Danh sách chặn ({0})".format(len(phat_hien)),
    ]
    if not phat_hien:
        dong.append("(không có)")
    else:
        theo_loai: Dict[str, List[PhatHien]] = {}
        for p in phat_hien:
            theo_loai.setdefault(p.loai, []).append(p)
        for loai in sorted(theo_loai):
            dong.append("")
            dong.append("### {0} ({1})".format(loai, len(theo_loai[loai])))
            for p in theo_loai[loai]:
                dong.append("- `{0}` — {1}".format(p.duong, p.ghi_chu))

    dong.append("")
    dong.append("## pytest trên cây sạch")
    if not ket_qua_pytest.da_chay:
        dong.append("Hoãn: {0}".format(ket_qua_pytest.ly_do_hoan or "(không rõ lý do)"))
    else:
        dong.append("Mã thoát: {0}".format(ket_qua_pytest.ma_thoat))
        if ket_qua_pytest.stdout:
            duoi_stdout = ket_qua_pytest.stdout.strip().splitlines()[-20:]
            dong.append("")
            dong.append("```")
            dong.extend(duoi_stdout)
            dong.append("```")

    duong = duong_bao_cao(goc, ngay=ngay)
    ghi_chu(duong, "\n".join(dong) + "\n")
    return duong


# ── main ─────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Kiểm phát hành v3.0: cây sạch -> quét bí mật/dữ liệu -> "
                    "(có điều kiện) pytest.")
    ap.add_argument("--goc", default=GOC, help="Gốc kho tool (mặc định: kho hiện tại).")
    ap.add_argument("--giu-cay-sach", action="store_true",
                     help="Không xoá cây sạch sau khi quét xong (để soi tay).")
    ap.add_argument("--bo-qua-pytest", action="store_true",
                     help="Không thử chạy pytest dù đủ điều kiện RAM/khoá.")
    ns = ap.parse_args(argv)

    def log(dong: str) -> None:
        print(dong)

    goc = os.path.abspath(ns.goc)
    print("=== Kiểm phát hành v3.0 — {0} ===".format(goc))

    don_cay_cu(log=log)

    print("--- Bước 1: xuất cây sạch ---")
    cay = xuat_cay_sach(goc, log=log)

    print("--- Bước 2: quét cây sạch ---")
    phat_hien = quet_cay_sach(cay)
    print("  {0} phát hiện.".format(len(phat_hien)))
    for p in phat_hien:
        print("  ! [{0}] {1} — {2}".format(p.loai, p.duong, p.ghi_chu))

    print("--- Bước 3: pytest trên cây sạch ---")
    if ns.bo_qua_pytest:
        ket_qua = KetQuaPytest(da_chay=False, ly_do_hoan="--bo-qua-pytest.")
        print("  hoãn: --bo-qua-pytest.")
    else:
        san_sang, ly_do = san_sang_chay_pytest(goc)
        if not san_sang:
            ket_qua = KetQuaPytest(da_chay=False, ly_do_hoan=ly_do)
            print("  hoãn: {0}".format(ly_do))
        else:
            ket_qua = chay_pytest_cay_sach(cay, log=log)
            print("  mã thoát: {0}".format(ket_qua.ma_thoat))

    duong_bc = viet_bao_cao(cay, phat_hien, ket_qua, goc=goc)
    print("--- Báo cáo: {0} ---".format(duong_bc))

    if not ns.giu_cay_sach:
        shutil.rmtree(cay.duong, ignore_errors=True)
    else:
        print("  cây sạch giữ lại: {0}".format(cay.duong))

    return 1 if phat_hien or (ket_qua.da_chay and ket_qua.ma_thoat) else 0


if __name__ == "__main__":
    sys.exit(main())
