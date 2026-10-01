"""Nguồn kế hoạch TỪ TOOL cho tool đăng (`dang.py` của `D:\\upload`).

Chủ dự án, 01/09/2026: *"nó cần upload được — cái đó luồng cũ làm rồi, chỉ là
thay đổi ở chỗ dựa vào trang tính thì giờ là lấy dữ liệu từ tool"*.

`dang.py` chạm trang tính ở đúng BA chỗ (đọc mã nó ngày 01/09/2026):

    get_rows_fast(INPUT_SHEET)            đọc toàn bộ dòng (một lần mỗi phiên)
    update_source_status(client, code, s) ghi "ĐÃ ĐĂNG" theo MÃ gói
    gs_client()                           chỉ để phục vụ chỗ ghi ở trên

Tệp này thay cả ba: đọc kế hoạch từ TRẠM của tool (`GET /ke-hoach`), dựng lại
đúng KHỔ DÒNG RỘNG mà `dang.py` đang tiêu thụ (mã ở cột 0, kênh ở AI=34,
trạng thái ở AV=47, tiêu đề BB=53… — khổ của trang tính cũ, giữ nguyên để
`dang.py` gần như không phải sửa), và báo trạng thái về `POST /dang-xong`.

Chỉ thư viện chuẩn — chạy được trên máy ảo trần như `vm/agent.py`.
Ghép vào `dang.py` bằng `vm/ghep_tool_dang.py` — xem tệp đó.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
import urllib.parse
import urllib.request

__all__ = ["get_rows", "bao_dang", "thu_muc_dang", "RONG_DONG"]

#: Vị trí cột trong khổ dòng của trang tính cũ — PHẢI khớp S3 của `dang.py`.
O_MA = 0
O_KENH = 34        # IDX_CHANNEL_AI
O_THE = 37         # IDX_TAG_AL
O_TRANG_THAI = 47  # IDX_STATUS_AV
O_TIEU_DE = 53     # IDX_TITLE_BB
O_MO_TA = 54       # IDX_DESC_BC
O_LINK = (55, 56, 57, 58)   # BD..BG
O_NGAY = 60        # IDX_DATE_BI
O_GIO = 61         # IDX_TIME_BJ
O_DSP = 62         # Danh sách phát (cột mới của kế hoạch; rỗng = hành vi cũ)

#: `get_all_ready_codes` đòi `len(row) > 61` — 62 ô là vừa đủ, thêm cho chắc.
RONG_DONG = 64

#: Tên cột trong kế hoạch của tool (`core/ke_hoach_dang.py`) → việc đổi tên
#: cột bên tool sẽ làm KeyError ngay ở đây chứ không âm thầm đăng thiếu chữ.
_C = {"ma": "Mã gói", "ngay": "Ngày đăng", "gio": "Giờ đăng",
      "tieu_de": "Tiêu đề", "mo_ta": "Mô tả", "the": "Thẻ SEO",
      "san_sang": "Sẵn sàng", "da_dang": "Trạng thái đăng",
      "dsp": "Danh sách phát"}
_C_LINK = ("Link card 1", "Link card 2", "Link card 3", "Link card 4")


def _danh_sach_kenh(cau_hinh: dict) -> list:
    """Mọi kênh máy này ĐĂNG — một VPS giờ phục vụ tới 5 kênh cùng niche.

    `CAC_KENH`/`cac_kenh` (bộ cài đóng gói cho máy nhiều kênh) thắng nếu
    có; không thì về kênh đơn `CHANNEL_CODE`/`kenh` (nếp một-máy-một-kênh
    cũ — giữ NGUYÊN cho mọi máy đang chạy, không đụng gì tới chúng).
    """
    nhieu = (cau_hinh.get("CAC_KENH") or cau_hinh.get("cac_kenh") or [])
    ds = [str(k).strip() for k in nhieu if str(k).strip()]
    if ds:
        return list(dict.fromkeys(ds))
    don = str(cau_hinh.get("CHANNEL_CODE") or cau_hinh.get("kenh") or "")
    return [don] if don else []


def _tram(cau_hinh: dict) -> str:
    """Địa chỉ trạm: config trước; trống thì lấy bản agent đã CHỐT mỗi nhịp
    tim (`cai-dat-tool.json` cạnh đây) — config đóng gói cố ý để trống `tram`
    vì nó mang nhiều ứng viên, agent mới là người biết cái nào đang sống."""
    tram = str(cau_hinh.get("TRAM") or cau_hinh.get("tram") or "").rstrip("/")
    if tram:
        return tram
    try:
        import json as _json
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "cai-dat-tool.json"), encoding="utf-8") as _f:
            return str((_json.load(_f) or {}).get("tram") or "").rstrip("/")
    except Exception:  # noqa: BLE001 — chưa có thì thôi
        return ""


def _tai_csv(cau_hinh: dict, kenh: str) -> str:
    """Kế hoạch tươi CỦA MỘT KÊNH từ trạm; trạm tắt thì dùng bản đã tải lần
    trước (mỗi kênh một tệp đệm riêng — máy nhiều kênh không giẫm nhau)."""
    tram = _tram(cau_hinh)
    duong_cache = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "ke-hoach-{0}.csv".format(kenh or "kenh"))
    if tram and kenh:
        try:
            url = tram + "/ke-hoach?" + urllib.parse.urlencode({"kenh": kenh})
            with urllib.request.urlopen(url, timeout=20) as tra_loi:
                chu = tra_loi.read().decode("utf-8-sig", "replace")
            if chu.strip():
                with open(duong_cache, "w", encoding="utf-8-sig",
                          newline="") as tep:
                    tep.write(chu)
            return chu
        except Exception:  # noqa: BLE001 — trạm tắt thì đọc bản cũ bên dưới
            pass
    try:
        with open(duong_cache, "r", encoding="utf-8-sig") as tep:
            return tep.read()
    except OSError:
        return ""


def thu_muc_dang(cau_hinh: dict, kenh: str) -> str:
    """Thư mục CHỨA gói video đã bàn giao của MỘT kênh (26/09/2026 — trạm
    có thêm `GET /thu-muc-dang?kenh=X`, xem docstring của route đó trong
    `core/chi_so_ytb/tram.py`: nguồn sự thật DUY NHẤT là `kenh.yaml` qua
    `core.kenh.doc_kenh`, CÙNG hàm mà `core/ban_giao_dang.py` dùng để bàn
    giao — nên không thể lệch nhau).

    `GET /ke-hoach` (đọc kế hoạch) KHÔNG mang đường này — chỉ mã/ngày/giờ/
    tiêu đề — nên phải hỏi RIÊNG. Trạm tắt, hoặc bản trạm CŨ chưa có route
    này (404/lỗi bất kỳ), thì đọc bản đã tải lần trước (tệp đệm riêng từng
    kênh, giống nếp `_tai_csv`); chưa từng tải được lần nào -> trả rỗng —
    nơi gọi (`may_dang.py`) tự lùi về đường mặc định của nó, máy MỘT kênh
    nếp cũ không đổi hành vi một chút nào."""
    tram = _tram(cau_hinh)
    duong_cache = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "thu-muc-dang-{0}.json".format(kenh or "kenh"))
    if tram and kenh:
        try:
            url = tram + "/thu-muc-dang?" + urllib.parse.urlencode({"kenh": kenh})
            with urllib.request.urlopen(url, timeout=10) as tra_loi:
                du = json.loads(tra_loi.read().decode("utf-8-sig", "replace") or "{}")
            duong = str((du or {}).get("thu_muc_done") or "")
            with open(duong_cache, "w", encoding="utf-8") as tep:
                json.dump({"thu_muc_done": duong}, tep, ensure_ascii=False)
            return duong
        except Exception:  # noqa: BLE001 — tram tat/ban cu thi doc cache duoi day
            pass
    try:
        with open(duong_cache, "r", encoding="utf-8") as tep:
            return str((json.load(tep) or {}).get("thu_muc_done") or "")
    except (OSError, ValueError):
        return ""


def hang_tu_csv(chu: str, kenh: str, trang_thai_ok: str = "EDIT XONG") -> list:
    """Dựng dòng khổ CŨ từ NGUYÊN VĂN CSV kế hoạch (không gọi trạm) — máy
    đăng DOM dùng khi đọc thẳng kế hoạch trên đĩa (trạm tắt/đời cũ, 29/09/2026)."""
    return _dung_hang(chu, kenh, trang_thai_ok)


def _hang_mot_kenh(cau_hinh: dict, kenh: str, trang_thai_ok: str) -> list:
    """Các dòng (khổ CŨ) của MỘT kênh — đóng đúng mã kênh của nó ở cột AI,
    không ép chung một mã như máy một-kênh trước đây."""
    return _dung_hang(_tai_csv(cau_hinh, kenh), kenh, trang_thai_ok)


def _dung_hang(chu: str, kenh: str, trang_thai_ok: str) -> list:
    if not chu.strip():
        return []
    dong_csv = list(csv.reader(io.StringIO(chu)))
    if not dong_csv:
        return []
    cot = [str(o) for o in dong_csv[0]]
    o = {ten: (cot.index(ten) if ten in cot else None)
         for ten in list(_C.values()) + list(_C_LINK)}

    def lay(d, ten):
        i = o.get(ten)
        return str(d[i]).strip() if i is not None and i < len(d) else ""

    ra = []
    for d in dong_csv[1:]:
        if not d or not lay(d, _C["ma"]):
            continue
        r = [""] * RONG_DONG
        r[O_MA] = lay(d, _C["ma"])
        r[O_KENH] = kenh
        r[O_THE] = lay(d, _C["the"])
        da_dang = lay(d, _C["da_dang"])
        r[O_TRANG_THAI] = (da_dang if da_dang
                           else (trang_thai_ok if lay(d, _C["san_sang"]) else ""))
        r[O_TIEU_DE] = lay(d, _C["tieu_de"])
        r[O_MO_TA] = lay(d, _C["mo_ta"])
        for vi_tri, ten in zip(O_LINK, _C_LINK):
            r[vi_tri] = lay(d, ten)
        r[O_NGAY] = lay(d, _C["ngay"])
        r[O_GIO] = lay(d, _C["gio"])
        r[O_DSP] = lay(d, _C["dsp"])
        ra.append(r)
    return ra


def get_rows(cau_hinh: dict, trang_thai_ok: str = "EDIT XONG") -> list:
    """Toàn bộ dòng theo KHỔ CŨ — thế chân `get_rows_fast(INPUT_SHEET)`.

    Máy phục vụ NHIỀU kênh (tối đa 5, một VPS — xem `vm/KE-HOACH.md`): gộp
    kế hoạch của TỪNG kênh (mỗi kênh một lượt `GET /ke-hoach?kenh=X` riêng),
    mỗi dòng mang đúng MÃ KÊNH CỦA NÓ. `dang.py` (qua `get_all_ready_codes`)
    tự lọc theo kênh nó đang đăng — không cần biết gì đổi ở đây; máy MỘT
    kênh thì y hệt trước (một lượt gọi, một mã kênh).

    Ô trạng thái (AV) được dựng từ hai cột của kế hoạch: `Trạng thái đăng`
    thắng (máy đã đăng rồi thì kể "ĐÃ ĐĂNG" để vòng dọn dẹp xoá thư mục);
    chưa đăng mà `Sẵn sàng` có chữ thì kể `trang_thai_ok` — đúng chữ mà
    `dang.py` đang so (`STATUS_OK` trong config của nó).
    """
    ra = [[""] * RONG_DONG]           # dòng tiêu đề giả — dang.py bỏ qua dòng 0
    for kenh in _danh_sach_kenh(cau_hinh):
        ra.extend(_hang_mot_kenh(cau_hinh, kenh, trang_thai_ok))
    return ra


def _them_hop_le(them: dict) -> dict:
    """Chỉ giữ trường phụ gửi được qua JSON (chuỗi/số), bỏ None/rỗng."""
    ra = {}
    for k, v in (them or {}).items():
        if k in ("kenh", "ma", "trang_thai") or v is None or v == "":
            continue
        ra[str(k)] = v if isinstance(v, (int, float)) else str(v)
    return ra


def bao_dang(cau_hinh: dict, ma: str, trang_thai: str = "ĐÃ ĐĂNG",
            kenh: str = None, **them) -> bool:
    """Báo về trạm một gói đã đăng — thế chân `update_source_status`.

    `kenh`: kênh THẬT của gói (máy nhiều kênh — rút từ cột AI của dòng kế
    hoạch, `may_dang.py` truyền vào); bỏ trống thì lấy kênh mặc định của
    máy (nếp một-kênh cũ, `CHANNEL_CODE`/`kenh` của config).

    `**them` (29/09/2026, máy đăng DOM — thiết kế mục 4.4): trường phụ như
    `video_id`, `lich` đi kèm trong JSON gửi `/dang-xong` VÀ trong sổ chờ
    (gửi bù vẫn mang đủ). Trạm đời cũ chỉ đọc kenh/ma/trang_thai nên trường
    thêm rơi qua vô hại; `may_dang.py` gọi không có `them` → y hệt trước.

    Trạm tắt đúng lúc báo thì ghi vào sổ chờ cạnh tệp này; lần gọi sau (hay
    lần chạy sau) gửi bù — không được để mất một dòng "ĐÃ ĐĂNG": mất nó là
    lần chạy sau đăng LẶP đúng video ấy lên kênh thật.
    """
    tram = _tram(cau_hinh)
    kenh = (str(kenh).strip() if kenh else
           str(cau_hinh.get("CHANNEL_CODE") or cau_hinh.get("kenh") or ""))
    duong_cho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "cho-bao-{0}.json".format(kenh or "kenh"))
    cho = []
    try:
        with open(duong_cho, "r", encoding="utf-8") as tep:
            cho = json.load(tep)
    except (OSError, ValueError):
        cho = []
    muc_moi = {"ma": str(ma), "trang_thai": str(trang_thai),
               "luc": time.strftime("%Y-%m-%d %H:%M:%S")}
    phu = _them_hop_le(them)
    if phu:
        muc_moi["them"] = phu
    cho.append(muc_moi)
    con_lai = []
    duoc_het = True
    for muc in cho:
        try:
            goi = {"kenh": kenh, "ma": muc["ma"], "trang_thai": muc["trang_thai"]}
            goi.update(_them_hop_le(muc.get("them")))
            du_lieu = json.dumps(goi, ensure_ascii=False).encode("utf-8")
            yeu_cau = urllib.request.Request(
                tram + "/dang-xong", data=du_lieu,
                headers={"Content-Type": "application/json"})
            urllib.request.urlopen(yeu_cau, timeout=20).read()
        except Exception:  # noqa: BLE001 — giữ lại, lần sau gửi bù
            con_lai.append(muc)
            duoc_het = False
    try:
        if con_lai:
            with open(duong_cho, "w", encoding="utf-8") as tep:
                json.dump(con_lai, tep, ensure_ascii=False, indent=1)
        elif os.path.exists(duong_cho):
            os.remove(duong_cho)
    except OSError:
        pass
    return duoc_het
