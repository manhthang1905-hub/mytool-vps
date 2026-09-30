"""Bài kiểm luật dọn THỨ HAI của `core/don_dep.py` — "quá N lượt, chưa đăng".

═══ VÌ SAO CÓ BỘ BÀI NÀY (24/09/2026) ═══

Luật MỘT (`ung_vien_don`) chỉ xoá lượt có "Trạng thái đăng" ∈
`don_dep.TRANG_THAI_DA_DANG`. Đo thật trên VPS hôm nay: máy tự chạy hai ngày,
chủ dự án chưa duyệt/đăng lượt nào → `PROJECTS/` lên **10,4 GB / 12 lượt** mà
cửa dọn không mở được lần nào. Luật HAI (`ung_vien_qua_so_luot`) là cửa thứ
hai, gác bằng khoá `giu_toi_da_luot` trong `kenh.yaml`.

Mỗi bài dưới đây khoá đúng một lời hứa của luật ấy:

* lượt trong N mới nhất KHÔNG bị đụng;
* lượt cũ hơn mất phần NẶNG nhưng giữ đủ tệp nhỏ (danh sách y hệt luật một);
* lượt CHƯA XONG (`trang-thai.json` chưa `xong_het`) không bị đụng;
* khoá `CHANNEL/<kênh>/tu-chay/.khoa` còn tươi → bỏ qua CẢ KÊNH;
* `giu_toi_da_luot: 0` → `don()` y hệt hành vi cũ (chỉ luật một);
* gói đã bàn giao trong `thu_muc_done` KHÔNG bị đụng (nó đang CHỜ đăng);
* sổ `don-dep.log` + `da-don.json` nói rõ lý do "quá N lượt, chưa đăng".

Toàn bộ dùng `tmp_path` của pytest, KHÔNG đụng `PROJECTS/` thật. Không gọi mạng.
"""

from __future__ import annotations

import datetime
import json
import os

from core import don_dep, ke_hoach_dang
from core.auto import MA_KHAU, TEP_TRANG_THAI, XONG, duong_luot

KENH = "K1"

#: Mốc "bây giờ" cố định của mọi bài — không phụ thuộc đồng hồ máy chạy test.
BAY_GIO = datetime.datetime(2026, 9, 24, 10, 0)

#: Danh sách tệp NHỎ mà CẢ HAI luật đều phải giữ — đúng danh sách ở docstring
#: đầu `core/don_dep.py`. Sai một tệp ở đây là làm hỏng một tính năng khác
#: (vòng học đọc `4-canh.json`, `core/da_lam.py` đọc `0-doi-thu.txt`…).
TEP_NHO_PHAI_GIU = (
    "0-doi-thu.txt", "1-kich-ban.txt", "1-tieu-de.txt", "1-seo.txt",
    "3-phu-de.srt", "4-canh.json", "trang-thai.json", "_van-tay-anh.json",
)

#: Thứ NẶNG luật hai phải xoá — `_MUC_NANG` cộng `2-doan/`.
MUC_NANG_PHAI_XOA = ("5-anh", "6-clip", "8-video.mp4", "9-video-capcut.mp4",
                     "2-giong-doc.mp3", "2-doan")


# ── Dựng hiện trường ─────────────────────────────────────────────────────────


def _ghi(duong: str, chu: str = "x") -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def _ghi_nhi_phan(duong: str, so_byte: int) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "wb") as tep:
        tep.write(b"\x00" * so_byte)


def _trang_thai(xong: bool) -> str:
    """Nội dung `trang-thai.json` — `xong=True` cho `LuotChay.xong_het` là True.

    Phải điền ĐỦ `core.auto.MA_KHAU`: `xong_het` là `all(...)` trên cả dãy, nên
    thiếu một khâu là cả lượt thành "chưa xong" (và bài kiểm im lặng sai).
    """
    tt = XONG if xong else "cho"
    return json.dumps({
        "ma_kenh": KENH, "ma_luot": "0000", "dau_vao": {}, "tao_luc": 0.0,
        "khau": {m: {"ma": m, "trang_thai": tt, "so_lan": 1, "loi": "",
                     "bat_dau": 0.0, "ket_thuc": 0.0, "ghi_chu": {}}
                 for m in MA_KHAU},
    }, ensure_ascii=False)


def _dung_luot(goc: str, luot: str, *, xong: bool = True,
               co_bia_chon: bool = True) -> str:
    """Một thư mục lượt đủ bộ: tệp nhỏ phải giữ + tệp nặng phải xoá."""
    d = duong_luot(goc, KENH, luot)
    os.makedirs(d, exist_ok=True)
    for ten in TEP_NHO_PHAI_GIU:
        if ten == "trang-thai.json":
            continue
        _ghi(os.path.join(d, ten))
    _ghi(os.path.join(d, TEP_TRANG_THAI), _trang_thai(xong))

    _ghi_nhi_phan(os.path.join(d, "5-anh", "canh-001.png"), 1000)
    _ghi_nhi_phan(os.path.join(d, "6-clip", "canh-001.mp4"), 2000)
    _ghi_nhi_phan(os.path.join(d, "2-doan", "doan-001.mp3"), 1500)
    _ghi_nhi_phan(os.path.join(d, "8-video.mp4"), 5000)
    _ghi_nhi_phan(os.path.join(d, "9-video-capcut.mp4"), 4000)
    _ghi_nhi_phan(os.path.join(d, "2-giong-doc.mp3"), 3000)

    thumb = os.path.join(d, "7-thumbnail")
    _ghi_nhi_phan(os.path.join(thumb, "thumb_001.png"), 500)
    _ghi_nhi_phan(os.path.join(thumb, "thumb_002.png"), 500)
    if co_bia_chon:
        _ghi_nhi_phan(os.path.join(thumb, "CHON-thumb_001.png"), 500)
    return d


def _ghi_kenh_yaml(goc: str, **khoa) -> None:
    dong = ["ma: {0}".format(KENH)]
    for k, v in khoa.items():
        dong.append("{0}: {1}".format(k, v))
    _ghi(os.path.join(goc, "CHANNEL", KENH, "kenh.yaml"), "\n".join(dong) + "\n")


def _bang_rong(goc: str) -> None:
    """Kế hoạch đăng RỖNG — không lượt nào "đã đăng", nên luật MỘT không nhận
    ứng viên nào. Mọi thứ xoá được trong các bài dưới đây đều do luật HAI."""
    ke_hoach_dang.luu_bang(goc, KENH, [], list(ke_hoach_dang.COT))


def _khoa_tu_chay(goc: str, *, tuoi_giay: float) -> str:
    """Tệp khoá `CHANNEL/<kênh>/tu-chay/.khoa` với `bat_dau` cách `BAY_GIO`
    đúng `tuoi_giay` giây — cùng khuôn `core.tu_chay._tao_tep_khoa` ghi."""
    duong = os.path.join(goc, "CHANNEL", KENH, "tu-chay", ".khoa")
    _ghi(duong, json.dumps({"pid": 4242,
                            "bat_dau": BAY_GIO.timestamp() - tuoi_giay}))
    return duong


def _con(duong: str) -> bool:
    return os.path.exists(duong)


# ── N lượt mới nhất không bị đụng ────────────────────────────────────────────


def test_giu_dung_n_luot_moi_nhat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=3)
    _bang_rong(goc)
    thu_muc = {l: _dung_luot(goc, l) for l in ("0001", "0002", "0003", "0004", "0005")}

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO,
                giu_toi_da_luot=3)

    # Ba lượt MỚI NHẤT còn nguyên cả phần nặng.
    for l in ("0003", "0004", "0005"):
        for ten in MUC_NANG_PHAI_XOA:
            assert _con(os.path.join(thu_muc[l], ten)), \
                "lượt mới {0} bị đụng: {1}".format(l, ten)
    # Hai lượt CŨ mất hết phần nặng.
    for l in ("0001", "0002"):
        for ten in MUC_NANG_PHAI_XOA:
            assert not _con(os.path.join(thu_muc[l], ten)), \
                "lượt cũ {0} chưa xoá: {1}".format(l, ten)


def test_it_luot_hon_tran_thi_khong_xoa_gi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=3)
    _bang_rong(goc)
    for l in ("0001", "0002", "0003"):
        _dung_luot(goc, l)

    assert don_dep.ung_vien_qua_so_luot(goc, KENH, giu=3, bay_gio=BAY_GIO) == []


# ── Tệp nhỏ vẫn còn ──────────────────────────────────────────────────────────


def test_luot_cu_van_giu_tep_nho_va_bia_da_chon(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO, giu_toi_da_luot=1)

    for ten in TEP_NHO_PHAI_GIU:
        assert os.path.isfile(os.path.join(cu, ten)), "bị xoá nhầm: " + ten
    assert os.path.isfile(os.path.join(cu, "7-thumbnail", "CHON-thumb_001.png"))
    # Bìa CHƯA chọn thì đi cùng phần nặng.
    assert not _con(os.path.join(cu, "7-thumbnail", "thumb_002.png"))


# ── Lượt chưa xong / đang chạy ───────────────────────────────────────────────


def test_luot_chua_xong_khong_bi_dung(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    do = _dung_luot(goc, "0001", xong=False)
    _dung_luot(goc, "0002")

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO, giu_toi_da_luot=1)

    for ten in MUC_NANG_PHAI_XOA:
        assert _con(os.path.join(do, ten)), "lượt chưa xong bị đụng: " + ten


def test_thieu_trang_thai_json_thi_khong_bi_dung(tmp_path):
    """Không có `trang-thai.json` = không biết lượt xong chưa → không đụng."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    do = _dung_luot(goc, "0001")
    os.remove(os.path.join(do, TEP_TRANG_THAI))
    _dung_luot(goc, "0002")

    assert don_dep.ung_vien_qua_so_luot(goc, KENH, giu=1, bay_gio=BAY_GIO) == []


def test_khoa_con_tuoi_thi_bo_qua_ca_kenh(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")
    _khoa_tu_chay(goc, tuoi_giay=60)      # một lượt vừa bắt đầu một phút trước

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO, giu_toi_da_luot=1)

    for ten in MUC_NANG_PHAI_XOA:
        assert _con(os.path.join(cu, ten)), "khoá còn tươi mà vẫn xoá: " + ten


def test_khoa_qua_cu_thi_khong_chan_nua(tmp_path):
    """Khoá cũ hơn `KHOA_CON_TUOI_GIAY` là khoá của một lượt đã chết — để nó
    chặn mãi thì đĩa phình mãi, đúng thứ luật này sinh ra để chặn."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")
    _khoa_tu_chay(goc, tuoi_giay=don_dep.KHOA_CON_TUOI_GIAY + 60)

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO, giu_toi_da_luot=1)

    for ten in MUC_NANG_PHAI_XOA:
        assert not _con(os.path.join(cu, ten)), "khoá đã chết mà vẫn chừa: " + ten


# ── Tắt bằng 0 ───────────────────────────────────────────────────────────────


def test_giu_0_la_tat_han_luat_nay(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=0)
    _bang_rong(goc)
    thu_muc = {l: _dung_luot(goc, l) for l in ("0001", "0002", "0003")}

    ket = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO,
                      giu_toi_da_luot=0)

    assert ket["ung_vien"] == [], "giu=0 mà vẫn nhận ứng viên"
    assert ket["tong_bytes"] == 0
    for l, d in thu_muc.items():
        for ten in MUC_NANG_PHAI_XOA:
            assert _con(os.path.join(d, ten)), \
                "giu=0 mà vẫn xoá {0}/{1}".format(l, ten)


def test_khong_khai_khoa_thi_mac_dinh_la_tat(tmp_path):
    """`kenh.yaml` không có `giu_toi_da_luot` → mặc định 0 → không đụng gì.
    Đây là lời hứa "thêm, KHÔNG thay": kênh chưa khai khoá mới phải chạy y cũ."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true")
    _bang_rong(goc)
    thu_muc = {l: _dung_luot(goc, l) for l in ("0001", "0002", "0003")}

    ket = don_dep.don_theo_cai_dat(goc, KENH)

    assert ket["chay"] is True
    assert ket["ung_vien"] == []
    for d in thu_muc.values():
        assert _con(os.path.join(d, "5-anh"))


def test_tu_don_tat_thi_tran_luot_khong_co_tac_dung(tmp_path):
    """Trần số lượt nằm SAU cờ `tu_don` — kênh chủ dự án đã CHỌN không dọn thì
    một con số ở khoá khác không được lật lại quyết định ấy."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="false", giu_toi_da_luot=1)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")

    ket = don_dep.don_theo_cai_dat(goc, KENH)

    assert ket["chay"] is False
    assert _con(os.path.join(cu, "5-anh"))


def test_don_theo_cai_dat_doc_khoa_tu_kenh_yaml(tmp_path):
    """Đường THẬT mà `core/tu_chay.py` đi: `don_theo_cai_dat` phải tự lấy
    `giu_toi_da_luot` từ `kenh.yaml`, không cần ai truyền vào."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=2)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")
    _dung_luot(goc, "0003")

    ket = don_dep.don_theo_cai_dat(goc, KENH)

    assert ket["chay"] is True
    assert [u["luot"] for u in ket["ung_vien"]] == ["0001"]
    for ten in MUC_NANG_PHAI_XOA:
        assert not _con(os.path.join(cu, ten)), "chưa xoá: " + ten


# ── Gói đã bàn giao trong `thu_muc_done` ─────────────────────────────────────


def test_khong_dung_goi_da_ban_giao(tmp_path):
    """Lượt CHƯA đăng thì gói trong `done/` chính là thứ đang CHỜ chủ dự án
    đăng — xoá nó là làm mất việc, không phải dọn rác. (Khác luật MỘT: ở đó
    lượt đã lên sóng rồi nên gói mới hết việc.)"""
    goc = str(tmp_path)
    done = os.path.join(goc, "done", KENH)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1, thu_muc_done=done)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")
    goi = os.path.join(done, "{0}-0001".format(KENH))
    _ghi_nhi_phan(os.path.join(goi, "video.mp4"), 5000)

    don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO, giu_toi_da_luot=1)

    assert os.path.isfile(os.path.join(goi, "video.mp4")), \
        "gói chờ đăng bị xoá oan"
    assert not _con(os.path.join(cu, "5-anh")), "phần nặng của lượt vẫn phải đi"


# ── Sổ sách nói rõ lý do ─────────────────────────────────────────────────────


def test_so_ghi_ro_ly_do_qua_n_luot(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")

    ket = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO,
                      giu_toi_da_luot=1)

    ly_do = don_dep.LY_DO_QUA_SO_LUOT.format(1)
    assert ly_do == "xoá vì quá 1 lượt, chưa đăng"

    # Byte giải phóng có thật và được báo lên nơi gọi (sổ ngày của `tu_chay`).
    assert ket["tong_bytes"] > 0
    assert ket["da_don"] and ket["da_don"][0]["ly_do"] == ly_do

    # `da-don.json` trong chính thư mục lượt.
    with open(os.path.join(cu, don_dep.TEN_MARKER), encoding="utf-8") as tep:
        marker = json.load(tep)
    assert marker["ly_do"] == ly_do
    assert marker["bytes"] > 0

    # Nhật ký gộp của kênh.
    duong_log = os.path.join(goc, "CHANNEL", KENH, "tu-chay", don_dep.TEN_LOG)
    with open(duong_log, encoding="utf-8") as tep:
        dong = tep.read().strip().splitlines()
    assert len(dong) == 1
    assert ly_do in dong[0]
    assert str(ket["tong_bytes"]) in dong[0]


def test_luat_mot_van_ghi_ly_do_cua_no(tmp_path):
    """Thêm cột lý do không được làm sổ của luật MỘT nói sai."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true")
    cu = _dung_luot(goc, "0001")
    cot = list(ke_hoach_dang.COT)
    dong = {ten: "" for ten in cot}
    dong.update({"Mã gói": "{0}-0001".format(KENH), "Ngày đăng": "01/09/2026",
                 "Giờ đăng": "10:00", "Trạng thái đăng": "ĐÃ ĐĂNG",
                 "Sẵn sàng": "x"})
    ke_hoach_dang.luu_bang(goc, KENH, [[dong[t] for t in cot]], cot)
    # `8-video.mp4` phải CŨ hơn mốc đăng, không thì `don` coi là "vừa dựng lại".
    moc = datetime.datetime(2026, 9, 1, 9, 30).timestamp()
    os.utime(os.path.join(cu, "8-video.mp4"), (moc, moc))

    ket = don_dep.don(goc, KENH, thuc_hien=True, bay_gio=BAY_GIO,
                      giu_toi_da_luot=0)

    assert ket["da_don"] and ket["da_don"][0]["ly_do"] == don_dep.LY_DO_DA_DANG
    with open(os.path.join(cu, don_dep.TEN_MARKER), encoding="utf-8") as tep:
        assert json.load(tep)["ly_do"] == don_dep.LY_DO_DA_DANG


# ── Hai luật cùng nhận một lượt thì chỉ tính MỘT lần ─────────────────────────


def test_hai_luat_trung_luot_khong_cong_doi_byte(tmp_path):
    """Một lượt vừa ĐÃ ĐĂNG quá hạn vừa ra ngoài trần số lượt: để nó vào danh
    sách hai lần là sổ ngày báo byte gấp đôi số thật."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")
    cot = list(ke_hoach_dang.COT)
    dong = {ten: "" for ten in cot}
    dong.update({"Mã gói": "{0}-0001".format(KENH), "Ngày đăng": "01/09/2026",
                 "Giờ đăng": "10:00", "Trạng thái đăng": "ĐÃ ĐĂNG",
                 "Sẵn sàng": "x"})
    ke_hoach_dang.luu_bang(goc, KENH, [[dong[t] for t in cot]], cot)
    moc = datetime.datetime(2026, 9, 1, 9, 30).timestamp()
    os.utime(os.path.join(cu, "8-video.mp4"), (moc, moc))

    ket = don_dep.don(goc, KENH, bay_gio=BAY_GIO, giu_toi_da_luot=1)

    assert [u["luot"] for u in ket["ung_vien"]] == ["0001"]
    # Bản của luật MỘT thắng (nó đứng trước) — lý do đúng hơn cho lượt đã đăng.
    assert ket["ung_vien"][0]["ly_do"] == don_dep.LY_DO_DA_DANG


# ── Ứng viên đủ khuôn để `don_khan` xếp chung ────────────────────────────────


def test_ung_vien_du_khoa_cho_don_khan(tmp_path):
    """`don_khan` gom ứng viên của MỌI kênh rồi `sort` theo `moc_dang` — thiếu
    khoá ấy là nó ném `TypeError` giữa một lượt đang XOÁ DỞ."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")

    ung = don_dep.ung_vien_qua_so_luot(goc, KENH, giu=1, bay_gio=BAY_GIO)

    assert len(ung) == 1
    u = ung[0]
    for khoa in ("kenh", "luot", "ma_goi", "thu_muc_luot", "duong", "bytes",
                 "moc_dang", "ly_do"):
        assert khoa in u, "thiếu khoá " + khoa
    assert isinstance(u["moc_dang"], str)
    assert u["chua_dang"] is True


def test_don_khan_dung_ca_luat_hai(tmp_path):
    """Đĩa chạm ngưỡng: cửa dọn khẩn cũng phải thấy lượt chưa đăng quá trần."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    cu = _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")

    ket = don_dep.don_khan(goc, [KENH], nguong_gb=5.0, bay_gio=BAY_GIO,
                           con_trong_gb_fn=lambda _g: 1.0)

    assert ket["da_chay"] is True
    assert ket["da_giai_phong_bytes"] > 0
    assert ket["theo_kenh"].get(KENH, 0) > 0
    assert not _con(os.path.join(cu, "5-anh"))


# ── Không đi ra ngoài `PROJECTS/AUTO/<kênh>/` ────────────────────────────────


def test_bo_qua_ten_khong_phai_so(tmp_path):
    """Tệp/thư mục lẻ nằm cùng cấp (`anh-tham-chieu.json` trên máy thật) không
    được coi là một lượt, và không được đẩy lượt thật ra khỏi N mới nhất."""
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=2)
    _bang_rong(goc)
    _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")
    _ghi(os.path.join(goc, "PROJECTS", "AUTO", KENH, "anh-tham-chieu.json"), "{}")
    os.makedirs(os.path.join(goc, "PROJECTS", "AUTO", KENH, "nhap"), exist_ok=True)

    assert don_dep.ung_vien_qua_so_luot(goc, KENH, giu=2, bay_gio=BAY_GIO) == []


def test_khong_co_thu_muc_auto_thi_im_lang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    assert don_dep.ung_vien_qua_so_luot(goc, KENH, giu=1, bay_gio=BAY_GIO) == []


def test_lay_tran_tu_kenh_yaml_khi_khong_truyen(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh_yaml(goc, tu_don="true", giu_toi_da_luot=1)
    _bang_rong(goc)
    _dung_luot(goc, "0001")
    _dung_luot(goc, "0002")

    ung = don_dep.ung_vien_qua_so_luot(goc, KENH, bay_gio=BAY_GIO)

    assert [u["luot"] for u in ung] == ["0001"]
