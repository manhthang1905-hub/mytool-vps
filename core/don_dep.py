"""Dọn đĩa VPS — chỉ xoá thứ NẶNG không ai dùng lại nữa. HAI luật, không một.

═══ LUẬT MỘT: ĐÃ ĐĂNG + QUÁ HẠN ÂN XÁ (18/09/2026) ═══
    `ung_vien_don` · cờ `tu_don` + `don_sau_gio` trong `kenh.yaml`.

═══ LUẬT HAI: QUÁ N LƯỢT, KHÔNG HỎI ĐÃ ĐĂNG CHƯA (24/09/2026) ═══
    `ung_vien_qua_so_luot` · khoá `giu_toi_da_luot` trong `kenh.yaml`.

═══ LUẬT BỐN: GÓI DONE ĐÃ ĐĂNG + ĐÃ XÁC NHẬN + HẬU KIỂM OK (01/10/2026) ═══
    `ung_vien_done` · `don_done`. Xem docstring `ung_vien_done`.

    Trước 01/10/2026 luật MỘT xoá CẢ thư mục gói trong `thu_muc_done` (kèm
    `.srt`, bìa, `qa`) chỉ 24 giờ sau giờ đăng ghi trong kế hoạch, không hỏi sổ
    xác nhận lẫn hậu kiểm. Từ nay luật MỘT KHÔNG đụng DONE nữa; DONE chỉ mất
    tệp media NẶNG, qua luật BỐN, giữ lại tệp nhỏ cho khám nghiệm.

Vì sao phải có luật hai: đo thật trên VPS ngày 24/09/2026, `PROJECTS/` đã
**10,4 GB với 12 lượt** (TL1 5 lượt, TL2 3, TL3 4 — lượt `TL3-T7/0002` một mình
2,4 GB) trên ổ C chỉ 49,4 GB, vì máy tự chạy hai ngày liền. Mà cửa dọn duy nhất
lúc ấy (luật MỘT) chưa mở được lần nào: chủ dự án chưa duyệt/đăng lượt nào, nên
không lượt nào có "Trạng thái đăng" ∈ `TRANG_THAI_DA_DANG` → không lượt nào bị
dọn → đĩa phình mãi. Chủ dự án: *"hằng ngày có tải dữ liệu kênh về thì cũng
phải có logic dọn dẹp"*.

Luật hai **thêm vào**, không thay: `giu_toi_da_luot: 0` (mặc định) là tắt nó, và
cả hai luật đều nằm sau cờ `tu_don`. Chi tiết bốn thứ luật hai không bao giờ
đụng (N lượt mới nhất · lượt chưa xong · cả kênh khi khoá `.khoa` còn tươi ·
gói đã bàn giao trong `thu_muc_done`): xem docstring `ung_vien_qua_so_luot`.

═══ VÌ SAO CÓ TỆP NÀY (18/09/2026) ═══

Chủ dự án: một video đăng xong rồi thì 5–6 GB ảnh cảnh + clip + mp3 giọng đọc
của lượt đó chỉ còn nằm chật đĩa VPS — chẳng ai mở lại. Muốn tool TỰ XOÁ, an
toàn, sau khi chắc chắn video đã lên sóng.

"An toàn" ở đây có ba lớp:

1. **Chỉ xoá thứ NẶNG, không đụng thứ NHỎ mà việc khác còn đọc.** `0-doi-thu.txt`
   (chặn remake trùng nguồn, `core/da_lam.py`), `1-*.txt`/`3-phu-de.srt`/
   `4-canh.json` (`core/chi_so_ytb.su_that_tu_luot`, dùng làm chuẩn so cho vòng
   chấm-sửa lượt sau), `trang-thai.json`, `_van-tay-*.json` (so nội dung để biết
   "đã có sẵn" — `core/auto_khau.VanTay`), và tấm ảnh bìa ĐÃ CHỌN — không tệp nào
   trong số này to, và xoá đi là làm hỏng một tính năng khác đang sống nhờ nó.
   Chỉ `5-anh/`, `6-clip/`, `8-video.mp4`, `9-video-capcut.mp4`,
   `2-giong-doc.mp3`, ảnh bìa CHƯA chọn, và tệp tạm `*.tam` mới bị xoá (luật
   HAI xoá thêm `2-doan/` — xem `_MUC_NANG_QUA_SO_LUOT`). Lớp này CHUNG cho cả
   hai luật: chúng chỉ khác nhau ở câu hỏi "lượt nào đủ điều kiện", không ở
   câu hỏi "trong một lượt thì được xoá gì".

2. **Chỉ xoá lượt đã ĐĂNG THẬT, và chỉ sau một hạn ân xá.** (Riêng luật MỘT;
   luật HAI thay lớp này bằng trần số lượt + ba cái chốt của nó.) Đọc đúng dòng kế
   hoạch (`core/ke_hoach_dang.py`) — "Trạng thái đăng" phải là "ĐÃ ĐĂNG" (máy) hay
   "ĐÃ ĐĂNG (tay)" (`core/ban_giao_dang.TRANG_THAI_DANG_TAY`). Hạn ân xá
   (`don_sau_gio` trong `kenh.yaml`, mặc định 24 giờ) chừa chỗ cho ca YouTube xử
   lý hỏng phải tải lại. Và nếu `8-video.mp4` mới hơn cả lúc đăng — tức có ai vừa
   dựng lại — thì bỏ qua cả lượt, không đoán mò lý do.

3. **Không bao giờ đi ra khỏi hai thư mục được phép.** Mọi đường xoá đều được
   `os.path.realpath` rồi kiểm nằm THẬT SỰ trong `PROJECTS/AUTO/<kênh>/` (thư
   mục lượt) hoặc thư mục `thu_muc_done` của kênh (gói bàn giao) — lệch một chữ
   trong tên lượt/CSV cũng không đủ để đường xoá trồi ra ngoài. Không theo
   symlink/junction: gặp là bỏ qua, không xoá.

Mặc định của MỌI hàm ở đây là **không xoá gì** (`thuc_hien=False`) — trả về kế
hoạch để nơi gọi (hoặc người) xem trước. Chỉ khi kênh khai `tu_don: true` trong
`kenh.yaml` thì `don_theo_cai_dat` mới cho xoá thật; mặc định của khoá đó cũng
là tắt. Luật HAI cần THÊM `giu_toi_da_luot > 0` — hai khoá, hai lần đồng ý.

Không mạng, không Qt, không phụ thuộc phần còn lại của tool.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import shutil
import stat as _stat
from typing import Any, Callable, Dict, List, Optional, Sequence

from . import ban_giao_dang, ke_hoach_dang, ghi_dia
from .auto import doc_luot, duong_luot
from .kenh import doc_kenh

__all__ = [
    "TEN_MARKER", "TEN_LOG", "TRANG_THAI_DA_DANG", "LY_DO_DA_DANG",
    "LY_DO_QUA_SO_LUOT", "LY_DO_SAO_LUU", "KHOA_CON_TUOI_GIAY",
    "SO_BAN_SAO_LUU_GIU",
    "ung_vien_don", "ung_vien_qua_so_luot", "ung_vien_sao_luu", "don",
    "don_sao_luu", "don_tat_ca", "don_theo_cai_dat", "don_khan",
    "LY_DO_DONE_DA_DANG", "LY_DO_DONE_BO", "LY_DO_DA_BAN_GIAO",
    "GIO_CHO_SAU_CONG_KHAI", "NGAY_CHO_GOI_BO",
    "ung_vien_done", "don_done", "ung_vien_da_ban_giao", "byte_giai_phong",
]

#: Tên tệp đánh dấu "lượt này đã dọn", nằm ngay trong thư mục lượt.
TEN_MARKER = "da-don.json"
#: Nhật ký gộp của kênh, nằm ở `CHANNEL/<kênh>/tu-chay/` — cùng thư mục sổ ngày
#: của `core/tu_chay.py`.
TEN_LOG = "don-dep.log"

#: Hai chuỗi trạng thái coi là "đã đăng thật" — máy tự đăng hoặc chủ đăng tay.
TRANG_THAI_DA_DANG = ("ĐÃ ĐĂNG", ban_giao_dang.TRANG_THAI_DANG_TAY)

#: Tệp/thư mục NẶNG trong một lượt — tên đúng bằng sản phẩm khâu, xem `core/auto.KHAU`.
#: Ba mục cuối (`_lam-lai`, `_dung-do`, `_cat`) là thư mục TẠM sinh ra NGAY
#: TRONG thư mục lượt lúc đang chạy — không phải sản phẩm khâu: `_lam-lai` là
#: đổi lại kịch bản của `core/auto._lam_lai`, `_dung-do` là thư mục dựng dở của
#: bước mã hoá (`_dung-do` — chưa có trong code hôm nay, chừa chỗ cho một việc
#: khác), `_cat` là thư mục cắt clip trung gian của `core/auto_khau.py`. Bình
#: thường cả ba tự dọn khi lượt chạy xong trót lọt; lượt hỏng/dừng giữa chừng
#: để chúng lại MÃI, ăn đĩa vô ích. Vẫn nằm NGAY trong thư mục lượt, giống hệt
#: các mục còn lại nên `_muc_nang_trong_luot` ăn theo tự động (đã kiểm
#: `os.path.exists` trước khi thêm vào danh sách xoá).
_MUC_NANG = ("5-anh", "6-clip", "8-video.mp4", "9-video-capcut.mp4", "2-giong-doc.mp3",
            "_lam-lai", "_dung-do", "_cat")

#: THÊM cho luật "quá N lượt" (`ung_vien_qua_so_luot`): các mảnh mp3 giọng đọc
#: từng đoạn. Lượt ĐÃ ĐĂNG không xoá thư mục này (giữ nguyên `_MUC_NANG` đời
#: trước, khỏi đổi nết một đường đã chạy ổn), nhưng lượt bị xoá vì quá trần thì
#: xoá — đo trên `PROJECTS/AUTO/TL3-T7/0002` (24/09/2026) `2-doan/` là phần nặng
#: thứ ba của lượt, sau `5-anh/` và `6-clip/`.
_MUC_NANG_QUA_SO_LUOT = _MUC_NANG + ("2-doan",)

_THU_MUC_THUMB = "7-thumbnail"

#: Lý do ghi vào `da-don.json` + `don-dep.log` — để chủ dự án đọc sổ là biết
#: NGAY vì sao mất, không tưởng tool xoá oan (`core/don_dep.py` từng chỉ có
#: một lý do nên không cần ghi).
LY_DO_DA_DANG = "đã đăng, quá hạn ân xá"
LY_DO_QUA_SO_LUOT = "xoá vì quá {0} lượt, chưa đăng"
LY_DO_SAO_LUU = "xoá vì vượt quá {0} bản sao lưu mới nhất trong thư mục sao-luu"

#: Số bản MỚI NHẤT giữ lại trong mỗi thư mục tên `sao-luu` — xem
#: `ung_vien_sao_luu`.
SO_BAN_SAO_LUU_GIU = 3

#: Khoá `CHANNEL/<kênh>/tu-chay/.khoa` mới hơn ngần này giây thì coi là CÒN
#: TƯƠI — một lượt có thể đang chạy, luật "quá N lượt" bỏ qua CẢ KÊNH.
#:
#: Bằng đúng `core.tu_chay.KHOA_CU_QUA_GIAY` (12 giờ — mốc mà chính `tu_chay`
#: coi khoá là chết và giành lại). Không `import core.tu_chay` để lấy hằng số:
#: `tu_chay` đã import `don_dep`, nối thêm chiều ngược là vòng import. Đổi một
#: bên thì đổi cả bên kia.
KHOA_CON_TUOI_GIAY = 12 * 3600

#: Khoá độc quyền của vòng tự chạy — `core.tu_chay.TEN_TEP_KHOA`, cùng luật
#: "không import ngược" như trên.
_TEN_TEP_KHOA = ".khoa"
_THU_MUC_TU_CHAY = "tu-chay"

#: Cờ reparse point của Windows (junction, symlink thư mục) — `stat` định nghĩa
#: hằng này trên mọi hệ điều hành dù chỉ có ý nghĩa trên Windows.
_CO_REPARSE = getattr(_stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


# ── Đường dẫn an toàn ────────────────────────────────────────────────────────


def _la_lien_ket(duong: str) -> bool:
    """`True` nếu `duong` là symlink hay junction — đừng đi theo, đừng xoá xuyên."""
    try:
        st = os.lstat(duong)
    except OSError:
        return False
    if _stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _CO_REPARSE)


def _duong_thuc(duong: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.realpath(duong)))


def _trong_thu_muc(duong: str, cha: str) -> bool:
    """`True` nếu `duong` nằm THẬT SỰ (đã theo đường dẫn thực) bên trong `cha`."""
    if not duong or not cha:
        return False
    con = _duong_thuc(duong)
    goc = _duong_thuc(cha)
    return con != goc and (con + os.sep).startswith(goc + os.sep)


# ── Đọc kế hoạch đăng ────────────────────────────────────────────────────────


def _thoi_diem_dang(dong: Dict[str, str]) -> Optional[datetime.datetime]:
    """Ngày+giờ đăng của một dòng kế hoạch, hoặc `None` nếu chưa biết được.

    Trống thì trả `None` — kể cả cho lượt đăng tay: `ghi_nhan_dang_tay` chỉ đổi
    cột trạng thái của một dòng ĐÃ CÓ mà không đụng ngày giờ, nên trống ở đây có
    thể là "chưa ai từng ghi mốc" chứ không phải lỗi đọc. Chỗ gọi bỏ qua lượt
    này (đường an toàn) thay vì đoán một mốc không có thật.
    """
    ngay = (dong.get("Ngày đăng") or "").strip()
    gio = (dong.get("Giờ đăng") or "").strip()
    if not ngay:
        return None
    ngay_dt = None
    for mau in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            ngay_dt = datetime.datetime.strptime(ngay, mau)
            break
        except ValueError:
            continue
    if ngay_dt is None:
        return None
    if gio:
        for mau in ("%H:%M", "%H:%M:%S"):
            try:
                gio_t = datetime.datetime.strptime(gio, mau).time()
                return datetime.datetime.combine(ngay_dt.date(), gio_t)
            except ValueError:
                continue
    return ngay_dt


# ── Tìm thứ NẶNG còn lại trong một lượt ──────────────────────────────────────


def _kich_thuoc(duong: str) -> int:
    """Byte THẬT SỰ được giải phóng nếu xoá `duong` (01/10/2026: không tính tệp
    còn liên kết cứng ở chỗ khác — `8-video.mp4` của lượt là hardlink với bản
    trong DONE, xoá một phía không trả lại byte nào). Xem `byte_giai_phong`."""
    return byte_giai_phong([duong])


def _tep_duoi(duong: str) -> List[str]:
    """Mọi TỆP dưới `duong` (chính nó nếu là tệp). Không đi theo liên kết."""
    if os.path.isfile(duong):
        return [duong]
    ra: List[str] = []
    if os.path.isdir(duong) and not _la_lien_ket(duong):
        for cha, _thu, tep in os.walk(duong):
            ra.extend(os.path.join(cha, t) for t in tep)
    return ra


def byte_giai_phong(duong: Sequence[str]) -> int:
    """Số byte ổ đĩa THẬT SỰ lấy lại được khi xoá CẢ danh sách `duong` (tệp hoặc
    thư mục).

    Gom theo (thiết bị, inode): một tệp có `st_nlink` liên kết chỉ trả lại byte
    khi MỌI liên kết của nó đều nằm trong danh sách xoá. Còn liên kết ở chỗ
    khác (ví dụ `8-video.mp4` trong `PROJECTS` và trong `DONE` là một tệp) thì
    tính 0 — đúng thứ mà `shutil.disk_usage` sẽ thấy sau khi xoá."""
    nhom: Dict[Any, List[Any]] = {}
    for goc_duong in duong:
        for p in _tep_duoi(goc_duong):
            try:
                st = os.stat(p)
            except OSError:
                continue
            khoa = (st.st_dev, st.st_ino) if st.st_ino else ("p", _duong_thuc(p))
            muc = nhom.setdefault(khoa, [st.st_size, max(1, int(st.st_nlink or 1)), set()])
            muc[2].add(_duong_thuc(p))
    return sum(kt for kt, nlink, tap in nhom.values() if len(tap) >= nlink)


def _anh_bia_chua_chon(thu_muc_luot: str) -> List[str]:
    """Ảnh bìa CHƯA được chọn — cùng luật chọn với `ban_giao_dang._tim_thumb`.

    Gọi thẳng hàm ấy để chắc chắn giữ ĐÚNG tấm mà bàn giao từng lấy: chưa ai bấm
    "Chọn" (không có `CHON-*`) thì bàn giao tự lấy tấm đầu theo bảng chữ cái —
    dọn dẹp phải giữ đúng tấm đó, không phải xoá sạch vì "không thấy CHON-".
    """
    thu_muc = os.path.join(thu_muc_luot, _THU_MUC_THUMB)
    if not os.path.isdir(thu_muc) or _la_lien_ket(thu_muc):
        return []
    giu = ban_giao_dang._tim_thumb(thu_muc_luot)  # noqa: SLF001 — dùng chung luật chọn
    ra = []
    try:
        ten_tep = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    for ten in ten_tep:
        p = os.path.join(thu_muc, ten)
        if not os.path.isfile(p) or _la_lien_ket(p):
            continue
        if giu and os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(giu)):
            continue
        ra.append(p)
    return ra


def _muc_nang_trong_luot(thu_muc_luot: str,
                         muc: Sequence[str] = _MUC_NANG) -> List[str]:
    """Đường dẫn tuyệt đối mọi thứ NẶNG còn nằm trong một thư mục lượt.

    `muc`: danh sách tên cần xoá. Mặc định `_MUC_NANG` (luật "đã đăng", giữ
    nguyên nết đời trước); luật "quá N lượt" truyền `_MUC_NANG_QUA_SO_LUOT`.
    """
    ra: List[str] = []
    for ten in muc:
        p = os.path.join(thu_muc_luot, ten)
        if os.path.exists(p) and not _la_lien_ket(p):
            ra.append(p)
    ra.extend(_anh_bia_chua_chon(thu_muc_luot))
    try:
        ra.extend(
            p for p in glob.glob(os.path.join(thu_muc_luot, "**", "*.tam"), recursive=True)
            if os.path.isfile(p) and not _la_lien_ket(p)
        )
    except OSError:
        pass
    return ra


# ── Ứng viên ─────────────────────────────────────────────────────────────────


def ung_vien_don(goc: str, ma_kenh: str, *,
                 bay_gio: Optional[datetime.datetime] = None,
                 cho_gio: Optional[float] = None) -> List[Dict[str, Any]]:
    """Những lượt của `ma_kenh` đủ điều kiện dọn NGAY BÂY GIỜ.

    Mỗi phần tử: `{"kenh", "luot", "ma_goi", "thu_muc_luot", "duong" (danh sách
    đường tuyệt đối sẽ xoá), "bytes"}`. Không xoá gì ở đây — hàm này chỉ ĐỌC.
    """
    if bay_gio is None:
        bay_gio = datetime.datetime.now()
    kenh = doc_kenh(goc, ma_kenh)
    if cho_gio is None:
        cho_gio = kenh.don_sau_gio
    han = datetime.timedelta(hours=max(0.0, float(cho_gio)))

    auto_goc = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)

    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    if "Mã gói" not in cot or "Trạng thái đăng" not in cot:
        return []
    tien_to = ma_kenh + "-"

    o_ma = cot.index("Mã gói")
    da_thay: set = set()
    trung: set = set()
    for hang_tho in hang:
        ma = (hang_tho[o_ma] if o_ma < len(hang_tho) else "").strip()
        if not ma:
            continue
        if ma in da_thay:
            trung.add(ma)
        da_thay.add(ma)

    ra: List[Dict[str, Any]] = []
    for hang_tho in hang:
        dong = {ten: (hang_tho[i] if i < len(hang_tho) else "") for i, ten in enumerate(cot)}
        ma = (dong.get("Mã gói") or "").strip()
        if not ma or ma in trung:
            # Mã trùng nhiều dòng — không còn "MỘT" dòng rõ ràng để tin theo,
            # bỏ qua thay vì đoán dòng nào đúng.
            continue
        if (dong.get("Trạng thái đăng") or "").strip() not in TRANG_THAI_DA_DANG:
            continue
        if not ma.startswith(tien_to):
            continue  # sổ của kênh khác lẫn vào, hoặc mã không đúng khuôn — bỏ qua
        luot = ma[len(tien_to):]
        if not luot:
            continue

        thu_muc_luot = duong_luot(goc, ma_kenh, luot)
        # Phải nằm ĐÚNG một cấp dưới AUTO/<kênh> — chặn mã lượt mang "..\" hay "/".
        if os.path.normcase(os.path.normpath(os.path.dirname(thu_muc_luot))) \
                != os.path.normcase(os.path.normpath(auto_goc)):
            continue
        if not os.path.isdir(thu_muc_luot) or _la_lien_ket(thu_muc_luot):
            continue
        if not _trong_thu_muc(thu_muc_luot, auto_goc):
            continue

        moc = _thoi_diem_dang(dong)
        if moc is None:
            continue
        if bay_gio - moc < han:
            continue

        video = os.path.join(thu_muc_luot, "8-video.mp4")
        if os.path.isfile(video) and os.path.getmtime(video) > moc.timestamp():
            continue  # video mới hơn lúc đăng — vừa dựng lại, đừng đụng

        duong_xoa = _muc_nang_trong_luot(thu_muc_luot)
        # 01/10/2026: KHÔNG còn gom cả thư mục gói trong `thu_muc_done` vào đây
        # (trước đó xoá luôn `.srt`/bìa/`qa` chỉ 24 giờ sau giờ đăng, không hỏi
        # sổ xác nhận/hậu kiểm). Gói DONE giờ do luật BỐN (`ung_vien_done`) lo.

        if not duong_xoa:
            continue  # đã sạch từ trước — không có gì để dọn

        ra.append({
            "kenh": ma_kenh,
            "luot": luot,
            "ma_goi": ma,
            "thu_muc_luot": thu_muc_luot,
            "duong": duong_xoa,
            "bytes": byte_giai_phong(duong_xoa),
            #: Mốc đăng THẬT của lượt này, dạng CHUỖI ISO (không phải `datetime`
            #: sống) — dùng để xếp thứ tự "cũ nhất trước" ở `don_khan` (dọn
            #: khẩn, xem đó). Chuỗi, không phải `datetime`, vì `dict` này có
            #: thể đi thẳng vào sổ ngày JSON (`core/tu_chay.py` ghi nguyên kết
            #: quả `don_khan` vào `run["dia"]["don_khan"]`) — `datetime` sống
            #: làm `json.dump` (không `default=`) ném lỗi giữa một lượt đang
            #: XOÁ DỞ, còn tệ hơn cả không ghi được sổ. Chuỗi ISO của cùng một
            #: định dạng vẫn so sánh CŨ/MỚI đúng bằng so sánh chuỗi thường.
            "moc_dang": moc.isoformat(),
            #: Vì sao lượt này bị dọn — đi thẳng vào `da-don.json`, `don-dep.log`
            #: và sổ ngày. Xem `LY_DO_DA_DANG`.
            "ly_do": LY_DO_DA_DANG,
        })
    return ra


# ── Ứng viên theo luật THỨ HAI: quá N lượt, không hỏi đã đăng chưa ───────────


def _khoa_con_tuoi(goc: str, ma_kenh: str,
                   bay_gio: Optional[datetime.datetime] = None) -> bool:
    """Kênh này có khoá tự chạy CÒN TƯƠI không — tức có thể đang chạy một lượt.

    Tệp khoá (`core.tu_chay._tao_tep_khoa`) chỉ chứa `{"pid", "bat_dau"}`, KHÔNG
    ghi mã lượt đang chạy — nên không có cách nào biết lượt NÀO đang mở. Đường
    an toàn duy nhất là bỏ qua CẢ KÊNH khi khoá còn tươi: thà chậm một vòng dọn
    còn hơn xoá `5-anh/` ngay dưới chân một khâu đang dựng.

    `bat_dau` đọc hỏng thì lùi về thời gian sửa tệp — tệp khoá có mặt mà không
    đọc được nội dung vẫn là dấu "có người đang giữ", không được coi là sạch.
    """
    duong = os.path.join(goc, "CHANNEL", ma_kenh, _THU_MUC_TU_CHAY, _TEN_TEP_KHOA)
    if not os.path.exists(duong):
        return False
    moc: Optional[float] = None
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        if isinstance(du, dict):
            moc = float(du.get("bat_dau") or 0) or None
    except (OSError, ValueError, TypeError):
        moc = None
    if moc is None:
        try:
            moc = os.path.getmtime(duong)
        except OSError:
            return True  # có tệp mà không đo được tuổi → coi như còn tươi
    now = (bay_gio or datetime.datetime.now()).timestamp()
    return (now - moc) < KHOA_CON_TUOI_GIAY


def _ma_luot_tren_dia(auto_goc: str) -> List[str]:
    """Mã các lượt của một kênh, xếp CŨ → MỚI.

    Chỉ nhận tên toàn CHỮ SỐ — đúng khuôn `core.tu_chay._ma_luot_moi` sinh ra
    (`"0001"`, `"0002"`…), nên xếp theo giá trị số là xếp theo thứ tự thời gian
    mà không cần đọc mtime (mtime đổi mỗi lần có ai mở lại thư mục). Tệp lẻ nằm
    cùng cấp (`anh-tham-chieu.json`) rơi ra ngoài.
    """
    try:
        ten = os.listdir(auto_goc)
    except OSError:
        return []
    so = [t for t in ten if t.isdigit() and os.path.isdir(os.path.join(auto_goc, t))]
    return sorted(so, key=lambda t: (int(t), t))


def ung_vien_qua_so_luot(goc: str, ma_kenh: str, *,
                         giu: Optional[int] = None,
                         bay_gio: Optional[datetime.datetime] = None,
                         ) -> List[Dict[str, Any]]:
    """Những lượt CŨ hơn `giu` lượt mới nhất — dọn được DÙ CHƯA ĐĂNG.

    ═══ VÌ SAO CẦN LUẬT THỨ HAI (đo thật 24/09/2026) ═══

    `ung_vien_don` ở trên chỉ nhận lượt có "Trạng thái đăng" ∈
    `TRANG_THAI_DA_DANG`. Chủ dự án chưa duyệt/đăng lượt nào, máy thì tự chạy
    mỗi giờ — nên `PROJECTS/` lên **10,4 GB / 12 lượt** mà cửa dọn duy nhất
    không mở được lần nào. Chủ dự án: *"hằng ngày có tải dữ liệu kênh về thì
    cũng phải có logic dọn dẹp"*. Luật này là cửa thứ hai, không hỏi trạng thái
    đăng, chỉ hỏi "lượt này còn nằm trong N lượt mới nhất không".

    ═══ BỐN THỨ KHÔNG BAO GIỜ ĐỤNG ═══

    1. **N lượt mới nhất** (`giu`, mặc định `kenh.giu_toi_da_luot`). `giu <= 0`
       = tắt luật, trả `[]` — hành vi y như trước khoá này ra đời.
    2. **Lượt chưa xong** — `trang-thai.json` thiếu, đọc hỏng, hay
       `LuotChay.xong_het` còn `False`. Lượt dở còn đang chờ chạy tiếp, xoá
       `5-anh/` của nó là bắt làm lại từ đầu.
    3. **Cả kênh, khi khoá `tu-chay/.khoa` còn tươi** — xem `_khoa_con_tuoi`.
    4. **Gói đã bàn giao trong `thu_muc_done`** — khác hẳn `ung_vien_don` (luật
       kia gom cả gói vào danh sách xoá vì lượt ẤY đã lên sóng rồi). Ở đây lượt
       CHƯA đăng, nên gói trong `done/` chính là thứ đang CHỜ chủ dự án đăng:
       xoá nó là làm mất việc, không phải dọn rác.

    Giữ ĐÚNG danh sách tệp nhỏ mà `ung_vien_don` giữ (`0-doi-thu.txt`, kịch
    bản `1-*`, `3-phu-de.srt`, `4-canh.json`, `_van-tay-*.json`, bìa ĐÃ CHỌN,
    `trang-thai.json`) — cùng một `_muc_nang_trong_luot`, chỉ thêm `2-doan/`.

    Trả về danh sách dict CÙNG KHUÔN `ung_vien_don` (để `_xoa_mot_ung_vien` và
    `don_khan` dùng lại y nguyên), với `ly_do` = `LY_DO_QUA_SO_LUOT`.
    """
    if bay_gio is None:
        bay_gio = datetime.datetime.now()
    if giu is None:
        giu = doc_kenh(goc, ma_kenh).giu_toi_da_luot
    giu = int(giu or 0)
    if giu <= 0:
        return []
    if _khoa_con_tuoi(goc, ma_kenh, bay_gio):
        return []

    auto_goc = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    if not os.path.isdir(auto_goc) or _la_lien_ket(auto_goc):
        return []
    tat_ca = _ma_luot_tren_dia(auto_goc)
    cu = tat_ca[:-giu] if giu < len(tat_ca) else []
    ly_do = LY_DO_QUA_SO_LUOT.format(giu)

    ra: List[Dict[str, Any]] = []
    for luot in cu:
        thu_muc_luot = duong_luot(goc, ma_kenh, luot)
        if not os.path.isdir(thu_muc_luot) or _la_lien_ket(thu_muc_luot):
            continue
        if not _trong_thu_muc(thu_muc_luot, auto_goc):
            continue
        try:
            tt = doc_luot(thu_muc_luot)
        except Exception:  # noqa: BLE001 — một lượt đọc hỏng không chặn lượt khác
            continue
        if tt is None or not tt.xong_het:
            continue  # chưa xong (hay chưa có trang-thai.json) — không đụng
        duong_xoa = _muc_nang_trong_luot(thu_muc_luot, _MUC_NANG_QUA_SO_LUOT)
        if not duong_xoa:
            continue  # đã sạch từ trước
        ra.append({
            "kenh": ma_kenh,
            "luot": luot,
            "ma_goi": "{0}-{1}".format(ma_kenh, luot),
            "thu_muc_luot": thu_muc_luot,
            "duong": duong_xoa,
            "bytes": byte_giai_phong(duong_xoa),
            #: Lượt này CHƯA đăng nên không có mốc đăng. Dùng lúc sửa thư mục
            #: lượt làm khoá xếp thứ tự cho `don_khan` (cũ nhất xoá trước) —
            #: cùng định dạng chuỗi ISO với `ung_vien_don` để hai nguồn ứng
            #: viên xếp chung được trong một `sort`.
            "moc_dang": _moc_thu_muc_iso(thu_muc_luot),
            "ly_do": ly_do,
            "chua_dang": True,
        })
    return ra


def _moc_thu_muc_iso(thu_muc: str) -> str:
    try:
        return datetime.datetime.fromtimestamp(os.path.getmtime(thu_muc)).isoformat()
    except OSError:
        return ""


# ── Ứng viên theo luật THỨ BA: sổ sao lưu chung, siết còn 3 bản (29/09/2026) ─


def ung_vien_sao_luu(goc: str) -> List[str]:
    """Tệp sao lưu CŨ, vượt quá `SO_BAN_SAO_LUU_GIU` bản mới nhất, dưới MỌI thư
    mục con tên ĐÚNG `sao-luu` bên trong `CHANNEL/<kênh>/`.

    Khác hẳn luật MỘT/HAI ở trên: không hỏi lượt nào, kênh nào — quét THẲNG
    theo đường `CHANNEL/*/**/sao-luu` vì việc này không thuộc riêng một lượt
    sản xuất. Vài sổ sao lưu đã tự giữ 14 bản (`core/doi_thu_kenh.py`,
    `core/so_csv.py` — content.csv/doi-thu.txt), nhưng đây là một tầng an toàn
    CHUNG siết lại còn `SO_BAN_SAO_LUU_GIU` bản cho MỌI thư mục tên `sao-luu`
    dưới một kênh — kể cả những chỗ sao lưu khác chưa tự dọn (ví dụ ảnh bìa,
    `core/ho_so_video._sao_luu_anh_bia`).

    Chỉ đọc — không xoá. Không đệ quy vào thư mục con của `sao-luu` (chỉ tính
    TỆP nằm trực tiếp trong nó). Bỏ qua thư mục `sao-luu` là symlink/junction.
    """
    ra: List[str] = []
    try:
        thu_muc_sao_luu = glob.glob(
            os.path.join(goc, "CHANNEL", "*", "**", "sao-luu"), recursive=True)
    except OSError:
        return ra
    for tsl in sorted(thu_muc_sao_luu):
        if not os.path.isdir(tsl) or _la_lien_ket(tsl):
            continue
        try:
            ten_tep = os.listdir(tsl)
        except OSError:
            continue
        teps: List[tuple] = []
        for ten in ten_tep:
            p = os.path.join(tsl, ten)
            if not os.path.isfile(p) or _la_lien_ket(p):
                continue
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                continue
            teps.append((mtime, p))
        teps.sort(key=lambda x: x[0], reverse=True)
        ra.extend(p for _mtime, p in teps[SO_BAN_SAO_LUU_GIU:])
    return ra


def _ma_kenh_tu_duong_channel(goc: str, duong: str) -> str:
    """Rút mã kênh từ một đường `<goc>/CHANNEL/<kênh>/...` — chỉ để biết ghi
    log dọn sao lưu vào sổ của kênh nào; đọc hỏng thì trả chuỗi rỗng (không
    ghi log, không lỗi)."""
    goc_channel = os.path.join(goc, "CHANNEL")
    try:
        rel = os.path.relpath(duong, goc_channel)
    except ValueError:
        return ""
    if rel.startswith(".."):
        return ""
    phan = rel.split(os.sep)
    return phan[0] if phan and phan[0] not in ("", ".") else ""


def don_sao_luu(goc: str) -> List[str]:
    """Xoá THẬT các tệp sao lưu cũ trả về bởi `ung_vien_sao_luu` (giữ
    `SO_BAN_SAO_LUU_GIU` bản mới nhất mỗi thư mục `sao-luu`, xoá phần còn
    lại). Trả danh sách đường ĐÃ XOÁ thật.

    Ghi một dòng vào `CHANNEL/<kênh>/tu-chay/don-dep.log` (cùng `TEN_LOG` các
    luật khác dùng) cho MỖI kênh có tệp bị xoá — rút mã kênh từ đường dẫn
    (`_ma_kenh_tu_duong_channel`), để chủ dự án đọc một sổ là thấy đủ, không
    cần một sổ riêng cho luật này.
    """
    ung_vien = ung_vien_sao_luu(goc)
    da_xoa: List[str] = []
    theo_kenh: Dict[str, List[str]] = {}
    for p in ung_vien:
        if _la_lien_ket(p):
            continue
        try:
            os.remove(p)
        except OSError:
            continue
        da_xoa.append(p)
        ma_kenh = _ma_kenh_tu_duong_channel(goc, p)
        if ma_kenh:
            theo_kenh.setdefault(ma_kenh, []).append(p)
    if theo_kenh:
        luc = datetime.datetime.now()
        ly_do = LY_DO_SAO_LUU.format(SO_BAN_SAO_LUU_GIU)
        for ma_kenh, ds in theo_kenh.items():
            _ghi_log(goc, ma_kenh, "(sao-luu)", 0, len(ds), luc, ly_do)
    return da_xoa


# ── Ứng viên theo luật BỐN: gói DONE đã đăng + xác nhận + hậu kiểm (01/10/2026) ─

#: Phải qua giờ CÔNG KHAI (`lich` trong sổ máy đăng) ngần này giờ mới dọn DONE.
GIO_CHO_SAU_CONG_KHAI = 48.0
#: Gói có ghi chú "Bỏ" trong kế hoạch: chỉ dọn khi đã nằm yên ngần này ngày.
NGAY_CHO_GOI_BO = 7.0
LY_DO_DONE_DA_DANG = "DONE: đã đăng + xác nhận + hậu kiểm OK, quá {0:g} giờ công khai"
LY_DO_DONE_BO = "DONE: gói ghi chú Bỏ, nằm yên quá {0:g} ngày"
LY_DO_DA_BAN_GIAO = "dọn mạnh (ổ dưới {0:g} GB): lượt đã bàn giao"

#: Tệp media NẶNG trong một gói DONE — CHỈ những đuôi này bị xoá. Còn lại
#: (`.srt`, ảnh bìa, `1-*.txt`, `qa-*`, `.json`) được GIỮ cho khám nghiệm.
_DUOI_MEDIA_NANG = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v",
                    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".tam")
_TEN_SO_VIDEO = os.path.join("vm", "logs", "so-video-id.json")
_TEN_DANG_DO = os.path.join("vm", "logs", "dang-dodang.json")


def _doc_json_an_toan(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _gio_so(chu: Any, mau: Sequence[str]) -> Optional[datetime.datetime]:
    chu = str(chu or "").strip()
    for m in mau:
        try:
            return datetime.datetime.strptime(chu, m)
        except ValueError:
            continue
    return None


def _dang_tai_cua_kenh(goc: str, ma_kenh: str) -> Optional[set]:
    """Mã gói ĐANG tải lên của kênh này, hoặc `None` = không biết chắc → bỏ qua
    CẢ kênh. Hai nguồn: `vm/logs/dang-dodang.json` (máy đăng ghi khi bắt đầu
    một mã, xoá khi xong) và khe "nang" đang giữ việc `tai_len`."""
    ra: set = set()
    duong = os.path.join(goc, _TEN_DANG_DO)
    if os.path.exists(duong):
        du = _doc_json_an_toan(duong)
        kenh = str(du.get("kenh") or "").strip() if isinstance(du, dict) else ""
        ma = str(du.get("ma") or "").strip() if isinstance(du, dict) else ""
        if not kenh or not ma:
            return None  # có tệp mà không đọc được ai đang tải → không đoán
        if kenh == ma_kenh:
            ra.add(ma)
    try:
        from . import khe  # noqa: PLC0415 — chỉ đọc trạng thái khe

        giu = khe.trang_thai(goc).get("nang")
    except Exception:  # noqa: BLE001
        giu = None
    if isinstance(giu, dict) and str(giu.get("viec") or "") == "tai_len":
        kenh = str(giu.get("kenh") or "")
        if not kenh or kenh == ma_kenh:
            return None  # đang tải một gói của kênh này (không ghi mã) → chờ
    return ra


def _ghi_chu_theo_ma(goc: str, ma_kenh: str) -> Dict[str, str]:
    try:
        cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    except Exception:  # noqa: BLE001
        return {}
    if "Mã gói" not in cot or "Ghi chú" not in cot:
        return {}
    o_ma, o_gc = cot.index("Mã gói"), cot.index("Ghi chú")
    ra: Dict[str, str] = {}
    for h in hang:
        ma = (h[o_ma] if o_ma < len(h) else "").strip()
        if ma:
            ra[ma] = (h[o_gc] if o_gc < len(h) else "").strip()
    return ra


def _la_ghi_chu_bo(chu: str) -> bool:
    return str(chu or "").strip().lower().startswith("bỏ")


def _media_nang_trong_goi(thu_muc_goi: str) -> List[str]:
    ra: List[str] = []
    for cha, _thu, tep in os.walk(thu_muc_goi):
        if _la_lien_ket(cha):
            continue
        for t in tep:
            p = os.path.join(cha, t)
            if os.path.splitext(t)[1].lower() in _DUOI_MEDIA_NANG \
                    and os.path.isfile(p) and not _la_lien_ket(p):
                ra.append(p)
    return sorted(ra)


def _moc_moi_nhat(thu_muc: str) -> float:
    moc = 0.0
    for cha, _thu, tep in os.walk(thu_muc):
        for t in [cha] + [os.path.join(cha, x) for x in tep]:
            try:
                moc = max(moc, os.path.getmtime(t))
            except OSError:
                pass
    return moc


def _ban_sinh_doi_trong_luot(goc: str, ma_kenh: str, ma_goi: str,
                             teps: Sequence[str]) -> List[str]:
    """Liên kết CỨNG còn lại của các tệp gói nằm trong thư mục lượt (cùng tên,
    `os.path.samefile`) — chỉ khi lượt đã XONG hết (không phải lượt đang dựng)."""
    tien_to = ma_kenh + "-"
    if not ma_goi.startswith(tien_to):
        return []
    luot = ma_goi[len(tien_to):]
    auto_goc = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    thu_muc_luot = duong_luot(goc, ma_kenh, luot)
    if not luot or not os.path.isdir(thu_muc_luot) or _la_lien_ket(thu_muc_luot) \
            or not _trong_thu_muc(thu_muc_luot, auto_goc):
        return []
    try:
        tt = doc_luot(thu_muc_luot)
    except Exception:  # noqa: BLE001
        return []
    if tt is None or not tt.xong_het:
        return []
    ra: List[str] = []
    for p in teps:
        try:
            if os.stat(p).st_nlink <= 1:
                continue
        except OSError:
            continue
        ung = os.path.join(thu_muc_luot, os.path.basename(p))
        try:
            if os.path.isfile(ung) and not _la_lien_ket(ung) and os.path.samefile(ung, p):
                ra.append(ung)
        except OSError:
            continue
    return ra


def ung_vien_done(goc: str, ma_kenh: str, *,
                  bay_gio: Optional[datetime.datetime] = None,
                  so_video: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Gói trong `thu_muc_done` của kênh được bỏ media NẶNG ngay bây giờ. CHỈ ĐỌC.

    Một gói đủ điều kiện khi (a) HOẶC (b):

    (a) ĐÃ ĐĂNG THẬT — sổ máy đăng `vm/logs/so-video-id.json` khoá
        `"<kênh>/<mã gói>"` có `trang_thai == "xac-nhan"`, `hau_kiem` bắt đầu
        bằng `"ok"` (thời lượng trên YouTube khớp tệp), và giờ công khai
        `lich` đã qua ≥ `GIO_CHO_SAU_CONG_KHAI`. Thiếu một trong ba (sổ cũ
        trước 30/09 chưa có `hau_kiem`) → KHÔNG đụng. Video bị dựng lại SAU
        lúc tải xong (`mtime > tai_xong_luc`) → không đụng.
    (b) Ghi chú kế hoạch bắt đầu bằng "Bỏ" và gói nằm yên ≥ `NGAY_CHO_GOI_BO`
        ngày (mtime mới nhất trong gói), sổ không ghi đang tải.

    Không bao giờ đụng: gói đang tải lên (`dang-dodang.json`, khe nặng
    `tai_len` — không rõ mã thì bỏ cả kênh), gói chưa đăng / đang chờ / lỗi.
    Chỉ xoá đuôi trong `_DUOI_MEDIA_NANG`; `.srt`, bìa, mô tả, `qa` ở lại.
    Tệp còn liên kết cứng trong thư mục lượt đã XONG (`8-video.mp4`) thì xoá
    luôn bản ấy — không thì không lấy lại được byte nào. `bytes` = byte THẬT
    giải phóng (`byte_giai_phong`), `bytes_tep` = tổng cỡ tệp bị xoá.
    """
    bay_gio = bay_gio or datetime.datetime.now()
    kenh = doc_kenh(goc, ma_kenh)
    thu_muc_done = (kenh.thu_muc_done or "").strip()
    if not thu_muc_done or not os.path.isdir(thu_muc_done) or _la_lien_ket(thu_muc_done):
        return []
    dang_tai = _dang_tai_cua_kenh(goc, ma_kenh)
    if dang_tai is None:
        return []
    if so_video is None:
        so_video = _doc_json_an_toan(os.path.join(goc, _TEN_SO_VIDEO))
    so_video = so_video if isinstance(so_video, dict) else {}
    ghi_chu = _ghi_chu_theo_ma(goc, ma_kenh)
    han_dang = datetime.timedelta(hours=GIO_CHO_SAU_CONG_KHAI)
    han_bo = NGAY_CHO_GOI_BO * 86400.0

    ra: List[Dict[str, Any]] = []
    try:
        ten_goi = sorted(os.listdir(thu_muc_done))
    except OSError:
        return []
    for ma in ten_goi:
        goi = os.path.join(thu_muc_done, ma)
        if not ma.startswith(ma_kenh + "-") or ma in dang_tai:
            continue
        if not os.path.isdir(goi) or _la_lien_ket(goi) or not _trong_thu_muc(goi, thu_muc_done):
            continue
        muc = so_video.get("{0}/{1}".format(ma_kenh, ma))
        muc = muc if isinstance(muc, dict) else {}
        trang = str(muc.get("trang_thai") or "")
        moc_cong_khai: Optional[datetime.datetime] = None
        if trang == "xac-nhan":
            if not str(muc.get("hau_kiem") or "").lower().startswith("ok"):
                continue  # chưa hậu kiểm (hay hậu kiểm lệch) — không đụng
            moc_cong_khai = _gio_so(muc.get("lich"), ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"))
            if moc_cong_khai is None or bay_gio - moc_cong_khai < han_dang:
                continue
            ly_do = LY_DO_DONE_DA_DANG.format(GIO_CHO_SAU_CONG_KHAI)
        elif _la_ghi_chu_bo(ghi_chu.get(ma, "")) and not trang:
            if bay_gio.timestamp() - _moc_moi_nhat(goi) < han_bo:
                continue
            ly_do = LY_DO_DONE_BO.format(NGAY_CHO_GOI_BO)
        else:
            continue  # chưa đăng / đang chờ / đang tải / lỗi — không đụng
        teps = _media_nang_trong_goi(goi)
        if not teps:
            continue
        if moc_cong_khai is not None:
            tai_xong = _gio_so(muc.get("tai_xong_luc") or muc.get("cap_nhat"),
                               ("%Y-%m-%d %H:%M:%S",))
            if tai_xong is not None and any(
                    os.path.getmtime(p) > tai_xong.timestamp() for p in teps
                    if p.lower().endswith(".mp4")):
                continue  # video mới hơn lúc tải xong — có ai vừa dựng lại
        duong_xoa = teps + _ban_sinh_doi_trong_luot(goc, ma_kenh, ma, teps)
        ra.append({
            "kenh": ma_kenh, "luot": "done:" + ma, "ma_goi": ma, "loai": "done",
            "thu_muc_luot": goi, "duong": duong_xoa,
            "bytes": byte_giai_phong(duong_xoa),
            "bytes_tep": sum(os.path.getsize(p) for p in duong_xoa if os.path.isfile(p)),
            "moc_dang": (moc_cong_khai or datetime.datetime.fromtimestamp(
                _moc_moi_nhat(goi))).isoformat(),
            "ly_do": ly_do,
        })
    return ra


def _xoa_tep_giai_phong(u: Dict[str, Any], goc: str, ma_kenh: str,
                        bay_gio: datetime.datetime) -> Optional[Dict[str, Any]]:
    """Xoá TỆP trong `u["duong"]` (luật BỐN / dọn mạnh), đo byte THẬT giải
    phóng: đo nhóm inode TRƯỚC khi xoá, chỉ cộng nhóm mà mọi liên kết đều đã
    xoá được. Ghi `da-don.json` + `don-dep.log` như các luật khác."""
    nhom: Dict[Any, List[Any]] = {}
    for p in u["duong"]:
        for t in _tep_duoi(p):
            try:
                st = os.stat(t)
            except OSError:
                continue
            khoa = (st.st_dev, st.st_ino) if st.st_ino else ("p", _duong_thuc(t))
            nhom.setdefault(khoa, [st.st_size, max(1, int(st.st_nlink or 1)), set()])
    da_xoa: List[str] = []
    da_xoa_thuc: Dict[Any, int] = {}
    for p in u["duong"]:
        if _la_lien_ket(p):
            continue
        cac_tep = _tep_duoi(p)
        khoa_tep = []
        for t in cac_tep:
            try:
                st = os.stat(t)
                khoa_tep.append((st.st_dev, st.st_ino) if st.st_ino else ("p", _duong_thuc(t)))
            except OSError:
                pass
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.isfile(p):
                os.remove(p)
            else:
                continue
        except OSError:
            continue
        da_xoa.append(p)
        for k in khoa_tep:
            da_xoa_thuc[k] = da_xoa_thuc.get(k, 0) + 1
    if not da_xoa:
        return None
    giai_phong = sum(nhom[k][0] for k, n in da_xoa_thuc.items()
                     if k in nhom and n >= nhom[k][1])
    ly_do = str(u.get("ly_do") or "")
    _ghi_marker(u["thu_muc_luot"], u["ma_goi"], da_xoa, giai_phong, bay_gio, ly_do)
    _ghi_log(goc, ma_kenh, u["ma_goi"], giai_phong, len(da_xoa), bay_gio, ly_do)
    return {**u, "da_xoa": da_xoa, "bytes": giai_phong}


def don_done(goc: str, ma_kenh: str, *, thuc_hien: bool = False,
             bay_gio: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """Luật BỐN cho một kênh. `thuc_hien=False`: chỉ tính. Trả `{"ung_vien",
    "tong_bytes" (byte THẬT, đã/ sẽ giải phóng), "da_don"}`."""
    bay_gio = bay_gio or datetime.datetime.now()
    ke = ung_vien_done(goc, ma_kenh, bay_gio=bay_gio)
    ra: Dict[str, Any] = {"kenh": ma_kenh, "thuc_hien": bool(thuc_hien), "ung_vien": ke,
                          "tong_bytes": sum(int(u["bytes"]) for u in ke), "da_don": []}
    if not thuc_hien:
        return ra
    for u in ke:
        ket = _xoa_tep_giai_phong(u, goc, ma_kenh, bay_gio)
        if ket is not None:
            ra["da_don"].append(ket)
    ra["tong_bytes"] = sum(int(d["bytes"]) for d in ra["da_don"])
    return ra


def ung_vien_da_ban_giao(goc: str, ma_kenh: str, *, nguong_gb: float,
                         bay_gio: Optional[datetime.datetime] = None,
                         yen_giay: float = 3600.0) -> List[Dict[str, Any]]:
    """DỌN MẠNH (ổ dưới ngưỡng khẩn): phần nặng của lượt ĐÃ BÀN GIAO, kể cả
    trong `giu_toi_da_luot` lượt mới nhất. Lượt phải XONG hết, `trang-thai.json`
    yên ≥ `yen_giay`, và gói của nó đã nằm trong DONE (có .mp4) hoặc kế hoạch ghi
    đã đăng. Lượt đang dựng (chưa xong) không bao giờ vào đây. Giữ đúng các tệp
    nhỏ như luật HAI (`_muc_nang_trong_luot`)."""
    bay_gio = bay_gio or datetime.datetime.now()
    kenh = doc_kenh(goc, ma_kenh)
    auto_goc = os.path.join(goc, "PROJECTS", "AUTO", ma_kenh)
    if not os.path.isdir(auto_goc) or _la_lien_ket(auto_goc):
        return []
    thu_muc_done = (kenh.thu_muc_done or "").strip()
    da_dang: set = set()
    try:
        cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
        if "Mã gói" in cot and "Trạng thái đăng" in cot:
            o_ma, o_tt = cot.index("Mã gói"), cot.index("Trạng thái đăng")
            for h in hang:
                if o_tt < len(h) and h[o_tt].strip() in TRANG_THAI_DA_DANG:
                    da_dang.add(h[o_ma].strip())
    except Exception:  # noqa: BLE001
        pass
    ly_do = LY_DO_DA_BAN_GIAO.format(nguong_gb)
    ra: List[Dict[str, Any]] = []
    for luot in _ma_luot_tren_dia(auto_goc):
        thu_muc_luot = duong_luot(goc, ma_kenh, luot)
        if _la_lien_ket(thu_muc_luot) or not _trong_thu_muc(thu_muc_luot, auto_goc):
            continue
        try:
            tt = doc_luot(thu_muc_luot)
            yen = bay_gio.timestamp() - os.path.getmtime(os.path.join(thu_muc_luot, "trang-thai.json"))
        except Exception:  # noqa: BLE001
            continue
        if tt is None or not tt.xong_het or yen < yen_giay:
            continue
        ma = "{0}-{1}".format(ma_kenh, luot)
        goi = os.path.join(thu_muc_done, ma) if thu_muc_done else ""
        co_goi = bool(goi) and os.path.isdir(goi) and any(
            t.lower().endswith(".mp4") for t in os.listdir(goi))
        if not co_goi and ma not in da_dang:
            continue
        duong_xoa = _muc_nang_trong_luot(thu_muc_luot, _MUC_NANG_QUA_SO_LUOT)
        if not duong_xoa:
            continue
        ra.append({"kenh": ma_kenh, "luot": luot, "ma_goi": ma, "loai": "ban_giao",
                   "thu_muc_luot": thu_muc_luot, "duong": duong_xoa,
                   "bytes": byte_giai_phong(duong_xoa),
                   "moc_dang": _moc_thu_muc_iso(thu_muc_luot), "ly_do": ly_do})
    return ra


# ── Xoá thật ─────────────────────────────────────────────────────────────────


def _duong_ghi_luot(thu_muc_luot: str, duong: str) -> str:
    """Đường hiển thị trong sổ: tương đối với thư mục lượt nếu nằm trong đó."""
    if _trong_thu_muc(duong, thu_muc_luot):
        return os.path.relpath(duong, thu_muc_luot).replace("\\", "/")
    return duong


def _ghi_marker(thu_muc_luot: str, ma_goi: str, da_xoa: Sequence[str],
                so_bytes: int, luc: datetime.datetime, ly_do: str = "") -> None:
    ghi_dia.ghi_json(os.path.join(thu_muc_luot, TEN_MARKER), {
        "ma_goi": ma_goi,
        "luc": luc.strftime("%Y-%m-%d %H:%M:%S"),
        "bytes": so_bytes,
        "ly_do": ly_do or LY_DO_DA_DANG,
        "xoa": [_duong_ghi_luot(thu_muc_luot, p) for p in da_xoa],
    })


def _ghi_log(goc: str, ma_kenh: str, ma_goi: str, so_bytes: int,
            so_muc: int, luc: datetime.datetime, ly_do: str = "") -> None:
    duong = os.path.join(goc, "CHANNEL", ma_kenh, "tu-chay", TEN_LOG)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    # Cột LÝ DO ở cuối, không chen vào giữa: sổ cũ đọc bằng mắt (và bằng
    # `split("\t")` nếu có ai viết) vẫn thấy đúng bốn cột đầu như trước.
    dong = "{0}\tgói {1}\txoá {2} mục\t{3} byte\t{4}\n".format(
        luc.strftime("%Y-%m-%d %H:%M:%S"), ma_goi, so_muc, so_bytes,
        ly_do or LY_DO_DA_DANG)
    try:
        with open(duong, "a", encoding="utf-8") as tep:
            tep.write(dong)
    except OSError:
        pass  # nhật ký là để xem lại, không phải van an toàn — hỏng thì bỏ qua


def _xoa_mot_ung_vien(goc: str, ma_kenh: str, u: Dict[str, Any],
                      bay_gio: datetime.datetime) -> Optional[Dict[str, Any]]:
    """Xoá thật các đường trong MỘT ứng viên (một phần tử của `ung_vien_don`);
    ghi tệp đánh dấu + nhật ký nếu xoá được ít nhất một mục. Trả `None` nếu
    không xoá được gì (đã sạch từ trước, hoặc mọi đường đều là liên kết).

    Tách riêng khỏi `don()` để `don_khan` (dọn khẩn, xem đó) dùng lại ĐÚNG một
    cơ chế xoá — không viết lại luật an toàn (bỏ qua liên kết, ghi marker/log)
    ở một chỗ thứ hai."""
    da_xoa: List[str] = []
    for p in u["duong"]:
        if _la_lien_ket(p):
            continue
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.isfile(p):
                os.remove(p)
            else:
                continue
        except OSError:
            continue
        da_xoa.append(p)
    if not da_xoa:
        return None
    ly_do = str(u.get("ly_do") or LY_DO_DA_DANG)
    _ghi_marker(u["thu_muc_luot"], u["ma_goi"], da_xoa, u["bytes"], bay_gio, ly_do)
    _ghi_log(goc, ma_kenh, u["ma_goi"], u["bytes"], len(da_xoa), bay_gio, ly_do)
    return {**u, "da_xoa": da_xoa}


def _gop_ung_vien(*nguon: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gộp nhiều danh sách ứng viên, MỘT lượt chỉ vào một lần.

    Hai luật có thể cùng nhận một lượt (đã đăng, quá hạn ân xá, VÀ đã ra ngoài
    N lượt mới nhất). Để nó vào hai lần là `_xoa_mot_ung_vien` chạy hai lượt
    trên cùng thư mục — lần hai không xoá được gì nên trả `None`, vô hại, nhưng
    `tong_bytes` thì đã cộng đôi và sổ ngày báo số gấp đôi số thật. Ưu tiên
    bản ĐẦU TIÊN (luật "đã đăng" đứng trước): lý do của nó đúng hơn.
    """
    ra: List[Dict[str, Any]] = []
    da_co: set = set()
    for danh_sach in nguon:
        for u in danh_sach:
            khoa = (str(u.get("kenh") or ""), str(u.get("luot") or ""))
            if khoa in da_co:
                continue
            da_co.add(khoa)
            ra.append(u)
    return ra


def don(goc: str, ma_kenh: str, *, thuc_hien: bool = False,
        bay_gio: Optional[datetime.datetime] = None,
        cho_gio: Optional[float] = None,
        giu_toi_da_luot: Optional[int] = None) -> Dict[str, Any]:
    """Dọn một kênh theo CẢ HAI luật: lượt đã đăng quá hạn ân xá, và lượt đã
    ra ngoài `giu_toi_da_luot` lượt mới nhất (dù chưa đăng).

    `thuc_hien=False` (mặc định): chỉ TÍNH, không đụng đĩa — trả kế hoạch +
    tổng byte sẽ giải phóng. `thuc_hien=True`: xoá đúng những đường đã tính,
    ghi tệp đánh dấu `da-don.json` vào từng thư mục lượt và thêm một dòng vào
    `CHANNEL/<kênh>/tu-chay/don-dep.log` (kèm LÝ DO, xem `_ghi_log`).

    `giu_toi_da_luot`: `None` (mặc định) = lấy từ `kenh.yaml`; `0` = tắt luật
    thứ hai, hành vi y như trước khi luật ấy ra đời.

    Gọi lại nhiều lần là an toàn: lượt đã dọn sạch không còn gì NẶNG để tính
    vào ứng viên nữa, nên lần gọi sau không làm gì thêm.
    """
    if bay_gio is None:
        bay_gio = datetime.datetime.now()
    ke_hoach = _gop_ung_vien(
        ung_vien_don(goc, ma_kenh, bay_gio=bay_gio, cho_gio=cho_gio),
        ung_vien_qua_so_luot(goc, ma_kenh, giu=giu_toi_da_luot, bay_gio=bay_gio),
    )
    # Luật BỐN (01/10/2026): gói DONE đã đăng + xác nhận + hậu kiểm. Chạy SAU
    # luật MỘT/HAI để bản sinh đôi trong lượt (nếu còn) đã được xoá trước.
    try:
        ke_done = ung_vien_done(goc, ma_kenh, bay_gio=bay_gio)
    except Exception:  # noqa: BLE001 — sổ máy đăng hỏng không chặn dọn PROJECTS
        ke_done = []
    ket_qua: Dict[str, Any] = {
        "kenh": ma_kenh,
        "thuc_hien": bool(thuc_hien),
        "ung_vien": ke_hoach,
        "ung_vien_done": ke_done,
        "tong_bytes": sum(u["bytes"] for u in ke_hoach) + sum(u["bytes"] for u in ke_done),
    }
    if not thuc_hien:
        return ket_qua

    da_don: List[Dict[str, Any]] = []
    for u in ke_hoach:
        ket = _xoa_mot_ung_vien(goc, ma_kenh, u, bay_gio)
        if ket is not None:
            da_don.append(ket)
    # Đo lại ứng viên DONE sau khi PROJECTS đã xoá: liên kết cứng vừa mất một
    # phía thì byte giải phóng của gói DONE đổi (0 → cỡ thật).
    try:
        ke_done = ung_vien_done(goc, ma_kenh, bay_gio=bay_gio)
    except Exception:  # noqa: BLE001
        ke_done = []
    for u in ke_done:
        ket = _xoa_tep_giai_phong(u, goc, ma_kenh, bay_gio)
        if ket is not None:
            da_don.append(ket)
    ket_qua["da_don"] = da_don
    ket_qua["tong_bytes"] = sum(int(d.get("bytes") or 0) for d in da_don)
    return ket_qua


def don_tat_ca(goc: str, kenh_list: Sequence[str], thuc_hien: bool) -> Dict[str, Dict[str, Any]]:
    """Gọi `don` cho từng kênh trong `kenh_list`. Trả `{mã kênh: kết quả}`.

    Kèm thêm khoá `"_sao_luu"` — luật BA (`ung_vien_sao_luu`/`don_sao_luu`,
    29/09/2026): dọn bớt tệp sao lưu cũ dưới MỌI thư mục con tên `sao-luu`
    trong `CHANNEL/*/`. Việc này quét THẲNG theo đường CHANNEL, không thuộc
    riêng một mã kênh nào trong `kenh_list`, nên không ghép được vào một mục
    `don()` sẵn có — đặt dưới khoá bắt đầu bằng `_` để không bao giờ trùng một
    mã kênh thật (mã kênh không bắt đầu bằng `_`), giữ NGUYÊN kiểu trả về
    `Dict[str, Dict[str, Any]]` để nơi gọi cũ (`ket_qua[<mã kênh>]`) không vỡ.
    """
    ket_qua: Dict[str, Dict[str, Any]] = {ma: don(goc, ma, thuc_hien=thuc_hien) for ma in kenh_list}
    if thuc_hien:
        da_xoa = don_sao_luu(goc)
        ket_qua["_sao_luu"] = {"thuc_hien": True, "da_xoa": da_xoa, "so_luong": len(da_xoa)}
    else:
        ung_vien = ung_vien_sao_luu(goc)
        ket_qua["_sao_luu"] = {"thuc_hien": False, "ung_vien": ung_vien, "so_luong": len(ung_vien)}
    return ket_qua


def don_theo_cai_dat(goc: str, ma_kenh: str) -> Dict[str, Any]:
    """Dọn kênh này NẾU `kenh.yaml` bật `tu_don`; không thì báo lý do, không đụng gì.

    Cửa dọn THƯỜNG (cuối mỗi lượt `--tat-ca`, xem `core/tu_chay.chay_tat_ca`) —
    mặc định của `tu_don` là tắt, nên một kênh mới không tự nhiên bị dọn khi
    chủ chưa bật cờ. `don_khan` bên dưới là cửa DỌN KHẨN (giữa lượt, khi đĩa
    chạm ngưỡng an toàn) — cùng luật `tu_don`, không nới lỏng gì thêm.
    """
    kenh = doc_kenh(goc, ma_kenh)
    if not kenh.tu_don:
        return {"kenh": ma_kenh, "chay": False,
               "ly_do": "kênh chưa bật `tu_don` trong kenh.yaml — không đụng gì."}
    # Luật "quá N lượt" đi cùng cửa này, tức vẫn nằm SAU `tu_don`: một trần số
    # lượt không được biến một kênh chủ dự án đã CHỌN không dọn thành kênh bị
    # dọn. Muốn bật thì bật cả hai khoá.
    ket_qua = don(goc, ma_kenh, thuc_hien=True, cho_gio=kenh.don_sau_gio,
                  giu_toi_da_luot=kenh.giu_toi_da_luot)
    ket_qua["chay"] = True
    return ket_qua


# ── Dọn KHẨN — đĩa chạm ngưỡng an toàn giữa lượt, hoặc vừa dính ENOSPC ───────


def _con_trong_gb(goc: str) -> Optional[float]:
    try:
        _tong, _dung, con = shutil.disk_usage(goc)
    except OSError:
        return None
    return con / 1024 ** 3


def don_khan(goc: str, danh_sach_kenh: Sequence[str], *, nguong_gb: float,
            bay_gio: Optional[datetime.datetime] = None,
            con_trong_gb_fn: Optional[Callable[[str], Optional[float]]] = None) -> Dict[str, Any]:
    """DỌN KHẨN — gọi từ `core/tu_chay.py` khi van đĩa trống thấy đĩa chạm/dưới
    ngưỡng an toàn (trước khi mở video mới), hoặc vừa dính lỗi ĐĨA ĐẦY
    (`ENOSPC`/`WinError 112`) giữa chừng sản xuất.

    ═══ AN TOÀN — GIỐNG HỆT DỌN THƯỜNG, KHÔNG NỚI LỎNG GÌ ═══

    Chỉ dọn kênh đã tự bật `tu_don: true` (cùng luật `don_theo_cai_dat`, cùng
    hạn ân xá `don_sau_gio` của từng kênh) — khẩn cấp không phải lý do để lật
    lại một cờ chủ dự án đã CHỌN tắt. Kênh chưa bật `tu_don` bị BỎ QUA hoàn
    toàn, dù đĩa có sắp đầy tới đâu; tên các kênh bị bỏ qua trả về trong
    `bo_qua_khong_tu_don` để nơi gọi ghi rõ vào sổ ngày (không giấu giới hạn
    này). Mọi luật an toàn khác (chỉ video ĐÃ ĐĂNG, chỉ thứ NẶNG, không đi ra
    ngoài `PROJECTS/AUTO/<kênh>/` hay `thu_muc_done`) đi qua nguyên `ung_vien_don`
    + `_xoa_mot_ung_vien` — không viết lại.

    ═══ THỨ TỰ: CŨ NHẤT TRƯỚC, DỪNG NGAY KHI ĐỦ ═══

    Gom ứng viên (`ung_vien_don`) của MỌI kênh trong `danh_sach_kenh` đã bật
    `tu_don`, xếp theo `moc_dang` tăng dần (lượt đăng lâu đời nhất trước — xa
    ngày đăng nhất thì ít khả năng còn cần xem/tải lại), rồi xoá TỪNG lượt một,
    đo lại dung lượng trống sau MỖI lượt, dừng ngay khi đã vượt `nguong_gb`
    hoặc hết ứng viên — không xoá quá tay khi đã đủ.

    Trả về `dict` có `da_chay` (có thật sự dọn gì không), `con_truoc_gb`/
    `con_sau_gb`, `da_giai_phong_bytes`, `theo_kenh` ({mã kênh: byte đã xoá}),
    `da_don` (chi tiết từng lượt đã xoá), `bo_qua_khong_tu_don`.
    """
    bay_gio = bay_gio or datetime.datetime.now()
    do_dia = con_trong_gb_fn or _con_trong_gb
    con_luc_dau = do_dia(goc)

    if con_luc_dau is not None and con_luc_dau >= nguong_gb:
        return {"da_chay": False, "con_truoc_gb": con_luc_dau, "con_sau_gb": con_luc_dau,
               "da_giai_phong_bytes": 0, "theo_kenh": {}, "da_don": [],
               "bo_qua_khong_tu_don": [],
               "ly_do": "đĩa còn {0:.1f} GB, đã ≥ ngưỡng {1:.1f} GB — không cần dọn khẩn."
                       .format(con_luc_dau, nguong_gb)}

    ung_vien_tat_ca: List[Dict[str, Any]] = []
    bo_qua: List[str] = []
    for ma in danh_sach_kenh:
        try:
            kenh = doc_kenh(goc, ma)
        except Exception:  # noqa: BLE001 — một kênh đọc hỏng không được chặn cả lượt dọn khẩn
            continue
        if not kenh.tu_don:
            bo_qua.append(ma)
            continue
        try:
            ung_vien_tat_ca.extend(_gop_ung_vien(
                ung_vien_don(goc, ma, bay_gio=bay_gio, cho_gio=kenh.don_sau_gio),
                # Đúng luật của dọn thường, không nới lỏng: `giu_toi_da_luot`
                # của chính kênh ấy. Kênh để `0` thì cửa này vẫn chỉ thấy lượt
                # ĐÃ ĐĂNG, dù đĩa sắp đầy tới đâu.
                ung_vien_qua_so_luot(goc, ma, giu=kenh.giu_toi_da_luot, bay_gio=bay_gio),
                # Luật BỐN — cùng điều kiện như dọn thường, không nới lỏng.
                ung_vien_done(goc, ma, bay_gio=bay_gio),
            ))
        except Exception:  # noqa: BLE001 — kế hoạch đăng của MỘT kênh hỏng không chặn kênh khác
            continue

    # Chuỗi ISO cùng định dạng so được CŨ/MỚI đúng bằng so sánh chuỗi thường —
    # thiếu (không nên xảy ra, `ung_vien_don` luôn kèm mốc) thì đẩy xuống CUỐI
    # (`"￿"`, sau mọi chuỗi ngày thật) — an toàn hơn: không đoán bừa một
    # lượt không rõ tuổi là "cũ nhất", đứng xoá trước tiên.
    ung_vien_tat_ca.sort(key=lambda u: u.get("moc_dang") or "￿")

    theo_kenh: Dict[str, int] = {}
    da_don: List[Dict[str, Any]] = []
    tong_bytes = 0
    con_hien_tai = con_luc_dau
    for u in ung_vien_tat_ca:
        if con_hien_tai is not None and con_hien_tai >= nguong_gb:
            break
        if u.get("loai") == "done":
            ket = _xoa_tep_giai_phong(u, goc, u["kenh"], bay_gio)
        else:
            ket = _xoa_mot_ung_vien(goc, u["kenh"], u, bay_gio)
        if ket is None:
            continue
        da_don.append(ket)
        theo_kenh[u["kenh"]] = theo_kenh.get(u["kenh"], 0) + int(ket["bytes"])
        tong_bytes += int(ket["bytes"])
        con_hien_tai = do_dia(goc)

    return {"da_chay": True, "con_truoc_gb": con_luc_dau, "con_sau_gb": con_hien_tai,
           "da_giai_phong_bytes": tong_bytes, "theo_kenh": theo_kenh, "da_don": da_don,
           "bo_qua_khong_tu_don": bo_qua}
