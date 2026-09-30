"""Bài kiểm van ĐĨA TRỐNG của `core/tu_chay.py` + dọn khẩn của `core/don_dep.py`.

Ba việc phải chứng minh (xem yêu cầu chống đầy đĩa, 21/09/2026):

    (a) đĩa dưới ngưỡng an toàn thì KHÔNG mở/chạy tiếp video mới;
    (b) `OSError` mang mã ĐĨA ĐẦY (`errno.ENOSPC` / Windows `WinError 112`)
        được nhận diện RIÊNG, không rơi vào nhánh lỗi sản xuất chung;
    (c) dọn khẩn (`don_dep.don_khan`) chỉ đụng video ĐÃ ĐĂNG của kênh đã bật
        `tu_don`, không đụng video chưa đăng, không đụng kênh chưa bật cờ.

Toàn bộ dùng `tmp_path` của pytest — không đụng `PROJECTS/`/`CHANNEL/` thật của
kho này, không mạng, không đĩa thật (mọi con số dung lượng đều qua seam giả
`con_trong_gb_fn` hoặc monkeypatch `_dung_luong_trong_gb`).
"""

from __future__ import annotations

import datetime
import errno
import os

import core.tu_chay as tu_chay_mod
from core import don_dep, ke_hoach_dang
from core.auto import duong_luot

NO_LOG = lambda *_a, **_k: None  # noqa: E731


def _dem_goi(fn):
    def boc(*a, **k):
        boc.so_lan += 1
        return fn(*a, **k)
    boc.so_lan = 0
    return boc


def _ghi_kenh(goc, ma, **cai):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    mac_dinh = {"ma": ma, "ngon_ngu": "ja", "engine": "veo3", "phut_muc_tieu": 10}
    mac_dinh.update(cai)
    dong = []
    for k, v in mac_dinh.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, (int, float)):
            dong.append("{0}: {1}".format(k, v))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    return thu_muc


def _lam_kenh_san_sang(goc, ma):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(thu_muc, "nv"), exist_ok=True)
    with open(os.path.join(thu_muc, "nv", "nv1.png"), "wb") as tep:
        tep.write(b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(thu_muc, "style.yaml"), "w", encoding="utf-8") as tep:
        tep.write('image_style: "phong cách thử"\n')
    os.makedirs(os.path.join(thu_muc, "prompt"), exist_ok=True)
    for ten in ("2-viet.md", "7-canh.md"):
        with open(os.path.join(thu_muc, "prompt", ten), "w", encoding="utf-8") as tep:
            tep.write("nội dung mẫu\n")


def _danh_sach_gia(moi):
    def fn(goc, kenh):
        return {"moi": list(moi)}
    return fn


def _don_khan_gia_rong():
    """`don_khan` giả — "đã thử dọn khẩn nhưng không giải phóng được gì" —
    dùng cho bài kiểm không quan tâm dọn khẩn có chạy hay không, chỉ cần nó
    không ném lỗi và không lỡ tay coi là đủ chỗ."""
    return {"da_chay": True, "con_truoc_gb": None, "con_sau_gb": None,
           "da_giai_phong_bytes": 0, "theo_kenh": {}, "da_don": [],
           "bo_qua_khong_tu_don": []}


# ── (a) Đĩa dưới ngưỡng an toàn thì KHÔNG mở/chạy tiếp video mới ────────────


def test_dia_thap_thi_khong_mo_video_moi(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/PPPPPPPPPPP", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    # Đĩa "còn" đúng 0,5 GB — dưới hẳn ngưỡng an toàn (>=1 GB biên dự phòng +
    # phần theo phút, xem `GB_MOI_PHUT_VIDEO`/`BIEN_DU_PHONG_DIA_GB`).
    monkeypatch.setattr(tu_chay_mod, "_dung_luong_trong_gb", lambda goc_: 0.5)
    # Dọn khẩn được gọi (van đĩa PHẢI thử dọn trước khi bỏ cuộc) nhưng không
    # giải phóng được gì — không có video đã đăng nào để dọn ở đây.
    goi_don_khan = []
    monkeypatch.setattr(don_dep, "don_khan", lambda *a, **k: (
        goi_don_khan.append((a, k)) or _don_khan_gia_rong()))

    ket = tu_chay_mod.chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert ket["ok"] is True, "đĩa thiếu không phải lỗi ngoài dự kiến, giống hệt hết ngân sách"
    assert goi_chay_auto.so_lan == 0, "đĩa dưới ngưỡng an toàn thì không được sản xuất"
    assert goi_don_khan, "phải thử dọn khẩn trước khi bỏ cuộc"
    assert ket["run"]["dia"]["du"] is False
    assert ket["run"]["dia"]["con_trong_gb"] == 0.5
    assert "GB" in ket["tom_tat"]


def test_dia_du_thi_khong_dung_toi_don_khan(tmp_path, monkeypatch):
    """Đĩa còn dư dả thì van đĩa cho qua NGAY, không cần gọi dọn khẩn — dọn
    khẩn chỉ nên động tới khi thật sự cần."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/RRRRRRRRRRR", "tieu_de": "x", "kenh": "Z"}]

    monkeypatch.setattr(tu_chay_mod, "_dung_luong_trong_gb", lambda goc_: 999.0)
    goi_don_khan = []
    monkeypatch.setattr(don_dep, "don_khan", lambda *a, **k: goi_don_khan.append(1))

    ket = tu_chay_mod.chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=lambda luot, viec, **k: luot,
    )
    assert ket["run"]["dia"]["du"] is True
    assert not goi_don_khan, "đĩa còn dư dả thì không được gọi dọn khẩn"


def test_don_khan_that_qua_van_dia_ghi_so_ngay_khong_vo(tmp_path, monkeypatch):
    """Bài kiểm HỒI QUY: chạy dọn khẩn THẬT (không đồ giả cho `don_dep.don_khan`
    như hai bài trên) xuyên suốt `chay_mot_ngay` — phải xoá được video đã đăng
    cũ trên đĩa thật (`tmp_path`), VÀ kết quả đó phải ghi nguyên vẹn được vào
    sổ ngày JSON (`ghi_json` không truyền `default=`, một `datetime` sống lọt
    vào cấu trúc kết quả là vỡ `json.dump` ngay giữa một lượt vừa xoá dở —
    lỗi này bài kiểm dùng đồ giả cho `don_khan` ở các bài trên KHÔNG bắt được,
    vì đồ giả không bao giờ trả về `ung_vien_don` thật)."""
    goc = str(tmp_path)
    ma_kenh = "K1"
    _ghi_kenh(goc, ma_kenh, ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1",
             tu_don="true", don_sau_gio=1)
    _lam_kenh_san_sang(goc, ma_kenh)

    # Một lượt ĐÃ ĐĂNG từ trước, quá hạn ân xá từ lâu — ứng viên hợp lệ để
    # dọn khẩn THẬT xoá.
    d_cu, video_cu = _dung_luot_nang(goc, ma_kenh, "0001")
    moc_cu = datetime.datetime(2026, 9, 1, 9, 0).timestamp()
    os.utime(video_cu, (moc_cu, moc_cu))
    _ghi_ke_hoach(goc, ma_kenh, [
        {"Mã gói": "{0}-0001".format(ma_kenh), "Ngày đăng": "01/09/2026", "Giờ đăng": "10:00",
         "Trạng thái đăng": "ĐÃ ĐĂNG"},
    ])

    # Van đĩa của `chay_mot_ngay` thấy THIẾU đúng một lần (kích dọn khẩn).
    monkeypatch.setattr(tu_chay_mod, "_dung_luong_trong_gb", lambda g: 0.5)
    # `don_khan` (THẬT) tự đo lại bằng `_con_trong_gb` của chính nó: THIẾU ở
    # lần đo đầu (chịu xoá lượt 0001), ĐỦ ở mọi lần đo sau (dừng lại, không
    # xoá thêm).
    lan_do = {"n": 0}

    def _do_dan(_g):
        lan_do["n"] += 1
        return 0.5 if lan_do["n"] == 1 else 999.0

    monkeypatch.setattr(don_dep, "_con_trong_gb", _do_dan)

    moi = [{"link": "https://youtu.be/YYYYYYYYYYY", "tieu_de": "video mới", "kenh": "Z"}]
    ket = tu_chay_mod.chay_mot_ngay(
        goc, ma_kenh, che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=lambda luot, viec, **k: luot,  # không cần sản xuất xong — chỉ cần qua được van đĩa
    )

    # Dọn khẩn THẬT đã chạy và xoá đúng lượt cũ trên đĩa thật.
    assert not os.path.isdir(os.path.join(d_cu, "5-anh"))
    assert not os.path.isfile(video_cu)
    assert ket["run"]["dia"]["du"] is True, "phải đủ chỗ sau dọn khẩn rồi mới chạy tiếp"

    # `chay_mot_ngay` (qua `finalize` → `_ghi_bao_cao_ngay` → `ghi_json`) không
    # ném lỗi — nếu `moc_dang` còn là `datetime` sống, bước này đã vỡ từ bên
    # trong `chay_mot_ngay` rồi, không tới được đây. Đọc lại sổ từ ĐĨA THẬT
    # (không phải từ bộ nhớ) để chắc chắn tệp JSON ghi ra là hợp lệ.
    bao_cao_doc_lai = tu_chay_mod._doc_bao_cao_ngay(goc, ma_kenh, ket["ngay"])
    run_ghi = next(r for r in bao_cao_doc_lai["runs"] if r.get("ma_luot") == ket["run"]["ma_luot"])
    don_khan_ghi = run_ghi["dia"]["don_khan"]
    assert don_khan_ghi["da_chay"] is True
    assert don_khan_ghi["theo_kenh"].get(ma_kenh, 0) > 0
    assert don_khan_ghi["da_don"][0]["luot"] == "0001"
    assert isinstance(don_khan_ghi["da_don"][0]["moc_dang"], str), \
        "phải là chuỗi ISO, không phải datetime sống — xem lý do trong docstring bài kiểm này"


# ── (b) ENOSPC được nhận đúng — không rơi vào nhánh lỗi sản xuất chung ──────


def test_enospc_duoc_nhan_dung_khong_phai_loi_san_xuat(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/QQQQQQQQQQQ", "tieu_de": "x", "kenh": "Z"}]

    def _het_dia(luot, viec, **k):
        raise OSError(errno.ENOSPC, "No space left on device")

    goi_don_khan = []
    monkeypatch.setattr(don_dep, "don_khan", lambda *a, **k: (
        goi_don_khan.append(1) or _don_khan_gia_rong()))

    nhat_ky = []
    ket = tu_chay_mod.chay_mot_ngay(
        goc, "K1", che_do="that", on_log=nhat_ky.append,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_het_dia,
    )
    assert ket["ok"] is False
    assert ket["buoc_loi"] == "dia_day", "phải đánh dấu RIÊNG, không phải 'san_xuat' chung"
    assert ket["buoc_loi"] != "san_xuat"
    assert ket["run"]["san_xuat"]["dia_day"] is True
    assert goi_don_khan, "vừa dính ENOSPC thì phải kích dọn khẩn ngay"
    assert any("ĐĨA ĐẦY" in d for d in nhat_ky)


def test_winerror_112_cung_duoc_nhan_la_dia_day(tmp_path, monkeypatch):
    """Mã lỗi Windows tương đương ENOSPC (`WinError 112`) cũng phải nhận đúng,
    không chỉ mã POSIX — máy chạy thật là Windows Server."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/WWWWWWWWWWW", "tieu_de": "x", "kenh": "Z"}]

    def _het_dia_windows(luot, viec, **k):
        loi = OSError("[WinError 112] There is not enough space on the disk")
        loi.winerror = 112
        loi.errno = None
        raise loi

    monkeypatch.setattr(don_dep, "don_khan", lambda *a, **k: _don_khan_gia_rong())

    ket = tu_chay_mod.chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_het_dia_windows,
    )
    assert ket["buoc_loi"] == "dia_day"


def test_loi_mang_binh_thuong_van_roi_vao_nhanh_san_xuat(tmp_path, monkeypatch):
    """Lỗi KHÔNG phải đĩa đầy (ví dụ mạng rớt) vẫn phải đi đúng nhánh cũ
    ('san_xuat') — van mới không được nuốt nhầm lỗi khác."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/EEEEEEEEEEE", "tieu_de": "x", "kenh": "Z"}]

    def _mang_rot(luot, viec, **k):
        raise RuntimeError("mạng rớt giữa chừng")

    ket = tu_chay_mod.chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_mang_rot,
    )
    assert ket["buoc_loi"] == "san_xuat"
    assert "dia_day" not in ket["run"]["san_xuat"]


# ── (c) Dọn khẩn chỉ đụng video ĐÃ ĐĂNG, chỉ kênh đã bật `tu_don` ───────────


def _dung_luot_nang(goc, ma_kenh, luot):
    """Một thư mục lượt tối giản chỉ có phần NẶNG (đủ để `don_khan` tính vào
    ứng viên) — không cần bộ đủ như `test_don_dep._dung_luot`, việc đang kiểm
    ở đây là "đụng đúng lượt nào", không phải "giữ đúng tệp nhẹ nào"."""
    d = duong_luot(goc, ma_kenh, luot)
    os.makedirs(os.path.join(d, "5-anh"), exist_ok=True)
    with open(os.path.join(d, "5-anh", "canh-001.png"), "wb") as tep:
        tep.write(b"\x00" * 1000)
    video = os.path.join(d, "8-video.mp4")
    with open(video, "wb") as tep:
        tep.write(b"\x00" * 5000)
    return d, video


def _ghi_ke_hoach(goc, ma_kenh, dong_list):
    cot = list(ke_hoach_dang.COT)
    hang = []
    for d in dong_list:
        dong = {ten: "" for ten in cot}
        dong.update(d)
        dong.setdefault("Sẵn sàng", "x")
        hang.append([dong[ten] for ten in cot])
    ke_hoach_dang.luu_bang(goc, ma_kenh, hang, cot)


def _ghi_kenh_yaml_dep(goc, ma_kenh, **khoa):
    d = os.path.join(goc, "CHANNEL", ma_kenh)
    os.makedirs(d, exist_ok=True)
    dong = ["ma: {0}".format(ma_kenh)]
    for k, v in khoa.items():
        dong.append("{0}: {1}".format(k, v))
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


#: "Bây giờ" cố định, đủ xa mọi mốc đăng giả lập bên dưới để qua hạn ân xá.
_BAY_GIO = datetime.datetime(2026, 9, 25, 10, 0)


def test_don_khan_chi_dong_video_da_dang(tmp_path):
    goc = str(tmp_path)
    ma_kenh = "K1"
    _ghi_kenh_yaml_dep(goc, ma_kenh, tu_don="true", don_sau_gio=1)

    _d_da_dang, _v_da_dang = _dung_luot_nang(goc, ma_kenh, "0001")
    _d_chua_dang, v_chua_dang = _dung_luot_nang(goc, ma_kenh, "0002")
    moc_video = datetime.datetime(2026, 9, 20, 9, 0).timestamp()
    os.utime(_v_da_dang, (moc_video, moc_video))
    os.utime(v_chua_dang, (moc_video, moc_video))

    _ghi_ke_hoach(goc, ma_kenh, [
        {"Mã gói": "{0}-0001".format(ma_kenh), "Ngày đăng": "20/09/2026", "Giờ đăng": "10:00",
         "Trạng thái đăng": "ĐÃ ĐĂNG"},
        {"Mã gói": "{0}-0002".format(ma_kenh), "Ngày đăng": "", "Giờ đăng": "",
         "Trạng thái đăng": ""},
    ])

    ket = don_dep.don_khan(goc, [ma_kenh], nguong_gb=1_000_000.0, bay_gio=_BAY_GIO,
                           con_trong_gb_fn=lambda g: 0.0)  # luôn "thiếu" -> dọn hết ứng viên hợp lệ

    assert ket["da_chay"] is True
    assert not os.path.isdir(os.path.join(_d_da_dang, "5-anh")), "lượt ĐÃ ĐĂNG phải bị dọn"
    assert not os.path.isfile(_v_da_dang)
    assert os.path.isdir(os.path.join(_d_chua_dang, "5-anh")), "lượt CHƯA đăng không được đụng"
    assert os.path.isfile(v_chua_dang)
    assert ket["theo_kenh"].get(ma_kenh, 0) > 0


def test_don_khan_bo_qua_kenh_chua_bat_tu_don(tmp_path):
    goc = str(tmp_path)
    ma_kenh = "K2"
    _ghi_kenh_yaml_dep(goc, ma_kenh)  # không khai tu_don -> mặc định tắt

    d, video = _dung_luot_nang(goc, ma_kenh, "0001")
    moc_video = datetime.datetime(2026, 9, 20, 9, 0).timestamp()
    os.utime(video, (moc_video, moc_video))
    _ghi_ke_hoach(goc, ma_kenh, [
        {"Mã gói": "{0}-0001".format(ma_kenh), "Ngày đăng": "20/09/2026", "Giờ đăng": "10:00",
         "Trạng thái đăng": "ĐÃ ĐĂNG"},
    ])

    ket = don_dep.don_khan(goc, [ma_kenh], nguong_gb=1_000_000.0, bay_gio=_BAY_GIO,
                           con_trong_gb_fn=lambda g: 0.0)

    assert ket["da_chay"] is True
    assert ket["bo_qua_khong_tu_don"] == [ma_kenh]
    assert os.path.isdir(os.path.join(d, "5-anh")), "kênh chưa bật tu_don thì dọn khẩn không được đụng"
    assert os.path.isfile(video)
    assert ket["theo_kenh"] == {}


def test_don_khan_du_dia_roi_thi_khong_dong_gi(tmp_path):
    """Đĩa đã đủ ngay từ đầu — dọn khẩn không được xoá bất cứ thứ gì, dù có
    ứng viên hợp lệ nằm chờ sẵn."""
    goc = str(tmp_path)
    ma_kenh = "K1"
    _ghi_kenh_yaml_dep(goc, ma_kenh, tu_don="true", don_sau_gio=1)
    d, video = _dung_luot_nang(goc, ma_kenh, "0001")
    moc_video = datetime.datetime(2026, 9, 20, 9, 0).timestamp()
    os.utime(video, (moc_video, moc_video))
    _ghi_ke_hoach(goc, ma_kenh, [
        {"Mã gói": "{0}-0001".format(ma_kenh), "Ngày đăng": "20/09/2026", "Giờ đăng": "10:00",
         "Trạng thái đăng": "ĐÃ ĐĂNG"},
    ])

    ket = don_dep.don_khan(goc, [ma_kenh], nguong_gb=1.0, bay_gio=_BAY_GIO,
                           con_trong_gb_fn=lambda g: 50.0)  # đĩa còn 50 GB, thừa so với ngưỡng 1 GB

    assert ket["da_chay"] is False
    assert os.path.isdir(os.path.join(d, "5-anh"))
    assert os.path.isfile(video)


def test_don_khan_dung_ngay_khi_du_khong_xoa_qua_tay(tmp_path):
    """Nhiều ứng viên đã đăng cùng lúc — dọn khẩn phải DỪNG ngay khi đã vượt
    ngưỡng, không xoá nốt những lượt còn lại."""
    goc = str(tmp_path)
    ma_kenh = "K1"
    _ghi_kenh_yaml_dep(goc, ma_kenh, tu_don="true", don_sau_gio=1)

    moc_video = datetime.datetime(2026, 9, 18, 9, 0).timestamp()
    dong_list = []
    thu_muc = {}
    for luot, ngay in (("0001", "18/09/2026"), ("0002", "19/09/2026"), ("0003", "20/09/2026")):
        d, video = _dung_luot_nang(goc, ma_kenh, luot)
        os.utime(video, (moc_video, moc_video))
        thu_muc[luot] = d
        dong_list.append({"Mã gói": "{0}-{1}".format(ma_kenh, luot), "Ngày đăng": ngay,
                          "Giờ đăng": "10:00", "Trạng thái đăng": "ĐÃ ĐĂNG"})
    _ghi_ke_hoach(goc, ma_kenh, dong_list)

    # Đĩa "đủ" ngay sau lượt xoá ĐẦU TIÊN (cũ nhất, 0001) — giả một chuỗi
    # dung lượng tăng dần qua từng lần đo lại.
    lan_do = {"n": 0}

    def _do_dan(_g):
        lan_do["n"] += 1
        return 0.0 if lan_do["n"] == 1 else 1_000_000.0

    ket = don_dep.don_khan(goc, [ma_kenh], nguong_gb=100.0, bay_gio=_BAY_GIO, con_trong_gb_fn=_do_dan)

    assert ket["da_chay"] is True
    assert len(ket["da_don"]) == 1, "phải dừng ngay sau lượt đầu tiên đã đủ, không dọn tiếp"
    assert ket["da_don"][0]["luot"] == "0001", "lượt CŨ NHẤT (mốc đăng sớm nhất) phải bị dọn trước"
    assert not os.path.isdir(os.path.join(thu_muc["0001"], "5-anh"))
    assert os.path.isdir(os.path.join(thu_muc["0002"], "5-anh")), "chưa cần đụng tới, phải còn nguyên"
    assert os.path.isdir(os.path.join(thu_muc["0003"], "5-anh"))
