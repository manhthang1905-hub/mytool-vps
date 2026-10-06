"""Tự nhận video ĐÃ ĐĂNG qua đối chiếu Studio — chủ kênh không cần bấm gì.

═══ VÌ SAO CÓ TỆP NÀY (chẩn đoán 28/09/2026) ═══

Chủ kênh đăng video TAY trên YouTube (Studio, hẹn giờ của chính YouTube…)
chứ không đi qua tool, và không biết/không muốn bấm "Đã đăng thủ công" —
thấy quản lý thủ công quá khó. Hậu quả: `core.tu_chay._cua_so_san_xuat` coi
mọi gói "Sẵn sàng" chưa có "Trạng thái đăng" là đang CHỜ, không mở nguồn mới
khi còn gói chờ — kênh ĐỨNG IM VÔ HẠN vì một thao tác không bao giờ tới.

Mục tiêu: chủ kênh CHỈ cần đăng video trên YouTube, tool tự nhận ra bằng cách
đối chiếu tiêu đề giữa danh sách video thật trên kênh (Studio, do phiên kênh
`vm/agent.py` cào bằng extension, xem `CHANNEL/<kênh>/chi-so/kenh/`) với các
dòng kế hoạch đang chờ đăng.

═══ NGUỒN DỮ LIỆU ═══

`CHANNEL/<kênh>/chi-so/kenh/<kenh|tay>-<YYYYMMDD>/raw/*get_creator_videos*.json`
— mỗi lần phiên kênh mở Studio, extension chụp lại kết quả gọi
`youtubei/v1/creator/get_creator_videos` của chính YouTube. Một số bản ghi
chỉ xin `mask` hẹp (chỉ videoId/quyền/kiếm tiền — KHÔNG có `title`); bản ghi
đủ trường có `videoId`, `title`, `privacy`, `timePublishedSeconds` (mốc CÔNG
KHAI THẬT, epoch giây, dạng chuỗi). Chỉ nhận video có `privacy` là
`VIDEO_PRIVACY_PUBLIC` — video riêng tư/đang xử lý CHƯA đăng thật.

═══ KHỚP MỜ AN TOÀN, KHÔNG ĐOÁN BỪA ═══

Chủ kênh có thể sửa nhẹ tiêu đề lúc đăng (thêm emoji, sửa vài chữ, đổi
full-width ⇄ half-width…) nên so khớp CHÍNH XÁC là vô dụng. `chuan_hoa_tieu_de`
gộp Unicode NFKC (full/half-width về một mối), bỏ dấu câu, gộp khoảng trắng
thừa, rồi so bằng `difflib.SequenceMatcher` (thư viện chuẩn, không thêm phụ
thuộc — cùng nếp `core/bao_dong.py` chọn `urllib` thay vì `requests`).

An toàn: MỘT dòng kế hoạch chỉ được tự đánh dấu khi có ĐÚNG MỘT video công
khai đạt tỉ lệ giống ≥ `NGUONG_GIONG_MAC_DINH` (0,85). Không có video nào đạt,
hoặc có từ hai video trở lên cùng đạt (không phân biệt được cái nào), thì BỎ
QUA — không đoán bừa, an toàn hơn đánh dấu nhầm.

Một video trên kênh không khớp gói nào (kênh có nội dung khác tool này làm,
hoặc lượt AUTO không có trong kế hoạch vì QA chưa từng đạt) thì cũng BỎ QUA
ÊM — không phải lỗi.

═══ GHI SỔ QUA ĐÚNG MỘT CỬA ═══

Việc "đánh dấu đã đăng" đi qua `core.ban_giao_dang.danh_dau_dang_tay` — ĐÚNG
hàm mà nút "Đã đăng thủ công" trên giao diện gọi — không viết lại luật ghi
sổ ở một chỗ thứ hai. Chỉ khác ở `ghi_chu` ("tự nhận từ Studio <videoId>", để
chủ dự án đọc sổ biết ai/cái gì đánh dấu) và mốc giờ (ngày CÔNG KHAI THẬT nếu
Studio có, không thì giờ quét).

Không mạng, không Qt, không tốn ví — chỉ đọc `chi-so/`, và (khi `thuc_hien=True`)
ghi `ke-hoach.csv`. `thuc_hien=False` chỉ TÍNH, không ghi gì — dùng để kiểm
"chạy khô" trên dữ liệu thật mà không đụng sổ sách.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import ban_giao_dang, ke_hoach_dang
from .chi_so_ytb import kho_raw as _kho_raw

__all__ = ["NGUONG_GIONG_MAC_DINH", "chuan_hoa_tieu_de",
           "doc_video_cong_khai_tren_kenh", "tu_nhan_video_da_dang"]

#: Tỉ lệ giống tối thiểu (0..1, `difflib.SequenceMatcher.ratio`) để coi hai
#: tiêu đề là "cùng một video" — xem "KHỚP MỜ AN TOÀN" ở đầu tệp.
NGUONG_GIONG_MAC_DINH = 0.85

#: Trạng thái coi là "ĐÃ ĐĂNG rồi" — không cần đối chiếu lại, bỏ qua êm.
_DA_DANG = ("ĐÃ ĐĂNG", ban_giao_dang.TRANG_THAI_DANG_TAY)

_RE_KHOANG_TRANG = re.compile(r"\s+")
#: Dấu câu la-tinh (`!-/`, `:-@`, `[-`` `, `{-~`) + dấu câu CJK hay gặp trong
#: tiêu đề YouTube tiếng Nhật (｡ ･ 、 。 ！ ？ 「」『』【】・…〜～ và khoảng trắng
#: toàn độ rộng U+3000). Đổi thành MỘT khoảng trắng, không xoá trắng — tránh
#: dính hai từ liền nhau thành một từ khác nghĩa.
_RE_DAU_CAU = re.compile(
    r"[!-/:-@\[-`{-~｡-･、。！？「」『』【】・…〜～　]+"
)

#: Tên thư mục một lượt quét kênh — `kenh-20260927` (quét lịch) hoặc
#: `tay-20260927` (quét tay/khác) — cả hai đều đáng tin như nhau.
_RE_TEN_THU_MUC_QUET = re.compile(r"^(?:kenh|tay)-(\d{8})$")


def chuan_hoa_tieu_de(tieu_de: str) -> str:
    """Chuẩn hoá một tiêu đề để so khớp MỜ: NFKC (gộp full-width/half-width
    về một mối — vd `"！"` và `"!"` thành cùng một ký tự), hạ chữ thường
    (không đổi gì với chữ CJK), đổi dấu câu thành khoảng trắng, gộp khoảng
    trắng thừa. Hai tiêu đề "giống hệt về nội dung, khác vài dấu câu/khoảng
    trắng/full-half width" sẽ chuẩn hoá về CÙNG một chuỗi.
    """
    chu = unicodedata.normalize("NFKC", str(tieu_de or ""))
    chu = chu.lower()
    chu = _RE_DAU_CAU.sub(" ", chu)
    chu = _RE_KHOANG_TRANG.sub(" ", chu).strip()
    return chu


def _diem_giong(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _thu_muc_quet_kenh(goc: str, ma_kenh: str) -> str:
    return os.path.join(goc, "CHANNEL", ma_kenh, "chi-so", "kenh")


def doc_video_cong_khai_tren_kenh(goc: str, ma_kenh: str) -> Dict[str, Dict[str, Any]]:
    """Mọi video ĐÃ CÔNG KHAI mà Studio từng thấy trên kênh, gộp từ TẤT CẢ
    các lượt quét trong `chi-so/kenh/<kenh|tay>-<ngày>/raw/*get_creator_videos*.json`.

    Trả `{videoId: {"tieu_de", "cong_khai_luc" (epoch giây hoặc `None`),
    "lan_quet_gan_nhat" (chuỗi `YYYYMMDD`)}}`. Một video xuất hiện ở nhiều lượt
    quét thì giữ bản ở lượt quét MỚI NHẤT (sắp theo ngày trong tên thư mục,
    không phải theo bảng chữ cái — `"kenh-"` và `"tay-"` xen kẽ ngày sẽ xếp
    sai nếu so thẳng tên) — tiêu đề có thể được chủ kênh sửa lại sau khi đăng.

    Chỉ ĐỌC, không mạng, không sửa gì. Một thư mục/tệp JSON hỏng, thiếu
    trường, hay chỉ mang `mask` hẹp (không có `title`) đều bị BỎ QUA lặng lẽ —
    một lượt quét hỏng không được làm mất dấu các lượt quét khác.
    """
    goc_quet = _thu_muc_quet_kenh(goc, ma_kenh)
    try:
        ten_con = os.listdir(goc_quet)
    except OSError:
        return {}

    #: `(khoá sắp xếp theo NGÀY, tên thư mục)` — thư mục không đúng khuôn
    #: `kenh-YYYYMMDD`/`tay-YYYYMMDD` (hiếm, sửa tay) xếp CUỐI theo chính tên
    #: nó, coi như "không rõ ngày" chứ không loại bỏ.
    thu_muc_theo_ngay: List[Tuple[str, str]] = []
    for ten in ten_con:
        duong = os.path.join(goc_quet, ten)
        if not os.path.isdir(duong):
            continue
        mau = _RE_TEN_THU_MUC_QUET.match(ten)
        khoa = mau.group(1) if mau else ("9" * 8 + ten)
        thu_muc_theo_ngay.append((khoa, ten))
    thu_muc_theo_ngay.sort()

    ra: Dict[str, Dict[str, Any]] = {}
    for khoa_ngay, ten in thu_muc_theo_ngay:
        ngay_quet = khoa_ngay if khoa_ngay.isdigit() else ten
        duong_raw = os.path.join(goc_quet, ten, "raw")
        try:
            danh_sach_tep = _kho_raw.liet_ke(duong_raw, "*get_creator_videos*.json")  # cả bản .gz
        except OSError:
            continue
        for duong_json in danh_sach_tep:
            try:
                du = _kho_raw.doc_json(duong_json)
            except (OSError, ValueError):
                continue
            if not isinstance(du, dict):
                continue
            videos = (((du.get("response") or {}).get("videos")) or [])
            if not isinstance(videos, list):
                continue
            for vid in videos:
                if not isinstance(vid, dict):
                    continue
                video_id = str(vid.get("videoId") or "").strip()
                tieu_de = vid.get("title")
                if not video_id or tieu_de is None:
                    continue  # bản ghi mask hẹp — không mang tiêu đề, bỏ qua
                if vid.get("privacy") not in (None, "VIDEO_PRIVACY_PUBLIC"):
                    continue  # riêng tư/chưa liệt kê/đang xử lý — chưa đăng thật
                cong_khai_luc: Optional[float]
                try:
                    cong_khai_luc = float(vid.get("timePublishedSeconds"))
                except (TypeError, ValueError):
                    cong_khai_luc = None
                ra[video_id] = {"tieu_de": str(tieu_de), "cong_khai_luc": cong_khai_luc,
                               "lan_quet_gan_nhat": ngay_quet}
    return ra


def tu_nhan_video_da_dang(
    goc: str, ma_kenh: str, *,
    bay_gio: Optional[_dt.datetime] = None,
    nguong_giong: float = NGUONG_GIONG_MAC_DINH,
    on_log: Optional[Callable[[str], None]] = None,
    thuc_hien: bool = True,
) -> List[Dict[str, Any]]:
    """Đối chiếu video ĐÃ CÔNG KHAI trên kênh (Studio) với các dòng kế hoạch
    "Sẵn sàng" mà CHƯA có "Trạng thái đăng" — tự đánh dấu ĐÃ ĐĂNG khi chắc
    chắn, để chủ kênh không cần bấm "Đã đăng thủ công" trong tool.

    Mỗi dòng kế hoạch đang chờ chỉ được đánh dấu khi có ĐÚNG MỘT video công
    khai đạt tỉ lệ giống tiêu đề (đã chuẩn hoá, xem `chuan_hoa_tieu_de`)
    `>= nguong_giong` — xem "KHỚP MỜ AN TOÀN" ở đầu tệp. Một video chỉ được
    dùng cho ĐÚNG MỘT dòng trong một lần gọi (tránh một video "ăn" nhầm nhiều
    dòng trùng tiêu đề soạn kiểu template).

    `thuc_hien=False`: CHỈ TÍNH, không ghi gì vào `ke-hoach.csv` — dùng để
    kiểm "chạy khô" trên dữ liệu thật mà không đụng sổ sách.

    Trả về danh sách một phần tử cho mỗi hành động ĐÃ/SẼ làm:
    `{"ma_goi", "video_id", "tieu_de_ke_hoach", "tieu_de_studio", "diem_giong",
    "cong_khai_luc", "moc_danh_dau", "da_danh_dau"}`. Không ném lỗi vì thiếu
    dữ liệu — kênh chưa có lượt quét nào, hay kế hoạch trống, đều trả `[]`.
    """
    def log(dong: str) -> None:
        if on_log is not None:
            on_log(dong)

    videos = doc_video_cong_khai_tren_kenh(goc, ma_kenh)
    if not videos:
        return []

    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    can_thiet = ("Mã gói", "Sẵn sàng", "Trạng thái đăng", "Tiêu đề")
    if any(ten not in cot for ten in can_thiet):
        return []
    o_ma, o_san, o_tt, o_td = (cot.index("Mã gói"), cot.index("Sẵn sàng"),
                              cot.index("Trạng thái đăng"), cot.index("Tiêu đề"))

    #: Chuẩn hoá tiêu đề Studio MỘT LẦN, dùng lại cho mọi dòng kế hoạch —
    #: kênh có thể có hàng trăm video, đừng chuẩn hoá lại mỗi vòng lặp dòng.
    video_chuan: Dict[str, str] = {vid: chuan_hoa_tieu_de(meta["tieu_de"])
                                   for vid, meta in videos.items()}
    da_dung: set = set()
    ket_qua: List[Dict[str, Any]] = []

    for dong in hang:
        ma = dong[o_ma].strip() if o_ma < len(dong) else ""
        if not ma:
            continue
        san_sang = dong[o_san].strip() if o_san < len(dong) else ""
        if not san_sang:
            continue  # chưa qua QA/chưa duyệt — không phải việc của hàm này
        trang_thai = dong[o_tt].strip() if o_tt < len(dong) else ""
        if trang_thai in _DA_DANG:
            continue  # đã đăng rồi (máy hoặc tay) — bỏ qua êm
        tieu_de_kh = dong[o_td].strip() if o_td < len(dong) else ""
        if not tieu_de_kh:
            continue
        chuan_kh = chuan_hoa_tieu_de(tieu_de_kh)
        if not chuan_kh:
            continue

        khop: List[Tuple[str, float]] = []
        for vid, chuan_vid in video_chuan.items():
            if vid in da_dung:
                continue
            diem = _diem_giong(chuan_kh, chuan_vid)
            if diem >= nguong_giong:
                khop.append((vid, diem))
        if not khop:
            continue
        if len(khop) > 1:
            log("  {0}: {1} video công khai cùng khớp mờ tiêu đề — không chắc, bỏ qua."
               .format(ma, len(khop)))
            continue

        vid, diem = khop[0]
        meta = videos[vid]
        da_dung.add(vid)
        cong_khai_luc = meta.get("cong_khai_luc")
        if cong_khai_luc:
            try:
                moc = _dt.datetime.fromtimestamp(cong_khai_luc)
            except (OverflowError, OSError, ValueError):
                moc = bay_gio or _dt.datetime.now()
        else:
            moc = bay_gio or _dt.datetime.now()
        ghi_chu = "tự nhận từ Studio {0}".format(vid)
        ket = {"ma_goi": ma, "video_id": vid, "tieu_de_ke_hoach": tieu_de_kh,
              "tieu_de_studio": meta["tieu_de"], "diem_giong": round(diem, 3),
              "cong_khai_luc": cong_khai_luc,
              "moc_danh_dau": moc.isoformat(timespec="minutes"), "da_danh_dau": False}
        if thuc_hien:
            ket["da_danh_dau"] = bool(ban_giao_dang.danh_dau_dang_tay(
                goc, ma_kenh, ma, ghi_chu=ghi_chu, bay_gio=moc))
            if ket["da_danh_dau"]:
                log("  {0}: tự nhận ĐÃ ĐĂNG (khớp {1:.0%} với video {2} “{3}”)."
                   .format(ma, diem, vid, meta["tieu_de"][:60]))
        else:
            log("  [CHẠY KHÔ] {0}: sẽ tự nhận ĐÃ ĐĂNG (khớp {1:.0%} với video {2} “{3}”)."
               .format(ma, diem, vid, meta["tieu_de"][:60]))
        ket_qua.append(ket)
    return ket_qua
