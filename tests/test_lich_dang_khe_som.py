"""Không bỏ trống ngày đăng khi đã có video (19/10/2026, `core/xep_lich.py` + máy đăng + tự kiểm).

Ca gốc: TL2-T7-0032 bàn giao 19/10 01:04, `bien_xu_ly_gio: 4` → khe 19/10 05:00 bị bỏ, gói nhận 20/10 05:00; máy đăng
tải lên 01:10 vẫn hẹn 20/10 → ngày 19/10 trống. Không mạng, không ví — mọi bài dùng `tmp_path`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from core import auto, ke_hoach_dang, xep_lich
from core import tu_kiem as tk
from core.kenh import doc_kenh
from core.tu_chay import chay_mot_ngay

NO_LOG = lambda *_a, **_k: None  # noqa: E731
K = "TL2-T7"


def _ghi_kenh(goc, ma=K, **cai):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    mac_dinh = {"ma": ma, "ngon_ngu": "ja", "engine": "veo3", "phut_muc_tieu": 10, "tu_duyet": True,
                "nhip_dang": ["05:00"], "gio_dang": "20:00", "bien_xu_ly_gio": 4}
    mac_dinh.update(cai)
    dong = []
    for k, v in mac_dinh.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, (int, float)):
            dong.append("{0}: {1}".format(k, v))
        elif isinstance(v, list):
            dong.append("{0}: [{1}]".format(k, ", ".join('"{0}"'.format(x) for x in v)))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    return doc_kenh(goc, ma)


def _ghi_ke_hoach(goc, *dong_kv, ma=K):
    hang = []
    for kv in dong_kv:
        d = {ten: "" for ten in ke_hoach_dang.COT}
        d.update(kv)
        hang.append([d[ten] for ten in ke_hoach_dang.COT])
    ke_hoach_dang.luu_bang(goc, ma, hang)


def _ghi_so(goc, so):
    p = os.path.join(goc, "vm", "logs", "so-video-id.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as tep:
        json.dump(so, tep, ensure_ascii=False)


def _lich(goc, ma_goi, kenh=K):
    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    d = next(dict(zip(cot, h)) for h in hang if h[cot.index("Mã gói")] == ma_goi)
    return d["Ngày đăng"], d["Giờ đăng"]


DA_DANG_18 = {"Mã gói": "TL2-T7-0031", "Ngày đăng": "18/10/2026", "Giờ đăng": "05:00", "Sẵn sàng": "x",
              "Trạng thái đăng": "ĐÃ ĐĂNG", "Video ID": "vidGia4673d"}


def _goi(ngay="20/10/2026", **them):
    return dict({"Mã gói": "TL2-T7-0032", "Ngày đăng": ngay, "Giờ đăng": "05:00", "Sẵn sàng": "x"}, **them)


# ── bàn giao: biên đo bằng biên bàn giao (≤ 90'), không phải bien_xu_ly_gio 4h ────────────────────────────


def test_bien_ban_giao_tran_90_phut(tmp_path):
    goc = str(tmp_path)
    assert xep_lich.bien_ban_giao_gio(_ghi_kenh(goc)) == 1.5                       # 4h → trần 90'
    assert xep_lich.bien_ban_giao_gio(_ghi_kenh(goc, bien_xu_ly_gio=1)) == 1.0     # nhỏ hơn trần: giữ


def test_ban_giao_luc_01_04_lay_khe_05_00_cung_ngay(tmp_path):
    """Ca TL2-T7-0032: bàn giao 01:04 — khe 19/10 05:00 còn gần 4 giờ → phải lấy, không nhảy 20/10."""
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, DA_DANG_18)
    bay = _dt.datetime(2026, 10, 19, 1, 4)
    assert xep_lich.khe_trong_som_nhat(goc, K, k, bay_gio=bay, bien_gio=xep_lich.bien_ban_giao_gio(k)) \
        == ("19/10/2026", "05:00")
    # biên cũ (bien_xu_ly_gio 4h) chính là lỗi: 01:04 + 4h = 05:04 > 05:00 → 20/10
    assert xep_lich.khe_trong_som_nhat(goc, K, k, bay_gio=bay) == ("20/10/2026", "05:00")


def test_ban_giao_sat_khe_bien_90_phut(tmp_path):
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    bien = xep_lich.bien_ban_giao_gio(k)
    assert xep_lich.khe_trong_som_nhat(goc, K, k, bay_gio=_dt.datetime(2026, 10, 19, 3, 30), bien_gio=bien) \
        == ("19/10/2026", "05:00")                                                   # đúng 90' trước: kịp
    assert xep_lich.khe_trong_som_nhat(goc, K, k, bay_gio=_dt.datetime(2026, 10, 19, 3, 31), bien_gio=bien) \
        == ("20/10/2026", "05:00")                                                   # 89': sang ngày sau


def _lam_kenh_san_sang(goc, ma=K):
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


def _chay_auto_het(luot, viec, **k):
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


def test_chay_mot_ngay_ban_giao_gan_khe_xep_dung_ngay(tmp_path):
    """Tích hợp bước 5 `chay_mot_ngay`: gói xong 01:04 được hẹn 19/10 05:00 (kênh bien_xu_ly_gio 4h)."""
    goc = str(tmp_path)
    _ghi_kenh(goc, ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc)
    _ghi_ke_hoach(goc, DA_DANG_18)
    goi = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi.append((ngay, gio))
        return "TL2-T7-0032", True

    ket = chay_mot_ngay(
        goc, K, che_do="that", hom_nay=_dt.date(2026, 10, 19), on_log=NO_LOG,
        bay_gio=_dt.datetime(2026, 10, 19, 1, 4),
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=lambda g, k: {"moi": [{"link": "https://youtu.be/JJJJJJJJJJJ", "tieu_de": "x", "kenh": "Z"}]},
        video_da_lam_nhom=lambda g, k: set(), tieu_de_da_lam_nhom=lambda g, k: [],
        dung_viec=lambda bc: {}, chay_auto=_chay_auto_het, ban_giao=ban_giao_gia)
    assert ket["ok"] is True, ket
    assert goi == [("19/10/2026", "05:00")]


# ── lúc tải lên: kéo về khe trống sớm hơn (biên BIEN_TAI_TOI_THIEU_PHUT) ──────────────────────────────────


def test_tai_luc_01_10_keo_ve_khe_05_00(tmp_path):
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, DA_DANG_18, _goi())
    doi = xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=_dt.datetime(2026, 10, 19, 1, 10), so_video_id={})
    assert doi == ("TL2-T7-0032", "20/10/2026 05:00", "19/10/2026 05:00")
    assert _lich(goc, "TL2-T7-0032") == ("19/10/2026", "05:00")


def test_tai_bien_toi_thieu_45_phut(tmp_path):
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    assert xep_lich.BIEN_TAI_TOI_THIEU_PHUT == 45
    f = xep_lich.khe_som_hon_khi_tai
    assert f(goc, K, k, "TL2-T7-0032", "20/10/2026", "05:00", bay_gio=_dt.datetime(2026, 10, 19, 4, 15),
             so_video_id={}) == ("19/10/2026", "05:00")                             # còn đúng 45'
    assert f(goc, K, k, "TL2-T7-0032", "20/10/2026", "05:00", bay_gio=_dt.datetime(2026, 10, 19, 4, 16),
             so_video_id={}) == ("", "")                                             # còn 44': giữ 20/10


def test_khong_bao_gio_day_muon(tmp_path):
    """Gói đã hẹn khe sớm nhất (kể cả còn < 45') thì giữ nguyên — kéo SỚM, không đẩy muộn tạo ngày trống."""
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, _goi("19/10/2026"))
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=_dt.datetime(2026, 10, 19, 4, 30),
                                 so_video_id={}) is None
    assert _lich(goc, "TL2-T7-0032") == ("19/10/2026", "05:00")


def test_khong_xep_chong_khe_ke_hoach(tmp_path):
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, {"Mã gói": "TL2-T7-0033", "Ngày đăng": "19/10/2026", "Giờ đăng": "05:00", "Sẵn sàng": "x"},
                  _goi())
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=_dt.datetime(2026, 10, 19, 1, 10),
                                 so_video_id={}) is None


def test_khong_xep_chong_video_da_hen_trong_so(tmp_path):
    """Video đã hẹn trên YouTube (sổ máy đăng) lệch giờ 05:15 vẫn chiếm khe 05:00 của ngày đó."""
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, _goi())
    so = {"TL2-T7/TL2-T7-0030": {"video_id": "AAAAAAAAAAA", "trang_thai": "xac-nhan", "lich": "19/10/2026 05:15"}}
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=_dt.datetime(2026, 10, 19, 1, 10),
                                 so_video_id=so) is None
    # bản nháp/tải hỏng trong sổ KHÔNG chiếm khe
    so["TL2-T7/TL2-T7-0030"]["trang_thai"] = "tai-hong"
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=_dt.datetime(2026, 10, 19, 1, 10),
                                 so_video_id=so) is not None


def test_dung_khe_cua_goi_bo_hoac_bi_giu(tmp_path):
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    bay = _dt.datetime(2026, 10, 19, 1, 10)
    for giu in ({"Trạng thái đăng": "Bỏ — trùng nguồn", "Sẵn sàng": "x"},      # gói bỏ
                {"Sẵn sàng": ""}):                                              # gói bị giữ / bỏ duyệt
        _ghi_ke_hoach(goc, dict({"Mã gói": "TL2-T7-0031", "Ngày đăng": "19/10/2026", "Giờ đăng": "05:00"}, **giu),
                      _goi())
        assert ("19/10/2026", "05:00") not in xep_lich.khe_da_dung(goc, K)
        assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=bay, so_video_id={})[2] == "19/10/2026 05:00"
        # bàn giao cũng dùng lại khe đó
        _ghi_ke_hoach(goc, dict({"Mã gói": "TL2-T7-0031", "Ngày đăng": "19/10/2026", "Giờ đăng": "05:00"}, **giu))
        assert xep_lich.khe_trong_som_nhat(goc, K, k, bay_gio=bay, bien_gio=xep_lich.bien_ban_giao_gio(k)) \
            == ("19/10/2026", "05:00")


def test_khong_keo_goi_da_len_kenh_hoac_kenh_khong_tu_duyet(tmp_path):
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, _goi())
    bay = _dt.datetime(2026, 10, 19, 1, 10)
    so = {"TL2-T7/TL2-T7-0032": {"video_id": "vidGiacf429", "trang_thai": "xac-nhan", "lich": "20/10/2026 05:00"}}
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=bay, so_video_id=so) is None
    k2 = _ghi_kenh(goc, tu_duyet=False)
    assert xep_lich.keo_lich_som(goc, K, k2, "TL2-T7-0032", bay_gio=bay, so_video_id={}) is None
    assert _lich(goc, "TL2-T7-0032") == ("20/10/2026", "05:00")


def test_nhieu_goi_cho_lap_kin_ngay_trong(tmp_path):
    """Hai gói chờ 20/10 và 21/10, 19/10 trống: lần lượt tải → 19/10 rồi 20/10 (mỗi ngày đúng 1 video)."""
    goc = str(tmp_path)
    k = _ghi_kenh(goc)
    _ghi_ke_hoach(goc, _goi(), {"Mã gói": "TL2-T7-0033", "Ngày đăng": "21/10/2026", "Giờ đăng": "05:00",
                                "Sẵn sàng": "x"})
    bay = _dt.datetime(2026, 10, 19, 1, 10)
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0032", bay_gio=bay, so_video_id={})[2] == "19/10/2026 05:00"
    assert xep_lich.keo_lich_som(goc, K, k, "TL2-T7-0033", bay_gio=bay, so_video_id={})[2] == "20/10/2026 05:00"


def test_may_dang_keo_lich_som_tool(tmp_path):
    """Đường máy đăng (`vm/may_dang_dom.keo_lich_som_tool`): gốc tool có kenh.yaml → dời; không có → None."""
    import sys
    vm = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm")
    if vm not in sys.path:
        sys.path.insert(0, vm)
    import may_dang_dom as mdd

    goc = str(tmp_path)
    _ghi_kenh(goc)
    _ghi_ke_hoach(goc, DA_DANG_18, _goi())
    bay = _dt.datetime(2026, 10, 19, 1, 10)
    assert mdd.keo_lich_som_tool(goc, K, "TL2-T7-0032", {}, bay) == ("19/10/2026", "05:00")
    assert mdd.keo_lich_som_tool(str(tmp_path / "khong-co"), K, "TL2-T7-0032", {}, bay) is None


# ── tự kiểm: ngày trống kèm nguyên nhân ────────────────────────────────────────────────────────────────


def _tu_kiem(goc, monkeypatch, bay):
    monkeypatch.setattr(tk, "_kenh_tu_chay", lambda g, k: True)
    ctx = tk.BoiCanh(goc, bay=bay, tai=lambda url: (404, b""), kenh_ds=[K], so={})
    return {m["khoa"]: m for m in tk.kiem_nhip(ctx)}


def test_tu_kiem_ngay_trong_do_xep_lich_muon(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_kenh(goc)
    _ghi_so(goc, {
        "TL2-T7/TL2-T7-0030": {"video_id": "vidGia37ac9", "trang_thai": "xac-nhan", "lich": "17/10/2026 05:00",
                               "tai_xong_luc": "2026-10-16 22:00:00"},
        "TL2-T7/TL2-T7-0031": {"video_id": "vidGia4673d", "trang_thai": "xac-nhan", "lich": "18/10/2026 05:00",
                               "tai_xong_luc": "2026-10-17 22:49:47"},
        "TL2-T7/TL2-T7-0032": {"video_id": "vidGiacf429", "trang_thai": "xac-nhan", "lich": "20/10/2026 05:00",
                               "lich_dat": "20/10/2026 05:00", "tai_xong_luc": "2026-10-19 01:10:02"}})
    ds = _tu_kiem(goc, monkeypatch, _dt.datetime(2026, 10, 19, 15, 0))
    m = ds["nhip:khe:TL2-T7:2026-10-19"]
    assert m["tt"] == tk.HONG and m["nguyen_nhan"] == "xep_muon"
    assert "TL2-T7-0032" in m["bang_chung"] and "20/10 05:00" in m["bang_chung"]
    assert "19/10 (xếp lịch muộn)" in ds["nhip:3ngay:TL2-T7:2026-10-19"]["bang_chung"]
    assert not any(k.startswith("nhip:khe:TL2-T7:2026-10-1" + d) for k in ds for d in "78")


def test_tu_kiem_ngay_trong_do_thieu_goi_va_goi_bi_giu(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_kenh(goc)
    _ghi_so(goc, {"TL2-T7/TL2-T7-0031": {"video_id": "vidGia4673d", "trang_thai": "xac-nhan",
                                         "lich": "17/10/2026 05:00", "tai_xong_luc": "2026-10-16 22:00:00"},
                  # tải SAU khe 18/10 05:00 → không phải lỗi xếp lịch của 18/10
                  "TL2-T7/TL2-T7-0033": {"video_id": "BBBBBBBBBBB", "trang_thai": "xac-nhan",
                                         "lich": "20/10/2026 05:00", "tai_xong_luc": "2026-10-19 04:40:00"}})
    _ghi_ke_hoach(goc, {"Mã gói": "TL2-T7-0032", "Ngày đăng": "19/10/2026", "Giờ đăng": "05:00", "Sẵn sàng": "x",
                        "Ghi chú": "bìa chưa qua cổng chữ"})
    ds = _tu_kiem(goc, monkeypatch, _dt.datetime(2026, 10, 19, 15, 0))
    assert ds["nhip:khe:TL2-T7:2026-10-18"]["nguyen_nhan"] == "thieu_goi"
    m19 = ds["nhip:khe:TL2-T7:2026-10-19"]
    assert m19["nguyen_nhan"] == "giu_goi" and "bìa chưa qua cổng chữ" in m19["bang_chung"]


def test_tu_kiem_khe_chua_qua_thi_chua_bao(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_kenh(goc, nhip_dang=["20:00"])
    _ghi_so(goc, {"TL2-T7/a": {"video_id": "x1", "trang_thai": "xac-nhan", "lich": "17/10/2026 20:00"},
                  "TL2-T7/b": {"video_id": "x2", "trang_thai": "xac-nhan", "lich": "18/10/2026 20:00"}})
    ds = _tu_kiem(goc, monkeypatch, _dt.datetime(2026, 10, 19, 12, 0))
    assert not any(k.startswith("nhip:khe:") for k in ds)                           # 19/10 20:00 chưa tới
