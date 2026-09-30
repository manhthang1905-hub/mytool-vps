"""Vòng học trước mỗi lượt — bước "0) Học từ số liệu" của `core/tu_chay.py`.

Việc 3, `workspace/THIET-KE-DUNG-VA-VONG-HOC.md`: mọi thứ ở đây là VÒNG LẶP tự
chạy MỖI LƯỢT, ngay TRƯỚC "1) Nghiên cứu" — học từ số liệu Studio của các video
CŨ trước khi quyết định video MỚI. Bốn bước, MỖI BƯỚC TỰ `try/except` RIÊNG:
một bước hỏng chỉ ghi log rồi bỏ qua ĐÚNG bước đó — không bước nào, dù hỏng,
được phép chặn sản xuất/chặn đăng (luật đầu tiên của bản thiết kế).

    1. `core.kho_nhac.cap_nhat`         — chuẩn hoá kho nhạc TĂNG DẦN (300s).
    2. `core.ho_so_video.bu_ho_so`      — bù hồ sơ các gói đã đăng trước.
       `core.ho_so_video.cap_nhat_chi_so` — nối video_id + số liệu Studio.
    3. `core.bai_hoc_san_xuat.xuat_markdown` — rút bài học (DEBOUNCE, xem
       `_can_hoc_lai`: chỉ khi bước 2 vừa nối được số mới, hoặc bản đã lưu cũ
       hơn 24 giờ — giữ nguyên ngưỡng an toàn n<3 không bơm/3-5 số thô/≥6 xếp
       hạng đã có sẵn trong `bai_hoc_san_xuat`, tệp này không đụng vào).
    4. `core.khuon_bia.cap_nhat` (Việc 4, CHƯA LÀM) — kiểm tồn tại module
       trước khi gọi; chưa có thì bỏ qua êm, không phải lỗi.
    5. `core.chien_luoc.ket_qua.ghi_tep` (B4 bộ máy chiến lược, 30/09/2026) —
       ghi `nghien-cuu/chien-luoc.json`: thống kê theo công thức + tỉ trọng
       GỢI Ý (chưa áp) + 1 dòng log. Cùng luật debounce với bước 3 (số mới
       hoặc tệp của chính nó cũ hơn 24h / chưa có), try riêng.

Cờ `kenh.yaml: vong_hoc` (mặc định BẬT, đọc qua `core.kenh.Kenh.vong_hoc`) tắt
được cả bốn bước cho một kênh — nơi gọi (`tu_chay.py`) kiểm cờ này TRƯỚC khi
gọi `truoc_luot`, không kiểm ở đây, để hàm này gọi độc lập được từ test/tay mà
không cần đọc `kenh.yaml` trước.
"""

from __future__ import annotations

import datetime as _dt
import os
from typing import Any, Callable, Dict, Optional

from . import bai_hoc_san_xuat, ho_so_video, kho_nhac

__all__ = ["truoc_luot", "GIO_DEBOUNCE_BAI_HOC", "NGAN_SACH_KHO_NHAC_GIAY"]

#: Bước 3 (bài học) chỉ tính lại khi bản đã lưu CŨ hơn ngần này giờ — tránh
#: tính lại (thuần CPU, không tốn ví, nhưng vẫn phí công đĩa) mỗi lượt khi
#: không có số liệu Studio mới nào về. Xem "debounce" ở mục Việc 3 bản thiết kế.
GIO_DEBOUNCE_BAI_HOC = 24.0

#: Ngân sách giây cho `kho_nhac.cap_nhat` Ở BƯỚC NÀY ("mỗi lượt", trước sản
#: xuất) — khác ngân sách 60s bên trong khâu dựng (Việc 2). Chạy tay lần đầu
#: (nạp hết kho) thì gọi thẳng `kho_nhac.cap_nhat(goc, None)` (`--het`), không
#: qua hàm này.
NGAN_SACH_KHO_NHAC_GIAY = 300


def _can_hoc_lai(goc: str, kenh: str, co_so_moi: bool, *, bay_gio: _dt.datetime,
                 duong: Optional[str] = None) -> bool:
    """DEBOUNCE bước 3: học lại khi vừa có số liệu MỚI (`co_so_moi`), bản đã
    lưu CŨ hơn `GIO_DEBOUNCE_BAI_HOC` giờ, hoặc CHƯA TỪNG học lần nào (kênh
    mới) — không chờ đủ 24h đầu tiên trước khi có bài học lần đầu.

    `duong` (bước 5): đo tuổi trên tệp KHÁC (`chien-luoc.json`) với cùng luật —
    mặc định là tệp bài học sản xuất như cũ."""
    if co_so_moi:
        return True
    duong = duong or bai_hoc_san_xuat.duong_tep_bai_hoc(goc, kenh)
    try:
        mtime = os.path.getmtime(duong)
    except OSError:
        return True
    tuoi_gio = (bay_gio.timestamp() - mtime) / 3600.0
    return tuoi_gio > GIO_DEBOUNCE_BAI_HOC


def truoc_luot(goc: str, ma_kenh: str, goi_chat: Optional[Callable[..., str]],
               log: Callable[[str], None], *,
               bay_gio: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Bốn bước "học từ số liệu" — gọi TRƯỚC "1) Nghiên cứu" của mỗi lượt.

    `goi_chat` dành cho bước 4 (Việc 4, mô tả khuôn ảnh bìa bằng AI) — Việc 3
    không tự gọi AI ở đâu cả (0₫ đúng như bản thiết kế). Không bao giờ ném lỗi:
    mỗi bước tự `try/except`, hỏng bước nào chỉ ghi log rồi bỏ qua bước đó, các
    bước sau vẫn chạy tiếp. Trả một tóm tắt để nơi gọi/test kiểm được đã làm
    gì — KHÔNG dùng để quyết định có tiếp tục lượt sản xuất hay không.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    ket: Dict[str, Any] = {"kho_nhac": None, "bu_ho_so": [], "chi_so": None,
                           "bai_hoc": False, "khuon_bia": None, "chien_luoc": None}

    # 1) Kho nhạc — chuẩn hoá tăng dần, không chặn lượt nếu ffmpeg/kho nhạc hỏng.
    try:
        ket["kho_nhac"] = kho_nhac.cap_nhat(goc, NGAN_SACH_KHO_NHAC_GIAY, ghi=log)
    except Exception as loi:  # noqa: BLE001
        log("  0) [vòng học] cập nhật kho nhạc hỏng: {0} — bỏ qua.".format(str(loi)[:200]))

    # 2) Hồ sơ video: bù các gói cũ trước, rồi nối video_id + số liệu Studio.
    co_so_moi = False
    try:
        moi_bu = ho_so_video.bu_ho_so(goc, ma_kenh, on_log=log)
        ket["bu_ho_so"] = moi_bu
        if moi_bu:
            log("  0) [vòng học] bù {0} hồ sơ video đã đăng trước đó: {1}."
               .format(len(moi_bu), ", ".join(moi_bu)))
    except Exception as loi:  # noqa: BLE001
        log("  0) [vòng học] bù hồ sơ video hỏng: {0} — bỏ qua.".format(str(loi)[:200]))
    try:
        tt = ho_so_video.cap_nhat_chi_so(goc, ma_kenh, bay_gio=bay_gio, on_log=log)
        ket["chi_so"] = tt
        co_so_moi = bool(tt.get("cap_nhat_moc"))
        if tt.get("noi_video_id") or tt.get("cap_nhat_moc"):
            log("  0) [vòng học] số liệu Studio: nối {0} video_id, điền {1} mốc mới."
               .format(tt.get("noi_video_id", 0), tt.get("cap_nhat_moc", 0)))
    except Exception as loi:  # noqa: BLE001
        log("  0) [vòng học] nối số liệu Studio hỏng: {0} — bỏ qua.".format(str(loi)[:200]))

    # 3) Bài học sản xuất — DEBOUNCE (số mới hoặc >24h), giữ nguyên ngưỡng an toàn.
    try:
        if _can_hoc_lai(goc, ma_kenh, co_so_moi, bay_gio=bay_gio):
            bai_hoc_san_xuat.xuat_markdown(goc, ma_kenh, bay_gio=bay_gio)
            ket["bai_hoc"] = True
    except Exception as loi:  # noqa: BLE001
        log("  0) [vòng học] rút bài học sản xuất hỏng: {0} — bỏ qua.".format(str(loi)[:200]))

    # 4) Khuôn ảnh bìa thắng (Việc 4) — CHƯA LÀM: để trống có kiểm tồn tại module.
    try:
        from . import khuon_bia  # noqa: PLC0415 — Việc 4, module có thể chưa tồn tại
    except ImportError:
        pass  # chưa tới Việc 4 — không phải lỗi, chỉ chưa xây
    except Exception as loi:  # noqa: BLE001
        log("  0) [vòng học] nạp module khuôn bìa hỏng: {0} — bỏ qua.".format(str(loi)[:200]))
    else:
        try:
            ket["khuon_bia"] = khuon_bia.cap_nhat(goc, ma_kenh, goi_chat)
        except Exception as loi:  # noqa: BLE001
            log("  0) [vòng học] cập nhật khuôn bìa hỏng: {0} — bỏ qua.".format(str(loi)[:200]))

    # 5) Thống kê theo công thức + tỉ trọng GỢI Ý (chưa áp) — cùng debounce bước 3.
    try:
        from .chien_luoc import ket_qua  # noqa: PLC0415 — gói chiến lược nạp muộn

        if _can_hoc_lai(goc, ma_kenh, co_so_moi, bay_gio=bay_gio,
                        duong=ket_qua.duong_tep(goc, ma_kenh)):
            ket["chien_luoc"] = ket_qua.ghi_tep(goc, ma_kenh, bay_gio=bay_gio, log=log)
    except Exception as loi:  # noqa: BLE001
        log("  0) [vòng học] thống kê theo công thức hỏng: {0} — bỏ qua.".format(str(loi)[:200]))

    return ket
