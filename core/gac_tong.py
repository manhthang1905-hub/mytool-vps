"""core/gac_tong.py — "Người gác tổng": đọc đĩa, KHÔNG đụng gì, rồi nói xem có
sự cố nào cần người xử lý — Việc V3 (+ nền cho V4/V6/V9), `workspace/
KE-HOACH-GIA-CO-1-NAM.md` (duyệt 26/09/2026):

    "V3 Người gác tổng: core/gac_tong.py mới + lịch ShopAPI-GacTong 15 phút
    chạy bằng Administrator (KHÔNG SYSTEM — cần DPAPI/màn hình/Chrome). Kiểm:
    gói chờ+tu_dang tắt >24h; số giờ không có video mới/kênh; Last Result của
    TuChay/CanhTram; tuổi .khoa-may; đĩa <15GB; van RAM chặn >3h."

═══ ĐÓNG BĂNG 29/09 → 30/09: CHỈ MODULE MỚI, KHÔNG NỐI VÀO LUỒNG SỐNG ═══

Bản này CHƯA đăng ký lịch Windows (`ShopAPI-GacTong`) và CHƯA được `tu_chay.py`
hay bất kỳ vòng sống nào gọi tới — đúng yêu cầu đóng băng tới sáng 30/09 (đêm
29/09 là lần đầu vòng tự chạy thật chạy thật, không được đụng
`core/tu_chay.py` và bạn bè). Cách nối vào sau: xem `GHI-CHU.md` mục "CÁCH NỐI
SAU" trong bản vá `workspace/ban-va/2026-09-29-dot3-tin-cay/`.

═══ BA LỚP, TÁCH RÕ ĐỂ TEST ĐƯỢC MÀ KHÔNG ĐỤNG ĐĨA THẬT ═══

1. :func:`chup_trang_thai` — LỚP DUY NHẤT chạm đĩa/hệ thống (đọc file JSON,
   CSV, `schtasks` qua `core.lich_tu_chay` — seam `chay_lenh` mock được, và một
   lượt dò cổng cục bộ — seam `kiem_cong` mock được). Trả về một "ảnh chụp"
   thuần dict. KHÔNG GHI gì, KHÔNG gọi mạng ra ngoài máy.
2. :func:`kiem_su_co` — hàm THUẦN, nhận ảnh chụp, trả danh sách sự cố. Test
   được bằng ảnh chụp dựng tay, không cần tmp_path nào cả.
3. :func:`bao_cao_su_co` / :func:`ban_tin_ngay` — lớp GHI (jsonl + tinh-trang.json)
   và lớp GỌI `core.bao_dong` — đây mới là chỗ có thể sinh tác dụng phụ, và cả
   hai đều nhận seam (`gui`, hoặc gọi thẳng `core.bao_dong.bao_dong_khan` mặc
   định — chính `bao_dong` đã tự nuốt lỗi mạng và tự tắt khi chưa cấu hình, xem
   docstring module đó).

═══ CHUẨN 4 TRẠNG THÁI — BEST-EFFORT, CHƯA CÓ NGUỒN CHUẨN ═══

Kế hoạch gốc định nghĩa 4 trạng thái ĐANG CHẠY / TỰ CHỜ CÓ HẠN / CHỜ NGƯỜI /
XONG do `core/tu_chay.py` tự ghi ra (việc V2, dự kiến sửa quanh dòng ~980-983,
~1462, ~1472 của tệp đó). Kiểm tra ngày 29/09/2026 cho thấy **V2 CHƯA làm** —
không có trường `trang_thai` nào trong sổ ngày, chỉ có `runs[].ok` (bool) và
`runs[].cho_nguoi` (bool). `xep_trang_thai_kenh` ở đây tự SUY ra 4 trạng thái
từ hai cờ đó — best-effort, KHÔNG PHẢI nguồn chuẩn. Khi V2 làm xong (ghi thẳng
`trang_thai` vào sổ ngày), hàm này nên đọc thẳng trường đó thay vì suy diễn —
ghi rõ trong `GHI-CHU.md`.

═══ NGUỒN DỮ LIỆU ĐÃ DÒ (29/09/2026), KHÔNG ĐOÁN BỪA ═══

* `CHANNEL/<k>/tu-chay/<ngày>.json`: `{"ngay","kenh","runs":[...],"nhat_ky":[...]}`
  — đọc qua đường dẫn công khai `core.tu_chay.duong_bao_cao_ngay` (không đụng
  hàm `_doc_bao_cao_ngay` riêng, tự đọc lấy cho gọn).
* `CHANNEL/<k>/ke-hoach-dang/ke-hoach.csv`: đọc qua `core.ke_hoach_dang.doc_bang`
  (công khai) rồi phân loại từng dòng bằng `core.trung_tam.phan_loai_dong_ke_hoach`
  (công khai) — `"da_dang"|"cho_duyet"|"sap_dang"|"bo"|"khac"`.
* `vm/trang-thai.json`: đọc qua `core.trung_tam._trang_thai_vm` — hàm RIÊNG
  không có bản công khai tương đương, tái dùng y hệt cách `core.an_toan_khoi_dong`
  đã làm trước đây (xem `# noqa: SLF001` ở đó).
* `vm/logs/kiem-dom/<ma>.json`: đọc qua `core.bang_dieu_khien.doc_kiem_dom`
  (công khai) — chỉ để mang vào ảnh chụp cho Bảng điều khiển sau này đọc,
  KHÔNG tự sinh sự cố từ đây ở bản này (ngoài phạm vi 7 kiểm được giao).
* `vm/logs/so-video-id.json`: khoá `"<kênh>/<mã gói>"`, trường `video_id`,
  `lan_tai_moi` (số lần tải lại CÙNG NGÀY — tăng dần mỗi lần Studio báo lỗi
  buộc thử lại, xem `vm/may_dang_dom.py:813-818`), `ngay_tai`, `id_cu[]`.
* `.khoa-may` (`workspace/tu-chay/.khoa-may`): `{"pid","bat_dau"}`, giành lại
  cứng sau `core.tu_chay.KHOA_CU_QUA_GIAY` (12 giờ) — `gac_tong` CẢNH BÁO SỚM
  HƠN mốc đó (`NGUONG_CANH_BAO_KHOA_GIAY`, 6 giờ) vì tới lúc bị giành thì đã là
  chuyện đã rồi.
* Đĩa trống: `shutil.disk_usage(goc)` thẳng — không qua `core.trung_tam._o_dia`
  (chỉ vài dòng, tự làm cho khỏi thêm một `# noqa`).
* Cổng 8765 (trạm)/8767 (khoá một-mình của agent, `vm/agent.py:2439`): dò bằng
  một lượt `socket.create_connection` cục bộ (127.0.0.1), seam `kiem_cong` để
  test không chạm socket thật. 8767 CHỈ mang tính THÔNG TIN ở bản này — nó chỉ
  có người nghe trong ~60 phút quanh giờ đăng của từng kênh (chế độ phiên,
  xem `CLAUDE.local.md`), nên cổng đó "im" phần lớn thời gian trong ngày là
  BÌNH THƯỜNG, không tự sinh sự cố. Đo agent sống/chết đúng nghĩa là việc V6
  (`giam_sat_vm` thêm nhịp tim) — NGOÀI PHẠM VI đóng băng của bản vá này
  (`vm/*.py`, `core/giam_sat_vm.py` đều bị khoá).
* Last Result của `ShopAPI-TuChay`/`ShopAPI-CanhTram`: `core.lich_tu_chay.trang_thai`/
  `trang_thai_canh_tram` (công khai, seam `chay_lenh` sẵn có — không viết lại).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
import socket
import sys
from typing import Any, Callable, Dict, List, Optional

from . import auto
from . import bang_dieu_khien
from . import bao_dong
from . import ben_bi
from . import chi_phi
from . import don_dep_mo_rong
from . import khe
from . import ke_hoach_dang
from . import kenh as kenh_mod
from . import lich_tu_chay
from . import tien_trinh_con
from . import trung_tam as tt
from . import tu_chay
from . import vm_cai_dat
from .trung_tam import phan_loai_dong_ke_hoach
from .tu_chay import _pid_con_song  # noqa: SLF001 — không có bản công khai, xem docstring đầu tệp

__all__ = [
    "TRANG_THAI_DANG_CHAY", "TRANG_THAI_TU_CHO", "TRANG_THAI_CHO_NGUOI", "TRANG_THAI_XONG",
    "NGUONG_KHONG_VIDEO_MOI_GIO", "NGUONG_HEN_LICH_GIO", "NGUONG_TAI_LEN_LAP_LAI",
    "NGUONG_CANH_BAO_KHOA_GIAY", "NGUONG_DIA_GB", "NGUONG_STUDIO_CU_GIO",
    "NGUONG_KHAU_DUNG_PHUT", "NGUONG_CHO_KHE_PHUT", "NGUONG_RAM_TRONG_GB",
    "NGUONG_LOI_LAP_KHAU", "NGUONG_TU_DUNG_KHAU_PHUT", "NGUONG_VI_SO_NGAY",
    "NGUONG_CPU_GIAY_DUNG_YEN",
    "duong_tinh_trang", "duong_nhat_ky_ngay", "duong_loi_chay_max",
    "chup_trang_thai", "kiem_su_co", "xep_trang_thai_kenh",
    "bao_cao_su_co", "ban_tin_ngay", "tu_sua",
]

# ── Ngưỡng — hằng số MODULE-LEVEL để một bản vá sau chỉ cần đổi một chỗ ─────

#: "N giờ không có video mới" — kế hoạch V3 không chốt số cụ thể, chọn 48 giờ
#: (2 ngày): đủ dài để không báo giả một ngày kênh nghỉ theo `chu_ky_dang_ngay`
#: >1, đủ ngắn để không im lặng cả tuần.
NGUONG_KHONG_VIDEO_MOI_GIO = 48.0

#: "video hẹn lịch mà chưa tải lên" — kế hoạch ghi rõ "<12h".
NGUONG_HEN_LICH_GIO = 12.0
#: Dưới ngần này giờ tới giờ hẹn mà chưa tải lên thì mới là KHẨN.
NGUONG_HEN_LICH_KHAN_GIO = 3.0

#: "tải lên lỗi lặp" — `lan_tai_moi` (số lần tải LẠI trong CÙNG một ngày,
#: `vm/may_dang_dom.py:813-818`) từ 3 trở lên coi là lặp đáng báo.
NGUONG_TAI_LEN_LAP_LAI = 3

#: "khoá giữ quá lâu" — cảnh báo SỚM hơn mốc giành lại cứng của `core.tu_chay`
#: (`KHOA_CU_QUA_GIAY`, 12 giờ) một nửa, để còn kịp người xem trước khi máy tự
#: giành khoá (giành khoá là quyết định của `core.tu_chay`, KHÔNG PHẢI việc
#: của module này — `gac_tong` chỉ báo, không tự giành/xoá khoá).
NGUONG_CANH_BAO_KHOA_GIAY = 6 * 3600

#: Ổ trống dưới ngưỡng này thì báo động — 06/10/2026 dùng CHUNG đúng số của van ổ
#: (`don_dep_mo_rong.NGUONG_O_GB`, 10 GB: dưới mức ấy không mở video mới). Luật chủ:
#: "ổ trống <10 GB thì không bắt đầu dựng video mới và báo động" — một con số, không hai.
NGUONG_DIA_GB = don_dep_mo_rong.NGUONG_O_GB

#: Ổ đầy kéo dài thì nhắc lại mỗi ngần này giờ (không phải mỗi lượt 15').
LAP_DIA_DAY_GIO = 24.0

#: "số liệu Studio cũ >48h" — đúng số kế hoạch nêu, khớp ngưỡng đã có sẵn ở
#: `core.bang_dieu_khien` (dòng ~1012-1018, không có hằng số export riêng).
NGUONG_STUDIO_CU_GIO = 48.0

# ── Ngưỡng thêm 29/09/2026 (tối) — "chế độ chạy max", xem
# `workspace/ban-va/2026-09-29-tu-canh-loi/GHI-CHU.md` ─────────────────────

#: "lượt sản xuất đứng một khâu quá lâu" — CẢNH BÁO (không tự sửa). Best-effort,
#: đo bằng `_moc_hoat_dong_tuoi_phut` — MAX của BỐN nguồn (mtime
#: `CHANNEL/<k>/tu-chay/<ngày>.json`, dòng cuối "[<k>]" trong `tu-chay.log`,
#: mtime tệp mới nhất trong thư mục LƯỢT đang hoạt động, dòng cuối của PID giữ
#: khe trong `nhat-ky.jsonl`), KHÔNG CHỈ mtime tệp báo cáo ngày như bản đầu —
#: sự cố báo giả TL3-T7 29/09/2026 23:18 ("đứng 296 phút" trong khi
#: `tu-chay.log` vừa có dòng lúc 23:14): tệp báo cáo ngày CHỈ được ghi lại ở
#: CUỐI CẢ LƯỢT (`core.tu_chay._chay_mot_ngay_trong_khoa.finalize()`), nên
#: đứng yên hàng giờ GIỮA một lượt dài là chuyện BÌNH THƯỜNG, không phải bằng
#: chứng treo. CHỈ áp dụng khi khe "nang" (core.khe) đang thật sự giữ bởi đúng
#: kênh đó, tránh báo giả một kênh đang NGHỈ (không viết gì nên tệp cũ là bình
#: thường). Xem `workspace/ban-va/2026-09-29-tu-canh-loi/GHI-CHU.md` mục "Sự
#: cố báo giả TL3-T7".
NGUONG_KHAU_DUNG_PHUT = 90.0

#: "chờ khe >60'" — vé trong `core.khe` hàng chờ (`workspace/khe/cho/`).
NGUONG_CHO_KHE_PHUT = 60.0

#: "RAM trống <2GB".
NGUONG_RAM_TRONG_GB = 2.0

#: "lỗi lặp cùng khâu ≥3 lượt" — 3 lượt CUỐI trong `runs_hom_nay` đều lỗi
#: (không `ok`, không `cho_nguoi`) và cùng `buoc_loi`.
NGUONG_LOI_LAP_KHAU = 3

#: "tiến trình tu_chay treo không log/tệp mới >120' và không giữ khe tai_len
#: → dừng" — ngưỡng TỰ SỬA (giết tiến trình), CAO HƠN hẳn ngưỡng chỉ CẢNH BÁO
#: (`NGUONG_KHAU_DUNG_PHUT`, 90') — chỉ hành động khi đã rất chắc là treo
#: thật, không phải một khâu vốn dĩ chậm (dựng video/tạo ảnh có thể mất hàng
#: giờ, xem `core/lich_tu_chay.py`: "một video mất 2–4 giờ").
#:
#: VÁ 29/09/2026 (đêm, sự cố báo giả TL3-T7): "không log/tệp mới" một mình
#: KHÔNG CÒN ĐỦ để giết — `tu_sua` giờ đòi thêm BẰNG CHỨNG THỨ BA (CPU tiến
#: trình không nhích, `NGUONG_CPU_GIAY_DUNG_YEN`) quan sát LIÊN TỤC đủ
#: `NGUONG_TU_DUNG_KHAU_PHUT` phút NỮA (qua tệp trạng thái theo dõi
#: `workspace/gac-tong/nghi-treo.json`, đối chiếu qua NHIỀU lần chạy
#: `--mot-luot` cách nhau 15') — tổng cộng phải im lặng + đứng CPU liên tục
#: khoảng `2 × NGUONG_TU_DUNG_KHAU_PHUT` phút mới bị dừng. Xem `tu_sua`.
NGUONG_TU_DUNG_KHAU_PHUT = 120.0

#: "ví < 3 ngày chạy" — dùng `core.chi_phi` (đọc đĩa, KHÔNG gọi mạng) làm chi
#: tiêu/ngày; CHỈ tính khi nơi gọi tự truyền `so_du_vnd` vào (gác tổng KHÔNG tự
#: gọi `balance.retrieve()` — xem docstring `kiem_su_co` và "CÁCH NỐI SAU" ở
#: GHI-CHU bản vá, cùng nguyên tắc CLAUDE.md luật 3 "mỗi lần gọi API là một
#: lần trừ tiền", không tự thêm lượt gọi mạng vào một hàm vốn CHỦ ĐÍCH
#: "KHÔNG GỌI MẠNG" của cả module).
NGUONG_VI_SO_NGAY = 3.0

#: "CPU tiến trình không nhích quá ngần này (giây)" — coi là ĐỨNG YÊN, bằng
#: chứng THỨ BA `tu_sua` cần trước khi dám dừng một khâu (cùng
#: `NGUONG_TU_DUNG_KHAU_PHUT`, xem `tu_sua`). Một khâu THẬT đang chạy (FFmpeg
#: dựng video, Whisper tách phụ đề…) ăn CPU liên tục — chỉ vài giây tích luỹ
#: suốt cả một cửa sổ theo dõi dài (mặc định 120') là KHÔNG THỂ nếu còn sống.
NGUONG_CPU_GIAY_DUNG_YEN = 5.0

#: Vá 30/09/2026 (báo giả TL3-T7 "the_da_co") — `_kiem_may_dang_khong_nhan_dien`
#: đọc LẠI cùng một tệp `vm/logs/kiem-dom/<k>.json` tĩnh mỗi lượt lịch
#: `--mot-luot` (15'), nên hễ kết quả kiểm cũ còn "hỏng" là cứ 15' lại ghi
#: thêm một dòng "khan" vào `workspace/loi-chay-max.md` + gọi `bao_dong_khan`
#: — LẶP MÃI dù không có gì mới. Sự cố có `dedupe_khoa` (xem `_su_co`) chỉ
#: được báo lại khi NỘI DUNG đổi (kết quả kiểm MỚI) HOẶC đã đủ
#: `NGUONG_LAP_BAO_GIO` giờ kể từ lần báo trước — vẫn báo định kỳ để "không
#: chết im lặng" nếu lỗi kéo dài, chỉ là không dồn dập mỗi 15'. Trạng thái
#: kênh (`xep_trang_thai_kenh`, mục "CHỜ NGƯỜI") KHÔNG bị ảnh hưởng — tính từ
#: `ds_su_co` ĐẦY ĐỦ, trước khi lọc. Xem `_doc_da_bao_lap`/`_ghi_da_bao_lap`.
NGUONG_LAP_BAO_GIO = 4.0

#: Việc giám đốc kênh mà chỉ NGƯỜI làm được (cảnh báo chính sách TL4: nghi gậy/nội dung dùng lại…): nhắc lại 1 lần/ngày.
NGUONG_LAP_VIEC_NGUOI_GIO = 24.0

#: Kênh có `ngay_bat_dau` trong chừng này ngày mà chưa có video nào: đang làm video đầu, không phải "khan".
NGAY_KENH_MOI = 3

#: Thử lại một việc máy tự xử (`tu_xu_ly_viec_may`) tối đa 1 lần / chừng này giờ.
NHIP_TU_XU_LY_GIO = 6.0

TRANG_THAI_DANG_CHAY = "dang_chay"
TRANG_THAI_TU_CHO = "tu_cho_co_han"
TRANG_THAI_CHO_NGUOI = "cho_nguoi"
TRANG_THAI_XONG = "xong"

_NHAN_TRANG_THAI = {
    TRANG_THAI_DANG_CHAY: "ĐANG CHẠY",
    TRANG_THAI_TU_CHO: "TỰ CHỜ CÓ HẠN",
    TRANG_THAI_CHO_NGUOI: "CHỜ NGƯỜI",
    TRANG_THAI_XONG: "XONG",
}

ChayLenh = lich_tu_chay.ChayLenh
KiemCong = Callable[[int], bool]


# ═══════════════════════════════════════════════════════════════════════════
# Lớp 1 — CHUP_TRANG_THAI: chạm đĩa/hệ thống, KHÔNG GHI gì
# ═══════════════════════════════════════════════════════════════════════════


def _doc_json_an_toan(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _doc_bao_cao_ngay(goc: str, ma: str, ngay_str: str) -> Dict[str, Any]:
    """`CHANNEL/<ma>/tu-chay/<ngày>.json` — đường công khai
    (`core.tu_chay.duong_bao_cao_ngay`), tự đọc an toàn (không đụng hàm riêng
    `_doc_bao_cao_ngay` của `core.tu_chay` — trùng tên có chủ đích, cùng khuôn)."""
    du = _doc_json_an_toan(tu_chay.duong_bao_cao_ngay(goc, ma, ngay_str))
    if isinstance(du, dict) and isinstance(du.get("runs"), list):
        return du
    return {"ngay": ngay_str, "kenh": ma, "runs": [], "nhat_ky": []}


def _ghep_ngay_gio(ngay: str, gio: str) -> Optional[_dt.datetime]:
    """`"29/09/2026"` + `"20:00"` → datetime. `None` nếu không đọc được."""
    ngay = str(ngay or "").strip()
    gio = str(gio or "").strip() or "00:00"
    if not ngay:
        return None
    for dinh_ngay in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            d = _dt.datetime.strptime(ngay, dinh_ngay).date()
            break
        except ValueError:
            d = None
    if d is None:
        return None
    for dinh_gio in ("%H:%M", "%H:%M:%S"):
        try:
            t = _dt.datetime.strptime(gio, dinh_gio).time()
            break
        except ValueError:
            t = None
    if t is None:
        t = _dt.time(0, 0)
    return _dt.datetime.combine(d, t)


def _doc_so_video_id(thu_muc_vm: str) -> Dict[str, Any]:
    du = _doc_json_an_toan(os.path.join(thu_muc_vm, "logs", "so-video-id.json"))
    return du if isinstance(du, dict) else {}


def _mtime_chi_so_gio(goc: str, ma: str, bay_gio: _dt.datetime) -> Optional[float]:
    """Tuổi (giờ) của `CHANNEL/<ma>/chi-so/bang-tom-tat.csv` — cùng tệp/ngưỡng
    `core.bang_dieu_khien` (~dòng 1012-1018) đã dùng để báo số liệu Studio cũ."""
    duong = os.path.join(kenh_mod.duong_kenh(goc, ma), "chi-so", "bang-tom-tat.csv")
    try:
        mtime = os.path.getmtime(duong)
    except OSError:
        return None
    return (bay_gio.timestamp() - mtime) / 3600.0


def _mtime_bao_cao_ngay_epoch(goc: str, ma: str, ngay_str: str) -> Optional[float]:
    """mtime (epoch) của `CHANNEL/<ma>/tu-chay/<ngày>.json` — NGUỒN 1/4 của
    `_moc_hoat_dong_tuoi_phut` (xem đó). CHỈ được ghi lại ở CUỐI CẢ LƯỢT
    (`core.tu_chay._chay_mot_ngay_trong_khoa.finalize()`) — một mình nó KHÔNG
    còn đủ để kết luận "không có dòng nhật ký mới" (sự cố báo giả TL3-T7,
    29/09/2026)."""
    try:
        return os.path.getmtime(tu_chay.duong_bao_cao_ngay(goc, ma, ngay_str))
    except OSError:
        return None


#: Chỉ đọc TỐI ĐA ngần này byte CUỐI `tu-chay.log` — log xoay ở 5MB
#: (`core.tu_chay.GIOI_HAN_LOG_TAT_CA_BYTE`); dòng gần nhất của một kênh THẬT
#: SỰ đang chạy luôn nằm rất gần cuối tệp (nhiều kênh cùng ghi xen kẽ, xem
#: `tu_chay.py:79-82` — mỗi dòng có nhãn "[<kênh>]"), đọc hết cả tệp mỗi 15
#: phút cho từng kênh là phí vô ích.
_GIOI_HAN_DOC_DUOI_LOG_TAT_CA_BYTE = 300_000


def _moc_epoch_tu_log_tat_ca(goc: str, ma: str) -> Optional[float]:
    """Mốc giờ (epoch) của dòng CUỐI CÙNG trong `workspace/tu-chay/tu-chay.log`
    mang nhãn "[<ma>]" — NGUỒN 2/4 của `_moc_hoat_dong_tuoi_phut` (xem đó).

    Log này được ghi THẬT-THỜI-GIAN mỗi khi có gì mới (`core.tu_chay.
    bo_log_tat_ca`/`_ghi_dong_log`), khác hẳn tệp báo cáo ngày (chỉ ghi ở
    cuối lượt) — chính log này có dòng "[TL3-T7] clip: 179/179 đã có sẵn…"
    lúc 23:14 trong khi tệp báo cáo ngày đứng yên từ nhiều giờ trước, gây báo
    giả 29/09/2026 23:18. Định dạng một dòng:
    `"[2026-09-29 23:18:38] [TL3-T7]     cắt 20/179 clip…"` — ngoặc thời gian
    của `_ghi_dong_log`, ngoặc kênh gắn thêm ở CLI gốc `tu_chay.py` khi chạy
    `--kenh <ma>` (mỗi kênh một tiến trình riêng trong "chế độ chạy max",
    cùng ghi chung một tệp nên cần nhãn để phân biệt)."""
    duong = tu_chay.duong_log_tat_ca(goc)
    try:
        co_dia = os.path.getsize(duong)
    except OSError:
        return None
    nhan = "[{0}]".format(ma)
    try:
        with open(duong, "rb") as tep:
            if co_dia > _GIOI_HAN_DOC_DUOI_LOG_TAT_CA_BYTE:
                tep.seek(-_GIOI_HAN_DOC_DUOI_LOG_TAT_CA_BYTE, os.SEEK_END)
            noi_dung = tep.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    moc: Optional[float] = None
    for dong in noi_dung.splitlines():
        if not dong.startswith("["):
            continue
        try:
            dong_thoi, phan_con = dong.split("] ", 1)
        except ValueError:
            continue
        if not phan_con.startswith(nhan):
            continue
        try:
            moc_dt = _dt.datetime.strptime(dong_thoi[1:], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        moc_epoch = moc_dt.timestamp()
        if moc is None or moc_epoch > moc:
            moc = moc_epoch
    return moc


def _thu_muc_luot_hoat_dong_nhat(goc: str, ma: str) -> Optional[str]:
    """Thư mục `PROJECTS/AUTO/<ma>/<lượt>/` có `trang-thai.json`
    (`core.auto.TEP_TRANG_THAI`, ghi mỗi khi một ảnh/clip xong — xem
    `core.auto_khau.dem_tien_do`) MỚI NHẤT — best-effort "lượt đang hoạt
    động": sổ ngày (`runs_hom_nay`) CHƯA có `ma_luot` của lượt đang dở (chỉ
    ghi ở `finalize()`, xem `_mtime_bao_cao_ngay_epoch`), nên không tra thẳng
    được — chọn thư mục có dấu vết MỚI NHẤT thay vì đoán tên."""
    goc_auto = os.path.join(goc, "PROJECTS", "AUTO", ma)
    try:
        con = list(os.scandir(goc_auto))
    except OSError:
        return None
    tot_duong: Optional[str] = None
    tot_mtime = -1.0
    for d in con:
        try:
            if not d.is_dir():
                continue
        except OSError:
            continue
        try:
            m = os.path.getmtime(os.path.join(d.path, auto.TEP_TRANG_THAI))
        except OSError:
            continue
        if m > tot_mtime:
            tot_mtime, tot_duong = m, d.path
    return tot_duong


def _mtime_moi_nhat_trong_thu_muc(thu_muc: str) -> Optional[float]:
    """mtime lớn nhất trong MỌI tệp (đệ quy) của `thu_muc` — NGUỒN 3/4 của
    `_moc_hoat_dong_tuoi_phut` (xem đó). Gồm cả `trang-thai.json` (nguồn kia
    hay nhắc tới) LẪN từng tệp ảnh/clip/mp3 thật (`5-anh/12.png`,
    `6-clip/179.mp4`…) — cảnh nào vừa xong là tệp đó vừa được ghi."""
    moi_nhat: Optional[float] = None
    try:
        for goc_dd, _thu, tep in os.walk(thu_muc):
            for ten in tep:
                try:
                    m = os.path.getmtime(os.path.join(goc_dd, ten))
                except OSError:
                    continue
                if moi_nhat is None or m > moi_nhat:
                    moi_nhat = m
    except OSError:
        return moi_nhat
    return moi_nhat


def _moc_epoch_tu_nhat_ky_khe(goc: str, pid: int) -> Optional[float]:
    """Dòng CUỐI trong `workspace/khe/nhat-ky.jsonl` của ĐÚNG `pid` — NGUỒN
    4/4 của `_moc_hoat_dong_tuoi_phut` (xem đó). Chỉ ghi ở các mốc xin/được/
    nhả khe (không phải nhịp tim liên tục), nên nguồn này HIẾM khi là mốc lớn
    nhất trong bốn nguồn — vẫn giữ vì CHỈ cộng thêm bằng chứng, không hại gì
    khi đứng sau."""
    duong = khe.duong_nhat_ky(goc)
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            dong_list = tep.readlines()
    except OSError:
        return None
    moc: Optional[float] = None
    for dong in dong_list:
        dong = dong.strip()
        if not dong:
            continue
        try:
            muc = json.loads(dong)
        except ValueError:
            continue
        try:
            if int(muc.get("pid") or 0) != pid:
                continue
            luc = float(muc.get("luc"))
        except (TypeError, ValueError):
            continue
        if moc is None or luc > moc:
            moc = luc
    return moc


def _moc_hoat_dong_tuoi_phut(goc: str, ma: str, bay_gio: _dt.datetime,
                             pid_nang: Optional[int]) -> Optional[float]:
    """"Không có dòng nhật ký mới" — đo bằng BỐN nguồn, lấy MỐC MỚI NHẤT
    (MAX), rồi trả tuổi (phút) tính từ mốc đó. Sự cố báo giả TL3-T7 29/09/2026
    23:18 ("đứng ở khâu dựng đã 296 phút") xảy ra vì bản đầu CHỈ nhìn mtime
    của `CHANNEL/<ma>/tu-chay/<ngày>.json` — tệp đó CHỈ được ghi lại ở CUỐI
    CẢ LƯỢT (xem `_mtime_bao_cao_ngay_epoch`), nên đứng yên hàng giờ GIỮA một
    lượt dài (khâu dựng vừa nhận bàn giao từ khâu clip, `tu-chay.log` vừa có
    dòng "[TL3-T7] clip: 179/179 đã có sẵn…" lúc 23:14) là chuyện BÌNH
    THƯỜNG, không phải bằng chứng treo.

    Bốn nguồn (xem docstring từng hàm): (1) mtime tệp báo cáo ngày, (2) dòng
    cuối "[<ma>]" trong `tu-chay.log`, (3) mtime tệp mới nhất trong thư mục
    LƯỢT đang hoạt động gần đây nhất, (4) dòng cuối của `pid_nang` (PID đang
    giữ khe "nang" cho kênh này, `None` nếu không ai giữ) trong nhật ký khe.

    `None` khi KHÔNG nguồn nào đọc được (kênh chưa từng chạy) — nơi gọi bỏ
    qua kiểm, không đoán bừa (giữ đúng nếp cũ của `bao_cao_tuoi_phut`)."""
    mocs: List[float] = []
    ngay_str = bay_gio.strftime("%Y-%m-%d")
    m1 = _mtime_bao_cao_ngay_epoch(goc, ma, ngay_str)
    if m1 is not None:
        mocs.append(m1)
    m2 = _moc_epoch_tu_log_tat_ca(goc, ma)
    if m2 is not None:
        mocs.append(m2)
    thu_muc_luot = _thu_muc_luot_hoat_dong_nhat(goc, ma)
    if thu_muc_luot is not None:
        m3 = _mtime_moi_nhat_trong_thu_muc(thu_muc_luot)
        if m3 is not None:
            mocs.append(m3)
    if pid_nang:
        m4 = _moc_epoch_tu_nhat_ky_khe(goc, pid_nang)
        if m4 is not None:
            mocs.append(m4)
    if not mocs:
        return None
    return (bay_gio.timestamp() - max(mocs)) / 60.0


def _cpu_giay_tien_trinh(pid: int, chay_lenh: "ChayLenh") -> Optional[float]:
    """Tổng số giây CPU (`TotalProcessorTime`) một tiến trình đã dùng —
    BẰNG CHỨNG THỨ BA `tu_sua` cần trước khi dám dừng một tiến trình "đứng
    khâu" (xem đó): CPU không nhích thêm nghĩa là THẬT SỰ không làm gì, khác
    hẳn "chưa ghi log/tệp mới" (một khâu có thể im lặng nhiều phút mà vẫn
    đang tính, ví dụ đợi máy chủ AI trả lời — `tu-chay.log` thật 23:16 "máy
    chủ vẫn đang làm, đã đợi 2 phút…"). `None` khi không đo được (PowerShell
    lỗi, PID đã chết) — nơi gọi phải coi là CHƯA ĐỦ bằng chứng, không tự suy
    diễn."""
    if not pid:
        return None
    lenh = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
            "(Get-Process -Id {0} -ErrorAction Stop)."
            "TotalProcessorTime.TotalSeconds".format(int(pid))]
    try:
        ma, ra = chay_lenh(lenh)
    except Exception:  # noqa: BLE001
        return None
    if ma != 0:
        return None
    try:
        return float((ra or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def _chup_ke_hoach(goc: str, ma: str, thu_muc_vm: str,
                   bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Từng dòng kế hoạch + `_loai` (`phan_loai_dong_ke_hoach`) + hai trường
    tính thêm dùng riêng cho kiểm "hẹn lịch <12h chưa tải": `_gio_con_lai`
    (âm = đã quá giờ) và `_da_tai` (đối chiếu sổ `so-video-id.json` LẪN cột
    "Video ID" của chính CSV — có mặt ở MỘT trong hai coi như đã tải)."""
    so_video_id = _doc_so_video_id(thu_muc_vm)
    cot, hang = ke_hoach_dang.doc_bang(goc, ma)
    ra: List[Dict[str, Any]] = []
    for dong_tho in hang:
        dong = dict(zip(cot, dong_tho))
        dong["_loai"] = phan_loai_dong_ke_hoach(dong)
        ma_goi = str(dong.get("Mã gói") or "").strip()
        hen = _ghep_ngay_gio(dong.get("Ngày đăng", ""), dong.get("Giờ đăng", ""))
        dong["_gio_con_lai"] = ((hen - bay_gio).total_seconds() / 3600.0
                                if hen is not None else None)
        muc_so = so_video_id.get("{0}/{1}".format(ma, ma_goi)) if ma_goi else None
        da_tai_so = bool(isinstance(muc_so, dict) and str(muc_so.get("video_id") or "").strip())
        dong["_da_tai"] = da_tai_so or bool(str(dong.get("Video ID") or "").strip())
        dong["_lan_tai_moi_hom_nay"] = (
            int(muc_so.get("lan_tai_moi") or 0)
            if isinstance(muc_so, dict) and muc_so.get("ngay_tai") == bay_gio.strftime("%Y-%m-%d")
            else 0)
        ra.append(dong)
    return ra


def _la_kenh_moi(goc: str, ma: str, bay_gio: _dt.datetime) -> bool:
    """`ngay_bat_dau` của kênh cách nay < `NGAY_KENH_MOI` ngày (không đọc được → không phải kênh mới)."""
    try:
        moc = kenh_mod.doc_kenh(goc, ma).ngay_bat_dau
        return 0 <= (bay_gio.date() - _dt.date.fromisoformat(str(moc)[:10])).days < NGAY_KENH_MOI
    except Exception:  # noqa: BLE001
        return False


def _chup_kenh(goc: str, ma: str, thu_muc_vm: str, bay_gio: _dt.datetime,
               pid_nang: Optional[int] = None) -> Dict[str, Any]:
    try:
        k = kenh_mod.doc_kenh(goc, ma)
        tu_chay_bat = bool(getattr(k, "tu_chay", False))
    except Exception:  # noqa: BLE001 — một kênh hỏng không được chặn cả ảnh chụp
        tu_chay_bat = False

    bao_cao = _doc_bao_cao_ngay(goc, ma, bay_gio.strftime("%Y-%m-%d"))
    # "Máy đăng dùng DOM" — ĐÚNG guard `core.bang_dieu_khien.viec_cua_ban` mục
    # 10 đã dùng (chẩn đoán 29/09/2026: kiểm DOM của kênh KHÔNG dùng máy đăng
    # DOM — ví dụ TL4-T7, tu_dang=false/cach_dang="anh" — không liên quan gì
    # tới kênh đó; đọc mà không lọc thì báo giả). KHÔNG tự bịa lại luật, tái
    # dùng thẳng cách gọi `vm_cai_dat.doc`.
    try:
        cai_vm = vm_cai_dat.doc(goc, ma)
    except Exception:  # noqa: BLE001 — kênh hỏng thì coi như không dùng DOM, không chặn ảnh chụp
        cai_vm = {}
    dung_may_dang_dom = bool(cai_vm.get("tu_dang")) and str(
        cai_vm.get("cach_dang") or "") in ("dom", "tu_dong")
    return {
        "tu_chay": tu_chay_bat,
        "kenh_moi": _la_kenh_moi(goc, ma, bay_gio),
        "ke_hoach": _chup_ke_hoach(goc, ma, thu_muc_vm, bay_gio),
        "runs_hom_nay": list(bao_cao.get("runs") or []),
        "nhat_ky_hom_nay": list(bao_cao.get("nhat_ky") or []),
        "kiem_dom": bang_dieu_khien.doc_kiem_dom(thu_muc_vm, ma),
        "dung_may_dang_dom": dung_may_dang_dom,
        "chi_so_tuoi_gio": _mtime_chi_so_gio(goc, ma, bay_gio),
        "bao_cao_tuoi_phut": _moc_hoat_dong_tuoi_phut(goc, ma, bay_gio, pid_nang),
    }


def _cong_dang_nghe_mac_dinh(cong: int) -> bool:
    """Dò MỘT cổng cục bộ (127.0.0.1) — không mở kết nối ra Internet, không
    gửi dữ liệu gì. Lỗi bất kỳ (đóng, bị chặn, timeout) → coi là KHÔNG nghe."""
    try:
        with socket.create_connection(("127.0.0.1", int(cong)), timeout=0.7):
            return True
    except OSError:
        return False


def _tuoi_khoa_may_giay(goc: str, bay_gio: _dt.datetime) -> Dict[str, Any]:
    """`workspace/tu-chay/.khoa-may` — `{"co": bool, "tuoi_giay": float|None,
    "pid": int|None, "con_song": bool|None}`. Không ném lỗi khi thiếu tệp."""
    duong = os.path.join(goc, "workspace", "tu-chay", tu_chay.TEN_TEP_KHOA_MAY)
    du = _doc_json_an_toan(duong)
    if not isinstance(du, dict):
        return {"co": False, "tuoi_giay": None, "pid": None, "con_song": None}
    try:
        pid = int(du.get("pid") or 0)
        bat_dau = float(du.get("bat_dau") or 0)
    except (TypeError, ValueError):
        return {"co": True, "tuoi_giay": None, "pid": None, "con_song": None}
    if not pid or not bat_dau:
        return {"co": True, "tuoi_giay": None, "pid": None, "con_song": None}
    return {"co": True, "tuoi_giay": bay_gio.timestamp() - bat_dau,
            "pid": pid, "con_song": _pid_con_song(pid), "bat_dau": bat_dau}


def _doc_dia(goc: str) -> Dict[str, Optional[float]]:
    try:
        _tong, _dung, con = shutil.disk_usage(goc)
    except OSError:
        return {"con_gb": None}
    return {"con_gb": con / 1024.0 ** 3}


def _doc_ram(goc: str) -> Dict[str, Optional[float]]:
    """RAM trống/tổng (GB) — `core.khe.ram_gb()` (đã tự đứng, không ném lỗi,
    xem docstring `core/khe.py`). `goc` không dùng, giữ để seam nhất quán với
    các hàm `_doc_*` khác trong module này."""
    del goc
    trong, tong = khe.ram_gb()
    return {"trong_gb": trong, "tong_gb": tong}


def _doc_khe(goc: str) -> Dict[str, Any]:
    """`core.khe.trang_thai(goc)` — ai đang giữ khe "nang"/"api" + hàng chờ.
    Lỗi đọc (đĩa hỏng, quyền) thì trả bộ rỗng, không chặn cả ảnh chụp."""
    try:
        return khe.trang_thai(goc)
    except Exception:  # noqa: BLE001
        return {"nang": None, "api": [], "cho": []}


def _dem_tien_trinh_tu_chay(chay_lenh: ChayLenh) -> Optional[int]:
    """Đếm tiến trình `python(w).exe ... tu_chay.py` đang chạy thật trên máy.

    `tasklist` không có cột dòng lệnh nên không phân biệt được `tu_chay.py`
    với tiến trình Python khác (Claude Code, whisper…) — dùng PowerShell
    `Get-CimInstance Win32_Process` (có sẵn trên Windows Server 2019, không
    cần cài thêm gì). Qua `chay_lenh` — CÙNG một cửa lệnh hệ thống với
    `core.lich_tu_chay` (seam mock được cho test, không gọi PowerShell thật).
    `None` khi không đếm được — nơi gọi bỏ qua kiểm này, không đoán bừa.
    """
    lenh = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
            "(Get-CimInstance Win32_Process | Where-Object "
            "{ $_.CommandLine -like '*tu_chay.py*' }).ProcessId"]
    try:
        ma, ra = chay_lenh(lenh)
    except Exception:  # noqa: BLE001
        return None
    if ma != 0:
        return None
    dong = [d.strip() for d in (ra or "").splitlines() if d.strip().isdigit()]
    return len(dong)


def _chi_tieu_ngay_gan_nhat_vnd(goc: str) -> Optional[float]:
    """Chi tiêu THẬT hôm qua (`core.chi_phi.hom_qua`, đọc đĩa — KHÔNG mạng).
    `None` khi chưa có sổ (VPS mới/chưa từng gọi `chi_phi.lay_va_luu`)."""
    try:
        cs = chi_phi.hom_qua(goc)
    except Exception:  # noqa: BLE001
        return None
    return float(cs.tong_vnd) if cs is not None else None


def chup_trang_thai(
    goc: str,
    *,
    bay_gio: Optional[_dt.datetime] = None,
    chay_lenh: Optional[ChayLenh] = None,
    kiem_cong: Optional[KiemCong] = None,
) -> Dict[str, Any]:
    """Đọc TOÀN BỘ trạng thái liên quan từ đĩa + `schtasks` + hai cổng cục bộ.

    KHÔNG GHI GÌ RA ĐĨA, KHÔNG GỌI MẠNG RA NGOÀI MÁY. `chay_lenh`/`kiem_cong`
    là seam cho test (mặc định gọi `schtasks`/dò socket thật).

    Trả `{"luc": iso, "goc": goc, "kenh": {ma: {...}}, "may": {...}}`.
    """
    goc = str(goc)
    bay_gio = bay_gio or _dt.datetime.now()
    chay_lenh = chay_lenh or lich_tu_chay._chay_lenh_mac_dinh  # noqa: SLF001 — seam mặc định, cùng khuôn lich_tu_chay tự dùng nội bộ
    kiem_cong = kiem_cong or _cong_dang_nghe_mac_dinh

    thu_muc_vm = tt.thu_muc_vm(goc)
    cac_kenh = kenh_mod.liet_ke_kenh(goc)

    # Đọc khe TRƯỚC khi chụp từng kênh: `_chup_kenh` cần biết PID đang giữ
    # khe "nang" cho ĐÚNG kênh đó (nguồn 4/4 của `_moc_hoat_dong_tuoi_phut`,
    # xem đó) — và tiện tay gắn luôn CPU-giây của PID ấy vào `nang` (bằng
    # chứng THỨ BA `tu_sua` cần trước khi dám dừng một khâu, xem `_cpu_giay_
    # tien_trinh`/`tu_sua`), đỡ phải dò khe lần hai.
    khe_trang_thai = _doc_khe(goc)
    nang = khe_trang_thai.get("nang")
    pid_nang_theo_kenh: Dict[str, int] = {}
    if isinstance(nang, dict):
        try:
            pid_nang = int(nang.get("pid") or 0)
        except (TypeError, ValueError):
            pid_nang = 0
        nang["cpu_giay"] = _cpu_giay_tien_trinh(pid_nang, chay_lenh) if pid_nang else None
        ma_nang = str(nang.get("kenh") or "")
        if ma_nang and pid_nang:
            pid_nang_theo_kenh[ma_nang] = pid_nang

    kenh_snap = {ma: _chup_kenh(goc, ma, thu_muc_vm, bay_gio, pid_nang_theo_kenh.get(ma))
                for ma in cac_kenh}

    may = {
        "dia": _doc_dia(goc),
        "ram": _doc_ram(goc),
        "cong_8765_tram": kiem_cong(8765),
        "cong_8767_agent": kiem_cong(8767),
        "schtasks_tu_chay": lich_tu_chay.trang_thai(goc, chay_lenh=chay_lenh),
        "schtasks_canh_tram": lich_tu_chay.trang_thai_canh_tram(goc, chay_lenh=chay_lenh),
        "khoa_may": _tuoi_khoa_may_giay(goc, bay_gio),
        "khe": khe_trang_thai,
        "lan_api": khe.so_lan_api(goc),
        "so_tien_trinh_tu_chay": _dem_tien_trinh_tu_chay(chay_lenh),
        "chi_tieu_hom_qua_vnd": _chi_tieu_ngay_gan_nhat_vnd(goc),
    }

    return {"luc": bay_gio.isoformat(timespec="seconds"), "goc": goc,
            "kenh": kenh_snap, "may": may}


# ═══════════════════════════════════════════════════════════════════════════
# Lớp 2 — KIEM_SU_CO: hàm THUẦN, ảnh chụp vào → danh sách sự cố ra
# ═══════════════════════════════════════════════════════════════════════════


def _su_co(loai: str, muc: str, chuyen_gi: str, *,
          kenh: str = "", can_lam_gi: str = "", neu_khong_lam: str = "",
          dedupe_khoa: str = "") -> Dict[str, Any]:
    """`dedupe_khoa` (tuỳ chọn): khoá "nội dung sự cố" cho `bao_cao_su_co` lọc
    lặp (xem `NGUONG_LAP_BAO_GIO`) — để trống thì KHÔNG lọc gì (báo mọi lượt,
    hành vi cũ, dùng cho phần lớn sự cố hiện có)."""
    return {"loai": loai, "kenh": kenh, "muc": muc, "chuyen_gi": chuyen_gi,
           "can_lam_gi": can_lam_gi, "neu_khong_lam": neu_khong_lam,
           "dedupe_khoa": dedupe_khoa}


def _kiem_khong_video_moi(ma: str, snap: Dict[str, Any],
                          bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    if not snap.get("tu_chay"):
        return []
    da_dang = [d for d in snap.get("ke_hoach") or [] if d.get("_loai") == "da_dang"]
    mocs = [_ghep_ngay_gio(d.get("Ngày đăng", ""), d.get("Giờ đăng", "")) for d in da_dang]
    mocs = [m for m in mocs if m is not None]
    if not mocs:
        if snap.get("kenh_moi"):
            return []  # kênh mới (< NGAY_KENH_MOI ngày): đang làm video đầu — chỉ 1 dòng trạng thái trong bản tin
        sc = _su_co(
            "khong_video_moi", bao_dong.MUC_KHAN, kenh=ma,
            chuyen_gi="Kênh {0} đang bật tự động nhưng chưa từng có video nào đăng.".format(ma),
            can_lam_gi="Mở tool xem kênh {0} có đang chạy được không.".format(ma),
            neu_khong_lam="Kênh không có video mới, kênh đứng im mà không ai biết.",
            dedupe_khoa="khong_video_moi:{0}:chua_tung".format(ma))
        sc["lap_gio"] = ben_bi.NGUONG_LAP_BAO_TIEN_GIO  # 06/10: báo 1 lần rồi nhắc 1 lần/ngày, không mỗi 15'
        return [sc]
    gio_gan_nhat = max(mocs)
    tuoi_gio = (bay_gio - gio_gan_nhat).total_seconds() / 3600.0
    if tuoi_gio > NGUONG_KHONG_VIDEO_MOI_GIO:
        sc = _su_co(
            "khong_video_moi", bao_dong.MUC_KHAN, kenh=ma,
            chuyen_gi="Kênh {0} đã {1:.0f} giờ không có video mới (video gần nhất {2}).".format(
                ma, tuoi_gio, gio_gan_nhat.strftime("%d/%m %H:%M")),
            can_lam_gi="Mở tool xem kênh {0} đang bị chặn ở đâu.".format(ma),
            neu_khong_lam="Kênh ngừng ra video mà không ai biết, có thể mất cả tuần.",
            dedupe_khoa="khong_video_moi:{0}:{1}".format(ma, gio_gan_nhat.strftime("%Y%m%d%H%M")))
        sc["lap_gio"] = ben_bi.NGUONG_LAP_BAO_TIEN_GIO
        return [sc]
    return []


def _kiem_hen_lich_chua_tai(ma: str, snap: Dict[str, Any], bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    ra = []
    for d in snap.get("ke_hoach") or []:
        if d.get("_loai") != "sap_dang" or d.get("_da_tai"):
            continue
        gio_con_lai = d.get("_gio_con_lai")
        if gio_con_lai is None or gio_con_lai > NGUONG_HEN_LICH_GIO:
            continue
        tieu_de = str(d.get("Tiêu đề") or d.get("Mã gói") or "").strip()
        qua_han = gio_con_lai < 0
        # Máy đăng tải bổ sung theo khe nên video thường lên trước giờ hẹn 3–8 giờ;
        # còn xa (>3 giờ) chỉ là THƯỜNG, sát giờ hoặc quá giờ mới KHẨN (01/10/2026).
        muc = bao_dong.MUC_KHAN if gio_con_lai <= NGUONG_HEN_LICH_KHAN_GIO else bao_dong.MUC_THUONG
        ra.append(_su_co(
            "hen_lich_chua_tai", muc, kenh=ma,
            # 06/10: cùng video + cùng mức thì 4 giờ mới ghi/báo lại (trước: mỗi 15').
            dedupe_khoa="hen_lich:{0}:{1}:{2}".format(ma, str(d.get("Mã gói") or tieu_de)[:80], muc),
            chuyen_gi=("Video 「{0}」 của kênh {1} đã QUÁ giờ hẹn đăng {2:.1f} giờ mà "
                      "chưa thấy tải lên YouTube.".format(tieu_de, ma, abs(gio_con_lai))
                      if qua_han else
                      "Video 「{0}」 của kênh {1} còn {2:.1f} giờ nữa tới giờ hẹn đăng mà "
                      "chưa thấy tải lên YouTube.".format(tieu_de, ma, gio_con_lai)),
            can_lam_gi="Mở tool xem máy đăng của kênh {0} có đang chạy không.".format(ma),
            neu_khong_lam="Video có thể lỡ giờ hẹn, mất một ngày đăng."))
    return ra


def _kiem_tai_len_loi_lap(ma: str, snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    ra = []
    for d in snap.get("ke_hoach") or []:
        lan = int(d.get("_lan_tai_moi_hom_nay") or 0)
        if lan >= NGUONG_TAI_LEN_LAP_LAI:
            tieu_de = str(d.get("Tiêu đề") or d.get("Mã gói") or "").strip()
            ra.append(_su_co(
                "tai_len_loi_lap", bao_dong.MUC_KHAN, kenh=ma,
                dedupe_khoa="tai_len_lap:{0}:{1}:{2}".format(ma, str(d.get("Mã gói") or tieu_de)[:80], lan),
                chuyen_gi="Video 「{0}」 của kênh {1} đã thử tải lên YouTube {2} lần "
                         "hôm nay mà chưa xong.".format(tieu_de, ma, lan),
                can_lam_gi="Mở tool xem máy đăng kênh {0} báo lỗi gì.".format(ma),
                neu_khong_lam="Máy có thể đang kẹt ở đúng một video, các video sau cũng bị chặn theo."))
    return ra


def _kiem_studio_cu(ma: str, snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    tuoi_gio = snap.get("chi_so_tuoi_gio")
    if snap.get("tu_chay") and tuoi_gio is not None and tuoi_gio > NGUONG_STUDIO_CU_GIO:
        sc = _su_co(
            "so_lieu_studio_cu", bao_dong.MUC_THUONG, kenh=ma,
            chuyen_gi="Số liệu Studio của kênh {0} đã {1:.0f} giờ chưa cập nhật.".format(
                ma, tuoi_gio),
            can_lam_gi="Mở tool bấm quét số liệu Studio kênh {0}.".format(ma),
            neu_khong_lam="Máy chọn ảnh bìa/kịch bản dựa trên số liệu cũ, có thể học sai.",
            dedupe_khoa="studio_cu:{0}".format(ma))
        sc["lap_gio"] = 24.0  # 06/10: mức thường mà bao_dong chỉ lặng 1 giờ — trước đây nhắc mỗi giờ cả tuần
        return [sc]
    return []


def _kiem_dia_day(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    con_gb = ((anh.get("may") or {}).get("dia") or {}).get("con_gb")
    if con_gb is not None and con_gb < NGUONG_DIA_GB:
        sc = _su_co(
            "dia_day", bao_dong.MUC_KHAN,
            chuyen_gi="Ổ đĩa máy chỉ còn {0:.1f} GB trống (< {1:g} GB) — máy ngừng dựng video "
                      "mới.".format(con_gb, NGUONG_DIA_GB),
            can_lam_gi="Thêm dung lượng ổ đĩa cho VPS (máy đã tự dọn file nặng của video đã lên).",
            neu_khong_lam="Không có video mới cho tới khi ổ đủ chỗ.",
            dedupe_khoa="dia_day")
        sc["lap_gio"] = LAP_DIA_DAY_GIO
        return [sc]
    return []


def _kiem_tram_chet(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    may = anh.get("may") or {}
    if not may.get("cong_8765_tram"):
        return [_su_co(
            "tram_chet", bao_dong.MUC_KHAN,
            chuyen_gi="Trạm cổng 8765 không phản hồi — máy ảo không lấy được kế hoạch đăng.",
            can_lam_gi="Mở MyTool lên (trạm tự bật lại khi tool mở), hoặc khởi động lại máy.",
            neu_khong_lam="Mọi kênh ngừng đăng cho tới khi trạm sống lại.")]
    return []


def _kiem_khoa_may_qua_lau(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    khoa = (anh.get("may") or {}).get("khoa_may") or {}
    if not khoa.get("co"):
        return []
    tuoi_giay = khoa.get("tuoi_giay")
    if tuoi_giay is not None and tuoi_giay > NGUONG_CANH_BAO_KHOA_GIAY:
        gio = tuoi_giay / 3600.0
        con_song = khoa.get("con_song")
        return [_su_co(
            "khoa_may_qua_lau", bao_dong.MUC_KHAN,
            chuyen_gi="Khoá sản xuất toàn máy (.khoa-may) đã giữ {0:.1f} giờ ({1}).".format(
                gio, "tiến trình còn sống" if con_song else "tiến trình đã CHẾT"),
            can_lam_gi=("Đợi thêm — máy sẽ tự giành lại khoá sau 12 giờ."
                        if con_song else
                        "Khởi động lại máy hoặc mở tool kiểm tra — tiến trình giữ khoá đã chết "
                        "mà khoá chưa được dọn."),
            neu_khong_lam="Mọi kênh khác phải xếp hàng chờ, sản xuất cả máy bị chặn.")]
    return []


def _kiem_khau_dung_qua_lau(ma: str, snap: Dict[str, Any], anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"Lượt sản xuất đứng một khâu quá lâu" — khe "nang" đang giữ ĐÚNG kênh
    này mà `CHANNEL/<ma>/tu-chay/<ngày>.json` đã lâu không được ghi lại (xem
    `NGUONG_KHAU_DUNG_PHUT`). Best-effort — xem ghi chú ở hằng số đó."""
    nang = ((anh.get("may") or {}).get("khe") or {}).get("nang")
    if not isinstance(nang, dict) or str(nang.get("kenh") or "") != ma:
        return []
    tuoi_phut = snap.get("bao_cao_tuoi_phut")
    if tuoi_phut is None or tuoi_phut <= NGUONG_KHAU_DUNG_PHUT:
        return []
    viec = str(nang.get("viec") or "một khâu")
    return [_su_co(
        "khau_dung_qua_lau", bao_dong.MUC_KHAN, kenh=ma,
        chuyen_gi="Kênh {0} đứng ở khâu “{1}” đã {2:.0f} phút không thấy dòng "
                 "nhật ký mới.".format(ma, viec, tuoi_phut),
        can_lam_gi="Mở tool xem nhật ký kênh {0} — có thể máy chủ ảnh/video "
                   "đang treo.".format(ma),
        neu_khong_lam="Lượt có thể kẹt vô thời hạn, giữ khoá máy khiến kênh "
                     "khác cũng phải xếp hàng chờ.")]


def _kiem_loi_lap_cung_khau(ma: str, snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"Lỗi lặp cùng khâu ≥3 lượt" — `NGUONG_LOI_LAP_KHAU` lượt CUỐI hôm nay
    đều lỗi (không `ok`, không `cho_nguoi`) và cùng `buoc_loi`."""
    runs = [r for r in (snap.get("runs_hom_nay") or []) if isinstance(r, dict)]
    if len(runs) < NGUONG_LOI_LAP_KHAU:
        return []
    gan_nhat = runs[-NGUONG_LOI_LAP_KHAU:]
    if any(r.get("ok") or r.get("cho_nguoi") for r in gan_nhat):
        return []
    buoc = {str(r.get("buoc_loi") or "") for r in gan_nhat}
    if len(buoc) != 1 or not next(iter(buoc)):
        return []
    ten_buoc = next(iter(buoc))
    return [_su_co(
        "loi_lap_cung_khau", bao_dong.MUC_KHAN, kenh=ma,
        chuyen_gi="Kênh {0} lỗi liên tiếp {1} lượt cùng ở khâu “{2}”.".format(
            ma, NGUONG_LOI_LAP_KHAU, ten_buoc),
        can_lam_gi="Mở tool xem lỗi cụ thể ở khâu {0} của kênh {1} — tự thử "
                   "lại không giúp gì nữa, cần người xem.".format(ten_buoc, ma),
        neu_khong_lam="Kênh lặp đúng lỗi này mãi, mỗi lượt thử lại vẫn tốn "
                     "thời gian máy mà không ra video nào.")]


def _kiem_may_dang_khong_nhan_dien(ma: str, snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"Tải lên hỏng" — máy đăng DOM không nhận ra một ô nào đó trên Studio
    (`vm/logs/kiem-dom/<k>.json`, đã có sẵn trong ảnh chụp — trước 29/09 chỉ
    MANG VÀO cho Bảng điều khiển, chưa tự sinh sự cố; nay thêm). CHỈ kiểm khi
    kênh THẬT SỰ dùng máy đăng DOM (`snap["dung_may_dang_dom"]`) — kênh đang
    ở đường ảnh cũ hay chưa bật máy đăng thì kết quả kiểm DOM không liên quan
    gì (chẩn đoán thật 29/09/2026, dữ liệu TL4-T7: tu_dang=false,
    cach_dang="anh" — cùng guard `core.bang_dieu_khien.viec_cua_ban` mục 10)."""
    if not snap.get("dung_may_dang_dom"):
        return []
    kq = snap.get("kiem_dom")
    if not isinstance(kq, dict) or kq.get("ok", True):
        return []
    buoc = ", ".join(kq.get("hong_ten") or kq.get("hong") or []) or "một ô"
    # `dedupe_khoa` gồm cả "ngay" (mốc lượt --kiem-dom tạo ra kết quả này) LẪN
    # `buoc` — đổi MỘT trong hai (kiểm lại ra kết quả mới, hoặc hỏng thêm/bớt
    # mục) coi là "sự cố mới", báo lại ngay dù chưa đủ NGUONG_LAP_BAO_GIO giờ.
    return [_su_co(
        "tai_len_hong", bao_dong.MUC_KHAN, kenh=ma,
        chuyen_gi="Máy đăng kênh {0} không nhận ra {1} trên Studio (kiểm {2}) "
                 "— tải lên có thể hỏng.".format(ma, buoc, kq.get("ngay") or "?"),
        can_lam_gi="Báo người lập trình, kèm ngày kiểm ở trên.",
        neu_khong_lam="Video của kênh {0} có thể không tải lên được cho tới "
                     "khi có người sửa.".format(ma),
        dedupe_khoa="tai_len_hong:{0}:{1}|{2}".format(ma, kq.get("ngay") or "", buoc))]


def _kiem_cho_khe_qua_lau(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"Chờ khe >60'" — vé trong hàng chờ `core.khe` (`workspace/khe/cho/`)."""
    cho = ((anh.get("may") or {}).get("khe") or {}).get("cho") or []
    try:
        bay_gio_epoch = _dt.datetime.fromisoformat(anh["luc"]).timestamp()
    except (KeyError, ValueError):
        return []
    ra: List[Dict[str, Any]] = []
    for ve in cho:
        if not isinstance(ve, dict):
            continue
        try:
            luc_xin = float(ve.get("luc_xin") or 0)
        except (TypeError, ValueError):
            continue
        if not luc_xin:
            continue
        phut = (bay_gio_epoch - luc_xin) / 60.0
        if phut <= NGUONG_CHO_KHE_PHUT:
            continue
        kenh_ve = str(ve.get("kenh") or "")
        ra.append(_su_co(
            "cho_khe_qua_lau", bao_dong.MUC_KHAN, kenh=kenh_ve,
            chuyen_gi="Việc “{0}”{1} đã xếp hàng chờ khe {2:.0f} phút mà chưa "
                     "tới lượt.".format(
                         ve.get("viec") or "?",
                         " (kênh {0})".format(kenh_ve) if kenh_ve else "", phut),
            can_lam_gi="Mở tool xem khe đang bị ai giữ (nhật ký `core/khe`).",
            neu_khong_lam="Việc đó có thể chờ mãi nếu khe đang bị kẹt bởi một "
                         "tiến trình đã chết mà chưa được dọn."))
    return ra


def _kiem_ram_thap(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"RAM trống <2GB"."""
    trong = ((anh.get("may") or {}).get("ram") or {}).get("trong_gb")
    if trong is not None and trong < NGUONG_RAM_TRONG_GB:
        return [_su_co(
            "ram_thap", bao_dong.MUC_KHAN,
            chuyen_gi="RAM máy chỉ còn {0:.1f} GB trống.".format(trong),
            can_lam_gi="Đóng bớt trình duyệt/kênh đang mở, hoặc khởi động lại máy.",
            neu_khong_lam="Máy có thể treo, hoặc Windows tự đóng một tiến "
                         "trình đang chạy giữa chừng.")]
    return []


def _kiem_khoa_may_pid_chet(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"Khoá .khoa-may trỏ PID chết" — khác `_kiem_khoa_may_qua_lau` (dựa vào
    TUỔI khoá): ở đây PID đã CHẾT là sự thật xác nhận được NGAY, không cần
    đợi qua ngưỡng tuổi. TỰ SỬA an toàn ở `tu_sua` — xem đó."""
    khoa = (anh.get("may") or {}).get("khoa_may") or {}
    if not khoa.get("co") or not khoa.get("pid"):
        return []
    if khoa.get("con_song") is False:
        return [_su_co(
            "khoa_may_pid_chet", bao_dong.MUC_THUONG,
            chuyen_gi="Khoá sản xuất toàn máy (.khoa-may) trỏ PID {0} đã CHẾT "
                     "nhưng khoá chưa được dọn.".format(khoa.get("pid")),
            can_lam_gi="Máy sẽ tự dọn khoá này (xem hành động tự sửa) — nếu "
                       "vẫn còn, xoá tay workspace/tu-chay/.khoa-may.",
            neu_khong_lam="Kênh khác phải chờ dù không còn ai thật sự giữ khoá.")]
    return []


def _kiem_qua_nhieu_tu_chay(anh: Dict[str, Any]) -> List[Dict[str, Any]]:
    """"Tiến trình tu_chay nhiều hơn lan_api+1" — vượt trần cho phép."""
    may = anh.get("may") or {}
    so = may.get("so_tien_trinh_tu_chay")
    lan_api = may.get("lan_api")
    if so is None or lan_api is None:
        return []
    tran = int(lan_api) + 1
    if so > tran:
        return [_su_co(
            "qua_nhieu_tu_chay", bao_dong.MUC_KHAN,
            chuyen_gi="Máy đang có {0} tiến trình tu_chay.py cùng lúc, vượt "
                     "trần cho phép ({1} làn API + 1).".format(so, lan_api),
            can_lam_gi="Mở Task Manager xem tiến trình tu_chay.py nào treo, "
                       "đóng bớt hoặc khởi động lại máy.",
            neu_khong_lam="Các tiến trình chồng nhau có thể tranh khoá lẫn "
                         "nhau, làm chậm hoặc hỏng cả lượt sản xuất.")]
    return []


def _kiem_vi_sap_can(anh: Dict[str, Any], so_du_vnd: Optional[float]) -> List[Dict[str, Any]]:
    """"Ví < 3 ngày chạy" — CHỈ kiểm khi nơi gọi truyền `so_du_vnd` (gác tổng
    không tự gọi mạng lấy số dư, xem `NGUONG_VI_SO_NGAY`). Chi tiêu/ngày lấy
    từ `core.chi_phi` (đọc đĩa)."""
    if so_du_vnd is None:
        return []
    chi_ngay = (anh.get("may") or {}).get("chi_tieu_hom_qua_vnd")
    if not chi_ngay or chi_ngay <= 0:
        return []
    so_ngay = so_du_vnd / chi_ngay
    if so_ngay < NGUONG_VI_SO_NGAY:
        return [_su_co(
            "vi_sap_can", bao_dong.MUC_KHAN,
            chuyen_gi="Ví còn {0:,.0f}₫ — đủ chạy khoảng {1:.1f} ngày theo chi "
                     "tiêu hôm qua.".format(so_du_vnd, so_ngay).replace(",", "."),
            can_lam_gi="Nạp thêm tiền vào ví.",
            neu_khong_lam="Hết tiền giữa lượt sản xuất, kênh dừng đột ngột "
                         "không ai biết.")]
    return []


def kiem_su_co(anh: Dict[str, Any], *, so_du_vnd: Optional[float] = None) -> List[Dict[str, Any]]:
    """Ảnh chụp (`chup_trang_thai`) → danh sách sự cố. Hàm THUẦN — không đọc
    đĩa, không gọi mạng, test được bằng ảnh chụp dựng tay.

    `so_du_vnd`: số dư ví THẬT (VND) — tuỳ chọn, nơi gọi tự lấy rồi truyền vào
    (kiểm "ví < 3 ngày chạy"). Để trống thì bỏ qua kiểm đó, không tự gọi mạng
    (xem `NGUONG_VI_SO_NGAY`)."""
    ra: List[Dict[str, Any]] = []

    def _goi(ten: str, ham: Callable[..., List[Dict[str, Any]]], *doi_so: Any) -> None:
        # 06/10/2026: MỘT kiểm hỏng (dữ liệu lạ trong một kênh) không được nuốt mất
        # mọi kiểm còn lại — trước đây ngoại lệ ở đây làm cả lượt gác tổng sập im.
        try:
            ra.extend(ham(*doi_so))
        except Exception as loi:  # noqa: BLE001
            ra.append(_su_co(
                "kiem_hong", bao_dong.MUC_NHAC,
                "Một bước kiểm của người gác ({0}) bị lỗi: {1}: {2}".format(
                    ten, type(loi).__name__, str(loi)[:150]),
                can_lam_gi="Báo người quản trị tool.", dedupe_khoa="kiem_hong:" + ten))

    try:
        bay_gio = _dt.datetime.fromisoformat(str(anh.get("luc")))
    except (TypeError, ValueError):
        bay_gio = _dt.datetime.now()
    for ma, snap in (anh.get("kenh") or {}).items():
        _goi("khong_video_moi", _kiem_khong_video_moi, ma, snap, bay_gio)
        _goi("hen_lich_chua_tai", _kiem_hen_lich_chua_tai, ma, snap, bay_gio)
        _goi("tai_len_loi_lap", _kiem_tai_len_loi_lap, ma, snap)
        _goi("so_lieu_studio_cu", _kiem_studio_cu, ma, snap)
        _goi("khau_dung_qua_lau", _kiem_khau_dung_qua_lau, ma, snap, anh)
        _goi("loi_lap_cung_khau", _kiem_loi_lap_cung_khau, ma, snap)
        _goi("tai_len_hong", _kiem_may_dang_khong_nhan_dien, ma, snap)
    _goi("dia_day", _kiem_dia_day, anh)
    _goi("tram_chet", _kiem_tram_chet, anh)
    _goi("khoa_may_qua_lau", _kiem_khoa_may_qua_lau, anh)
    _goi("khoa_may_pid_chet", _kiem_khoa_may_pid_chet, anh)
    _goi("cho_khe_qua_lau", _kiem_cho_khe_qua_lau, anh)
    _goi("ram_thap", _kiem_ram_thap, anh)
    _goi("qua_nhieu_tu_chay", _kiem_qua_nhieu_tu_chay, anh)
    _goi("vi_sap_can", _kiem_vi_sap_can, anh, so_du_vnd)
    return ra


def xep_trang_thai_kenh(snap: Dict[str, Any], su_co_kenh: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Best-effort 4 trạng thái (xem docstring đầu tệp, mục "CHUẨN 4 TRẠNG
    THÁI") — `{"trang_thai": ..., "ly_do": str}`."""
    if not snap.get("tu_chay"):
        return {"trang_thai": TRANG_THAI_XONG, "ly_do": "Kênh không bật tự động."}
    khan = [s for s in su_co_kenh if s.get("muc") == bao_dong.MUC_KHAN]
    if khan:
        return {"trang_thai": TRANG_THAI_CHO_NGUOI, "ly_do": khan[0]["chuyen_gi"]}
    runs = snap.get("runs_hom_nay") or []
    if runs:
        cuoi = runs[-1]
        if cuoi.get("cho_nguoi"):
            return {"trang_thai": TRANG_THAI_CHO_NGUOI,
                    "ly_do": str(cuoi.get("loi") or cuoi.get("tom_tat") or "Đang chờ người xử lý.")}
        if cuoi.get("ok"):
            return {"trang_thai": TRANG_THAI_XONG,
                    "ly_do": str(cuoi.get("tom_tat") or "Đã chạy xong hôm nay.")}
        return {"trang_thai": TRANG_THAI_TU_CHO,
                "ly_do": str(cuoi.get("loi") or "Gặp trục trặc tạm thời, máy tự thử lại.")}
    return {"trang_thai": TRANG_THAI_DANG_CHAY,
            "ly_do": "Chưa ghi nhận lượt chạy nào hôm nay."}


# ═══════════════════════════════════════════════════════════════════════════
# Lớp 3 — GHI + BÁO: jsonl, tinh-trang.json, gọi core.bao_dong
# ═══════════════════════════════════════════════════════════════════════════

GuiHam = Callable[..., bool]


def duong_nhat_ky_ngay(goc: str, ngay_str: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "{0}.jsonl".format(ngay_str))


def duong_tinh_trang(goc: str) -> str:
    return os.path.join(goc, "workspace", "tinh-trang.json")


def duong_loi_chay_max(goc: str) -> str:
    return os.path.join(goc, "workspace", "loi-chay-max.md")


_TIEU_DE_LOI_CHAY_MAX = (
    "# Lỗi chạy max — nhật ký người gác tổng\n\n"
    "Mỗi dòng dưới đây là MỘT sự cố `core.gac_tong` phát hiện lúc chạy lịch "
    "`ShopAPI-GacTong` (mỗi 15 phút). Xem chi tiết đầy đủ trong "
    "`workspace/gac-tong/<ngày>.jsonl` (một dòng JSON/sự cố) và "
    "`workspace/tinh-trang.json` (trạng thái mới nhất).\n\n")


def _ghi_loi_chay_max_md(goc: str, bay_gio: _dt.datetime, ds_su_co: List[Dict[str, Any]]) -> None:
    """Nối thêm mỗi sự cố MỘT dòng Markdown vào `workspace/loi-chay-max.md`,
    tạo tệp (kèm tiêu đề) nếu chưa có. Không ghi hỏng thì bỏ qua — cùng luật
    "không ném lỗi" của `core.bao_dong` (máy chạy một mình nhiều năm)."""
    if not ds_su_co:
        return
    duong = duong_loi_chay_max(goc)
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        moi = not os.path.isfile(duong)
        with open(duong, "a", encoding="utf-8") as tep:
            if moi:
                tep.write(_TIEU_DE_LOI_CHAY_MAX)
            for sc in ds_su_co:
                kenh_nhan = " · kênh {0}".format(sc["kenh"]) if sc.get("kenh") else ""
                tep.write("- [{0}] **{1}**{2} — {3}\n".format(
                    bay_gio.strftime("%Y-%m-%d %H:%M"), sc.get("muc", "?"),
                    kenh_nhan, sc.get("chuyen_gi", "")))
    except OSError:
        pass


def _ghi_nhat_ky_jsonl(goc: str, bay_gio: _dt.datetime, ds_su_co: List[Dict[str, Any]]) -> None:
    if not ds_su_co:
        return
    duong = duong_nhat_ky_ngay(goc, bay_gio.strftime("%Y-%m-%d"))
    try:
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "a", encoding="utf-8") as tep:
            for sc in ds_su_co:
                dong = dict(sc)
                dong["luc"] = bay_gio.isoformat(timespec="seconds")
                tep.write(json.dumps(dong, ensure_ascii=False) + "\n")
    except OSError:
        pass  # cùng luật "không ném lỗi" của core.bao_dong — máy chạy một mình nhiều năm


def _ghi_tinh_trang(goc: str, du_lieu: Dict[str, Any]) -> None:
    """Ghi NGUYÊN TỬ — `.tmp` rồi `os.replace`, cùng khuôn `core.bao_dong._ghi_kho`."""
    try:
        duong = duong_tinh_trang(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du_lieu, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def _duong_da_bao_lap(goc: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "da-bao-lap.json")


def _doc_da_bao_lap(goc: str) -> Dict[str, Any]:
    du = _doc_json_an_toan(_duong_da_bao_lap(goc))
    return du if isinstance(du, dict) else {}


def _ghi_da_bao_lap(goc: str, du_lieu: Dict[str, Any]) -> None:
    """Ghi NGUYÊN TỬ — cùng khuôn `_ghi_tinh_trang`."""
    try:
        duong = _duong_da_bao_lap(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du_lieu, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def _loc_lap_su_co(goc: str, ds_su_co: List[Dict[str, Any]],
                   bay_gio: _dt.datetime) -> List[Dict[str, Any]]:
    """Lọc bớt sự cố có `dedupe_khoa` (xem `_su_co`) đã báo với ĐÚNG khoá đó
    chưa đủ `NGUONG_LAP_BAO_GIO` giờ — vá 30/09/2026 (TL3-T7 bị ghi "khan"
    mỗi 15' vào `loi-chay-max.md` dù cùng một kết quả kiểm cũ, xem
    `_kiem_may_dang_khong_nhan_dien`). Sự cố KHÔNG có `dedupe_khoa` (đa số)
    đi qua nguyên vẹn — hành vi cũ, không lọc gì.

    Đọc/ghi `workspace/gac-tong/da-bao-lap.json` — `{khoa: {"luc": epoch}}`,
    thay MỚI mỗi lượt bằng đúng các khoá còn xuất hiện trong `ds_su_co` lần
    này, nên khoá của sự cố ĐÃ HẾT (không còn trong `ds_su_co`) tự rụng,
    không phình mãi."""
    cu = _doc_da_bao_lap(goc)
    ra: List[Dict[str, Any]] = []
    moi: Dict[str, Any] = {}
    for sc in ds_su_co:
        khoa = sc.get("dedupe_khoa") or ""
        if not khoa:
            ra.append(sc)
            continue
        truoc = cu.get(khoa)
        gio_qua = None
        if isinstance(truoc, dict):
            try:
                gio_qua = (bay_gio.timestamp() - float(truoc.get("luc") or 0)) / 3600.0
            except (TypeError, ValueError):
                gio_qua = None
        try:
            nguong_lap = float(sc.get("lap_gio") or NGUONG_LAP_BAO_GIO)  # chốt an toàn: 4h (ví) / 24h (hạn ngày)
        except (TypeError, ValueError):
            nguong_lap = NGUONG_LAP_BAO_GIO
        if truoc is None or gio_qua is None or gio_qua >= nguong_lap:
            ra.append(sc)
            moi[khoa] = {"luc": bay_gio.timestamp()}
        else:
            moi[khoa] = truoc  # chưa tới lượt báo lại — giữ NGUYÊN mốc cũ
    if moi != cu:
        _ghi_da_bao_lap(goc, moi)
    return ra


#: Loại sự cố cấp máy do `core.chot_an_toan` sinh — được đưa lên giao diện.
LOAI_CANH_BAO_MAY = ("vi_sap_can", "vi_het_tien", "license_rearm_loi", "license_cho_khoi_dong_lai",
                     "license_khoi_dong_lai", "license_het_rearm", "han_vps",
                     "han_vps_sai_dinh_dang", "giong_doc_trung", "chot_an_toan_hong")


def canh_bao_may(ds_su_co: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rút gọn các sự cố cấp máy (không thuộc kênh nào) cho giao diện đọc từ tinh-trang.json."""
    return [{"loai": s["loai"], "muc": s.get("muc", ""), "chuyen_gi": s.get("chuyen_gi", ""),
             "can_lam_gi": s.get("can_lam_gi", ""), "neu_khong_lam": s.get("neu_khong_lam", "")}
            for s in ds_su_co if s.get("loai") in LOAI_CANH_BAO_MAY]


def bao_cao_su_co(
    goc: str,
    anh: Dict[str, Any],
    ds_su_co: List[Dict[str, Any]],
    *,
    bay_gio: Optional[_dt.datetime] = None,
    gui_khan: Optional[GuiHam] = None,
    gui_thuong: Optional[GuiHam] = None,
    ghi_dia: bool = True,
) -> Dict[str, Any]:
    """Ghi `workspace/gac-tong/<ngày>.jsonl` + `workspace/tinh-trang.json`, và
    GỌI `core.bao_dong` cho từng sự cố (mức `khan`/`thuong`) — `bao_dong` tự
    nuốt lỗi mạng + tự tắt khi chưa cấu hình `bao-dong.json`, xem module đó.

    `ghi_dia=False` (dùng cho `--thu`): KHÔNG ghi jsonl/tinh-trang.json, KHÔNG
    gọi `core.bao_dong` — chỉ tính toán, để xem trước sẽ báo gì mà không để
    lại dấu vết nào trên đĩa thật.

    `trang_thai_kenh`/`so_su_co` LUÔN tính từ `ds_su_co` ĐẦY ĐỦ (kênh vẫn
    hiện "CHỜ NGƯỜI" liên tục khi sự cố còn đó) — CHỈ phần thật sự GHI
    (jsonl/`loi-chay-max.md`) và GỬI (`gui_khan`/`gui_thuong`) đi qua
    `_loc_lap_su_co` để khỏi lặp mỗi 15' cho đúng MỘT kết quả cũ (xem
    `NGUONG_LAP_BAO_GIO`).

    Trả `{"so_su_co": int, "so_da_bao": int, "trang_thai_kenh": {ma: {...}}}`.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    gui_khan = gui_khan or bao_dong.bao_dong_khan
    gui_thuong = gui_thuong or bao_dong.bao_dong

    trang_thai_kenh: Dict[str, Any] = {}
    for ma, snap in (anh.get("kenh") or {}).items():
        su_co_kenh = [s for s in ds_su_co if s.get("kenh") == ma]
        trang_thai_kenh[ma] = xep_trang_thai_kenh(snap, su_co_kenh)

    so_da_bao = 0
    if ghi_dia:
        ds_de_bao = _loc_lap_su_co(goc, ds_su_co, bay_gio)
        for sc in ds_de_bao:
            kenh_tk = sc.get("kenh") or None
            try:
                if sc["muc"] == bao_dong.MUC_KHAN:
                    ok = gui_khan(sc["loai"], sc["chuyen_gi"], sc.get("can_lam_gi") or "",
                                  sc.get("neu_khong_lam") or "", goc=goc, kenh=kenh_tk,
                                  bay_gio=bay_gio.timestamp())
                else:
                    ok = gui_thuong(sc["loai"], sc["chuyen_gi"], "", goc=goc, kenh=kenh_tk,
                                    bay_gio=bay_gio.timestamp(), muc=sc["muc"])
            except Exception:  # noqa: BLE001 — một tin gửi hỏng không được chặn các tin sau
                ok = False
            if ok:
                so_da_bao += 1

        _ghi_nhat_ky_jsonl(goc, bay_gio, ds_de_bao)
        _ghi_loi_chay_max_md(goc, bay_gio, ds_de_bao)
        _ghi_tinh_trang(goc, {
            "luc": bay_gio.isoformat(timespec="seconds"),
            "kenh": trang_thai_kenh,
            "so_su_co": len(ds_su_co),
            "may": anh.get("may") or {},
            # Cảnh báo cấp MÁY của các chốt an toàn (ví/license/hạn VPS/giọng đọc) — giao
            # diện (`core.bang_dieu_khien`) đọc mục này. Luôn ghi ĐẦY ĐỦ (không lọc lặp).
            "canh_bao_may": canh_bao_may(ds_su_co),
        })

    return {"so_su_co": len(ds_su_co), "so_da_bao": so_da_bao, "trang_thai_kenh": trang_thai_kenh}


# ── Tự mở khoá gói kẹt QA (30/09/2026) ──────────────────────────────────────
#
# Gói kẹt trong `DONE/` vì `qa-loi.txt` (vd cổng độ dài cũ) không tự được kiểm
# lại sau khi luật QA nới. Mỗi `NGUONG_KIEM_LAI_QA_GIO` giờ, gác tổng chạy lại
# QA (`ban_giao_dang.kiem_lai_goi_ket`): đạt thì điền Sẵn sàng + khe trống sớm
# nhất; chưa đạt vì lỗi thật thì CHỈ báo (mức thường, lọc lặp 4 giờ qua
# `dedupe_khoa` như mọi sự cố khác). QA chạy FFmpeg nên giữ khe "nang"
# (`core.khe.thu_giu`, KHÔNG xếp hàng — bận thì để lần 15' sau); tối đa
# `TOI_DA_GOI_MOI_LUOT` gói mỗi lượt.

NGUONG_KIEM_LAI_QA_GIO = 1.0
TOI_DA_GOI_MOI_LUOT = 2


def _duong_qa_ket(goc: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "qa-ket.json")


def kiem_lai_goi_ket_dinh_ky(
    goc: str,
    ds_kenh: List[str],
    *,
    bay_gio: Optional[_dt.datetime] = None,
    ghi_dia: bool = True,
    kiem_lai: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    thu_giu: Optional[Callable[..., Any]] = None,
) -> List[Dict[str, Any]]:
    """Trả sự cố "gói kẹt QA vì lỗi thật" (rỗng nếu không có). Không bao giờ
    ném lỗi ra ngoài — hỏng ở đây không được chặn các bước gác khác."""
    from . import ban_giao_dang  # noqa: PLC0415 — tránh vòng nhập

    bay_gio = bay_gio or _dt.datetime.now()
    kiem_lai = kiem_lai or ban_giao_dang.kiem_lai_goi_ket
    thu_giu = thu_giu or khe.thu_giu
    try:
        st = _doc_json_an_toan(_duong_qa_ket(goc))
        st = st if isinstance(st, dict) else {}
        goi: Dict[str, Any] = st.get("goi") if isinstance(st.get("goi"), dict) else {}
        ket = {k: ban_giao_dang.liet_ke_goi_ket(goc, k) for k in ds_kenh}
        con_ket = {m for ds in ket.values() for m in ds}
        goi = {m: v for m, v in goi.items() if m in con_ket}   # đã mở/bỏ thì rụng
        luc = float(st.get("luc") or 0)
        den_han = (bay_gio.timestamp() - luc) / 3600.0 >= NGUONG_KIEM_LAI_QA_GIO
        da_kiem = False
        if ghi_dia and con_ket and den_han:
            phien = thu_giu(goc, khe.LOP_NANG, "qa-kiem-lai", "", 5, None, 1800)
            if phien is not None:   # bận khe: không đánh dấu, 15' sau thử lại
                try:
                    da_kiem = True
                    for k, ds in ket.items():
                        if not ds:
                            continue
                        for r in kiem_lai(goc, k, toi_da=TOI_DA_GOI_MOI_LUOT):
                            if r["ket_qua"] == "chua_dat":
                                goi[r["ma"]] = {"kenh": k, "loi": list(r.get("loi") or [])}
                            else:
                                goi.pop(r["ma"], None)
                finally:
                    phien.nha()
        if ghi_dia and (da_kiem or (not con_ket and den_han)):
            luc = bay_gio.timestamp()
        if ghi_dia:
            tam = _duong_qa_ket(goc) + ".tmp"
            os.makedirs(os.path.dirname(tam), exist_ok=True)
            with open(tam, "w", encoding="utf-8") as tep:
                json.dump({"luc": luc, "goi": goi}, tep, ensure_ascii=False, indent=1)
            os.replace(tam, _duong_qa_ket(goc))
        return [_su_co(
            "qa_goi_ket", bao_dong.MUC_THUONG, kenh=v.get("kenh") or "",
            chuyen_gi="Gói {0} nằm kẹt vì QA chưa đạt: {1}".format(
                m, "; ".join(v.get("loi") or ["(không rõ)"])[:300]),
            dedupe_khoa="qa-ket:" + m) for m, v in sorted(goi.items())]
    except Exception:  # noqa: BLE001
        return []


GietPid = Callable[[int], bool]


def _duong_nghi_treo(goc: str) -> str:
    return os.path.join(goc, "workspace", "gac-tong", "nghi-treo.json")


def _doc_nghi_treo(goc: str) -> Dict[str, Any]:
    du = _doc_json_an_toan(_duong_nghi_treo(goc))
    return du if isinstance(du, dict) else {}


def _ghi_nghi_treo(goc: str, du_lieu: Dict[str, Any]) -> None:
    """Ghi NGUYÊN TỬ — cùng khuôn `_ghi_tinh_trang`."""
    try:
        duong = _duong_nghi_treo(goc)
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        tam = duong + ".tmp"
        with open(tam, "w", encoding="utf-8") as tep:
            json.dump(du_lieu, tep, ensure_ascii=False, indent=1)
        os.replace(tam, duong)
    except OSError:
        pass


def tu_sua(
    goc: str,
    anh: Dict[str, Any],
    *,
    bay_gio: Optional[_dt.datetime] = None,
    ghi_dia: bool = True,
    giet: Optional[GietPid] = None,
) -> List[Dict[str, Any]]:
    """Tự sửa AN TOÀN những ca RÕ RÀNG (mục 2, `workspace/ban-va/
    2026-09-29-tu-canh-loi/GHI-CHU.md`). Mỗi hành động trả về MỘT dict
    `{"loai","chuyen_gi","kenh","thuc_hien"}` và luôn được GHI LẠI (jsonl +
    `loi-chay-max.md`) — "mọi hành động tự sửa đều ghi lại", không âm thầm.

    `ghi_dia=False` (dùng cho `--thu`) chỉ TÍNH sẽ làm gì — KHÔNG thật sự xoá
    tệp/giết tiến trình nào, và KHÔNG ghi đĩa (cùng nếp `bao_cao_su_co`).

    Hai ca, đúng những gì đặc tả gọi là "rõ ràng":

    1. `.khoa-may` trỏ PID đã CHẾT (`khoa_may.con_song is False`) → xoá tệp
       khoá qua `core.khe.xoa_tep_ben_vung` — không có gì để mất: PID đã chết
       nghĩa là KHÔNG CÒN AI thật sự giữ khoá, kênh khác đang chờ oan.
    2. Một tiến trình `tu_chay.py` đứng khâu quá `NGUONG_TU_DUNG_KHAU_PHUT`
       phút → dừng đúng PID đó (`tien_trinh_con.giet_pid`). Lượt TỰ NHẶT LẠI
       ở lần lịch kế tiếp — `core.tu_chay` đã có sẵn khoá độc quyền +
       `_tim_run_chua_xong` + vân tay từng khâu để làm tiếp, không mở video
       mới, không tiêu lại tiền đã tiêu (xem `core/lich_tu_chay.py`, mục
       "LẶP TRONG NGÀY = TỰ THỬ LẠI").

    ═══ VÁ 29/09/2026 (đêm) — sự cố báo giả TL3-T7 SUÝT giết một lượt ĐANG
    dựng thật (xem `workspace/loi-chay-max.md`) ═══

    Ca 2 giờ ĐÂY KHÔNG BAO GIỜ dừng một tiến trình đang giữ khe "nang" chỉ vì
    MỘT tín hiệu yếu (mtime một tệp đứng yên) — `NGUONG_TU_DUNG_KHAU_PHUT`
    giờ đo bằng `snap["bao_cao_tuoi_phut"]` đã là MAX của bốn nguồn độc lập
    (xem `_moc_hoat_dong_tuoi_phut`: log thật-thời-gian, tệp lượt, nhật ký
    khe, tệp báo cáo ngày) — nghĩa là tự nó đã gồm "không tệp nào trong thư
    mục lượt đổi" LẪN "không dòng log mới". `viec == "tai_len"` vẫn CHẶN
    CỨNG tuyệt đối (không có ngoại lệ nào, kể cả đủ bằng chứng — giữa lúc tải
    lên là trình duyệt thật đang mở, CLAUDE.local.md luật riêng VPS #2).

    Với MỌI việc khác (dựng/phụ đề/giọng/QA/quét…) — kể cả khi tuổi đã vượt
    `NGUONG_TU_DUNG_KHAU_PHUT` — vẫn CHƯA đủ để giết: cần thêm BẰNG CHỨNG THỨ
    BA, CPU tiến trình KHÔNG NHÍCH (`NGUONG_CPU_GIAY_DUNG_YEN`), quan sát
    LIÊN TỤC qua NHIỀU lần chạy `--mot-luot` (mỗi 15') trong ÍT NHẤT
    `NGUONG_TU_DUNG_KHAU_PHUT` phút NỮA — ghi nhớ ở `workspace/gac-tong/
    nghi-treo.json` (một bản ghi DUY NHẤT, vì khe "nang" độc quyền cả máy).
    Đổi PID, hoặc CPU vừa nhích (bằng chứng "còn sống thật") → đặt LẠI mốc
    theo dõi, không giết. Tổng thời gian im lặng + đứng CPU trước khi bị
    dừng: khoảng `2 × NGUONG_TU_DUNG_KHAU_PHUT` phút (mặc định ~4 giờ) — cố ý
    dài hơn hẳn "một video mất 2–4 giờ" (`core/lich_tu_chay.py`).
    """
    bay_gio = bay_gio or _dt.datetime.now()
    giet = giet or tien_trinh_con.giet_pid
    may = anh.get("may") or {}
    hanh_dong: List[Dict[str, Any]] = []

    khoa = may.get("khoa_may") or {}
    if khoa.get("co") and khoa.get("pid") and khoa.get("con_song") is False:
        # VÁ 06/10/2026: KHÔNG xoá theo ẢNH CHỤP đầu lượt nữa — giữa lúc chụp và lúc
        # tới đây (chốt ví, QA kiểm lại gói… có khi vài phút) một lượt MỚI có thể đã
        # giành khoá. `ben_bi.don_khoa_chet_an_toan` đọc lại tệp NGAY LÚC XOÁ: chỉ xoá
        # khi vẫn đúng PID/mốc đã thấy, PID vẫn chết và khoá đủ tuổi
        # (`ben_bi.TUOI_KHOA_CHET_TOI_THIEU_GIAY`); đổi tên nguyên tử rồi đọc lại.
        if ghi_dia:
            da_xoa, _ly_do = ben_bi.don_khoa_chet_an_toan(
                khe.duong_khoa_nang(goc), pid_thay=int(khoa.get("pid") or 0),
                bat_dau_thay=khoa.get("bat_dau"), bay_gio=bay_gio.timestamp(),
                pid_con_song=khe.pid_con_song)
        else:
            tuoi = khoa.get("tuoi_giay")
            da_xoa = tuoi is None or float(tuoi) >= ben_bi.TUOI_KHOA_CHET_TOI_THIEU_GIAY
        if da_xoa:
            hanh_dong.append({
                "loai": "don_khoa_may_chet", "kenh": "", "thuc_hien": ghi_dia,
                "chuyen_gi": "Xoá khoá .khoa-may trỏ PID {0} đã CHẾT.".format(khoa.get("pid")),
            })

    nang = (may.get("khe") or {}).get("nang")
    # Tuyệt đối không giết giữa lúc tải lên (CLAUDE.local.md luật riêng VPS
    # #2) — CHẶN CỨNG, không có bằng chứng nào đủ để vượt qua điều kiện này.
    xet_treo = isinstance(nang, dict) and str(nang.get("viec") or "") != "tai_len"
    ma_giu = str(nang.get("kenh") or "") if isinstance(nang, dict) else ""
    pid = 0
    if xet_treo:
        try:
            pid = int(nang.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
    snap = (anh.get("kenh") or {}).get(ma_giu) if ma_giu else None
    tuoi_phut = snap.get("bao_cao_tuoi_phut") if isinstance(snap, dict) else None
    can_xet_bang_chung = bool(
        xet_treo and pid and tuoi_phut is not None and tuoi_phut > NGUONG_TU_DUNG_KHAU_PHUT)

    nghi_cu = _doc_nghi_treo(goc)
    if can_xet_bang_chung:
        cpu_hien_tai = nang.get("cpu_giay") if isinstance(nang, dict) else None
        pid_cu = nghi_cu.get("pid")
        cpu_cu = nghi_cu.get("cpu_giay")
        tu_luc = nghi_cu.get("tu_luc")
        cpu_dung_yen = bool(
            cpu_hien_tai is not None and cpu_cu is not None and
            abs(float(cpu_hien_tai) - float(cpu_cu)) < NGUONG_CPU_GIAY_DUNG_YEN)
        du_thoi_gian_theo_doi = bool(
            pid_cu == pid and tu_luc is not None and
            (bay_gio.timestamp() - float(tu_luc)) / 60.0 >= NGUONG_TU_DUNG_KHAU_PHUT)
        if pid_cu == pid and cpu_dung_yen and du_thoi_gian_theo_doi:
            if ghi_dia:
                giet(pid)
                _ghi_nghi_treo(goc, {})
            hanh_dong.append({
                "loai": "dung_tu_chay_treo", "kenh": ma_giu, "pid": pid,
                "thuc_hien": ghi_dia,
                "chuyen_gi": ("Dừng tiến trình tu_chay.py (PID {0}) của kênh "
                             "{1} — đứng khâu “{2}” {3:.0f} phút không log/"
                             "tệp mới, CPU cũng đứng yên suốt ≥{4:.0f} phút "
                             "theo dõi.").format(
                    pid, ma_giu or "?", nang.get("viec") or "?", tuoi_phut,
                    NGUONG_TU_DUNG_KHAU_PHUT),
            })
        elif ghi_dia and (pid_cu != pid or not cpu_dung_yen):
            # Mới nghi ngờ (đổi PID), hoặc CPU vừa nhích (còn sống thật) —
            # đặt LẠI mốc theo dõi, KHÔNG dừng gì lần này (chưa đủ bằng
            # chứng, dù `tuoi_phut` đã vượt ngưỡng).
            _ghi_nghi_treo(goc, {"pid": pid, "kenh": ma_giu,
                                 "tu_luc": bay_gio.timestamp(),
                                 "cpu_giay": cpu_hien_tai})
        # else: cùng PID, CPU đứng yên nhưng CHƯA đủ thời gian theo dõi — giữ
        # NGUYÊN mốc `tu_luc` cũ (không ghi lại), để lần lịch sau tính đủ giờ.
    elif ghi_dia and nghi_cu:
        # Không (hoặc không còn) nghi treo kênh nào — dọn mốc theo dõi cũ,
        # tránh giữ "tu_luc" của một PID đã đổi việc/đã xong việc.
        _ghi_nghi_treo(goc, {})

    if hanh_dong and ghi_dia:
        su_co_ghi = [_su_co("tu_sua:" + h["loai"], bao_dong.MUC_THUONG,
                            kenh=h.get("kenh") or "", chuyen_gi=h["chuyen_gi"])
                    for h in hanh_dong]
        _ghi_nhat_ky_jsonl(goc, bay_gio, su_co_ghi)
        _ghi_loi_chay_max_md(goc, bay_gio, su_co_ghi)
    return hanh_dong


#: NHỊP TIM AGENT (04/10/2026): sự cố agent `vm/agent.py` đứng im 2 giờ dù tiến trình còn sống. Agent ghi
#: `vm/logs/nhip-tim.json` {pid, luc, buoc}; cũ hơn ngưỡng → dừng PID (giao diện tự bật lại agent trong ~10 giây).
NGUONG_NHIP_TIM_CU_PHUT = 20.0
#: Đang tải lên thì chờ lâu hơn hẳn — tải lên hợp lệ có thể kéo dài; quá mức này mới coi là treo.
NGUONG_NHIP_TIM_CU_KHI_TAI_PHUT = 60.0


def _dang_tai_len(goc: str) -> bool:
    """Có lượt tải lên đang chạy: tệp `dang-dodang.json` (vm/logs hoặc logs) hoặc tiến trình `may_dang_dom`."""
    for ten in (os.path.join(goc, "vm", "logs", "dang-dodang.json"), os.path.join(goc, "logs", "dang-dodang.json")):
        if os.path.exists(ten):
            return True
    try:
        import subprocess  # noqa: PLC0415
        ra = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*may_dang_dom.p[y]*' }).ProcessId"],
            capture_output=True, text=True, timeout=30)
        return any(d.strip().isdigit() for d in (ra.stdout or "").splitlines())
    except Exception:  # noqa: BLE001 — không dò được thì coi như ĐANG tải (an toàn: không giết)
        return True


def _pid_la_agent(pid: int) -> bool:
    try:
        import subprocess  # noqa: PLC0415
        ra = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance Win32_Process -Filter 'ProcessId={0}').CommandLine".format(int(pid))],
            capture_output=True, text=True, timeout=30)
        return "agent.py" in (ra.stdout or "")
    except Exception:  # noqa: BLE001
        return False


def tu_sua_agent_treo(
    goc: str,
    *,
    bay_gio: Optional[_dt.datetime] = None,
    ghi_dia: bool = True,
    giet: Optional[GietPid] = None,
    dang_tai: Optional[Callable[[str], bool]] = None,
    la_agent: Optional[Callable[[int], bool]] = None,
) -> List[Dict[str, Any]]:
    """Nhịp tim agent cũ quá ngưỡng → dừng PID agent + ghi sự cố. Không đọc được/chưa có nhịp tim → bỏ qua.
    Có lượt tải lên đang chạy → chỉ dừng khi cũ hơn `NGUONG_NHIP_TIM_CU_KHI_TAI_PHUT`."""
    bay_gio = bay_gio or _dt.datetime.now()
    nhip = _doc_json_an_toan(os.path.join(goc, "vm", "logs", "nhip-tim.json"))
    if not isinstance(nhip, dict):
        return []
    try:
        pid, luc = int(nhip["pid"]), float(nhip["luc"])
    except (KeyError, TypeError, ValueError):
        return []
    tuoi = (bay_gio.timestamp() - luc) / 60.0
    if tuoi <= NGUONG_NHIP_TIM_CU_PHUT or not _pid_con_song(pid):
        return []
    if (dang_tai or _dang_tai_len)(goc) and tuoi <= NGUONG_NHIP_TIM_CU_KHI_TAI_PHUT:
        return []
    if not (la_agent or _pid_la_agent)(pid):
        return []
    if ghi_dia:
        (giet or tien_trinh_con.giet_pid)(pid)
    h = {"loai": "agent_treo", "kenh": "", "pid": pid, "thuc_hien": ghi_dia,
         "chuyen_gi": "agent treo — đã tự khởi động lại (dừng PID {0}; nhịp tim cũ {1:.0f} phút, bước cuối: {2})".format(
             pid, tuoi, str(nhip.get("buoc") or "?")[:120])}
    if ghi_dia:
        su_co = [_su_co("tu_sua:agent_treo", bao_dong.MUC_THUONG, chuyen_gi=h["chuyen_gi"])]
        _ghi_nhat_ky_jsonl(goc, bay_gio, su_co)
        _ghi_loi_chay_max_md(goc, bay_gio, su_co)
    return [h]


def tu_xu_ly_viec_may(
    goc: str,
    anh: Dict[str, Any],
    *,
    bay_gio: Optional[_dt.datetime] = None,
    ghi_dia: bool = True,
    dang_ky_lich: Optional[Callable[[str], Any]] = None,
) -> List[Dict[str, Any]]:
    """Việc máy TỰ làm thay vì hiện "Việc của bạn" (04/10/2026, chủ dự án: "mọi thứ auto 100%"):

    * "lich": có kênh `tu_chay` mà lịch Windows tắt → đăng ký lại (`lich_tu_chay.dang_ky`, `/F` an toàn).
      (Máy nền Agent/Máy đăng: đã có `core.giam_sat_vm` trong giao diện tự bật lại; gác tổng KHÔNG sinh được tiến
      trình giao diện nên không tự xử ở đây.)
    KHÔNG đụng `tu_don`/`tu_chay`/`tu_dang`/`ngan_sach_ngay` (CLAUDE.md: do chủ quyết). Mỗi việc thử tối đa 1 lần / 6 giờ;
    sổ `workspace/gac-tong/tu-xu-ly.json` cho bảng điều khiển biết (`bang_dieu_khien.da_tu_xu_ly`): thử hỏng hoặc
    ≥ 3 lần vẫn còn thì mới hiện cho người. `ghi_dia=False` (`--thu`): chỉ tính, không làm gì."""
    bay_gio = bay_gio or _dt.datetime.now()
    may = anh.get("may") or {}
    cu: Dict[str, Any] = _doc_json_an_toan(bang_dieu_khien.duong_tu_xu_ly(goc))
    cu = cu if isinstance(cu, dict) else {}
    co_tu_chay = any(bool(s.get("tu_chay")) for s in (anh.get("kenh") or {}).values())

    def _lich() -> Any:
        return (dang_ky_lich or (lambda g: lich_tu_chay.dang_ky(g, "02:00")))(goc)

    viec = (("lich", co_tu_chay and not (may.get("schtasks_tu_chay") or {}).get("da_dang_ky"), _lich,
             "Lịch tự chạy đang tắt — máy tự đăng ký lại 02:00 hằng ngày."),)
    moi: Dict[str, Any] = {}
    hanh_dong: List[Dict[str, Any]] = []
    for khoa, dieu_kien, ham, cau in viec:
        if not dieu_kien:
            continue  # hết cớ → quên sổ
        b = cu.get(khoa) if isinstance(cu.get(khoa), dict) else None
        tuoi = None
        if b:
            try:
                tuoi = (bay_gio - _dt.datetime.fromisoformat(str(b.get("luc"))[:19])).total_seconds() / 3600.0
            except ValueError:
                tuoi = None
        if b and tuoi is not None and 0 <= tuoi < NHIP_TU_XU_LY_GIO:
            moi[khoa] = b  # mới thử xong — giữ nguyên, chưa tới lượt thử lại
            continue
        so_lan = int(b.get("so_lan") or 1) + 1 if b and tuoi is not None and tuoi < 24.0 else 1
        ok, ghi_chu = True, ""
        if ghi_dia:
            try:
                kq = ham()
                ok, ghi_chu = (bool(kq[0]), str(kq[1])) if isinstance(kq, tuple) else (bool(kq), "")
            except Exception as loi:  # noqa: BLE001 — tự xử hỏng thì để người thấy, không sập gác tổng
                ok, ghi_chu = False, "{0}: {1}".format(type(loi).__name__, str(loi)[:120])
        moi[khoa] = {"luc": bay_gio.isoformat(timespec="seconds"), "ket": "ok" if ok else "loi",
                     "so_lan": so_lan, "ghi_chu": ghi_chu[:160]}
        hanh_dong.append({"loai": "tu_xu_ly:" + khoa, "kenh": "", "thuc_hien": ghi_dia and ok,
                          "chuyen_gi": cau + ("" if ok or not ghi_dia else " (HỎNG: {0})".format(ghi_chu[:100]))})
    if ghi_dia and moi != cu:
        try:
            duong = bang_dieu_khien.duong_tu_xu_ly(goc)
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            with open(duong + ".tmp", "w", encoding="utf-8") as tep:
                json.dump(moi, tep, ensure_ascii=False, indent=1)
            os.replace(duong + ".tmp", duong)
        except OSError:
            pass
    if hanh_dong and ghi_dia:  # chỉ nhật ký jsonl — KHÔNG ghi loi-chay-max.md (không phải sự cố cần người)
        _ghi_nhat_ky_jsonl(goc, bay_gio, [_su_co(h["loai"], bao_dong.MUC_THUONG, h["chuyen_gi"]) for h in hanh_dong])
    return hanh_dong


def _co_video_moi(snap: Dict[str, Any], bay_gio: _dt.datetime) -> bool:
    for d in snap.get("ke_hoach") or []:
        if d.get("_loai") != "da_dang":
            continue
        hen = _ghep_ngay_gio(d.get("Ngày đăng", ""), d.get("Giờ đăng", ""))
        if hen is not None and (bay_gio - hen).total_seconds() <= NGUONG_KHONG_VIDEO_MOI_GIO * 3600:
            return True
    return False


def ban_tin_ngay(
    goc: str,
    anh: Dict[str, Any],
    ds_su_co: Optional[List[Dict[str, Any]]] = None,
    *,
    bay_gio: Optional[_dt.datetime] = None,
    so_du_vnd: Optional[float] = None,
    so_ngay_license_con_lai: Optional[int] = None,
) -> str:
    """"Máy còn sống" — một khối chữ, MỘT DÒNG/KÊNH: trạng thái, video mới,
    số video đã hẹn lịch/đã công khai. Kèm dòng MÁY (đĩa, trạm) và — khi nơi
    gọi truyền vào — số dư ví/ngày license Windows còn lại (V8/V5, KHÔNG tự
    gọi mạng lấy hai số này ở đây; nơi gọi tự lấy rồi truyền vào, đúng khuôn
    `core.bang_dieu_khien.dong_may` đã dùng cho `so_du_micro`).
    """
    bay_gio = bay_gio or _dt.datetime.now()
    ds_su_co = ds_su_co if ds_su_co is not None else kiem_su_co(anh)

    dong: List[str] = ["═══ Máy còn sống — {0} ═══".format(bay_gio.strftime("%d/%m/%Y %H:%M"))]
    for ma in sorted((anh.get("kenh") or {}).keys()):
        snap = (anh.get("kenh") or {})[ma]
        su_co_kenh = [s for s in ds_su_co if s.get("kenh") == ma]
        tk = xep_trang_thai_kenh(snap, su_co_kenh)
        video_moi = "có" if _co_video_moi(snap, bay_gio) else "không"
        so_hen = sum(1 for d in snap.get("ke_hoach") or [] if d.get("_loai") == "sap_dang")
        so_cong_khai = sum(1 for d in snap.get("ke_hoach") or [] if d.get("_loai") == "da_dang")
        dong.append("{0}: {1} — video mới: {2} — đã hẹn lịch: {3} — đã công khai: {4}{5}".format(
            ma, _NHAN_TRANG_THAI[tk["trang_thai"]], video_moi, so_hen, so_cong_khai,
            " — kênh mới, đang làm video đầu" if snap.get("kenh_moi") and not so_cong_khai else ""))

    may = anh.get("may") or {}
    con_gb = (may.get("dia") or {}).get("con_gb")
    dong.append("")
    dong.append("Máy: đĩa còn {0} — trạm 8765 {1}".format(
        "{0:.1f} GB".format(con_gb) if con_gb is not None else "(không rõ)",
        "sống" if may.get("cong_8765_tram") else "KHÔNG phản hồi"))
    if so_du_vnd is not None:
        dong.append("Ví: {0:,.0f}đ".format(so_du_vnd).replace(",", "."))
    if so_ngay_license_con_lai is not None:
        dong.append("Windows: còn {0} ngày trước khi hết hạn đánh giá.".format(
            so_ngay_license_con_lai))
    canh_bao = canh_bao_may(ds_su_co)
    if canh_bao:
        dong.append("")
        dong.append("CẢNH BÁO CẤP MÁY (ví / Windows / hạn VPS / giọng đọc):")
        for c in canh_bao:
            dong.append("  - {0}".format(c["chuyen_gi"]))
            if c.get("can_lam_gi"):
                dong.append("    Việc cần làm: {0}".format(c["can_lam_gi"]))
    return "\n".join(dong)


# ── Giám đốc kênh (01/10/2026) ──────────────────────────────────────────────


def kiem_giam_doc(goc: str, *, bay_gio: Optional[_dt.datetime] = None,
                  ghi_dia: bool = True) -> List[Dict[str, Any]]:
    """Sự cố của giám đốc kênh cho gác tổng:

    * `giam_doc_ket` (mức thường): kênh bật giám đốc đến hạn liền ≥ 6 giờ mà chưa chạy được lượt nào
      (`giam_doc.kiem_ket`);
    * `giam_doc_viec` (mức nhắc): mỗi dòng "Việc của bạn" trong báo cáo cuối của giám đốc — `dedupe_khoa`
      theo nội dung nên cùng một việc chỉ nhắc lại sau `NGUONG_LAP_BAO_GIO` (4 giờ).

    `ghi_dia=False` (`--thu`): chỉ đọc, không ghi `den-han.json`."""
    import hashlib  # noqa: PLC0415

    from core import giam_doc  # noqa: PLC0415

    ra: List[Dict[str, Any]] = []
    for k in giam_doc.kiem_ket(goc, bay_gio=bay_gio, ghi=ghi_dia):
        ra.append(_su_co(
            "giam_doc_ket", bao_dong.MUC_THUONG, kenh=k["ma"],
            chuyen_gi="Giám đốc kênh {0} đến hạn {1:.0f} giờ mà chưa chạy được lượt nào ({2}).".format(
                k["ma"], k["gio"], k["ly_do"]),
            can_lam_gi="Xem workspace/giam-doc/tien-trinh.log; tắt tạm bằng kenh.yaml giam_doc: tat nếu cần.",
            neu_khong_lam="Kênh không có ai đọc số và đề xuất việc sau khi đăng.",
            dedupe_khoa="giam_doc:ket:" + k["ma"]))
    for ma in giam_doc._kenh_bat(goc):  # noqa: SLF001
        for viec in giam_doc.viec_cua_ban_kenh(goc, ma, bay_gio=bay_gio):
            loai = giam_doc.phan_loai_viec(viec)
            if loai != "nguoi":
                # 04/10/2026: "chờ N video qua 48h…" = máy tự đợi; "mở Studio xem / kiểm tra bảng pool…" = bộ não
                # tự xem (`nao/viec-tu-giam-doc.json`). KHÔNG báo người, KHÔNG ghi loi-chay-max.md.
                if ghi_dia:
                    try:
                        giam_doc.ghi_viec_may(goc, ma, viec, loai, bay_gio=bay_gio)
                    except Exception:  # noqa: BLE001 — hàng đợi hỏng không được làm sập gác tổng
                        pass
                continue
            sc = _su_co(
                "giam_doc_viec", bao_dong.MUC_NHAC, kenh=ma,
                chuyen_gi="Giám đốc kênh {0}: {1}".format(ma, viec[:300]), can_lam_gi=viec[:300],
                dedupe_khoa="giam_doc:viec:{0}:{1}".format(ma, hashlib.sha1(viec.encode("utf-8")).hexdigest()[:12]))
            sc["lap_gio"] = NGUONG_LAP_VIEC_NGUOI_GIO  # cảnh báo chính sách thật: 1 lần/ngày, không phải mỗi 4 giờ
            ra.append(sc)
    return ra


# ── `python -m core.gac_tong --mot-luot [--thu]` ────────────────────────────


def _main(argv: Optional[List[str]] = None, *, goc: Optional[str] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    danh_sach = sys.argv[1:] if argv is None else argv
    if "--mot-luot" not in danh_sach:
        print("Dùng: python -m core.gac_tong --mot-luot [--thu]")
        print("  --thu: chỉ tính toán và in ra — KHÔNG ghi đĩa, KHÔNG gọi core.bao_dong.")
        return 0

    goc = goc or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    thu = "--thu" in danh_sach

    # 06/10/2026 (kiểm toán 1 năm): trước đây MỘT ngoại lệ ở `chup_trang_thai`/
    # `bao_cao_su_co`/`tu_sua` làm cả lượt chết im (pythonw không console) — mỗi 15'
    # lại chết đúng chỗ đó, không ai biết. Giờ: nhịp tim `workspace/gac-tong/nhip.json`
    # (bộ điều phối canh nó, `ben_bi.canh_gac_tong`), sổ sập liền + báo khẩn từ lần
    # thứ 2 (`ben_bi.ghi_loi_vong`).
    if not thu:
        ben_bi.ghi_nhip(goc, "gac_tong", "bat_dau")
    try:
        ma_ra = _mot_luot(goc, thu)
    except Exception as loi:  # noqa: BLE001 — lưới cuối của cả lượt
        if not thu:
            ben_bi.ghi_loi_vong(goc, "gac_tong", loi)
            ben_bi.ghi_nhip(goc, "gac_tong", "sap: {0}: {1}".format(type(loi).__name__, str(loi)[:120]))
        print("Gác tổng: lượt này SẬP ({0}: {1}) — lượt 15' sau tự chạy lại.".format(
            type(loi).__name__, str(loi)[:200]))
        return 1
    if not thu:
        ben_bi.xoa_loi_vong(goc, "gac_tong")
        ben_bi.ghi_nhip(goc, "gac_tong", "xong")
    return ma_ra


#: Hạn giờ CỨNG một lượt `--mot-luot` (lịch 15', `IgnoreNew`, hạn mặc định 72 giờ):
#: lượt treo quá mức này tự thoát (`ben_bi.hen_gio_tu_thoat`) để lượt sau chạy được.
#: Rộng tay vì QA kiểm lại gói (FFmpeg) có thể chạy tới ~30 phút.
GIAY_TOI_DA_MOT_LUOT = 40 * 60


def _mot_luot(goc: str, thu: bool) -> int:
    anh = chup_trang_thai(goc)
    # `so_du_vnd` KHÔNG tự lấy ở đây — `chup_trang_thai`/`kiem_su_co` chủ đích
    # KHÔNG gọi mạng (xem docstring đầu tệp + `NGUONG_VI_SO_NGAY`); kiểm "ví
    # < 3 ngày chạy" chỉ hoạt động khi có nơi khác truyền số dư thật vào.
    ds_su_co = kiem_su_co(anh)
    # Hai điều kiện THẬT SỰ mất tiền (06/10/2026): kênh 48h không video mới đã ở
    # `_kiem_khong_video_moi`; đây là "cả máy 36h không ra gói mới" + máy nền chết hẳn.
    ds_su_co += ben_bi.kiem_khong_san_xuat(goc, anh, ghi_dia=not thu)
    thu_muc_vm_gt = tt.thu_muc_vm(goc)
    hanh_dong_hoi_sinh, su_co_hoi_sinh = ben_bi.hoi_sinh_may_nen(goc, thu_muc_vm_gt, ghi_dia=not thu)
    ds_su_co += su_co_hoi_sinh + ben_bi.kiem_agent_sap(goc, thu_muc_vm_gt)
    # Bốn chốt an toàn 1 năm (30/09/2026, `core/chot_an_toan.py`): ví, license Windows (rearm
    # + khởi động lại lúc rảnh), hạn thuê VPS, giọng đọc trùng. `--thu` chỉ chạy phần thuần
    # (không gọi mạng, không rearm, không ghi đĩa).
    so_du_vnd = None
    ngay_license = None
    try:
        from core import chot_an_toan  # noqa: PLC0415

        if thu:
            ds_su_co += chot_an_toan.kiem_han_vps(goc) + chot_an_toan.kiem_giong_trung(goc)
        else:
            kq_chot = chot_an_toan.kiem_tat_ca(goc)
            ds_su_co += kq_chot["su_co"]
            so_du_vnd = kq_chot["so_du_vnd"]
            ngay_license = kq_chot["license_ngay"]
    except Exception as loi_chot:  # noqa: BLE001 — chốt hỏng không được làm sập gác tổng
        ds_su_co.append(_su_co(
            "chot_an_toan_hong", bao_dong.MUC_NHAC,
            "Các chốt an toàn (ví/license/hạn VPS/giọng) không chạy được: {0}".format(str(loi_chot)[:150]),
            can_lam_gi="Báo người quản trị tool xem nhật ký.", dedupe_khoa="chot:tat_ca"))
    ds_su_co += kiem_lai_goi_ket_dinh_ky(goc, sorted((anh.get("kenh") or {}).keys()), ghi_dia=not thu)
    # Giám đốc kênh (01/10/2026, `core/giam_doc`): `nhip` chỉ QUYẾT có việc không, có thì sinh tiến trình
    # tách rời `python -m core.giam_doc --chay` (khoá `workspace/giam-doc/.khoa`). try riêng — hỏng không
    # được làm sập gác tổng.
    tom_tat_gd = ""
    try:
        from core import giam_doc  # noqa: PLC0415

        kq_gd = giam_doc.nhip(goc, thu=thu)
        tom_tat_gd = "{0} kênh đến hạn — {1}".format(len(kq_gd.get("viec") or []), kq_gd.get("ly_do"))
        ds_su_co += kiem_giam_doc(goc, ghi_dia=not thu)
    except Exception as loi_gd:  # noqa: BLE001
        tom_tat_gd = "không chạy được ({0})".format(str(loi_gd)[:200])
        ds_su_co.append(_su_co(
            "giam_doc_hong", bao_dong.MUC_NHAC,
            "Giám đốc kênh không chạy được: {0}".format(str(loi_gd)[:150]),
            can_lam_gi="Báo người quản trị tool xem nhật ký.", dedupe_khoa="giam_doc:hong"))
    # Mở kênh mới (04/10/2026, `core/mo_kenh`): chỉ QUYẾT có bước đến hạn không (kích hoạt kênh đã đăng nhập, chuẩn bị
    # kênh đã đăng ký, đề xuất định kỳ 7 ngày/lần); có thì sinh `python -m core.mo_kenh tiep-tuc` tách rời. try riêng.
    tom_tat_mk = ""
    try:
        from core import mo_kenh  # noqa: PLC0415

        kq_mk = mo_kenh.nhip(goc, thu=thu)
        tom_tat_mk = ("đã sinh tiến trình — " if kq_mk.get("sinh") else "") + str(kq_mk.get("ly_do") or "")
    except Exception as loi_mk:  # noqa: BLE001 — mở kênh hỏng không được làm sập gác tổng
        tom_tat_mk = "không chạy được ({0})".format(str(loi_mk)[:200])
    ket_qua = bao_cao_su_co(goc, anh, ds_su_co, ghi_dia=not thu)
    hanh_dong_tu_sua: List[Dict[str, Any]] = []
    try:
        hanh_dong_tu_sua += tu_sua(goc, anh, ghi_dia=not thu)
    except Exception as loi_ts:  # noqa: BLE001 — tự sửa hỏng không được chặn các bước sau
        print("Tự sửa: lỗi ({0})".format(str(loi_ts)[:200]))
    if hanh_dong_hoi_sinh:
        hanh_dong_tu_sua += hanh_dong_hoi_sinh
        if not thu:
            ghi_hs = [_su_co("tu_sua:" + h["loai"], bao_dong.MUC_THUONG, h["chuyen_gi"]) for h in hanh_dong_hoi_sinh]
            _ghi_nhat_ky_jsonl(goc, _dt.datetime.now(), ghi_hs)
            _ghi_loi_chay_max_md(goc, _dt.datetime.now(), ghi_hs)
    try:
        hanh_dong_tu_sua += tu_sua_agent_treo(goc, ghi_dia=not thu)
    except Exception:  # noqa: BLE001 — canh nhịp tim hỏng không được làm sập gác tổng
        pass
    try:
        hanh_dong_tu_sua += tu_xu_ly_viec_may(goc, anh, ghi_dia=not thu)
    except Exception:  # noqa: BLE001 — tự xử hỏng không được làm sập gác tổng
        pass

    print(ban_tin_ngay(goc, anh, ds_su_co, so_du_vnd=so_du_vnd,
                       so_ngay_license_con_lai=ngay_license))
    print("")
    print("Số sự cố phát hiện: {0}{1}".format(
        ket_qua["so_su_co"], " (--thu: chưa ghi đĩa, chưa gửi báo động)" if thu else ""))
    for sc in ds_su_co:
        print("  [{0}] {1}{2}".format(sc["muc"], sc["chuyen_gi"],
                                       " (kênh {0})".format(sc["kenh"]) if sc.get("kenh") else ""))
    if hanh_dong_tu_sua:
        print("")
        print("Tự sửa{0}:".format(" (--thu: SẼ làm, chưa làm thật)" if thu else ""))
        for h in hanh_dong_tu_sua:
            print("  - {0}".format(h["chuyen_gi"]))
    if tom_tat_gd:
        print("")
        print("Giám đốc kênh: {0}".format(tom_tat_gd))
    if tom_tat_mk and "không có việc" not in tom_tat_mk:
        print("")
        print("Mở kênh: {0}".format(tom_tat_mk))
    # Dọn đĩa (06/10/2026, `core/don_dia.py`): mỗi 3 giờ xoá file nặng của video đã lên YouTube +
    # xoay *.log quá cỡ — để dọn không phụ thuộc lượt sản xuất. `--thu` không dọn. try riêng.
    if not thu:
        try:
            from core import don_dia  # noqa: PLC0415

            kq_dd = don_dia.nhip(goc)
            if kq_dd is not None:
                print("")
                print(don_dia.tom_tat(kq_dd))
        except Exception as loi_dd:  # noqa: BLE001 — dọn đĩa hỏng không được làm sập gác tổng
            print("Dọn đĩa: lỗi ({0})".format(str(loi_dd)[:200]))
    # Báo cáo sức khoẻ hằng ngày (06/10/2026, `core/bao_cao_ngay.py`): sau 06:30 ghi + gửi MỘT lần/ngày. try riêng.
    if not thu:
        try:
            from core import bao_cao_ngay  # noqa: PLC0415

            dong_bc = bao_cao_ngay.chay_hang_ngay(goc)
            if dong_bc:
                print("")
                print(dong_bc)
        except Exception as loi_bc:  # noqa: BLE001 — báo cáo hỏng không được làm sập gác tổng
            print("Báo cáo ngày: lỗi ({0})".format(str(loi_bc)[:200]))
    # Kiểm cập nhật (30/09/2026, `core/cap_nhat_git.py`): tự hãm nhịp ~30 phút,
    # `git fetch` + đọc origin/main:VERSION; có bản mới + tự động bật + máy rảnh
    # thì SINH tiến trình `dong_bo_git keo` tách rời (gác tổng không chờ nó).
    # `--thu` không kiểm (không gọi mạng, không sinh gì).
    if not thu:
        try:
            from core import cap_nhat_git  # noqa: PLC0415

            print("")
            print("Cập nhật: {0}".format(cap_nhat_git.nhip(goc)["tom_tat"]))
        except Exception as loi_cn:  # noqa: BLE001 — kiểm cập nhật hỏng không được làm sập gác tổng
            print("Cập nhật: không kiểm được ({0})".format(str(loi_cn)[:200]))
    return 0


if __name__ == "__main__":
    if "--mot-luot" in sys.argv[1:] and "--thu" not in sys.argv[1:]:
        ben_bi.hen_gio_tu_thoat(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gac_tong", GIAY_TOI_DA_MOT_LUOT)
    raise SystemExit(_main())
