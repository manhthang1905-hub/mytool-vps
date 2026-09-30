"""core/ban_quyen_windows.py — Windows còn bao nhiêu ngày trước khi hết hạn
đánh giá (Evaluation), và còn bao nhiêu lượt `rearm` (kích hoạt lại) — Việc V5,
`workspace/KE-HOACH-GIA-CO-1-NAM.md` (duyệt 26/09/2026):

    "Windows Evaluation hết hạn 24/03/2027, còn 2 lượt rearm; chỉ cảnh báo SAU
    khi máy đã bị tắt." — kiểm toán 26/09.

═══ CHỈ ĐỌC BẰNG `cscript`, TUYỆT ĐỐI KHÔNG `wscript` ═══

`slmgr.vbs` là một kịch bản VBScript — chạy nó qua trình biên dịch kịch bản
MẶC ĐỊNH của Windows (thường là `wscript.exe`, có cửa sổ) sẽ BẬT HỘP THOẠI lên
màn hình. Máy này đang đăng video thật (PyAutoGUI dò icon trên màn hình thấy
được) — một hộp thoại bất ngờ giữa lúc máy đăng có thể che icon, làm bấm nhầm.
Đây không phải lý thuyết: kiểm toán 26/09 đã từng thấy việc y hệt (`selfheal.ps1`
ép độ phân giải) làm màn hình lệch giữa lúc PyAutoGUI đang dò.

Nên MỌI lệnh ở đây đều gọi qua `cscript //nologo <slmgr.vbs> <cờ>` — `cscript`
là trình biên dịch dòng lệnh (không cửa sổ), `//nologo` bỏ luôn dòng banner.
KHÔNG BAO GIỜ gọi `slmgr.vbs` trần (Windows sẽ tự chọn trình biên dịch mặc định
của máy, có thể là `wscript`) và KHÔNG BAO GIỜ gọi `wscript` trực tiếp.

═══ HAI LỆNH DUY NHẤT ═══

* `/xpr` — "expiration": một câu cho biết bao giờ hết hạn (hoặc "kích hoạt
  vĩnh viễn"). Dùng để HIỂN THỊ ngày hết hạn cho người đọc.
* `/dlv` — "detailed license view": nhiều dòng, trong đó có
  `Timebased activation expiration: <N> minute(s) (<M> day(s))` — SỐ NGÀY còn
  lại tính sẵn, không phải tự trừ ngày-tháng (tránh sai múi giờ/định dạng ngày
  Anh-Mỹ M/D/YYYY lẫn với Việt DD/MM/YYYY) — và
  `Remaining Windows rearm count: <N>` — số lượt kích hoạt lại còn dùng được.
  `phan_tich_dlv` dùng con số NGÀY của `/dlv` làm nguồn chính; ngày hết hạn của
  `/xpr` chỉ để HIỂN THỊ (best-effort, không dùng để tính cảnh báo).

═══ TIẾNG ANH LẪN TIẾNG VIỆT ═══

VPS thuê ngoài thường cài Windows tiếng Anh, nhưng máy chủ dự án hoặc VPS khác
có thể ở tiếng Việt. `phan_tich_xpr`/`phan_tich_dlv` thử khớp câu tiếng Anh
trước (`"permanently activated"`, `"Remaining Windows rearm count"`), không
khớp thì thử bản đã bỏ dấu tiếng Việt (cùng cách `core.lich_tu_chay._bo_dau`
xử lý câu lỗi `schtasks` dịch theo ngôn ngữ hệ thống).

═══ `nen_rearm`: CHỈ KHUYẾN NGHỊ, KHÔNG TỰ LÀM GÌ ═══

Kế hoạch gốc (V5) có ý "còn ≤10 ngày và rearm>0 thì TỰ rearm + restart vào
khung an toàn". Bản này CHƯA làm phần tự hành động — chỉ trả về khuyến nghị và
điều kiện khung an toàn (gọi `core.an_toan_khoi_dong.kiem_tra`, đã có sẵn từ
trước, KHÔNG viết lại logic khung giờ). Tự rearm + khởi động lại là việc CÓ RỦI
RO (rearm dùng hết là hết, không hoàn lại) nên để dành làm sau, có xác nhận của
chủ dự án — xem `GHI-CHU.md` mục "CÁCH NỐI SAU".

═══ Hết rearm → việc người ═══

`rearm_con_lai == 0` thì `nen_rearm` luôn trả `de_xuat=False` — không còn gì để
khuyến nghị, đây là lúc chủ dự án phải tự mua license/gia hạn (xem bảng "Việc
con người không tránh được" trong kế hoạch gia cố). Việc BÁO chuyện này (qua
`core.bao_dong.bao_dong_khan`) là việc của nơi gọi (`gac_tong.py`), không phải
của module này — module này chỉ ĐỌC và ĐÁNH GIÁ.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
import sys
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import an_toan_khoi_dong

__all__ = [
    "MUC_BINH_THUONG", "MUC_NHAC_30", "MUC_NHAC_14", "MUC_KHAN_7", "MUC_KHONG_RO",
    "doc_xpr", "doc_dlv", "phan_tich_xpr", "phan_tich_dlv", "doc_giay_phep",
    "danh_gia", "nen_rearm", "thuc_hien_rearm",
]

#: `[lệnh...] -> (mã thoát, chữ in ra gộp stdout+stderr)` — cùng khuôn seam với
#: `core.lich_tu_chay.ChayLenh`, để bài kiểm không gọi `cscript` thật.
ChayLenh = Callable[[List[str]], Tuple[int, str]]

MUC_KHONG_RO = "khong_ro"
MUC_BINH_THUONG = "binh_thuong"
MUC_NHAC_30 = "nhac_30"
MUC_NHAC_14 = "nhac_14"
MUC_KHAN_7 = "khan_7"

#: Ngưỡng đề xuất `nen_rearm` — ≤10 ngày (kế hoạch V5 nói rõ "≤10 ngày").
_NGUONG_REARM_NGAY = 10


def _chay_lenh_mac_dinh(lenh: List[str]) -> Tuple[int, str]:
    """Gọi một lệnh hệ thống THẬT — cùng khuôn `core.lich_tu_chay._chay_lenh_mac_dinh`."""
    try:
        ra = subprocess.run(
            lenh, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as loi:
        return 1, str(loi)
    return ra.returncode, (ra.stdout or "") + (ra.stderr or "")


def _duong_slmgr() -> str:
    """`%windir%\\system32\\slmgr.vbs` — đọc biến môi trường, không hard-code ổ đĩa."""
    windir = os.environ.get("windir") or os.environ.get("SystemRoot") or r"C:\Windows"
    return os.path.join(windir, "system32", "slmgr.vbs")


def doc_xpr(*, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> str:
    """`cscript //nologo <slmgr.vbs> /xpr` — câu hết hạn/kích hoạt vĩnh viễn."""
    _, ra = chay_lenh(["cscript", "//nologo", _duong_slmgr(), "/xpr"])
    return ra


def doc_dlv(*, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> str:
    """`cscript //nologo <slmgr.vbs> /dlv` — chi tiết, có số ngày còn lại + rearm."""
    _, ra = chay_lenh(["cscript", "//nologo", _duong_slmgr(), "/dlv"])
    return ra


def _bo_dau(chu: str) -> str:
    """Chữ thường, bỏ dấu — cùng cách `core.lich_tu_chay._bo_dau` so khớp thô
    câu tiếng Việt dù bảng mã/định dạng dịch có sai khác."""
    chu = unicodedata.normalize("NFKD", chu or "")
    return "".join(c for c in chu if not unicodedata.combining(c)).lower()


_RE_VINH_VIEN_EN = re.compile(r"permanently\s+activated", re.IGNORECASE)
#: Bỏ dấu: "được kích hoạt vĩnh viễn" → "duoc kich hoat vinh vien".
_RE_VINH_VIEN_VI = re.compile(r"kich\s*hoat\s*vinh\s*vien")

#: "Timebased activation will expire 3/24/2027 2:35:57 AM" — chỉ lấy phần ngày.
_RE_NGAY_HET_HAN_EN = re.compile(
    r"expire\s+(\d{1,2}/\d{1,2}/\d{4})", re.IGNORECASE)
#: ISO dự phòng, phòng khi bản dịch xuất `YYYY-MM-DD`.
_RE_NGAY_HET_HAN_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")


def phan_tich_xpr(text: str) -> Dict[str, Any]:
    """Kết quả `/xpr` → `{"vinh_vien": bool, "het_han": date|None, "raw": str}`.

    `het_han` chỉ để HIỂN THỊ (best-effort, thử cả hai thứ tự ngày/tháng) —
    số ngày dùng để CẢNH BÁO lấy từ `/dlv` (xem :func:`phan_tich_dlv`), không
    phải trừ ngày ở đây, vì `/xpr` không nói rõ M/D hay D/M.
    """
    text = text or ""
    vinh_vien = bool(_RE_VINH_VIEN_EN.search(text) or _RE_VINH_VIEN_VI.search(_bo_dau(text)))
    het_han: Optional[_dt.date] = None
    if not vinh_vien:
        m = _RE_NGAY_HET_HAN_EN.search(text)
        if m:
            phan = m.group(1).split("/")
            for dinh in ("%m/%d/%Y", "%d/%m/%Y"):
                try:
                    het_han = _dt.datetime.strptime(m.group(1), dinh).date()
                    break
                except ValueError:
                    continue
            del phan
        if het_han is None:
            m2 = _RE_NGAY_HET_HAN_ISO.search(text)
            if m2:
                try:
                    het_han = _dt.datetime.strptime(m2.group(1), "%Y-%m-%d").date()
                except ValueError:
                    het_han = None
    return {"vinh_vien": vinh_vien, "het_han": het_han, "raw": text}


#: "Timebased activation expiration: 252828 minute(s) (176 day(s))".
_RE_NGAY_CON_LAI_EN = re.compile(
    r"expiration:\s*[\d,]+\s*minute\(s\)\s*\(\s*([\d,]+)\s*day\(s\)\)", re.IGNORECASE)
#: Dự phòng tiếng Việt (bỏ dấu): tìm số đứng ngay trước "ngay" gần "con lai".
_RE_NGAY_CON_LAI_VI = re.compile(r"([\d,]+)\s*ngay\b")

#: "Remaining Windows rearm count: 2" — CHỈ lấy dòng "Windows rearm", không
#: lấy "SKU rearm count" (đếm khác nhau — xem docstring đầu module).
_RE_REARM_EN = re.compile(
    r"remaining\s+windows\s+rearm\s+count\s*:\s*(\d+)", re.IGNORECASE)
#: Dự phòng: bất kỳ dòng nào có "rearm" + số, khi câu không khớp mẫu chuẩn.
_RE_REARM_LONG = re.compile(r"rearm\s+count\s*:\s*(\d+)", re.IGNORECASE)


def phan_tich_dlv(text: str) -> Dict[str, Any]:
    """Kết quả `/dlv` → `{"so_ngay_con_lai": int|None, "rearm_con_lai": int|None,
    "vinh_vien": bool, "raw": str}`.

    `so_ngay_con_lai` là NGUỒN CHÍNH cho mọi cảnh báo — số Windows tự tính sẵn,
    không tự trừ ngày-tháng ở đây.
    """
    text = text or ""
    vinh_vien = bool(_RE_VINH_VIEN_EN.search(text) or _RE_VINH_VIEN_VI.search(_bo_dau(text)))

    so_ngay: Optional[int] = None
    if not vinh_vien:
        m = _RE_NGAY_CON_LAI_EN.search(text)
        if m:
            try:
                so_ngay = int(m.group(1).replace(",", ""))
            except ValueError:
                so_ngay = None
        if so_ngay is None:
            m2 = _RE_NGAY_CON_LAI_VI.search(_bo_dau(text))
            if m2:
                try:
                    so_ngay = int(m2.group(1).replace(",", ""))
                except ValueError:
                    so_ngay = None

    rearm: Optional[int] = None
    m3 = _RE_REARM_EN.search(text) or _RE_REARM_LONG.search(text)
    if m3:
        try:
            rearm = int(m3.group(1))
        except ValueError:
            rearm = None

    return {"so_ngay_con_lai": so_ngay, "rearm_con_lai": rearm,
            "vinh_vien": vinh_vien, "raw": text}


def doc_giay_phep(*, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Dict[str, Any]:
    """Gọi CẢ HAI lệnh, gộp thành một khối — điểm vào chính của module này.

    `{"vinh_vien": bool, "het_han": date|None, "so_ngay_con_lai": int|None,
    "rearm_con_lai": int|None, "raw_xpr": str, "raw_dlv": str}`.
    """
    xpr = phan_tich_xpr(doc_xpr(chay_lenh=chay_lenh))
    dlv = phan_tich_dlv(doc_dlv(chay_lenh=chay_lenh))
    return {
        "vinh_vien": bool(xpr["vinh_vien"] or dlv["vinh_vien"]),
        "het_han": xpr["het_han"],
        "so_ngay_con_lai": dlv["so_ngay_con_lai"],
        "rearm_con_lai": dlv["rearm_con_lai"],
        "raw_xpr": xpr["raw"],
        "raw_dlv": dlv["raw"],
    }


def danh_gia(thong_tin: Dict[str, Any]) -> Dict[str, Any]:
    """`thong_tin` (từ :func:`doc_giay_phep`) → mức báo 30/14/7 ngày.

    `{"muc": ..., "so_ngay_con_lai": int|None}`. Kích hoạt vĩnh viễn hoặc
    không đọc được số ngày → :data:`MUC_BINH_THUONG`/:data:`MUC_KHONG_RO` —
    KHÔNG đoán bừa để tránh báo giả khi `slmgr` đổi định dạng câu.
    """
    if thong_tin.get("vinh_vien"):
        return {"muc": MUC_BINH_THUONG, "so_ngay_con_lai": None}
    so_ngay = thong_tin.get("so_ngay_con_lai")
    if so_ngay is None:
        return {"muc": MUC_KHONG_RO, "so_ngay_con_lai": None}
    if so_ngay <= 7:
        muc = MUC_KHAN_7
    elif so_ngay <= 14:
        muc = MUC_NHAC_14
    elif so_ngay <= 30:
        muc = MUC_NHAC_30
    else:
        muc = MUC_BINH_THUONG
    return {"muc": muc, "so_ngay_con_lai": so_ngay}


def thuc_hien_rearm(*, chay_lenh: ChayLenh = _chay_lenh_mac_dinh) -> Tuple[bool, str]:
    """`cscript //nologo <slmgr.vbs> /rearm` — LỆNH THẬT, dùng mất 1 lượt rearm; Windows
    chỉ áp dụng sau KHỞI ĐỘNG LẠI. Chỉ gọi từ `core.chot_an_toan` (kiểm 1 lần/ngày,
    có khoá chống rearm lặp). Trả `(thành công, chữ lệnh in ra)`."""
    ma, ra = chay_lenh(["cscript", "//nologo", _duong_slmgr(), "/rearm"])
    return ma == 0, ra


def nen_rearm(
    thong_tin: Dict[str, Any],
    goc: str,
    *,
    bay_gio: Optional[_dt.datetime] = None,
    viec_chay_tay: bool = False,
    con_song: Optional[Callable[[int], bool]] = None,
) -> Dict[str, Any]:
    """Có NÊN rearm bây giờ không — CHỈ TRẢ VỀ khuyến nghị, KHÔNG tự làm gì.

    Điều kiện đề xuất: còn ≤10 ngày (kế hoạch V5), rearm còn > 0, KHÔNG kích
    hoạt vĩnh viễn, VÀ đang trong khung an toàn để khởi động lại
    (`core.an_toan_khoi_dong.kiem_tra` — tái dùng nguyên logic năm điều kiện đã
    có, không viết lại). Hết rearm (`rearm_con_lai == 0`) luôn trả
    `de_xuat=False` — đó là lúc cần NGƯỜI xử lý (mua license/gia hạn), không
    còn gì máy tự làm được.

    Trả `{"de_xuat": bool, "trong_han": bool, "con_rearm": bool, "an_toan":
    {...} | None, "ghi_chu": str}`.
    """
    vinh_vien = bool(thong_tin.get("vinh_vien"))
    so_ngay = thong_tin.get("so_ngay_con_lai")
    rearm = thong_tin.get("rearm_con_lai")

    trong_han = (not vinh_vien) and so_ngay is not None and so_ngay <= _NGUONG_REARM_NGAY
    con_rearm = rearm is not None and rearm > 0

    an_toan: Optional[Dict[str, Any]] = None
    de_xuat = False
    if trong_han and con_rearm:
        # (`con_song` giữ trong chữ ký cho tương thích cũ; `kiem_tra` không nhận nó.)
        an_toan = an_toan_khoi_dong.kiem_tra(goc, bay_gio, viec_chay_tay=viec_chay_tay)
        de_xuat = bool(an_toan.get("duoc"))

    return {
        "de_xuat": de_xuat,
        "trong_han": trong_han,
        "con_rearm": con_rearm,
        "an_toan": an_toan,
        "ghi_chu": ("Chỉ là khuyến nghị — module này KHÔNG tự rearm, KHÔNG tự "
                    "khởi động lại. Việc rearm + restart thật để dành làm sau, "
                    "có xác nhận (xem GHI-CHU.md)."),
    }


# ── `python -m core.ban_quyen_windows`: đọc thật, chỉ in ra ─────────────────


def _main(argv: Optional[List[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    thong_tin = doc_giay_phep()
    dg = danh_gia(thong_tin)

    print("═══ Bản quyền Windows (chỉ đọc, cscript //nologo slmgr.vbs) ═══")
    if thong_tin["vinh_vien"]:
        print("Kích hoạt: VĨNH VIỄN.")
    else:
        het_han = thong_tin.get("het_han")
        print("Ngày hết hạn (hiển thị): {0}".format(
            het_han.isoformat() if het_han else "(không đọc được ngày)"))
        print("Số ngày còn lại (theo slmgr /dlv): {0}".format(
            thong_tin.get("so_ngay_con_lai")
            if thong_tin.get("so_ngay_con_lai") is not None else "(không đọc được)"))
    print("Số lượt rearm còn lại: {0}".format(
        thong_tin.get("rearm_con_lai")
        if thong_tin.get("rearm_con_lai") is not None else "(không đọc được)"))
    print("Mức báo: {0}".format(dg["muc"]))

    nr = nen_rearm(thong_tin, goc)
    print("Đề xuất rearm ngay bây giờ: {0}".format("CÓ" if nr["de_xuat"] else "không"))
    if nr["trong_han"] and nr["con_rearm"] and not nr["de_xuat"] and nr["an_toan"]:
        print("  (chưa tới lúc an toàn để khởi động lại: {0})".format(
            "; ".join(nr["an_toan"].get("ly_do") or [])))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
