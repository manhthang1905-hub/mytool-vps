"""`core.tu_chay` + luật 07/10/2026 "thà không đăng còn hơn sản phẩm kém".

* 1d — gói CHỜ clip thật quá giờ đăng cũ: lượt dở được nhặt lại, bàn giao lấy khe
  trống KẾ TIẾP (≥ bây giờ + biên), không giữ giờ đã trôi.
* Lượt "xong" mà còn cảnh dựng từ ảnh → `mo_lai_khau_clip` mở lại khâu clip + dựng
  (không kẹt mãi ở bước bàn giao bị từ chối).

Không mạng, không ví — `tmp_path`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from core import auto, ke_hoach_dang
from core.tu_chay import _ghi_bao_cao_ngay, _tim_run_chua_xong, chay_mot_ngay

NO_LOG = lambda *_a, **_k: None  # noqa: E731


def _ghi_kenh(goc, ma, **cai):
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(thu_muc, "nv"), exist_ok=True)
    mac_dinh = {"ma": ma, "ngon_ngu": "ja", "engine": "veo3", "phut_muc_tieu": 10,
                "ngan_sach_ngay": 100_000_000, "thu_muc_done": "done", "voice_id": "v1"}
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
    with open(os.path.join(thu_muc, "nv", "nv1.png"), "wb") as tep:
        tep.write(b"\x89PNG\r\n\x1a\n")
    with open(os.path.join(thu_muc, "style.yaml"), "w", encoding="utf-8") as tep:
        tep.write('image_style: "phong cách thử"\n')
    os.makedirs(os.path.join(thu_muc, "prompt"), exist_ok=True)
    for ten in ("2-viet.md", "7-canh.md"):
        with open(os.path.join(thu_muc, "prompt", ten), "w", encoding="utf-8") as tep:
            tep.write("nội dung mẫu\n")


def _luot_do(goc, *, trang=None, ban_giao=False, xong_het=False, ngay="2026-10-06"):
    """Lượt K1/0001 sinh ngày `ngay`, đã chạy sản xuất (sổ ngày + trang-thai.json)."""
    luot = auto.moi_luot(goc, "K1", "0001", {"link": "https://youtu.be/AAAAAAAAAAA",
                                             "tieu_de": "", "chu_bia": ""})
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = (trang or {}).get(m, auto.XONG)
    auto.ghi_luot(luot)
    run = {"ma_luot": "0001",
           "nguon": {"nguon": "vph", "ma": "AAAAAAAAAAA", "kenh": "Z",
                     "link": "https://youtu.be/AAAAAAAAAAA", "tieu_de": "x"},
           "ngan_sach": {}, "san_xuat": {"da_chay": True, "xong_het": xong_het,
                                         "khau_hong": [], "loi": ""},
           "ban_giao": {"da_ban_giao": ban_giao, "ma_goi": "", "ngay_dang": "",
                        "gio_dang": "", "ly_do_trong": "", "loi": ""}}
    _ghi_bao_cao_ngay(goc, "K1", ngay, {"ngay": ngay, "kenh": "K1", "runs": [run], "nhat_ky": []})
    return luot


def _chay(goc, bay_gio, chay_auto, ban_giao):
    return chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=bay_gio.date(), on_log=NO_LOG, bay_gio=bay_gio,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=lambda g, k: {"moi": []},
        video_da_lam_nhom=lambda g, k: set(), tieu_de_da_lam_nhom=lambda g, k: [],
        dung_viec=lambda bc: {}, chay_auto=chay_auto, ban_giao=ban_giao)


def _chay_auto_het(luot, viec, **k):
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


def test_goi_cho_clip_qua_gio_dang_lay_khe_ke_tiep(tmp_path):
    """Gói đăng 07/10 05:00 còn chờ kho clip; engine có lại, xong lúc 07/10 09:00 →
    bàn giao vào khe trống kế tiếp ≥ 09:00 + 12h (08/10 05:00 đã có gói khác →
    09/10 05:00), không phải khe 07/10 05:00 đã trôi."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", tu_duyet=True, gio_dang="05:00", nhip_dang=["05:00"])
    dong = {t: "" for t in ke_hoach_dang.COT}
    dong.update({"Mã gói": "K1-0099", "Ngày đăng": "08/10/2026", "Giờ đăng": "05:00", "Sẵn sàng": "x"})
    ke_hoach_dang.luu_bang(goc, "K1", [[dong[t] for t in ke_hoach_dang.COT]])
    _luot_do(goc, trang={"clip": auto.CHO, "thumbnail": auto.CHO, "dung": auto.CHO})
    assert _tim_run_chua_xong(goc, "K1", _dt.date(2026, 10, 7)) == ("2026-10-06", "0001")
    goi = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi.append((luot_, ngay, gio))
        return "K1-0001", True

    ket = _chay(goc, _dt.datetime(2026, 10, 7, 9, 0), _chay_auto_het, ban_giao_gia)
    assert ket["ok"] is True, ket
    assert goi == [("0001", "09/10/2026", "05:00")]


def test_luot_xong_tren_clip_tu_anh_mo_lai_khau_clip(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    luot = _luot_do(goc, xong_het=True)
    d = luot.thu_muc
    os.makedirs(os.path.join(d, "6-clip"), exist_ok=True)
    with open(os.path.join(d, "4-canh.json"), "w", encoding="utf-8") as tep:
        json.dump([{"scene_id": 1}, {"scene_id": 2}], tep)
    for n in (1, 2):
        open(os.path.join(d, "6-clip", "{0}.mp4".format(n)), "wb").write(b"c")
    with open(os.path.join(d, "6-clip", "tu-anh.json"), "w", encoding="utf-8") as tep:
        json.dump({"canh": [2], "tong": 2}, tep)
    open(os.path.join(d, "8-video.mp4"), "wb").write(b"v")
    thay = []

    def chay_auto(luot_, viec, **k):
        thay.append({m: luot_.tt(m).trang_thai for m in ("anh", "clip", "dung")})
        return _chay_auto_het(luot_, viec)

    ket = _chay(goc, _dt.datetime(2026, 10, 7, 9, 0), chay_auto,
                lambda *a, **k: ("K1-0001", True))
    assert thay == [{"anh": auto.XONG, "clip": auto.CHO, "dung": auto.CHO}], \
        "lượt xong trên clip từ ảnh phải chạy lại sản xuất từ khâu clip"
    assert ket["run"]["ban_giao"]["da_ban_giao"] is True


def test_luot_du_clip_that_khong_mo_lai(tmp_path):
    from core import lam_lai_clip_that as ll

    goc = str(tmp_path)
    luot = _luot_do(goc, xong_het=True)
    os.makedirs(os.path.join(luot.thu_muc, "6-clip"))
    with open(os.path.join(luot.thu_muc, "4-canh.json"), "w", encoding="utf-8") as tep:
        json.dump([{"scene_id": 1}], tep)
    open(os.path.join(luot.thu_muc, "6-clip", "1.mp4"), "wb").write(b"c")
    assert ll.mo_lai_khau_clip(luot, None) is False
    assert auto.doc_luot(luot.thu_muc).tt("clip").trang_thai == auto.XONG
