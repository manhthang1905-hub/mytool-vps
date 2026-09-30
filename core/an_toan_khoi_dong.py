"""Đóng cửa sổ MyTool rồi mở lại (khởi động lại giao diện) có AN TOÀN không —
mục 6 của `workspace/THIET-KE-BANG-DIEU-KHIEN.md` (duyệt 29/09/2026), Việc 3.

═══ HÀM THUẦN — CHỈ ĐỌC, KHÔNG BAO GIỜ TỰ LÀM GÌ ═══

`kiem_tra()` chỉ ĐỌC vài tệp trên đĩa rồi trả lời "có nên bấm khởi động lại
bây giờ không" — không ghi tệp nào, không gọi mạng, không sinh tiến trình
con, và TUYỆT ĐỐI không tự đóng/mở cửa sổ hay giết tiến trình nào. Bản thiết
kế nói rõ ở mục 5: "chưa làm nút tự khởi động lại" — khi nào bấm vẫn là
người vận hành tự quyết, hàm này chỉ đưa thêm thông tin để quyết cho đúng.

═══ NĂM ĐIỀU KIỆN — SỬA 29/09/2026 (tối), xem
`workspace/ban-va/2026-09-29-tu-canh-loi/GHI-CHU.md` ═══

Bản duyệt gốc (mục 6) coi "có kênh đang sản xuất" (điều kiện 3 cũ) là một lý
do chặn khởi động lại — nhưng vòng tự chạy thật (`core.tu_chay --tat-ca`/
`--dieu-phoi`) chạy như tiến trình TÁCH RỜI qua lịch Windows, không chung
tiến trình với giao diện, và từ bản vá 29/09 (tối) `core.tien_trinh_con` đã
phân biệt được tiến trình nào của giao diện (`chu == "gui"`) với tiến trình
nào của một lượt sản xuất tách rời (`chu == "tu_chay"`) — "kênh đang sản
xuất" một mình không còn là lý do đủ để chặn giao diện mở lại nữa. Điều kiện
3 vì vậy đổi từ "không kênh nào đang sản xuất" (dò `core.trung_tam.
khoa_dang_giu`) sang "khe *nang* (`core.khe`, độc quyền toàn máy) không đang
giữ một việc THỰC SỰ nguy hiểm nếu bị ngắt giữa chừng" — chỉ còn "tai_len"
(đang tải video lên YouTube) và "quet" (đang quét Studio bằng trình duyệt
thật): hai việc trình duyệt CÒN MỞ, giết ngang có thể để lại video dở hoặc
phiên trình duyệt hỏng (CLAUDE.local.md luật riêng VPS #2). Các khâu nội bộ
khác (viết kịch bản, dựng video, tạo ảnh…) không giữ trình duyệt, an toàn để
giao diện mở lại song song.

(1) Không đang đăng dở video nào — `vm/logs/dang-dodang.json`, ghi bởi
    `vm/may_dang.py::_ghi_dodang` lúc bắt đầu một lượt tải/hẹn lịch, xoá bởi
    `_xoa_dodang` khi xong. Có tệp = có kênh đang giữa một lượt tải lên,
    giết lúc này có thể để lại video dở trên kênh thật (CLAUDE.local.md luật
    riêng VPS #2).
(2) Không phiên máy đăng nào đang mở — `<vm>/trang-thai.json`
    (`core.trung_tam._trang_thai_vm`, đọc qua `thu_muc_vm`/`doc_cau_hinh_vm`
    công khai), khoá `phien_cuoi@<k>` (ngày bắt đầu phiên, ghi bởi
    `vm/agent.py::chay_hang_doi_phien`) và `phien_ket_qua@<k>["ket_thuc"]`
    (giờ phiên kết thúc, ghi bởi `vm/agent.py::chay_mot_phien`). Phiên của
    kênh `k` coi là ĐANG MỞ khi `phien_cuoi@k` là hôm nay mà `ket_thuc` của
    `phien_ket_qua@k` KHÔNG bắt đầu bằng hôm nay (chưa ghi xong, hoặc ghi từ
    hôm trước). Cộng thêm hai khung giờ tránh: 07:25–08:15 (máy quét số liệu
    Studio buổi sáng, hằng số cứng — không phụ thuộc dữ liệu kênh) và MỘT
    khung/kênh `[gio_dang − phien_truoc_phut − 5', gio_dang + 60']`, tính
    THẬT từ `gio_dang` của từng kênh (`core.kenh.doc_kenh`, tệp `kenh.yaml`)
    và `phien_truoc_phut` của từng kênh (`core.vm_cai_dat.doc`, tệp
    `may-ao.json`) — KHÔNG hard-code "19:00–21:05": con số đó chỉ là kết quả
    công thức áp cho giờ đăng 20:00 của lịch vận hành lúc duyệt bản thiết kế
    (29/09/2026), và được giữ lại làm khung DỰ PHÒNG khi máy chưa có kênh nào
    khai `gio_dang` hợp lệ để tính (xem `_KHUNG_TOI_MAC_DINH`).
(3) Khe "nang" (`core.khe.trang_thai(goc)["nang"]`, độc quyền toàn máy)
    KHÔNG đang giữ việc `"tai_len"` hay `"quet"` — xem giải thích ở trên.
    Cộng thêm tránh phút :58–:05 mỗi giờ (máy hay ghi sổ đúng lúc đổi
    giờ/phút).
(4) `workspace/tien-trinh-con.json` (sổ của `core.tien_trinh_con`) rỗng, hoặc
    mọi tiến trình con `chu != "tu_chay"` đã ghi nhận đều đã chết — dùng
    thẳng `tien_trinh_con.con_song(pid, tao_luc)`, KHÔNG viết lại logic kiểm
    tiến trình sống. Tiến trình `chu == "tu_chay"` (một lượt sản xuất tách
    rời, xem trên) KHÔNG được tính vào đây nữa — nó sống độc lập với giao
    diện, không cần đợi.
(5) Không có việc khách bấm tay qua giao diện (`core.jobs.JobManager`) còn
    đang chạy. `core.jobs` KHÔNG ghi trạng thái ra đĩa (chỉ sống trong bộ nhớ
    của tiến trình tool đang chạy) — hàm THUẦN ở đây không tự biết được, nên
    nhận qua tham số `viec_chay_tay` (nơi gọi — trang Cài đặt — tự hỏi
    `app.jobs.is_running` rồi truyền vào).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from . import khe
from . import tien_trinh_con
from . import trung_tam as tt
from . import vm_cai_dat
from .kenh import doc_kenh, liet_ke_kenh

__all__ = ["kiem_tra"]

# ── Khung giờ tránh buổi sáng — HẰNG SỐ CỨNG, không phụ thuộc kênh (mục 6):
# máy quét số liệu Studio buổi sáng theo `vm_cai_dat.MAC_DINH["gio_quet"]`
# ("07:30"), cùng giờ mọi kênh — không có "giờ quét của riêng từng kênh" để
# tính động như giờ đăng.
_KHUNG_SANG = (_dt.time(7, 25), _dt.time(8, 15))

#: Khung tối DỰ PHÒNG — chỉ dùng khi KHÔNG kênh nào khai `gio_dang` hợp lệ để
#: tính công thức thật (`_khung_toi_theo_kenh`). Đúng con số bản thiết kế nêu
#: "(hiện 19:00–21:05)": công thức [gio_dang − phien_truoc_phut − 5', gio_dang
#: + 60'] áp cho giờ đăng mặc định 20:00 (`core.kenh`) và `phien_truoc_phut`
#: mặc định 60 phút (`vm_cai_dat.MAC_DINH`) ra đúng [18:55, 21:00] — làm tròn
#: rộng thêm vài phút thành [19:00, 21:05] cho khớp câu bản thiết kế đã duyệt.
_KHUNG_TOI_MAC_DINH = (_dt.time(19, 0), _dt.time(21, 5))

#: Công thức khung tối MỖI KÊNH — [gio_dang − phien_truoc_phut − đệm, gio_dang
#: + sau_gio_dang] (mục 6: "giờ đăng − phien_truoc_phut − 5', giờ đăng + 60'").
_DEM_TRUOC_PHIEN_PHUT = 5
_SAU_GIO_DANG_PHUT = 60

# Phút tránh quanh mốc đổi giờ/phút: :58–:05 (bắc qua đỉnh giờ).
_PHUT_TRANH_TU = 58
_PHUT_TRANH_DEN = 5

# Trần tìm "lúc an toàn tiếp theo" khi CHỈ vướng khung giờ (không vướng việc
# thật đang chạy) — 6 giờ, đủ qua cả khung tối dài nhất trong ngày.
_TOI_DA_PHUT_TIM = 6 * 60


def _doc_json(duong: str) -> Any:
    try:
        with open(duong, "r", encoding="utf-8-sig") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _trong_khung(gio: _dt.time, khung: Any) -> bool:
    dau, cuoi = khung
    return dau <= gio <= cuoi


def _trong_phut_tranh(phut: int) -> bool:
    return phut >= _PHUT_TRANH_TU or phut <= _PHUT_TRANH_DEN


def _khung_toi_theo_kenh(goc: str, cac_kenh: List[str]) -> List[Tuple[_dt.time, _dt.time, str]]:
    """`[(đầu, cuối, mã kênh), ...]` — MỘT khung/kênh, đọc THẬT từ đĩa.

    Công thức mục 6: `[gio_dang − phien_truoc_phut − 5', gio_dang + 60']`.
    `gio_dang` từ `core.kenh.doc_kenh` (tệp `kenh.yaml`), `phien_truoc_phut`
    từ `core.vm_cai_dat.doc` (tệp `may-ao.json`, mặc định 60 phút — khớp
    `vm_cai_dat.MAC_DINH`). Kênh thiếu/lỗi `kenh.yaml`, hoặc chưa khai
    `gio_dang`, bị BỎ QUA (không chặn cả máy vì một kênh hỏng) — `kiem_tra`
    tự lùi về `_KHUNG_TOI_MAC_DINH` khi danh sách trả về rỗng.
    """
    ra: List[Tuple[_dt.time, _dt.time, str]] = []
    for ma in cac_kenh:
        try:
            k = doc_kenh(goc, ma)
        except Exception:  # noqa: BLE001 — kênh hỏng thì bỏ qua, không chặn cả máy
            continue
        gio_dang = tt._gio(str(getattr(k, "gio_dang", "") or ""))  # noqa: SLF001 — hàm nguồn ĐÃ được phép gọi (mục 6)
        if gio_dang is None:
            continue
        phien_truoc = 60
        try:
            phien_truoc = int(vm_cai_dat.doc(goc, ma).get("phien_truoc_phut") or 60)
        except (TypeError, ValueError):
            pass
        phut_dang = gio_dang.hour * 60 + gio_dang.minute
        dau_phut = max(0, phut_dang - phien_truoc - _DEM_TRUOC_PHIEN_PHUT)
        cuoi_phut = min(23 * 60 + 59, phut_dang + _SAU_GIO_DANG_PHUT)
        ra.append((_dt.time(dau_phut // 60, dau_phut % 60),
                  _dt.time(cuoi_phut // 60, cuoi_phut % 60), ma))
    return ra


def _ly_do_khung_gio(bay_gio: _dt.datetime,
                     khung_toi: List[Tuple[_dt.time, _dt.time, str]]) -> List[str]:
    gio = bay_gio.time()
    ra: List[str] = []
    if _trong_khung(gio, _KHUNG_SANG):
        ra.append("Sắp tới giờ máy quét số liệu Studio buổi sáng (07:25–08:15) "
                  "— đợi qua giờ đó rồi hẵng khởi động lại.")
    if khung_toi:
        for dau, cuoi, ma in khung_toi:
            if _trong_khung(gio, (dau, cuoi)):
                ra.append(
                    "Sắp tới hoặc đang trong khung giờ đăng của kênh {0} "
                    "({1}–{2}) — đợi qua giờ đó rồi hẵng khởi động lại.".format(
                        ma, dau.strftime("%H:%M"), cuoi.strftime("%H:%M")))
    elif _trong_khung(gio, _KHUNG_TOI_MAC_DINH):
        ra.append("Đang trong khung giờ đăng video buổi tối (19:00–21:05) "
                  "— đợi qua giờ đó rồi hẵng khởi động lại.")
    return ra


def _ly_do_phut_doi_gio(bay_gio: _dt.datetime) -> List[str]:
    if _trong_phut_tranh(bay_gio.minute):
        return ["Đang sát phút đổi giờ (:58–:05), máy hay ghi sổ đúng lúc "
                "này — đợi qua phút này đã."]
    return []


def _chan_boi_gio(t: _dt.datetime, khung_toi: List[Tuple[_dt.time, _dt.time, str]]) -> bool:
    return bool(_ly_do_khung_gio(t, khung_toi) or _ly_do_phut_doi_gio(t))


def _tim_luc_an_toan_tiep(bay_gio: _dt.datetime,
                          khung_toi: List[Tuple[_dt.time, _dt.time, str]]) -> Optional[str]:
    """Phút gần nhất SAU `bay_gio` không vướng khung giờ/phút tránh nào.

    Chỉ dùng khi lý do chưa an toàn DUY NHẤT tới từ khung giờ cố định — việc
    thật đang chạy dở (đăng dở, phiên mở, kênh sản xuất, tiến trình con,
    việc chạy tay) thì không đoán được bao giờ xong, trả `None`. `khung_toi`
    đã đọc đĩa MỘT LẦN ở `kiem_tra` — dò từng phút ở đây KHÔNG đọc lại.
    """
    t = bay_gio.replace(second=0, microsecond=0) + _dt.timedelta(minutes=1)
    for _ in range(_TOI_DA_PHUT_TIM):
        if not _chan_boi_gio(t, khung_toi):
            return t.isoformat(timespec="minutes")
        t += _dt.timedelta(minutes=1)
    return None


def _kiem_dang_dodang(thu_muc_vm: str) -> List[str]:
    """(1) `vm/logs/dang-dodang.json` — có tệp là có kênh đang tải dở."""
    duong = os.path.join(thu_muc_vm, "logs", "dang-dodang.json")
    if not os.path.isfile(duong):
        return []
    du = _doc_json(duong)
    kenh = str((du or {}).get("kenh") or "").strip() if isinstance(du, dict) else ""
    ma = str((du or {}).get("ma") or "").strip() if isinstance(du, dict) else ""
    nhan = " ".join(x for x in (kenh, ma) if x) or "một video"
    return ["Máy đăng đang tải dở {0} lên YouTube — đợi xong lượt này đã."
           .format(nhan)]


def _kiem_phien_dang_mo(thu_muc_vm: str, cac_kenh: List[str], hom_nay: str) -> List[str]:
    """(2) Phiên máy đăng — `phien_cuoi@<k>` hôm nay mà `ket_thuc` chưa ghi hôm nay."""
    cau_hinh = tt.doc_cau_hinh_vm(thu_muc_vm)
    tt_vm = tt._trang_thai_vm(thu_muc_vm, cau_hinh) if cau_hinh else {}  # noqa: SLF001 — tái dùng nguyên hàm nguồn, không dò lại định dạng
    ra: List[str] = []
    for ma in cac_kenh:
        cuoi = str(tt_vm.get("phien_cuoi@" + ma) or "")
        if cuoi != hom_nay:
            continue
        ket = tt_vm.get("phien_ket_qua@" + ma)
        ket_thuc = str(ket.get("ket_thuc") or "") if isinstance(ket, dict) else ""
        if not ket_thuc.startswith(hom_nay):
            ra.append("Kênh {0} vẫn đang trong một phiên đăng/chăm kênh, chưa xong."
                      .format(ma))
    return ra


#: Việc khe "nang" đang giữ mà KHÔNG an toàn để ngắt — cả hai đều là trình
#: duyệt thật đang mở (tải video lên YouTube / quét số liệu Studio).
_VIEC_KHE_NGUY_HIEM = {
    "tai_len": "đang tải video lên YouTube",
    "quet": "đang quét số liệu Studio",
}


def _kiem_khe_nang_dang_ban(goc: str) -> List[str]:
    """(3) `core.khe.trang_thai(goc)["nang"]` — khe độc quyền toàn máy đang
    giữ việc `"tai_len"`/`"quet"` thì chưa an toàn (xem docstring đầu tệp)."""
    try:
        giu = khe.trang_thai(goc).get("nang")
    except Exception:  # noqa: BLE001 — đọc khe hỏng thì đừng chặn vì lý do không rõ
        return []
    if not isinstance(giu, dict):
        return []
    viec = str(giu.get("viec") or "")
    ten = _VIEC_KHE_NGUY_HIEM.get(viec)
    if ten is None:
        return []
    kenh = str(giu.get("kenh") or "")
    return ["Máy {0}{1} — đợi xong lượt này rồi hẵng khởi động lại.".format(
        ten, " (kênh {0})".format(kenh) if kenh else "")]


def _kiem_tien_trinh_con(goc: str) -> List[str]:
    """(4) `workspace/tien-trinh-con.json` — còn tiến trình con `chu != "tu_chay"`
    nào sống (mục `chu == "tu_chay"` là một lượt sản xuất tách rời, không
    tính — xem docstring đầu tệp)."""
    duong = os.path.join(goc, "workspace", tien_trinh_con.TEN_SO)
    du = _doc_json(duong)
    muc = [m for m in du if isinstance(m, dict)] if isinstance(du, list) else []
    con_song_sot = 0
    for m in muc:
        if str(m.get("chu") or "") == tien_trinh_con.CHU_TU_CHAY:
            continue
        try:
            pid, tao_luc = int(m.get("pid") or 0), int(m.get("tao_luc") or 0)
        except (TypeError, ValueError):
            continue
        if pid and tien_trinh_con.con_song(pid, tao_luc):
            con_song_sot += 1
    if con_song_sot:
        return ["Còn {0} việc nền (ví dụ ghép video, viết kịch bản) chưa xong "
                "— đợi xong rồi hẵng khởi động lại.".format(con_song_sot)]
    return []


def _kiem_viec_chay_tay(viec_chay_tay: bool) -> List[str]:
    """(5) Việc khách bấm tay qua giao diện — trạng thái chỉ có trong bộ nhớ,
    nơi gọi tự truyền vào (xem docstring đầu tệp)."""
    if viec_chay_tay:
        return ["Bạn đang có một việc chạy tay chưa xong trên tool — đợi việc "
                "đó xong đã."]
    return []


def kiem_tra(goc: str, bay_gio: Optional[_dt.datetime] = None, *,
             viec_chay_tay: bool = False) -> Dict[str, Any]:
    """`{"duoc": bool, "ly_do": [câu tiếng Việt,...], "luc_an_toan_tiep": str|None}`.

    `bay_gio`: thời điểm giả cho test (mặc định `datetime.now()`), cùng nếp
    `bay_gio` của `core.trung_tam`/`core.bang_dieu_khien`.
    `viec_chay_tay`: nơi gọi tự hỏi `app.jobs.is_running` (điều kiện 5, chỉ
    có trong bộ nhớ — xem docstring đầu tệp) rồi truyền vào.
    """
    bay_gio = bay_gio or _dt.datetime.now()
    hom_nay = bay_gio.strftime("%Y-%m-%d")
    thu_muc_vm = tt.thu_muc_vm(goc)
    cac_kenh = liet_ke_kenh(goc)

    # Lý do vì VIỆC THẬT đang chạy dở — không đoán được bao giờ xong.
    ly_do_trang_thai: List[str] = []
    ly_do_trang_thai += _kiem_dang_dodang(thu_muc_vm)
    ly_do_trang_thai += _kiem_phien_dang_mo(thu_muc_vm, cac_kenh, hom_nay)
    ly_do_trang_thai += _kiem_khe_nang_dang_ban(goc)
    ly_do_trang_thai += _kiem_tien_trinh_con(goc)
    ly_do_trang_thai += _kiem_viec_chay_tay(viec_chay_tay)

    # Lý do vì KHUNG GIỜ — biết trước bao giờ hết. `khung_toi` đọc đĩa (kênh.yaml
    # + may-ao.json) ĐÚNG MỘT LẦN ở đây, dùng lại cho cả lý do lẫn dò "lúc an
    # toàn tiếp theo" bên dưới.
    khung_toi = _khung_toi_theo_kenh(goc, cac_kenh)
    ly_do_gio = _ly_do_khung_gio(bay_gio, khung_toi) + _ly_do_phut_doi_gio(bay_gio)

    ly_do = ly_do_trang_thai + ly_do_gio
    duoc = not ly_do
    if duoc:
        luc_an_toan_tiep = None
    elif ly_do_trang_thai:
        luc_an_toan_tiep = None  # việc thật đang chạy — không rõ bao giờ xong
    else:
        luc_an_toan_tiep = _tim_luc_an_toan_tiep(bay_gio, khung_toi)

    return {"duoc": duoc, "ly_do": ly_do, "luc_an_toan_tiep": luc_an_toan_tiep}
