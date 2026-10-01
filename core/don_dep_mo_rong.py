"""Dọn dẹp MỞ RỘNG — phần đĩa mà `core/don_dep.py` không đụng tới.

═══ CHIA VIỆC VỚI `core/don_dep.py` ═══

`don_dep.py` đã lo phần NẶNG NHẤT: ảnh cảnh/clip/video của một LƯỢT sản xuất,
sau khi lượt đó ĐÃ ĐĂNG (quá hạn ân xá) hoặc đã ra ngoài `giu_toi_da_luot` lượt
mới nhất. Đó là nguồn phình lớn nhất (đo 24/09/2026: một lượt tới 2,4 GB).

Tệp này lo phần CÒN LẠI mà chủ dự án nêu 26/09/2026 — *"máy càng ngày càng
nặng"* — không phải vì một lượt to, mà vì rất nhiều tệp NHỎ cộng dồn qua nhiều
tháng chạy 24/7:

1. **Báo cáo ngày CŨ** — `workspace/tu-chay/<ngày>.{md,json}` (sổ chung cả
   máy) và `CHANNEL/<kênh>/tu-chay/<ngày>.json` (sổ riêng từng kênh). Một tệp
   nhỏ, nhưng MỘT TỆP MỖI NGÀY, MÃI MÃI — không ai đọc lại báo cáo của sáu
   tháng trước.
2. **Nhật ký dọn dẹp** (`CHANNEL/<kênh>/tu-chay/don-dep.log`) — nối thêm
   (append) vô hạn, không tự xoay vòng như `tu-chay.log`
   (`core.tu_chay._ghi_dong_log`) hay `su-co.log`/`tien-trinh.log`
   (`core/hung_su_co.py`, `core/nhat_ky_tien_trinh.py`) đã có.

Hai thứ dưới đây CỐ Ý KHÔNG nằm ở đây, đã có nơi lo:

* **Ảnh bằng chứng lỗi** (`vm/logs/anh-loi/`) — `vm/may_dang.py._don_bot_anh_loi`
  đã tự giữ tối đa 200 ảnh mới nhất. Không đụng `vm/` từ tệp này (luật VPS:
  sửa `vm/` phải qua bản vá riêng, không sửa thẳng).
* **File trung gian của một lượt đã đăng** (`5-anh/`, `6-clip/`, `2-doan/`…) —
  đã là việc của `core/don_dep.py` (`don_sau_gio`, tính theo GIỜ chứ không
  phải "N ngày", nhưng cùng một ý). Không viết lại một luật thứ hai cho cùng
  một việc.

═══ BỐN THỨ KHÔNG BAO GIỜ ĐỤNG (giống nguyên tắc của `don_dep.py`) ═══

Kịch bản, kết quả cuối (`8-video.mp4` hay bản trong `thu_muc_done`), file
trạng thái (`trang-thai.json`, `.khoa`), và `chi-so/` — bốn thứ này không bao
giờ nằm trong bất kỳ danh sách ứng viên nào ở đây. Cách chắc nhất để không xoá
nhầm không phải là "loại trừ" mà là **CHỈ NHẬN đúng tên tệp mong đợi**
(`_la_bao_cao_ngay` bên dưới) — tệp nào không khớp khuôn tên thì bị bỏ qua,
kể cả khi nó nằm đúng thư mục.

═══ AN TOÀN — Y HỆT `don_dep.py`, KHÔNG NỚI LỎNG ═══

Mặc định mọi hàm là `thuc_hien=False` — chỉ TÍNH, không đụng đĩa. Cửa dọn
THẬT (`don_theo_cai_dat`) vẫn nằm SAU cờ `tu_don` của từng kênh trong
`kenh.yaml` — kênh chưa bật thì không đụng gì, giống hệt `don_dep.py`. Không
tự bật cờ nào ở đây.

Không mạng, không Qt.
"""

from __future__ import annotations

import datetime
import glob
import os
import re
import shutil
from typing import Any, Dict, List, Optional, Sequence

from . import ghi_dia
from .kenh import doc_kenh

__all__ = [
    "GIU_NGAY_BAO_CAO_MAC_DINH", "GIOI_HAN_LOG_KENH_BYTE", "NGUONG_DIA_CANH_BAO_GB",
    "ung_vien_bao_cao_tat_ca_cu", "ung_vien_bao_cao_kenh_cu",
    "don_bao_cao_cu", "don_theo_cai_dat", "don_tat_ca_theo_cai_dat",
    "suc_khoe_dia", "dinh_dang_suc_khoe_dia_md", "NGUONG_O_GB", "van_o",
]

#: Giữ báo cáo ngày trong ngần này ngày. Mặc định RỘNG RÃI (nửa năm) — mục
#: tiêu là chặn phình VÔ HẠN qua nhiều năm, không phải giành lại đĩa ngay tuần
#: này. Kênh nào muốn giữ ngắn/dài hơn thì khai `don_mo_rong_giu_ngay` trong
#: `kenh.yaml`; thiếu khoá đó thì dùng đúng số này.
GIU_NGAY_BAO_CAO_MAC_DINH = 180

#: `don-dep.log` xoay vòng khi vượt cỡ này — cùng cỡ `su-co.log`
#: (`core/hung_su_co.py`), nhỏ hơn `tu-chay.log` (5 MB) vì đây là log của MỘT
#: kênh chứ không phải cả máy.
GIOI_HAN_LOG_KENH_BYTE = 1 * 1024 * 1024

#: Đĩa còn dưới ngưỡng này (GB) thì khối "sức khoẻ đĩa" trong sổ ngày cảnh báo
#: đỏ. Bằng đúng ngưỡng dọn khẩn mặc định của `core/tu_chay.py`
#: (`NGUONG_DIA_KHAN_MAC_DINH` — xem tệp đó) để hai chỗ nói cùng một con số.
NGUONG_DIA_CANH_BAO_GB = 5.0

#: Tên hai tệp KHÔNG BAO GIỜ được tính là "báo cáo ngày cũ" dù nằm chung thư
#: mục `tu-chay/` — log xoay vòng riêng (`tu-chay.log`) và khoá đang giữ.
_TEN_KHONG_DUNG = ("tu-chay.log", "don-dep.log", ".khoa")

#: Khuôn tên một báo cáo ngày: `YYYY-MM-DD.md` hoặc `YYYY-MM-DD.json`. CHỈ
#: nhận đúng khuôn này — tệp nào tên lạ (kể cả do người tự đặt) thì bị BỎ QUA,
#: không đoán.
_MAU_TEN_NGAY = re.compile(r"^(\d{4}-\d{2}-\d{2})\.(md|json)$")


# ── Đọc tuổi báo cáo ─────────────────────────────────────────────────────────


def _ngay_tu_ten(ten: str) -> Optional[datetime.date]:
    """Ngày rút từ tên tệp, hoặc `None` nếu tên không đúng khuôn `_MAU_TEN_NGAY`."""
    kh = _MAU_TEN_NGAY.match(ten)
    if not kh:
        return None
    try:
        return datetime.date.fromisoformat(kh.group(1))
    except ValueError:
        return None


def _kich_thuoc(duong: str) -> int:
    try:
        return os.path.getsize(duong)
    except OSError:
        return 0


def _ung_vien_trong_thu_muc(thu_muc: str, *, giu_ngay: int,
                            hom_nay: datetime.date) -> List[Dict[str, Any]]:
    """Mọi tệp `<ngày>.md`/`<ngày>.json` trong `thu_muc` cũ hơn `giu_ngay` ngày.

    Chỉ đọc — không xoá. `giu_ngay <= 0` tắt hẳn (trả `[]`), giống quy ước
    `giu_toi_da_luot: 0` của `don_dep.py`.
    """
    if giu_ngay <= 0:
        return []
    han = datetime.timedelta(days=giu_ngay)
    ra: List[Dict[str, Any]] = []
    try:
        ten_tep = os.listdir(thu_muc)
    except OSError:
        return []
    for ten in sorted(ten_tep):
        if ten in _TEN_KHONG_DUNG:
            continue
        ngay = _ngay_tu_ten(ten)
        if ngay is None:
            continue  # tên lạ — không đoán, không đụng
        if hom_nay - ngay < han:
            continue  # còn trong hạn giữ
        duong = os.path.join(thu_muc, ten)
        if not os.path.isfile(duong):
            continue
        ra.append({"duong": duong, "ngay": ngay.isoformat(), "bytes": _kich_thuoc(duong)})
    return ra


def ung_vien_bao_cao_tat_ca_cu(goc: str, *, giu_ngay: int = GIU_NGAY_BAO_CAO_MAC_DINH,
                               bay_gio: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """Báo cáo ngày CŨ trong `workspace/tu-chay/` (sổ chung cả máy).

    Không đụng `tu-chay.log` (log xoay vòng riêng theo cỡ, xem
    `core.tu_chay._ghi_dong_log`).
    """
    thu_muc = os.path.join(goc, "workspace", "tu-chay")
    return _ung_vien_trong_thu_muc(
        thu_muc, giu_ngay=giu_ngay, hom_nay=bay_gio or datetime.date.today())


def ung_vien_bao_cao_kenh_cu(goc: str, ma_kenh: str, *,
                             giu_ngay: int = GIU_NGAY_BAO_CAO_MAC_DINH,
                             bay_gio: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
    """Báo cáo ngày CŨ của MỘT kênh (`CHANNEL/<kênh>/tu-chay/<ngày>.json`).

    Không đụng `don-dep.log` (nhật ký dọn, xoay riêng — xem `_xoay_log_kenh`)
    hay `.khoa` (khoá tự chạy đang giữ hoặc mới rớt lại).
    """
    thu_muc = os.path.join(goc, "CHANNEL", ma_kenh, "tu-chay")
    return _ung_vien_trong_thu_muc(
        thu_muc, giu_ngay=giu_ngay, hom_nay=bay_gio or datetime.date.today())


# ── Xoay nhật ký dọn dẹp của một kênh ────────────────────────────────────────


def _duong_log_don_dep(goc: str, ma_kenh: str) -> str:
    return os.path.join(goc, "CHANNEL", ma_kenh, "tu-chay", "don-dep.log")


def _xoay_log_kenh(goc: str, ma_kenh: str, *, thuc_hien: bool,
                   gioi_han_byte: int = GIOI_HAN_LOG_KENH_BYTE) -> Dict[str, Any]:
    """`don-dep.log` của một kênh, xoay vòng khi vượt `gioi_han_byte`.

    Cùng cách các log khác trong tool tự xoay (`tu-chay.log`, `su-co.log`,
    `tien-trinh.log`): đơn giản, không cắt dở dòng đang ghi. Giữ NGUYÊN một
    bản `.cu` — chủ dự án đọc lại nhật ký gần nhất vẫn còn, chỉ mất bản xa hơn.
    """
    duong = _duong_log_don_dep(goc, ma_kenh)
    so_byte = _kich_thuoc(duong)
    ra: Dict[str, Any] = {"duong": duong, "bytes": so_byte, "vuot_nguong": so_byte > gioi_han_byte}
    if so_byte <= gioi_han_byte or not thuc_hien:
        return ra
    try:
        duong_cu = duong + ".cu"
        if os.path.exists(duong_cu):
            os.remove(duong_cu)
        os.replace(duong, duong_cu)
        ra["da_xoay"] = True
    except OSError:
        ra["da_xoay"] = False
    return ra


# ── Xoá thật báo cáo ngày cũ ─────────────────────────────────────────────────


def _xoa_ung_vien(ds: Sequence[Dict[str, Any]]) -> List[str]:
    da_xoa: List[str] = []
    for u in ds:
        try:
            os.remove(u["duong"])
        except OSError:
            continue
        da_xoa.append(u["duong"])
    return da_xoa


def don_bao_cao_cu(goc: str, danh_sach_kenh: Sequence[str], *, thuc_hien: bool = False,
                   giu_ngay: int = GIU_NGAY_BAO_CAO_MAC_DINH,
                   bay_gio: Optional[datetime.date] = None) -> Dict[str, Any]:
    """Tính (và xoá thật nếu `thuc_hien=True`) báo cáo ngày cũ của CẢ MÁY
    (`workspace/tu-chay/`) cộng báo cáo ngày cũ của TỪNG kênh trong
    `danh_sach_kenh` (`CHANNEL/<kênh>/tu-chay/`).

    Không kiểm `tu_don` ở đây — hàm này THUẦN TÍNH TOÁN theo `giu_ngay` được
    truyền vào; nơi gọi (`don_theo_cai_dat`/`don_tat_ca_theo_cai_dat`) mới là
    chỗ đọc cờ `tu_don` của từng kênh, giống cách `core.don_dep.don` (thuần
    tính) tách khỏi `don_dep.don_theo_cai_dat` (đọc cờ).
    """
    hom_nay = bay_gio or datetime.date.today()
    tat_ca = ung_vien_bao_cao_tat_ca_cu(goc, giu_ngay=giu_ngay, bay_gio=hom_nay)
    theo_kenh: Dict[str, List[Dict[str, Any]]] = {}
    for ma in danh_sach_kenh:
        ds = ung_vien_bao_cao_kenh_cu(goc, ma, giu_ngay=giu_ngay, bay_gio=hom_nay)
        if ds:
            theo_kenh[ma] = ds

    ket_qua: Dict[str, Any] = {
        "tat_ca": tat_ca,
        "theo_kenh": theo_kenh,
        "tong_bytes": sum(u["bytes"] for u in tat_ca)
                     + sum(u["bytes"] for ds in theo_kenh.values() for u in ds),
        "thuc_hien": bool(thuc_hien),
    }
    if not thuc_hien:
        return ket_qua

    ket_qua["da_xoa_tat_ca"] = _xoa_ung_vien(tat_ca)
    ket_qua["da_xoa_theo_kenh"] = {ma: _xoa_ung_vien(ds) for ma, ds in theo_kenh.items()}
    return ket_qua


def don_theo_cai_dat(goc: str, ma_kenh: str, *,
                     bay_gio: Optional[datetime.date] = None) -> Dict[str, Any]:
    """Dọn MỞ RỘNG cho MỘT kênh — báo cáo ngày cũ của riêng kênh đó + xoay
    `don-dep.log` — NHƯNG chỉ khi kênh đã bật `tu_don: true` trong
    `kenh.yaml`. Cùng cửa, cùng cờ với `core.don_dep.don_theo_cai_dat`; không
    nới lỏng thêm điều kiện nào.

    Khoá `don_mo_rong_giu_ngay` (tuỳ chọn, `kenh.yaml`) đổi số ngày giữ báo
    cáo; thiếu khoá đó thì dùng `GIU_NGAY_BAO_CAO_MAC_DINH`.
    """
    kenh = doc_kenh(goc, ma_kenh)
    if not kenh.tu_don:
        return {"kenh": ma_kenh, "chay": False,
               "ly_do": "kênh chưa bật `tu_don` trong kenh.yaml — không đụng gì."}
    giu_ngay = int(getattr(kenh, "don_mo_rong_giu_ngay", None)
                  or GIU_NGAY_BAO_CAO_MAC_DINH)
    hom_nay = bay_gio or datetime.date.today()
    bao_cao = don_bao_cao_cu(goc, [], thuc_hien=True, giu_ngay=giu_ngay, bay_gio=hom_nay)
    # `[]`: báo cáo CHUNG CẢ MÁY do `don_tat_ca_theo_cai_dat` lo (chạy đúng một
    # lần, không lặp lại theo từng kênh) — ở đây chỉ phần RIÊNG của kênh này.
    rieng = don_bao_cao_cu(goc, [ma_kenh], thuc_hien=True, giu_ngay=giu_ngay, bay_gio=hom_nay)
    log_ket = _xoay_log_kenh(goc, ma_kenh, thuc_hien=True)
    return {"kenh": ma_kenh, "chay": True,
           "bao_cao_cu": rieng.get("theo_kenh", {}).get(ma_kenh, []),
           "tong_bytes": sum(u["bytes"] for u in rieng.get("theo_kenh", {}).get(ma_kenh, [])),
           "log_don_dep": log_ket}


def don_tat_ca_theo_cai_dat(goc: str, danh_sach_kenh: Sequence[str], *,
                            bay_gio: Optional[datetime.date] = None) -> Dict[str, Any]:
    """Gọi cho MỖI kênh (`don_theo_cai_dat`, tự đọc `tu_don` từng kênh) rồi
    dọn thêm báo cáo ngày cũ CHUNG CẢ MÁY (`workspace/tu-chay/`) — đúng MỘT
    lần cho cả lượt `--tat-ca`, không lặp theo từng kênh.

    Báo cáo chung chỉ dọn khi có ÍT NHẤT MỘT kênh trong `danh_sach_kenh` đã
    bật `tu_don` — sổ chung không thuộc riêng kênh nào để hỏi cờ của nó, nên
    mượn đúng luật "đã có kênh nào đồng ý dọn tự động chưa" thay vì tự ý dọn
    một thư mục không có cờ riêng.
    """
    hom_nay = bay_gio or datetime.date.today()
    theo_kenh: Dict[str, Any] = {}
    co_kenh_bat_tu_don = False
    for ma in danh_sach_kenh:
        try:
            ket = don_theo_cai_dat(goc, ma, bay_gio=hom_nay)
        except Exception as loi:  # noqa: BLE001 — một kênh hỏng không chặn kênh khác
            theo_kenh[ma] = {"kenh": ma, "chay": False, "ly_do": "lỗi: {0}".format(loi)}
            continue
        theo_kenh[ma] = ket
        if ket.get("chay"):
            co_kenh_bat_tu_don = True

    bao_cao_chung: Dict[str, Any] = {"chay": False,
                                     "ly_do": "chưa kênh nào bật `tu_don` — không đụng workspace/tu-chay/."}
    if co_kenh_bat_tu_don:
        ds = ung_vien_bao_cao_tat_ca_cu(goc, bay_gio=hom_nay)
        da_xoa = _xoa_ung_vien(ds)
        bao_cao_chung = {"chay": True, "ung_vien": ds, "da_xoa": da_xoa,
                         "tong_bytes": sum(u["bytes"] for u in ds)}

    tong_bytes = int(bao_cao_chung.get("tong_bytes") or 0) + sum(
        int((k.get("tong_bytes") or 0)) for k in theo_kenh.values())
    return {"theo_kenh": theo_kenh, "bao_cao_chung": bao_cao_chung, "tong_bytes": tong_bytes}


# ── Sức khoẻ đĩa — đo, không xoá ─────────────────────────────────────────────


def _kich_thuoc_thu_muc(duong: str) -> int:
    if not os.path.isdir(duong):
        return 0
    tong = 0
    for cha, _thu, tep in os.walk(duong):
        for t in tep:
            try:
                tong += os.path.getsize(os.path.join(cha, t))
            except OSError:
                pass
    return tong


def suc_khoe_dia(goc: str, danh_sach_kenh: Sequence[str], *,
                 nguong_canh_bao_gb: float = NGUONG_DIA_CANH_BAO_GB) -> Dict[str, Any]:
    """Đo (KHÔNG xoá) dung lượng từng vùng hay phình + đĩa còn trống.

    Vùng đo: `PROJECTS/AUTO/<kênh>` và `thu_muc_done` của từng kênh,
    `CHANNEL/<kênh>/chi-so/`, `workspace/`, `models/` — toàn bộ CHỈ ĐỌC, dùng
    cho khối "Sức khoẻ đĩa" trong sổ ngày (`dinh_dang_suc_khoe_dia_md`) và cho
    `--thu` ở dòng lệnh. Không đo thư mục trình duyệt (`../TLx-T7/App/`) — nằm
    NGOÀI `goc` và luật cứng của phiên vá 26/09/2026 cấm đụng tới, kể cả đo
    trong lúc tool đang chạy thật (đường ấy có thể trỏ vào một Chrome đang mở).
    """
    theo_kenh: Dict[str, Dict[str, int]] = {}
    for ma in danh_sach_kenh:
        try:
            kenh = doc_kenh(goc, ma)
        except Exception:  # noqa: BLE001 — một kênh đọc hỏng không chặn kênh khác
            continue
        muc: Dict[str, int] = {
            "projects_auto": _kich_thuoc_thu_muc(os.path.join(goc, "PROJECTS", "AUTO", ma)),
            "chi_so": _kich_thuoc_thu_muc(os.path.join(goc, "CHANNEL", ma, "chi-so")),
        }
        thu_muc_done = (kenh.thu_muc_done or "").strip()
        if thu_muc_done:
            muc["done"] = _kich_thuoc_thu_muc(thu_muc_done)
        theo_kenh[ma] = muc

    workspace_bytes = _kich_thuoc_thu_muc(os.path.join(goc, "workspace"))
    models_bytes = _kich_thuoc_thu_muc(os.path.join(goc, "models"))

    try:
        tong, dung, con = shutil.disk_usage(goc)
    except OSError:
        tong = dung = con = None

    return {
        "theo_kenh": theo_kenh,
        "workspace_bytes": workspace_bytes,
        "models_bytes": models_bytes,
        "dia_tong_gb": (tong / 1024 ** 3) if tong is not None else None,
        "dia_dung_gb": (dung / 1024 ** 3) if dung is not None else None,
        "dia_con_trong_gb": (con / 1024 ** 3) if con is not None else None,
        "canh_bao_dia": con is not None and (con / 1024 ** 3) < nguong_canh_bao_gb,
        "nguong_canh_bao_gb": nguong_canh_bao_gb,
    }


def _gb(so_byte: int) -> str:
    return "{0:.2f} GB".format(so_byte / 1024 ** 3)


def dinh_dang_suc_khoe_dia_md(sk: Dict[str, Any]) -> str:
    """Khối markdown "Sức khoẻ đĩa" — chèn vào sổ ngày (`_dung_md_tat_ca`)."""
    dong = ["### Sức khoẻ đĩa", ""]
    con_gb = sk.get("dia_con_trong_gb")
    if con_gb is not None:
        dong.append("- Còn trống: {0:.1f} GB / {1:.1f} GB tổng".format(
            con_gb, sk.get("dia_tong_gb") or 0.0))
        if sk.get("canh_bao_dia"):
            dong.append("  - ⚠ CẢNH BÁO: dưới ngưỡng an toàn {0:.1f} GB.".format(
                sk.get("nguong_canh_bao_gb") or NGUONG_DIA_CANH_BAO_GB))
    else:
        dong.append("- Không đo được dung lượng đĩa trống.")
    for ma, muc in (sk.get("theo_kenh") or {}).items():
        phan = []
        if muc.get("projects_auto"):
            phan.append("PROJECTS {0}".format(_gb(muc["projects_auto"])))
        if muc.get("done"):
            phan.append("DONE {0}".format(_gb(muc["done"])))
        if muc.get("chi_so"):
            phan.append("chi-so {0}".format(_gb(muc["chi_so"])))
        if phan:
            dong.append("- {0}: {1}".format(ma, " · ".join(phan)))
    if sk.get("workspace_bytes"):
        dong.append("- workspace/: {0}".format(_gb(sk["workspace_bytes"])))
    if sk.get("models_bytes"):
        dong.append("- models/: {0}".format(_gb(sk["models_bytes"])))
    dong.append("")
    return "\n".join(dong)


# ── Van ổ đĩa (01/10/2026) — một ngưỡng ─────────────────────────────────────

#: Ổ còn dưới ngần này GB: không mở lượt sản xuất MỚI (lượt dở làm nốt), báo ở
#: "Việc của bạn"; đủ chỗ lại thì nhịp điều phối kế tự mở lại.
NGUONG_O_GB = 10.0


def van_o(goc: str, con_trong_gb: Optional[float] = None) -> Dict[str, Any]:
    """`{"duoc_mo_moi", "con_gb", "ly_do"}`. Không đo được ổ → không chặn ở đây."""
    if con_trong_gb is None:
        try:
            con_trong_gb = shutil.disk_usage(goc)[2] / 1024 ** 3
        except OSError:
            return {"duoc_mo_moi": True, "con_gb": None, "ly_do": ""}
    if con_trong_gb >= NGUONG_O_GB:
        return {"duoc_mo_moi": True, "con_gb": con_trong_gb, "ly_do": ""}
    return {"duoc_mo_moi": False, "con_gb": con_trong_gb,
            "ly_do": "ổ đĩa còn {0:.1f} GB < {1:g} GB — không mở video mới; máy tự chạy lại khi "
                     "ổ đủ chỗ.".format(con_trong_gb, NGUONG_O_GB)}


# ── Dòng lệnh: `python -m core.don_dep_mo_rong --goc . --thu` ───────────────


def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    from .kenh import liet_ke_kenh

    ap = argparse.ArgumentParser(
        description="Dọn dẹp mở rộng (báo cáo ngày cũ, log dọn dẹp) — mặc định chỉ TÍNH.")
    ap.add_argument("--goc", default=os.getcwd(), help="Thư mục gốc MyTool (mặc định thư mục hiện tại).")
    ap.add_argument("--thu", action="store_true",
                    help="Chỉ liệt kê sẽ xoá gì + tổng GB giải phóng — KHÔNG xoá (mặc định của lệnh này).")
    ap.add_argument("--thuc-hien", action="store_true",
                    help="Xoá THẬT — chỉ dùng khi chủ dự án chủ động chạy tay, KHÔNG dùng trong lịch tự động.")
    gia = ap.parse_args(argv)

    goc = os.path.abspath(gia.goc)
    danh_sach = liet_ke_kenh(goc)
    thuc_hien = bool(gia.thuc_hien) and not gia.thu

    sk = suc_khoe_dia(goc, danh_sach)
    print(dinh_dang_suc_khoe_dia_md(sk))

    bao_cao = don_bao_cao_cu(goc, danh_sach, thuc_hien=thuc_hien)
    print("Báo cáo ngày cũ hơn {0} ngày:".format(GIU_NGAY_BAO_CAO_MAC_DINH))
    print("  workspace/tu-chay/: {0} tệp, {1}".format(
        len(bao_cao["tat_ca"]), _gb(sum(u["bytes"] for u in bao_cao["tat_ca"]))))
    for ma, ds in bao_cao["theo_kenh"].items():
        print("  CHANNEL/{0}/tu-chay/: {1} tệp, {2}".format(ma, len(ds), _gb(sum(u["bytes"] for u in ds))))
    print("Tổng ước giải phóng: {0}".format(_gb(bao_cao["tong_bytes"])))
    if thuc_hien:
        print("ĐÃ XOÁ THẬT (chạy với --thuc-hien).")
    else:
        print("CHỈ TÍNH — không xoá gì (bỏ --thu hoặc thêm --thuc-hien để xoá thật).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
