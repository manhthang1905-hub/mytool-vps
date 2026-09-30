"""Chu kỳ ngày cho kênh "tự chạy" (`core/tu_chay.py`).

Mọi bài dùng seam giả cho nghiên cứu/chọn nguồn/sản xuất/bàn giao — không
mạng, không tốn ví ShopAPI (đúng luật 3 của CLAUDE.md).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

from core import auto
from core import ban_giao_dang, ke_hoach_dang
from core import cong_thuc_v7 as v7
from core import danh_ba_doi_thu as db
from core import su_co
from core.kenh import doc_kenh
from core.tu_chay import (_bo_luot_qua_han, _coi_nhu_da_xong, _cua_so_san_xuat,
                          _doc_bao_cao_ngay, _dung_md_tat_ca, _ghi_bao_cao_ngay,
                          _ghi_nhan_phuc_hoi, _ly_do_vuot_tran_phuc_hoi,
                          _moc_ban_giao_goi,
                          _nhan_nuoi_luot_mo_coi, _tim_gio_trong,
                          _tim_run_chua_xong,
                          chay_mot_ngay, chay_nhieu_kenh, chay_tat_ca,
                          dong_bo_nhom_truoc_khi_chay, duong_bao_cao_tat_ca,
                          ghi_bao_cao_tat_ca, giu_khoa_may, kenh_tu_chay,
                          nha_khoa_may)


def _ghi_ke_hoach(goc, ma, **gia_tri):
    dong = {ten: "" for ten in ke_hoach_dang.COT}
    dong.update(gia_tri)
    ke_hoach_dang.luu_bang(goc, ma,
                           [[dong[ten] for ten in ke_hoach_dang.COT]])


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
    """Đưa kênh qua được `core.kenh.kiem_kenh`: ảnh nhân vật, style, hai lời
    nhắc bắt buộc. Gọi CÙNG với `_ghi_kenh(..., voice_id="v1")` — `kiem_kenh`
    đòi cả hai."""
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
    """Đồ giả cho `mot_nut.doc_danh_sach`."""
    def fn(goc, kenh):
        return {"moi": list(moi)}
    return fn


def _danh_sach_gia_day_du(*, moi=None, vuot=None, but=None):
    """Đồ giả cho `mot_nut.doc_danh_sach` — có đủ cả ba bảng `moi`/`vuot`/`but`, như
    `mot_nut._viet_bao_cao` ghi thật (mỗi dòng mang `link`/`view`/`vuot`/`tang`)."""
    du = {"moi": list(moi or []), "vuot": list(vuot or []), "but": list(but or [])}

    def fn(goc, kenh):
        return du
    return fn


def _dong_de_xuat(link, *, tieu_de="x", kenh="Z", view=0, vuot=0.0, tang=0.0):
    return {"link": link, "tieu_de": tieu_de, "kenh": kenh, "view": view, "vuot": vuot, "tang": tang,
           "ngay": "", "tuyen": "", "chu_de": "", "but": 0.0, "diem": 0}


def _ghi_danh_ba_rong(goc, ma_kenh):
    """Giả một kênh ĐÃ SỐNG (không phải lượt "một nút" đầu tiên) — có sẵn danh bạ đối
    thủ rỗng trên đĩa. Xem `test_lan_dau_khong_co_danh_ba_thi_khong_dua_vi_vao_nghien_cuu`."""
    duong = db.duong_so(goc, ma_kenh)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("")


def _ghi_cong_thuc_v7(goc, ma_kenh, **cai):
    nc = os.path.join(goc, "CHANNEL", ma_kenh, "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, v7.TEP_CAU_HINH), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


def _tong_quan_that(goc, ma_kenh, ma_video, moc, **kv):
    d = os.path.join(goc, "CHANNEL", ma_kenh, "chi-so", ma_video, moc)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "tong-quan.json"), "w", encoding="utf-8") as tep:
        json.dump(kv, tep)


def _dem_goi(fn):
    """Bọc `fn`, đếm số lần gọi ở `.so_lan`."""
    def boc(*a, **k):
        boc.so_lan += 1
        return fn(*a, **k)
    boc.so_lan = 0
    return boc


class _DongV7Gia:
    def __init__(self, ma, link, tieu_de="", kenh="", diem=80, loai="Làm ngay", bi_loai=""):
        self.ma, self.link, self.tieu_de, self.kenh = ma, link, tieu_de, kenh
        self.diem, self.loai, self.ly_do, self.bi_loai = diem, loai, [], bi_loai


class _KetQuaV7Gia:
    def __init__(self, ung_vien):
        self.ung_vien = ung_vien


def _chay_auto_het(luot, viec, **k):
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


def _chay_auto_mot_khau(luot, viec, **k):
    """Đồ giả cho sản xuất DỞ DANG — chỉ khâu đầu xong."""
    luot.tt("kich-ban").trang_thai = auto.XONG
    auto.ghi_luot(luot)
    return luot


NO_LOG = lambda *_a, **_k: None  # noqa: E731


# ── Chọn nguồn: loại đã làm + loại nhóm đã làm ──────────────────────────────


def test_chon_nguon_loai_da_lam_va_nhom_qua_mot_nut(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "da-lam.txt"), "w", encoding="utf-8") as tep:
        tep.write("AAAAAAAAAAA | đã làm\n")

    moi = [
        {"link": "https://youtu.be/AAAAAAAAAAA", "tieu_de": "đã làm rồi", "kenh": "X"},
        {"link": "https://youtu.be/BBBBBBBBBBB", "tieu_de": "kênh khác trong nhóm đã làm", "kenh": "Y"},
        {"link": "https://youtu.be/CCCCCCCCCCC", "tieu_de": "còn mới", "kenh": "Z"},
    ]
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: {"BBBBBBBBBBB"},
    )
    assert ket["ok"] is True
    assert ket["run"]["nguon"]["ma"] == "CCCCCCCCCCC"
    assert ket["run"]["nguon"]["nguon"] == "mot_nut"


def test_chon_nguon_qua_cong_thuc_v7_khi_co_cau_hinh(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    # Có mặt tệp này là đủ để tool coi kênh "đã có cấu hình V7" — nội dung
    # không quan trọng vì `cham_v7` được thay bằng đồ giả.
    with open(os.path.join(nc, "cong-thuc-v7.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")

    da_lam_nhom = _DongV7Gia("JJJJJJJJJJJ", "https://youtu.be/JJJJJJJJJJJ", tieu_de="nhóm đã làm")
    con_moi = _DongV7Gia("KKKKKKKKKKK", "https://youtu.be/KKKKKKKKKKK", tieu_de="chọn cái này")

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([da_lam_nhom, con_moi]),
        video_da_lam_nhom=lambda g, k: {"JJJJJJJJJJJ"},
    )
    assert ket["run"]["nguon"]["nguon"] == "v7"
    assert ket["run"]["nguon"]["ma"] == "KKKKKKKKKKK"


# ── Sàn chất lượng V7: chỉ "Làm ngay"/"Nên làm", không bị loại; không fallback ─


def test_v7_chi_lay_lam_ngay_hoac_nen_lam_khong_bi_loai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "cong-thuc-v7.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")

    du_bi = _DongV7Gia("TTTTTTTTTTT", "https://youtu.be/TTTTTTTTTTT", loai="Dự bị")
    bi_loai_dong = _DongV7Gia("UUUUUUUUUUU", "https://youtu.be/UUUUUUUUUUU", loai="Làm ngay",
                              bi_loai="đã làm")
    nen_lam = _DongV7Gia("VVVVVVVVVVV", "https://youtu.be/VVVVVVVVVVV", loai="Nên làm", tieu_de="chọn")

    doc_ds = _dem_goi(_danh_sach_gia(
        [{"link": "https://youtu.be/WWWWWWWWWWW", "tieu_de": "x", "kenh": "Z"}]))
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([bi_loai_dong, du_bi, nen_lam]),
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert doc_ds.so_lan == 0, "kênh có cấu hình V7 thì không được rơi về bảng Một nút"
    assert ket["run"]["nguon"]["ma"] == "VVVVVVVVVVV"


def test_v7_khong_co_ung_vien_dat_chuan_thi_khong_fallback(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "cong-thuc-v7.json"), "w", encoding="utf-8") as tep:
        tep.write("{}")

    du_bi = _DongV7Gia("XXXXXXXXXXX", "https://youtu.be/XXXXXXXXXXX", loai="Dự bị")
    doc_ds = _dem_goi(_danh_sach_gia(
        [{"link": "https://youtu.be/YYYYYYYYYYY", "tieu_de": "x", "kenh": "Z"}]))

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([du_bi]),
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert doc_ds.so_lan == 0, "kênh có cấu hình V7 thì không được rơi về bảng Một nút"
    assert ket["run"] is None
    assert "không có" in ket["tom_tat"] or "Nên làm" in ket["tom_tat"]


# ── "thu" không được đưa client vào nghiên cứu (không tốn tiền AI) ──────────


def test_che_do_thu_khong_dua_client_vao_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nhan = {}

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", client=object(), on_log=NO_LOG,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
    )
    assert ket["ok"] is True
    assert nhan["client"] is None


def test_che_do_that_dua_dung_client_vao_nghien_cuu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_danh_ba_rong(goc, "K1")  # kênh ĐÃ SỐNG (có danh bạ) — không phải lượt đầu tiên
    nhan = {}
    sentinel = object()

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    chay_mot_ngay(
        goc, "K1", che_do="that", client=sentinel, on_log=NO_LOG,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert nhan["client"] is sentinel


# ── Kênh EM chưa có danh bạ (lượt "một nút" ĐẦU TIÊN) — không đưa ví vào ────


def test_lan_dau_khong_co_danh_ba_thi_khong_dua_vi_vao_nghien_cuu(tmp_path):
    """Kênh mới tách khỏi nhóm chưa có `nghien-cuu/doi-thu.csv` — lượt đầu tiên chấm
    lại cả khối hộp thư mang từ kênh gốc (~300 link), có ví ở đây là 100–200 lượt gọi
    AI cho một kênh còn chưa chắc sống được. Không đưa ví vào, dù `che_do="that"`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nhan = {}
    nhat_ky = []
    sentinel = object()

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    chay_mot_ngay(
        goc, "K1", che_do="that", client=sentinel, on_log=nhat_ky.append,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert nhan["client"] is None
    assert any("chưa có danh bạ" in d for d in nhat_ky), "phải nói rõ bằng tiếng Việt vì sao không đưa ví vào"


def test_lan_sau_da_co_danh_ba_thi_dua_vi_vao_nghien_cuu(tmp_path):
    """Đối chứng: cùng kênh, nhưng ĐÃ có danh bạ (không còn là lượt đầu) — ví vào như
    thường, không bị chặn."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_danh_ba_rong(goc, "K1")
    nhan = {}
    sentinel = object()

    def nghien_cuu_gia(goc_, kenh_, *, client=None, on_log=None, cancel=None):
        nhan["client"] = client

    chay_mot_ngay(
        goc, "K1", che_do="that", client=sentinel, on_log=NO_LOG,
        chay_mot_nut=nghien_cuu_gia,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert nhan["client"] is sentinel


def test_lan_dau_khong_co_danh_ba_nhung_khong_co_client_thi_khong_bao_gio_bao(tmp_path):
    """Không truyền ví (`client=None`) thì dù chưa có danh bạ cũng không có gì để chặn —
    và không cần thêm dòng log giải thích, vì không có ví để "không đưa vào"."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nhat_ky = []

    chay_mot_ngay(
        goc, "K1", che_do="that", client=None, on_log=nhat_ky.append,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert not any("chưa có danh bạ" in d for d in nhat_ky)


# ── Kênh chưa đủ điều kiện thì không sản xuất ───────────────────────────────


def test_kenh_chua_du_dieu_kien_thi_khong_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000)  # đủ ngân sách, nhưng CHƯA sẵn sàng
    moi = [{"link": "https://youtu.be/SSSSSSSSSSS", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert goi_chay_auto.so_lan == 0
    assert ket["ok"] is False
    assert ket["buoc_loi"] == "kiem_kenh"


# ── Idempotent trong ngày: không mở video trả tiền lần hai ──────────────────


def test_chay_lai_trong_ngay_khong_chon_nguon_lan_hai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=1_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/DDDDDDDDDDD", "tieu_de": "video mới", "kenh": "Z"}]
    doc_ds = _dem_goi(_danh_sach_gia(moi))
    hom_nay = _dt.date(2026, 9, 18)

    ket1 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_mot_khau,
    )
    assert ket1["ok"] is True
    assert doc_ds.so_lan == 1
    assert ket1["run"]["san_xuat"]["xong_het"] is False
    ma_luot_1 = ket1["run"]["ma_luot"]

    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0001", True

    ket2 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert doc_ds.so_lan == 1, "không được chọn nguồn mới — đây là chạy tiếp lượt cũ"
    assert ket2["run"]["ma_luot"] == ma_luot_1
    assert ket2["run"]["san_xuat"]["xong_het"] is True
    assert goi_ban_giao, "sản xuất xong hết thì phải thử bàn giao"


# ── Nhặt lại lượt dở từ NGÀY TRƯỚC (không mở video mới) ─────────────────────


def test_tiep_tuc_luot_hong_tu_ngay_truoc(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_qua = _dt.date(2026, 9, 17)
    hom_nay = _dt.date(2026, 9, 18)
    moi = [{"link": "https://youtu.be/MMMMMMMMMMM", "tieu_de": "video hôm qua", "kenh": "Z"}]
    doc_ds = _dem_goi(_danh_sach_gia(moi))

    ket_hom_qua = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_qua, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_mot_khau,  # hỏng dở — chỉ xong khâu đầu
    )
    assert doc_ds.so_lan == 1
    assert ket_hom_qua["run"]["san_xuat"]["xong_het"] is False
    ma_luot_hom_qua = ket_hom_qua["run"]["ma_luot"]

    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0002", True

    ket_hom_nay = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert doc_ds.so_lan == 1, "không được mở video mới khi lượt hôm qua còn dở"
    assert ket_hom_nay["run"]["ma_luot"] == ma_luot_hom_qua
    assert ket_hom_nay["run"]["san_xuat"]["xong_het"] is True
    assert goi_ban_giao

    bc_hom_nay = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert any(r.get("tham_chieu_ma_luot") == ma_luot_hom_qua for r in bc_hom_nay["runs"]), \
        "sổ hôm nay phải có dòng tham chiếu để video_moi_ngay đếm đúng"
    bc_hom_qua = _doc_bao_cao_ngay(goc, "K1", hom_qua.isoformat())
    run_hom_qua_luu = next(r for r in bc_hom_qua["runs"] if r["ma_luot"] == ma_luot_hom_qua)
    assert run_hom_qua_luu["san_xuat"]["xong_het"] is True, "bản chính (ở sổ ngày sinh ra nó) phải cập nhật"


def test_luot_bi_danh_dau_bo_thi_khong_nhat_lai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_qua = _dt.date(2026, 9, 17)
    hom_nay = _dt.date(2026, 9, 18)
    moi_hom_qua = [{"link": "https://youtu.be/NNNNNNNNNNN", "tieu_de": "hôm qua", "kenh": "Z"}]
    chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_qua, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi_hom_qua),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_mot_khau,
    )
    bc = _doc_bao_cao_ngay(goc, "K1", hom_qua.isoformat())
    bc["runs"][0]["bo"] = True
    _ghi_bao_cao_ngay(goc, "K1", hom_qua.isoformat(), bc)

    moi_hom_nay = [{"link": "https://youtu.be/OOOOOOOOOOO", "tieu_de": "video mới hôm nay", "kenh": "Z"}]
    doc_ds2 = _dem_goi(_danh_sach_gia(moi_hom_nay))
    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=doc_ds2,
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=lambda *a, **k: ("GOI", True),
    )
    assert doc_ds2.so_lan == 1, "lượt hôm qua đã bị đánh dấu bỏ — phải chọn nguồn mới"
    assert ket["run"]["nguon"]["ma"] == "OOOOOOOOOOO"


# ── Van ngân sách ────────────────────────────────────────────────────────────


def test_ngan_sach_khong_co_tran_thi_tu_choi_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", voice_id="v1")  # không khai ngan_sach_ngay -> mặc định 0
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/EEEEEEEEEEE", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert ket["ok"] is True  # bị chặn KHÔNG phải lỗi ngoài dự kiến
    assert goi_chay_auto.so_lan == 0, "chưa khai trần thì không được tốn tiền"
    assert ket["run"]["ngan_sach"]["cho_phep"] is False
    assert "ngan_sach_ngay" in ket["run"]["ngan_sach"]["ly_do"]


def test_ngan_sach_vuot_tran_thi_tu_choi_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=1_000, phut_muc_tieu=10, voice_id="v1")  # trần thấp hơn hẳn giá thật
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/FFFFFFFFFFF", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert goi_chay_auto.so_lan == 0
    assert ket["run"]["ngan_sach"]["cho_phep"] is False
    assert ket["run"]["ngan_sach"]["uoc_tinh_vnd"] > 1_000


# ── "thu" không bao giờ sản xuất ─────────────────────────────────────────────


def test_che_do_thu_khong_bao_gio_goi_san_xuat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000)  # trần rất rộng, không phải lý do bị chặn
    moi = [{"link": "https://youtu.be/GGGGGGGGGGG", "tieu_de": "x", "kenh": "Z"}]
    goi_chay_auto = _dem_goi(lambda luot, viec, **k: luot)

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=goi_chay_auto,
    )
    assert goi_chay_auto.so_lan == 0
    assert ket["run"]["nguon"]["ma"] == "GGGGGGGGGGG"


# ── Bàn giao: tu_duyet ───────────────────────────────────────────────────────


def test_ban_giao_tu_duyet_tat_de_trong_ngay_gio(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done", tu_duyet=False,
             voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/HHHHHHHHHHH", "tieu_de": "x", "kenh": "Z"}]
    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0001", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert goi_ban_giao == [("", "")]
    assert ket["run"]["ban_giao"]["da_ban_giao"] is True
    assert ket["run"]["ban_giao"]["ngay_dang"] == ""
    assert ket["run"]["ban_giao"]["ly_do_trong"]


def test_ban_giao_tu_duyet_bat_chon_khe_trong_ke_hoach(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done",
             tu_duyet=True, gio_dang="20:00", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    # Kế hoạch đã có một dòng đúng hôm nay 20:00 -> khe trống tiếp theo là mai.
    ke_hoach_dir = os.path.join(goc, "CHANNEL", "K1", "ke-hoach-dang")
    os.makedirs(ke_hoach_dir, exist_ok=True)
    with open(os.path.join(ke_hoach_dir, "ke-hoach.csv"), "w",
             encoding="utf-8-sig", newline="") as tep:
        tep.write("Mã gói,Ngày đăng,Giờ đăng,Tiêu đề,Mô tả,Thẻ SEO,Link card 1,Link card 2,"
                  "Link card 3,Link card 4,Sẵn sàng,Trạng thái đăng,Ghi chú\n")
        tep.write("X-0001,18/09/2026,20:00,,,,,,,,,,\n")

    moi = [{"link": "https://youtu.be/IIIIIIIIIII", "tieu_de": "x", "kenh": "Z"}]
    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0002", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        # Cố định "bây giờ" — mặc định `datetime.now()` của `_tim_gio_trong`
        # phụ thuộc đồng hồ thật, bài kiểm này chỉ soi luật "khe đã có -> sang
        # ngày kế", không soi luật 60 phút (có bài riêng cho luật đó).
        bay_gio=_dt.datetime(2026, 9, 18, 8, 0),
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert goi_ban_giao == [("19/09/2026", "20:00")]
    assert ket["run"]["ban_giao"]["ngay_dang"] == "19/09/2026"


# ── video_moi_ngay: không tự làm quá số đã khai ─────────────────────────────


def test_du_video_hom_nay_thi_khong_chon_them(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, video_moi_ngay=1, voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    moi = [{"link": "https://youtu.be/LLLLLLLLLLL", "tieu_de": "x", "kenh": "Z"}]
    hom_nay = _dt.date(2026, 9, 18)

    ket1 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=lambda *a, **k: ("GOI", True),
    )
    assert ket1["run"]["san_xuat"]["xong_het"] is True

    ket2 = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_dem_goi(lambda luot, viec, **k: luot),
    )
    assert ket2["run"] is None
    assert "đủ" in ket2["tom_tat"]


# ── kenh_tu_chay / chay_nhieu_kenh ───────────────────────────────────────────


def test_kenh_tu_chay_liet_ke_dung_co_bat(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", tu_chay=True)
    _ghi_kenh(goc, "B", tu_chay=False)
    _ghi_kenh(goc, "C", tu_chay=True)
    assert kenh_tu_chay(goc) == ["A", "C"]


def test_mot_kenh_hong_khong_chan_kenh_sau_trong_tat_ca():
    goi = []

    def gia(goc, kenh, *, client=None, che_do="that", on_log=None, **kw):
        goi.append(kenh)
        if kenh == "A":
            raise RuntimeError("kênh A hỏng")
        return {"ok": True, "tom_tat": kenh + ": xong", "loi": ""}

    bao_cao = chay_nhieu_kenh("goc-gia", ["A", "B", "C"], che_do="that",
                              chay_mot_ngay_fn=gia, on_log=NO_LOG)
    assert goi == ["A", "B", "C"], "một kênh hỏng không được chặn kênh sau"
    assert bao_cao["co_loi"] is True
    assert [d["ok"] for d in bao_cao["ket_qua"]] == [False, True, True]


# ── Khoá một tiến trình mỗi kênh ─────────────────────────────────────────────


def test_khoa_may_chan_luot_thu_hai_truoc_khi_goi_api(tmp_path):
    """Lịch và cú bấm tay không được chạy hai kênh nặng cùng lúc trên VPS."""
    goc = str(tmp_path)
    ok, ly_do = giu_khoa_may(goc)
    assert ok is True and ly_do == ""
    try:
        ok_hai, ly_do_hai = giu_khoa_may(goc, con_song=lambda _pid: True)
        assert ok_hai is False
        assert "bỏ qua để không quá tải" in ly_do_hai
    finally:
        nha_khoa_may(goc)
    assert not os.path.exists(os.path.join(goc, "workspace", "tu-chay", ".khoa-may"))


def test_khoa_may_cua_pid_da_chet_duoc_gianh_lai(tmp_path):
    goc = str(tmp_path)
    duong = os.path.join(goc, "workspace", "tu-chay", ".khoa-may")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time()}, tep)
    ok, _ly_do = giu_khoa_may(goc, con_song=lambda _pid: False)
    assert ok is True
    nha_khoa_may(goc)
    assert not os.path.exists(duong)


def test_khoa_dang_giu_boi_tien_trinh_song_thi_tu_choi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    duong_khoa = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time()}, tep)

    goi_nghien_cuu = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=goi_nghien_cuu,
        khoa_pid_con_song=lambda pid: True,  # giả vờ PID 999999 còn sống
    )
    assert ket["ok"] is False
    assert ket["buoc_loi"] == "khoa"
    assert goi_nghien_cuu.so_lan == 0, "khoá còn giữ thì không được đụng gì tới nghiên cứu"
    assert os.path.isfile(duong_khoa), "khoá của tiến trình khác không được đụng vào"


def test_khoa_pid_chet_thi_gianh_lai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    duong_khoa = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time()}, tep)

    goi_nghien_cuu = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=goi_nghien_cuu,
        doc_danh_sach=_danh_sach_gia([]),
        khoa_pid_con_song=lambda pid: False,  # PID coi như đã chết
    )
    assert ket["ok"] is True
    assert goi_nghien_cuu.so_lan == 1
    assert not os.path.isfile(duong_khoa), "khoá phải được nhả sau khi chạy xong"


def test_khoa_qua_12_gio_thi_gianh_lai_du_pid_con_song(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    duong_khoa = os.path.join(goc, "CHANNEL", "K1", "tu-chay", ".khoa")
    os.makedirs(os.path.dirname(duong_khoa), exist_ok=True)
    with open(duong_khoa, "w", encoding="utf-8") as tep:
        json.dump({"pid": 999999, "bat_dau": time.time() - 13 * 3600}, tep)

    goi_nghien_cuu = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=goi_nghien_cuu,
        doc_danh_sach=_danh_sach_gia([]),
        khoa_pid_con_song=lambda pid: True,  # còn sống, nhưng khoá đã quá 12 giờ
    )
    assert ket["ok"] is True
    assert goi_nghien_cuu.so_lan == 1


# ── `--tat-ca`: đồng bộ nhóm trước khi chạy ──────────────────────────────────


def test_dong_bo_nhom_goi_dung_moi_nhom_mot_lan(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="grp1")
    _ghi_kenh(goc, "B", nhom="grp1")
    _ghi_kenh(goc, "C")               # không khai nhóm -> phải bị bỏ qua
    _ghi_kenh(goc, "D", nhom="grp2")

    dong_bo_goi, ghi_bang_goi = [], []

    def dong_bo_gia(g, n):
        dong_bo_goi.append(n)
        return {"kenh": 2, "link_them": 1, "trang_chu_them": 0}

    def ghi_bang_gia(g, n):
        ghi_bang_goi.append(n)
        return "duong-gia"

    ra = dong_bo_nhom_truoc_khi_chay(
        goc, ["A", "B", "C", "D"], on_log=NO_LOG,
        dong_bo_doi_thu_fn=dong_bo_gia, ghi_bang_nhom_fn=ghi_bang_gia)

    assert dong_bo_goi == ["grp1", "grp2"], "mỗi nhóm chỉ một lượt, dù có nhiều kênh cùng nhóm"
    assert ghi_bang_goi == ["grp1", "grp2"]
    assert ra == ["grp1", "grp2"]


def test_dong_bo_nhom_mot_nhom_hong_khong_chan_nhom_khac(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "A", nhom="hong")
    _ghi_kenh(goc, "B", nhom="on")

    ghi_bang_goi = []

    def dong_bo_gia(g, n):
        if n == "hong":
            raise RuntimeError("CSV kẹt")
        return {"kenh": 1, "link_them": 0, "trang_chu_them": 0}

    ra = dong_bo_nhom_truoc_khi_chay(
        goc, ["A", "B"], on_log=NO_LOG, dong_bo_doi_thu_fn=dong_bo_gia,
        ghi_bang_nhom_fn=lambda g, n: ghi_bang_goi.append(n))

    assert ghi_bang_goi == ["hong", "on"], "nhóm lỗi ở đồng bộ đối thủ vẫn phải thử ghi bảng"
    assert ra == ["hong", "on"], "nhóm hỏng vẫn tính là đã thử — không chặn nhóm sau"


# ── `--tat-ca`: sổ ngày dùng chung cho cả máy ────────────────────────────────


def test_ghi_bao_cao_tat_ca_noi_them_khong_ghi_de(tmp_path):
    goc = str(tmp_path)
    duong_md, duong_json = ghi_bao_cao_tat_ca(goc, "2026-09-18", {
        "luc": "2026-09-18T02:00:00", "che_do": "that",
        "ket_qua": [{"kenh": "A", "ok": True, "tom_tat": "A: xong", "loi": ""}],
        "tong_uoc_vnd": 90000, "nhom_dong_bo": ["grp1"]})
    duong_md2, duong_json2 = ghi_bao_cao_tat_ca(goc, "2026-09-18", {
        "luc": "2026-09-18T14:00:00", "che_do": "thu",
        "ket_qua": [{"kenh": "B", "ok": False, "tom_tat": "B: lỗi", "loi": "x"}],
        "tong_uoc_vnd": 0, "nhom_dong_bo": []})
    assert duong_md == duong_md2 and duong_json == duong_json2

    with open(duong_json, "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 2, "gọi hai lần trong ngày phải GIỮ CẢ HAI lượt"
    assert so["runs"][0]["luc"] == "2026-09-18T02:00:00"
    assert so["runs"][1]["luc"] == "2026-09-18T14:00:00"

    with open(duong_md, "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "A: xong" in chu and "B: lỗi" in chu
    assert "Lượt 1" in chu and "Lượt 2" in chu
    assert duong_json == duong_bao_cao_tat_ca(goc, "2026-09-18", "json")


# ── `--tat-ca`: chay_tat_ca gộp cả ba việc ───────────────────────────────────


def test_chay_tat_ca_dong_bo_nhom_chay_kenh_va_ghi_so(tmp_path):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi_kenh(goc, ma, ngan_sach_ngay=1_000_000, thu_muc_done="done", voice_id="v1", nhom="grp")
        _lam_kenh_san_sang(goc, ma)
    moi = [{"link": "https://youtu.be/PPPPPPPPPPP", "tieu_de": "x", "kenh": "Z"}]
    hom_nay = _dt.date(2026, 9, 18)

    dong_bo_goi, ghi_bang_goi = [], []

    bao_cao = chay_tat_ca(
        goc, che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        danh_sach_kenh=["K1", "K2"],
        dong_bo_doi_thu_fn=lambda g, n: dong_bo_goi.append(n) or {
            "kenh": 2, "link_them": 0, "trang_chu_them": 0},
        ghi_bang_nhom_fn=lambda g, n: ghi_bang_goi.append(n),
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=lambda *a, **k: ("GOI", True),
    )

    assert dong_bo_goi == ["grp"], "hai kênh cùng nhóm -> chỉ một lượt đồng bộ"
    assert ghi_bang_goi == ["grp"]
    assert bao_cao["danh_sach"] == ["K1", "K2"]
    assert bao_cao["nhom_dong_bo"] == ["grp"]
    assert [d["ok"] for d in bao_cao["ket_qua"]] == [True, True]
    assert bao_cao["co_loi"] is False
    assert bao_cao["tong_uoc_vnd"] > 0, "cả hai kênh đều sản xuất thật -> phải có chi phí ước tính"

    with open(bao_cao["duong_bao_cao_json"], "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 1
    assert so["runs"][0]["tong_uoc_vnd"] == bao_cao["tong_uoc_vnd"]
    with open(bao_cao["duong_bao_cao_md"], "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "K1" in chu and "K2" in chu


def test_chay_tat_ca_khong_co_kenh_van_ghi_so_rong(tmp_path):
    goc = str(tmp_path)
    hom_nay = _dt.date(2026, 9, 18)
    bao_cao = chay_tat_ca(goc, che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
                          danh_sach_kenh=[])
    assert bao_cao["ket_qua"] == []
    assert bao_cao["co_loi"] is False
    with open(duong_bao_cao_tat_ca(goc, hom_nay.isoformat(), "json"), "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 1
    assert so["runs"][0]["ket_qua"] == []


def test_chay_tat_ca_hai_lan_trong_ngay_giu_ca_hai_luot(tmp_path):
    goc = str(tmp_path)
    hom_nay = _dt.date(2026, 9, 18)
    for _ in range(2):
        chay_tat_ca(goc, che_do="thu", hom_nay=hom_nay, on_log=NO_LOG, danh_sach_kenh=[])
    with open(duong_bao_cao_tat_ca(goc, hom_nay.isoformat(), "json"), "r", encoding="utf-8") as tep:
        so = json.load(tep)
    assert len(so["runs"]) == 2


# ── `--tat-ca`: log ra đĩa vì pythonw không có console ───────────────────────


def test_bo_log_tat_ca_ghi_dong_va_khong_vo_khi_khong_co_console(tmp_path, monkeypatch):
    import core.tu_chay as tu_chay_mod

    goc = str(tmp_path)
    monkeypatch.setattr(tu_chay_mod.sys, "stdout", None)  # giả pythonw không có console
    log = tu_chay_mod.bo_log_tat_ca(goc)
    log("dòng đầu")   # không được ném dù không có console để in
    log("dòng hai")
    with open(tu_chay_mod.duong_log_tat_ca(goc), "r", encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert "dòng đầu" in noi_dung and "dòng hai" in noi_dung


def test_bo_log_tat_ca_xoay_khi_qua_gioi_han(tmp_path):
    import core.tu_chay as tu_chay_mod

    goc = str(tmp_path)
    duong = tu_chay_mod.duong_log_tat_ca(goc)
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with open(duong, "w", encoding="utf-8") as tep:
        tep.write("X" * 1000 + "\n")

    log = tu_chay_mod.bo_log_tat_ca(goc, gioi_han_byte=100, in_console=False)
    log("dòng mới sau khi xoay")

    with open(duong, "r", encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert "X" * 1000 not in noi_dung
    assert "dòng mới sau khi xoay" in noi_dung


# ── Khe đăng phải cách "bây giờ" ít nhất 60 phút (không đặt lịch vào quá khứ) ─


def test_tim_gio_trong_xong_som_thi_dang_duoc_ngay_hom_nay(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 10, 0)  # xong lúc 10:00, giờ đăng 20:00 -> còn 10 tiếng
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("18/09/2026", "20:00")


def test_tim_gio_trong_xong_qua_sat_gio_dang_thi_sang_ngay_mai(tmp_path):
    """Sản xuất tốn 2–4 tiếng và `--tat-ca` chạy các kênh lần lượt — kênh có thể
    bàn giao xong SAU cả giờ đăng hôm nay của chính nó. Đặt lịch vào một mốc đã
    trôi qua (hoặc còn dưới 60 phút, không kịp chuẩn bị) là đặt vào chỗ vô ích."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 19, 30)  # còn 30 phút tới 20:00 — dưới mốc an toàn
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("19/09/2026", "20:00")


def test_tim_gio_trong_xong_sau_gio_dang_thi_sang_ngay_mai(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 23, 0)  # xong lúc 23:00 — giờ đăng 20:00 đã trôi qua
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("19/09/2026", "20:00")


def test_tim_gio_trong_khe_da_co_thi_sang_ngay_ke_tiep(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    ke_hoach_dir = os.path.join(goc, "CHANNEL", "K1", "ke-hoach-dang")
    os.makedirs(ke_hoach_dir, exist_ok=True)
    with open(os.path.join(ke_hoach_dir, "ke-hoach.csv"), "w",
             encoding="utf-8-sig", newline="") as tep:
        tep.write("Mã gói,Ngày đăng,Giờ đăng,Tiêu đề,Mô tả,Thẻ SEO,Link card 1,Link card 2,"
                  "Link card 3,Link card 4,Sẵn sàng,Trạng thái đăng,Ghi chú\n")
        tep.write("X-0001,18/09/2026,20:00,,,,,,,,,,\n")
        tep.write("X-0002,19/09/2026,20:00,,,,,,,,,,\n")
    hom_nay = _dt.date(2026, 9, 18)
    bay_gio = _dt.datetime(2026, 9, 18, 8, 0)  # sớm — không phải luật 60 phút chặn ở đây
    assert _tim_gio_trong(goc, "K1", "20:00", hom_nay, bay_gio=bay_gio) == ("20/09/2026", "20:00")


def test_chay_mot_ngay_bay_gio_qua_muon_thi_ban_giao_dat_lich_ngay_mai(tmp_path):
    """`chay_mot_ngay` phải truyền đúng `bay_gio` xuống `_tim_gio_trong`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, thu_muc_done="done",
             tu_duyet=True, gio_dang="20:00", voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_nay = _dt.date(2026, 9, 18)
    moi = [{"link": "https://youtu.be/QQQQQQQQQQQ", "tieu_de": "x", "kenh": "Z"}]
    goi_ban_giao = []

    def ban_giao_gia(goc_, kenh_, luot_, thu_muc_done_, ngay="", gio=""):
        goi_ban_giao.append((ngay, gio))
        return "GOI-0003", True

    ket = chay_mot_ngay(
        goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
        bay_gio=_dt.datetime(2026, 9, 18, 23, 0),  # xong lúc 23:00 — đã qua giờ đăng 20:00
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set(),
        dung_viec=lambda bc: {},
        chay_auto=_chay_auto_het,
        ban_giao=ban_giao_gia,
    )
    assert goi_ban_giao == [("19/09/2026", "20:00")]
    assert ket["run"]["ban_giao"]["ngay_dang"] == "19/09/2026"


# ── Sổ ngày ghi giờ bắt đầu/kết thúc từng kênh (`--tat-ca` trải dài nhiều giờ) ─


def test_chay_nhieu_kenh_ghi_bat_dau_ket_thuc_moi_kenh():
    def gia(goc, kenh, *, client=None, che_do="that", on_log=None, **kw):
        return {"ok": True, "tom_tat": kenh + ": xong", "loi": ""}

    bao_cao = chay_nhieu_kenh("goc-gia", ["A", "B"], che_do="that", chay_mot_ngay_fn=gia,
                              on_log=NO_LOG)
    for d in bao_cao["ket_qua"]:
        assert d["bat_dau"] and d["ket_thuc"]
        assert d["bat_dau"] <= d["ket_thuc"]


def test_bao_cao_tat_ca_md_hien_khoang_gio_tung_kenh(tmp_path):
    goc = str(tmp_path)
    duong_md, _ = ghi_bao_cao_tat_ca(goc, "2026-09-18", {
        "luc": "2026-09-18T02:00:00", "che_do": "that",
        "ket_qua": [{"kenh": "K1", "ok": True, "tom_tat": "K1: xong",
                    "loi": "", "bat_dau": "2026-09-18T02:00:03", "ket_thuc": "2026-09-18T04:41:10"}],
        "tong_uoc_vnd": 90000, "nhom_dong_bo": []})
    with open(duong_md, "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "02:00:03" in chu and "04:41:10" in chu


# ── V7 SWITCH: kênh EM có "tep" chỉ dùng V7 khi đã qua da_co_video_thang ────


def test_v7_tep_em_chua_qua_nguong_thi_dung_bang_mot_nut_khong_cham_v7(tmp_path):
    """Kênh EM (`nhom_kenh.tao_kenh_trong_nhom` gieo `cong-thuc-v7.json` có khoá "tep"
    NGAY NGÀY ĐẦU) nhưng CHƯA có video thắng thật (không có `chi-so/`) — có tệp cấu
    hình không đủ, phải rơi về bảng Một nút, và KHÔNG được gọi `cham_v7` (tốn công vô
    ích — sổ content chưa chắc đã quét)."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_cong_thuc_v7(goc, "K1", tep="mot-tep-nao-do")  # có "tep", chưa có chi-so/

    goi_cham_v7 = _dem_goi(lambda g, k: _KetQuaV7Gia([]))
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=goi_cham_v7,
        doc_danh_sach=_danh_sach_gia_day_du(
            moi=[_dong_de_xuat("https://youtu.be/YYYYYYYYYYY", tieu_de="chọn qua Một nút")]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert goi_cham_v7.so_lan == 0, "kênh EM chưa qua ngưỡng da_co_video_thang thì KHÔNG được dùng V7"
    assert ket["run"]["nguon"]["nguon"] == "mot_nut"
    assert ket["run"]["nguon"]["ma"] == "YYYYYYYYYYY"


def test_v7_tep_em_da_qua_nguong_thi_dung_v7(tmp_path):
    """Cùng kênh EM có "tep", nhưng lần này ĐÃ đạt ngưỡng `da_co_video_thang` (impressions
    ở mốc 48h + có bảng đề xuất) — phải dùng V7, không rơi về bảng Một nút."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_cong_thuc_v7(goc, "K1", tep="mot-tep-nao-do")
    # `raw/` TRƯỚC `tong-quan.json` — đúng thứ tự thật (Studio chụp raw rồi mới giải
    # mã ra tong-quan.json). Viết NGƯỢC (tong-quan trước, raw sau) làm `tong-quan.json`
    # có mtime CŨ hơn `raw/join_1.json` cạnh nó, và từ khi `core.vong_hoc` (Việc 3,
    # 28/09/2026) gọi `chi_so_ytb.doc_kenh` sớm hơn trong cùng chu kỳ, `_giai_ma_con_thieu`
    # coi tong-quan.json là "chưa giải mã kịp" rồi ÂM THẦM GHI ĐÈ nó bằng bản giải mã lại
    # từ `join_1.json` (chỉ có `href`, không có impressions/ctr) — xoá mất số liệu bài
    # kiểm này cố tình dựng, khiến `da_co_video_thang` luôn thấy `impressions=None` và
    # ngỡ kênh CHƯA đạt ngưỡng V7. Xác nhận bằng tay (không suy đoán): gọi thẳng
    # `chi_so_ytb.doc_kenh` trên đúng fixture cũ tái hiện đúng lỗi này.
    raw = os.path.join(goc, "CHANNEL", "K1", "chi-so", "aaaaaaaaaaa", "48h", "raw", "join_1.json")
    os.makedirs(os.path.dirname(raw), exist_ok=True)
    with open(raw, "w", encoding="utf-8") as tep:
        json.dump({"href": "https://x?ddr_value=YT_RELATED&dimension=TRAFFIC_SOURCE_DETAIL"}, tep)
    _tong_quan_that(goc, "K1", "aaaaaaaaaaa", "48h", impressions=25000, ctr=1.0, avd_pct=1.0)

    con_moi = _DongV7Gia("KKKKKKKKKKK", "https://youtu.be/KKKKKKKKKKK", tieu_de="chọn qua V7")
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([con_moi]),
        doc_danh_sach=_danh_sach_gia_day_du(
            moi=[_dong_de_xuat("https://youtu.be/ZZZZZZZZZZZ", tieu_de="không được chọn cái này")]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["nguon"] == "v7"
    assert ket["run"]["nguon"]["ma"] == "KKKKKKKKKKK"


def test_v7_khong_co_tep_giu_hanh_vi_cu_chi_can_co_tep_cau_hinh(tmp_path):
    """Đối chứng: kênh KHÔNG có "tep" trong cấu hình (như TL4-T7 — tự tay khai V7) —
    hành vi CŨ không đổi: chỉ cần tệp cấu hình tồn tại là dùng V7 ngay, không đòi
    `da_co_video_thang`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_cong_thuc_v7(goc, "K1")  # {} — không có "tep"

    con_moi = _DongV7Gia("LLLLLLLLLLL", "https://youtu.be/LLLLLLLLLLL", tieu_de="chọn qua V7")
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        cham_v7=lambda g, k: _KetQuaV7Gia([con_moi]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["nguon"] == "v7"
    assert ket["run"]["nguon"]["ma"] == "LLLLLLLLLLL"


# ── BOOTSTRAP: xếp hạng theo sức nổ khi gộp moi ∪ vuot ∪ but (kênh chưa có V7) ─


def test_bootstrap_uu_tien_view_100k_bat_ke_vuot_hay_tang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    manh = _dong_de_xuat("https://youtu.be/AAAAAAAAAA1", tieu_de="mạnh", view=150_000, vuot=2, tang=10)
    vuot_cao = _dong_de_xuat("https://youtu.be/BBBBBBBBBB1", tieu_de="vượt cao nhưng view thấp",
                             view=90_000, vuot=30, tang=5000)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(moi=[vuot_cao], vuot=[manh]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "AAAAAAAAAA1", "view ≥ 100.000 phải thắng dù vượt/tăng thấp hơn"


def test_bootstrap_hoa_view_manh_thi_xep_theo_vuot_da_chan_tran(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    a = _dong_de_xuat("https://youtu.be/CCCCCCCCCC1", tieu_de="vượt cao", view=200_000, vuot=25, tang=100)
    b = _dong_de_xuat("https://youtu.be/DDDDDDDDDD1", tieu_de="tăng cao", view=110_000, vuot=10, tang=9999)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(but=[a, b]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "CCCCCCCCCC1", \
        "cùng qua mốc 100k thì xếp theo vượt (chặn trần 25) trước tăng/ngày"


def test_bootstrap_gop_va_khu_trung_theo_link_uu_tien_bang_moi(tmp_path):
    """Cùng một link xuất hiện ở nhiều bảng (`moi`/`vuot`/`but`) chỉ tính MỘT lần —
    lấy đúng bản ở bảng ưu tiên cao nhất (moi > vuot > but), không cộng dồn hay lấy
    bản "mạnh" giả ở bảng khác."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    link = "https://youtu.be/EEEEEEEEEE1"
    trong_moi = _dong_de_xuat(link, tieu_de="bản ở MỚI", view=1_000, vuot=1, tang=1)
    trong_vuot = _dong_de_xuat(link, tieu_de="bản ở VƯỢT (không được dùng)", view=999_999, vuot=999, tang=999)
    khac = _dong_de_xuat("https://youtu.be/FFFFFFFFFF1", tieu_de="ứng viên khác mạnh hơn hẳn",
                         view=500_000, vuot=1, tang=1)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(moi=[trong_moi], vuot=[trong_vuot], but=[khac]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "FFFFFFFFFF1"
    assert ket["run"]["nguon"]["tieu_de"] == "ứng viên khác mạnh hơn hẳn"


def test_bootstrap_loai_tru_ap_dung_ca_o_vuot_va_but(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    nc = os.path.join(goc, "CHANNEL", "K1", "nghien-cuu")
    os.makedirs(nc, exist_ok=True)
    with open(os.path.join(nc, "da-lam.txt"), "w", encoding="utf-8") as tep:
        tep.write("IIIIIIIIII1 | đã làm\n")

    da_lam_row = _dong_de_xuat("https://youtu.be/IIIIIIIIII1", tieu_de="đã làm rồi", view=999_999)
    con_lai = _dong_de_xuat("https://youtu.be/JJJJJJJJJJ1", tieu_de="còn mới", view=1_000)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(vuot=[da_lam_row], but=[con_lai]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    assert ket["run"]["nguon"]["ma"] == "JJJJJJJJJJ1"


def test_bootstrap_ly_do_noi_view_vuot_tang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    d = _dong_de_xuat("https://youtu.be/MMMMMMMMMM1", tieu_de="x", view=150_000, vuot=3.2, tang=4200)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia_day_du(moi=[d]),
        video_da_lam_nhom=lambda g, k: set(),
    )
    ly_do = " ".join(ket["run"]["nguon"]["ly_do"])
    assert "150.000" in ly_do or "150000" in ly_do
    assert "3,2" in ly_do or "3.2" in ly_do
    assert "4.200" in ly_do or "4200" in ly_do


# ── DỌN ĐĨA trong `--tat-ca` (sau vòng sản xuất, trước khi ghi sổ ngày) ──────


def test_chay_tat_ca_don_dep_tung_kenh_va_gop_vao_so_ngay(tmp_path):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi_kenh(goc, ma)
    hom_nay = _dt.date(2026, 9, 18)
    goi_don = []

    def don_gia(g, ma):
        goi_don.append(ma)
        so_byte = {"K1": 5_000_000, "K2": 0}[ma]
        return {"kenh": ma, "chay": True, "tong_bytes": so_byte, "ung_vien": []}

    bao_cao = chay_tat_ca(
        goc, che_do="thu", hom_nay=hom_nay, on_log=NO_LOG,
        danh_sach_kenh=["K1", "K2"],
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
        don_theo_cai_dat_fn=don_gia,
    )
    assert goi_don == ["K1", "K2"], "dọn đĩa chạy SAU vòng sản xuất, lần lượt từng kênh"
    assert bao_cao["don_dep"]["theo_kenh"] == {"K1": 5_000_000, "K2": 0}
    assert bao_cao["don_dep"]["tong_bytes"] == 5_000_000

    with open(bao_cao["duong_bao_cao_json"], "r", encoding="utf-8") as tep:
        so_ = json.load(tep)
    assert so_["runs"][0]["don_dep"]["tong_bytes"] == 5_000_000
    assert so_["runs"][0]["don_dep"]["theo_kenh"] == {"K1": 5_000_000, "K2": 0}
    with open(bao_cao["duong_bao_cao_md"], "r", encoding="utf-8") as tep:
        chu = tep.read()
    assert "dọn đĩa" in chu.lower() and "K1" in chu


def test_chay_tat_ca_mot_kenh_don_hong_khong_chan_kenh_khac_va_khong_tinh_la_loi(tmp_path):
    goc = str(tmp_path)
    for ma in ("K1", "K2"):
        _ghi_kenh(goc, ma)
    hom_nay = _dt.date(2026, 9, 18)

    def don_gia(g, ma):
        if ma == "K1":
            raise RuntimeError("đĩa bận")
        return {"kenh": ma, "chay": True, "tong_bytes": 100, "ung_vien": []}

    bao_cao = chay_tat_ca(
        goc, che_do="thu", hom_nay=hom_nay, on_log=NO_LOG,
        danh_sach_kenh=["K1", "K2"],
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set(),
        don_theo_cai_dat_fn=don_gia,
    )
    assert bao_cao["don_dep"]["theo_kenh"] == {"K2": 100}, "K1 dọn hỏng thì bỏ qua, không ghi bừa"
    assert bao_cao["don_dep"]["tong_bytes"] == 100
    assert bao_cao["co_loi"] is False, "dọn đĩa hỏng không được coi là lượt --tat-ca lỗi"


def test_chay_tat_ca_khong_don_dep_thi_van_ghi_so_khong_bytes(tmp_path):
    """Không có kênh nào tự chạy — nhánh sổ rỗng vẫn phải mang khoá `don_dep` (dạng
    nhất quán), dù bằng 0."""
    goc = str(tmp_path)
    hom_nay = _dt.date(2026, 9, 18)
    bao_cao = chay_tat_ca(goc, che_do="that", hom_nay=hom_nay, on_log=NO_LOG, danh_sach_kenh=[])
    assert bao_cao["don_dep"] == {"theo_kenh": {}, "tong_bytes": 0}
    with open(duong_bao_cao_tat_ca(goc, hom_nay.isoformat(), "json"), "r", encoding="utf-8") as tep:
        so_ = json.load(tep)
    assert so_["runs"][0]["don_dep"] == {"theo_kenh": {}, "tong_bytes": 0}


# ── Nhịp đăng: không tích video, chốt nội dung gần lịch ────────────────────


def test_con_video_cho_dang_thi_khong_nghien_cuu_khong_mo_luot_moi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", chu_ky_dang_ngay=2, san_xuat_truoc_gio=24,
              gio_dang="20:00")
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0001", "Sẵn sàng": "x"})
    goi = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 25),
        bay_gio=_dt.datetime(2026, 9, 25, 10), on_log=NO_LOG,
        chay_mot_nut=goi, doc_danh_sach=_danh_sach_gia([]))
    assert ket["ok"] is True
    assert goi.so_lan == 0
    assert "chờ đăng" in ket["tom_tat"]
    # V2-tối-giản: đây là ca "máy đứng im CHỜ NGƯỜI", không phải "không có gì
    # phải làm" — xem `core.tu_chay._cua_so_san_xuat`/`finalize`.
    assert ket["cho_nguoi"] is True
    assert _doc_bao_cao_ngay(goc, "K1", "2026-09-25")["runs"] == []


def test_chi_chot_nguon_trong_24_gio_truoc_lich_dang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", chu_ky_dang_ngay=2, san_xuat_truoc_gio=24,
              gio_dang="20:00")
    _ghi_ke_hoach(
        goc, "K1", **{"Mã gói": "K1-0001", "Ngày đăng": "24/09/2026",
                       "Giờ đăng": "20:00", "Trạng thái đăng": "ĐÃ ĐĂNG (tay)"})
    goi = _dem_goi(lambda *a, **k: None)
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 25),
        bay_gio=_dt.datetime(2026, 9, 25, 10), on_log=NO_LOG,
        chay_mot_nut=goi, doc_danh_sach=_danh_sach_gia([]))
    assert goi.so_lan == 0
    assert "chọn nguồn từ 25/09 20:00" in ket["tom_tat"]

    ket2 = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 25),
        bay_gio=_dt.datetime(2026, 9, 25, 20, 1), on_log=NO_LOG,
        chay_mot_nut=goi, doc_danh_sach=_danh_sach_gia([]))
    assert ket2["ok"] is True
    assert goi.so_lan == 1


def test_dang_tay_ghi_gio_that_va_xoa_co_san_sang(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_ke_hoach(
        goc, "K1", **{"Mã gói": "K1-0001", "Ngày đăng": "01/01/2020",
                       "Giờ đăng": "08:00", "Sẵn sàng": "x"})
    luc = _dt.datetime(2026, 9, 25, 14, 35)
    assert ban_giao_dang.danh_dau_dang_tay(goc, "K1", "K1-0001", bay_gio=luc)
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    dong = dict(zip(cot, hang[0]))
    assert dong["Ngày đăng"] == "25/09/2026"
    assert dong["Giờ đăng"] == "14:35"
    assert dong["Sẵn sàng"] == ""
    assert dong["Trạng thái đăng"] == "ĐÃ ĐĂNG (tay)"


def test_sap_dot_ngot_van_checkpoint_de_lan_sau_tu_nhat_lai(tmp_path):
    import pytest

    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", ngan_sach_ngay=100_000_000, voice_id="v1")
    _lam_kenh_san_sang(goc, "K1")
    hom_nay = _dt.date(2026, 9, 25)
    moi = [{"link": "https://youtu.be/CRASH000001", "tieu_de": "nguồn đã chốt", "kenh": "Z"}]

    def sap_dot_ngot(*_a, **_k):
        raise KeyboardInterrupt("giả lập Windows hạ tiến trình")

    with pytest.raises(KeyboardInterrupt):
        chay_mot_ngay(
            goc, "K1", che_do="that", hom_nay=hom_nay, on_log=NO_LOG,
            chay_mot_nut=lambda *a, **k: None,
            doc_danh_sach=_danh_sach_gia(moi),
            video_da_lam_nhom=lambda g, k: set(), dung_viec=lambda bc: {},
            chay_auto=sap_dot_ngot)

    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert len(bc["runs"]) == 1
    ma_luot = bc["runs"][0]["ma_luot"]
    assert bc["runs"][0]["nguon"]["link"].endswith("CRASH000001")
    assert _tim_run_chua_xong(goc, "K1", hom_nay) == (hom_nay.isoformat(), ma_luot)
def test_nguon_da_chot_duoc_dung_truoc_cong_thuc_tu_dong(tmp_path):
    from core import chon_content as cc
    from core import tu_chay as tc

    uv = cc.UngVien(
        cc.LUONG_DOI_THU, "AAAAAAAAAAA", "Nguồn đã chốt", "Đối thủ A",
        "https://youtu.be/AAAAAAAAAAA", 91, "Ưu tiên", "đang tăng nhanh")
    cc.chot(str(tmp_path), "K1", uv)
    log = []

    def khong_duoc_goi(*_a, **_k):
        raise AssertionError("đã chốt tay thì không được chấm lại")

    ket = tc._chon_nguon(
        str(tmp_path), "K1", False, set(), cham_v7=khong_duoc_goi,
        doc_danh_sach=khong_duoc_goi, log=log.append)
    assert ket["ma"] == "AAAAAAAAAAA"
    assert ket["chon_tay"] is True
    assert cc.doc_lua_chon(str(tmp_path), "K1").trang_thai == "đang sản xuất"
    assert any("content đã chốt" in dong for dong in log)


# ═══════════════════════════════════════════════════════════════════════════
# Vá "lượt kẹt tự xử lý" (chẩn đoán 26/09/2026, xem
# workspace/KE-HOACH-GIA-CO-1-NAM.md, mục "Vá lượt dở (L1-L5)"):
#
#   L1 — lượt MỒ CÔI (có trang-thai.json, không có trong sổ) được nhận nuôi.
#   L2 — video đã dựng xong (khâu `dung`) không bị nhặt lại chỉ vì thumbnail hỏng.
#   L3 — trần tự phục hồi: quá 3 lần / 48 giờ / lỗi lặp lại / sắp lọt cửa sổ
#        quét thì tự BỎ, không remake mãi.
#   L4 — nhãn báo cáo dọn dùng ĐÚNG lý do đã xoá, không đoán bừa.
#   V2-tối-giản — cửa gói chờ đăng báo "[CHỜ NGƯỜI]", không còn "[OK]".
# ═══════════════════════════════════════════════════════════════════════════


def _tao_luot_mo_coi(goc, ma_kenh, ma_luot, *, link="https://youtu.be/ORPHAN00001",
                     tao_luc=None):
    """Dựng một thư mục lượt CÓ `trang-thai.json` (khâu đầu còn "dang" — đúng
    dấu vết một tiến trình bị giết giữa chừng) nhưng KHÔNG ghi vào sổ ngày nào
    — giả lập đúng ca TL1-T7/0003 + 0004 (24/09/2026, chẩn đoán L1)."""
    luot = auto.moi_luot(goc, ma_kenh, ma_luot, {"link": link, "tieu_de": "", "chu_bia": ""})
    if tao_luc is not None:
        luot.tao_luc = tao_luc
    luot.tt("kich-ban").trang_thai = auto.DANG
    luot.tt("kich-ban").bat_dau = tao_luc or time.time()
    auto.ghi_luot(luot)
    return luot


# ── L1: nhận con nuôi lượt mồ côi ────────────────────────────────────────────


def test_l1_luot_mo_coi_khong_trong_so_duoc_nhin_thay_lai(tmp_path):
    """Đúng ca TL1-T7/0003+0004: lượt có `trang-thai.json` nhưng KHÔNG có dòng
    nào trong sổ 7 ngày gần đây phải được `_tim_run_chua_xong` NHÌN THẤY LẠI —
    không còn bị quên im lặng chỉ vì tiến trình sinh ra nó bị giết trước khi
    kịp ghi sổ."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 26)
    _tao_luot_mo_coi(goc, "K1", "0003", link="https://youtu.be/ORPHAN00003",
                     tao_luc=_dt.datetime(2026, 9, 24, 10).timestamp())

    assert _tim_run_chua_xong(goc, "K1", hom_nay) == (hom_nay.isoformat(), "0003")

    # Một dòng "nhận con nuôi" đã được ghi vào sổ HÔM NAY, nguồn lấy từ
    # `dau_vao.link` của chính lượt trên đĩa (đúng chẩn đoán chỉ ra).
    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert len(bc["runs"]) == 1
    run = bc["runs"][0]
    assert run["ma_luot"] == "0003"
    assert run["nhan_nuoi"] is True
    assert run["nguon"]["link"].endswith("ORPHAN00003")
    assert not run.get("bo")


def test_l1_hai_luot_mo_coi_nhan_nuoi_cu_nhat_truoc(tmp_path):
    """TL1-T7 có CẢ 0003 lẫn 0004 mồ côi cùng lúc — chỉ nhận nuôi lượt CŨ NHẤT
    trước (đúng nhịp "một video một lúc"); lượt còn lại chờ lần gọi sau."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 26)
    _tao_luot_mo_coi(goc, "K1", "0004", tao_luc=_dt.datetime(2026, 9, 24, 20).timestamp())
    _tao_luot_mo_coi(goc, "K1", "0003", tao_luc=_dt.datetime(2026, 9, 24, 10).timestamp())

    assert _tim_run_chua_xong(goc, "K1", hom_nay) == (hom_nay.isoformat(), "0003")
    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert [r["ma_luot"] for r in bc["runs"]] == ["0003"]

    # 0003 giờ đã có dòng trong sổ nên nó chiếm đúng vai "lượt dở" — 0004 CHƯA
    # được nhận nuôi (đúng nhịp "một video một lúc"). Chỉ khi 0003 xong/bị bỏ
    # (L3) thì lần gọi SAU mới tới lượt 0004 — giả lập bằng cách đánh dấu bỏ.
    bc["runs"][0]["bo"] = True
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)
    assert _tim_run_chua_xong(goc, "K1", hom_nay) == (hom_nay.isoformat(), "0004")
    bc2 = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert sorted(r["ma_luot"] for r in bc2["runs"]) == ["0003", "0004"]


def test_l1_khong_nhan_nuoi_lai_luot_da_bi_bo_tu_truoc(tmp_path):
    """Lượt đã có dòng trong sổ (dù đã bị `\"bo\": true` từ ngày trước) thì
    KHÔNG bị nhận nuôi lần hai."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 26)
    _tao_luot_mo_coi(goc, "K1", "0003", tao_luc=_dt.datetime(2026, 9, 24, 10).timestamp())
    bc = _doc_bao_cao_ngay(goc, "K1", "2026-09-24")
    bc["runs"].append({"ma_luot": "0003", "bo": True, "ly_do_bo": "đã bỏ tay"})
    _ghi_bao_cao_ngay(goc, "K1", "2026-09-24", bc)

    assert _tim_run_chua_xong(goc, "K1", hom_nay) is None


def test_l1_luot_qua_7_ngay_van_thay_qua_tham_chieu(tmp_path):
    """Lượt được NHẶN NUÔI ở một ngày ngoài cửa sổ 7 ngày (vd hôm qua rất xa)
    nhưng có dòng THAM CHIẾU trong cửa sổ thì không bị nhận nuôi lại lần nữa —
    `da_thay_ma_luot` phải đọc cả khoá `tham_chieu_ma_luot`."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 26)
    _tao_luot_mo_coi(goc, "K1", "0001", tao_luc=_dt.datetime(2026, 9, 1, 10).timestamp())
    # Sổ hôm nay có một dòng THAM CHIẾU trỏ về một ngày rất xa, ngoài cửa sổ.
    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    bc["runs"].append({"tham_chieu_ma_luot": "0001", "tham_chieu_ngay": "2026-09-01"})
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)

    assert _tim_run_chua_xong(goc, "K1", hom_nay) is None


# ── L2: khâu `dung` xong không bị nhặt lại vì thumbnail hỏng ────────────────


def test_l2_dung_xong_thumbnail_hong_thi_coi_nhu_da_xong(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    luot = auto.moi_luot(goc, "K1", "0001",
                         {"link": "https://youtu.be/X", "tieu_de": "", "chu_bia": ""})
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    luot.tt("thumbnail").trang_thai = auto.HONG
    luot.tt("thumbnail").loi = "mạng lỗi"

    assert luot.xong_het is False  # đúng tình huống mô tả: thumbnail hỏng
    assert _coi_nhu_da_xong(luot) is True  # nhưng video (khâu `dung`) đã xong


def test_l2_video_da_dung_xong_khong_bi_nhat_lai_moi_gio(tmp_path):
    """Hết cảnh video xong rồi mà lượt cứ bị `--tat-ca` nhặt lại mỗi giờ."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 26)
    luot = auto.moi_luot(goc, "K1", "0001",
                         {"link": "https://youtu.be/X", "tieu_de": "", "chu_bia": ""})
    for m in auto.MA_KHAU:
        luot.tt(m).trang_thai = auto.XONG
    luot.tt("thumbnail").trang_thai = auto.HONG
    luot.tt("thumbnail").loi = "mạng lỗi"
    auto.ghi_luot(luot)

    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    bc["runs"].append({"ma_luot": "0001", "nguon": {"link": "x", "tieu_de": "y"}})
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)

    assert _tim_run_chua_xong(goc, "K1", hom_nay) is None


def test_l2_khau_dung_chua_xong_van_bi_nhat_lai_binh_thuong(tmp_path):
    """Đối chứng: `dung` CHƯA xong thì lượt vẫn phải được nhặt lại như cũ —
    L2 chỉ nới cho đúng ca "video xong, thumbnail hỏng", không nới chung."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 26)
    luot = auto.moi_luot(goc, "K1", "0001",
                         {"link": "https://youtu.be/X", "tieu_de": "", "chu_bia": ""})
    for m in ("kich-ban", "giong-doc", "phu-de", "bang-canh", "anh", "clip"):
        luot.tt(m).trang_thai = auto.XONG
    luot.tt("thumbnail").trang_thai = auto.HONG
    auto.ghi_luot(luot)  # "dung" vẫn còn "cho"

    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    bc["runs"].append({"ma_luot": "0001", "nguon": {"link": "x", "tieu_de": "y"}})
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)

    assert _tim_run_chua_xong(goc, "K1", hom_nay) == (hom_nay.isoformat(), "0001")


# ── L3: trần tự phục hồi ─────────────────────────────────────────────────────


def test_l3_ly_do_vuot_tran_so_lan(tmp_path):
    run = {"phuc_hoi": {"so_lan": 3, "lan_dau_luc": time.time()}}
    ly_do = _ly_do_vuot_tran_phuc_hoi(run, _dt.date(2026, 9, 26), "2026-09-24")
    assert "3 lần" in ly_do


def test_l3_ly_do_vuot_48_gio(tmp_path):
    lan_dau = _dt.datetime(2026, 9, 24, 0, 0).timestamp()
    run = {"phuc_hoi": {"so_lan": 1, "lan_dau_luc": lan_dau}}
    bay_gio = _dt.datetime(2026, 9, 26, 1, 0)  # 49 giờ sau lần phục hồi đầu
    ly_do = _ly_do_vuot_tran_phuc_hoi(run, _dt.date(2026, 9, 26), "2026-09-24", bay_gio=bay_gio)
    assert "48 giờ" in ly_do


def test_l3_ly_do_loi_lap_lai_khong_tu_het(tmp_path):
    run = {"phuc_hoi": {"so_lan": 1, "lan_dau_luc": time.time(), "loai_loi_truoc": su_co.HET_TIEN},
          "san_xuat": {"loi": "ví hết tiền, insufficient balance"}}
    ly_do = _ly_do_vuot_tran_phuc_hoi(run, _dt.date(2026, 9, 26), "2026-09-26")
    assert "lặp lại" in ly_do


def test_l3_ly_do_sap_lot_cua_so_7_ngay(tmp_path):
    # so_ngay mặc định 7; lượt mở 6 ngày trước hôm nay -> còn đúng 0 ngày an
    # toàn (7 - 1 - 6 = 0) -> phải bỏ NGAY, tránh lọt cửa sổ quên im lặng.
    ly_do = _ly_do_vuot_tran_phuc_hoi({}, _dt.date(2026, 9, 26), "2026-09-20")
    assert "cửa sổ quét" in ly_do


def test_l3_con_du_dieu_kien_thi_khong_bo(tmp_path):
    run = {"phuc_hoi": {"so_lan": 1, "lan_dau_luc": time.time()}}
    assert _ly_do_vuot_tran_phuc_hoi(run, _dt.date(2026, 9, 26), "2026-09-26") == ""
    assert _ly_do_vuot_tran_phuc_hoi({}, _dt.date(2026, 9, 26), "2026-09-26") == ""


def test_l3_ghi_nhan_phuc_hoi_tang_dan_giu_lan_dau(tmp_path):
    run = {"san_xuat": {"loi": ""}}
    _ghi_nhan_phuc_hoi(run, bay_gio=_dt.datetime(2026, 9, 24, 10))
    assert run["phuc_hoi"]["so_lan"] == 1
    lan_dau = run["phuc_hoi"]["lan_dau_luc"]

    run["san_xuat"]["loi"] = "hết tiền trong ví"
    _ghi_nhan_phuc_hoi(run, bay_gio=_dt.datetime(2026, 9, 24, 11))
    assert run["phuc_hoi"]["so_lan"] == 2
    assert run["phuc_hoi"]["lan_dau_luc"] == lan_dau  # không đổi ở lần sau
    assert run["phuc_hoi"]["loai_loi_truoc"] == su_co.HET_TIEN


def test_l3_bo_luot_qua_han_ghi_so_tep_danh_dau_va_bao_dong(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    from core import bao_dong as bd

    goi_bao_dong = []
    monkeypatch.setattr(bd, "bao_dong",
                        lambda *a, **k: goi_bao_dong.append((a, k)) or True)

    run = {"ma_luot": "0001", "nguon": {"tieu_de": "x"}}
    bao_cao = {"runs": [run]}
    log = []
    _bo_luot_qua_han(goc, "K1", run, bao_cao, "2026-09-24",
                     "đã tự phục hồi (nhặt lại) 3 lần...", log.append)

    assert run["bo"] is True
    assert run["ly_do_bo"] == "đã tự phục hồi (nhặt lại) 3 lần..."
    bc = _doc_bao_cao_ngay(goc, "K1", "2026-09-24")
    assert bc["runs"][0]["bo"] is True

    thu_muc_luot = auto.duong_luot(goc, "K1", "0001")
    ten_tep = [t for t in os.listdir(thu_muc_luot) if t.startswith("BO-VI-")]
    assert len(ten_tep) == 1
    with open(os.path.join(thu_muc_luot, ten_tep[0]), encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert "0001" in noi_dung and "K1" in noi_dung
    assert "KHÔNG" in noi_dung  # nói rõ không xoá gì (luật 1)

    assert any("[TỰ BỎ LƯỢT]" in dong for dong in log)
    assert len(goi_bao_dong) == 1
    _args, kwargs = goi_bao_dong[0]
    assert kwargs.get("muc") == bd.MUC_NHAC
    assert kwargs.get("kenh") == "K1"


def test_l3_tich_hop_vuot_tran_thi_tu_bo_va_chon_nguon_moi(tmp_path):
    """Tích hợp đầu-cuối: lượt dở đã vượt trần (3 lần phục hồi) bị TỰ BỎ ngay
    trong lượt chạy này, và — kênh cho phép 2 video/ngày — nhánh chọn nguồn
    mới chạy tiếp NGAY, không phải đợi thêm một ngày."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", video_moi_ngay=2)
    hom_nay = _dt.date(2026, 9, 26)

    luot_cu = auto.moi_luot(goc, "K1", "0001",
                            {"link": "https://youtu.be/OLD00000001", "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot_cu)  # mọi khâu còn "cho" — chưa xong

    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    bc["runs"].append({
        "ma_luot": "0001",
        "nguon": {"link": "https://youtu.be/OLD00000001", "tieu_de": "cũ", "ma": "OLD00000001"},
        "ngan_sach": {}, "san_xuat": {"da_chay": True, "xong_het": False, "khau_hong": [], "loi": ""},
        "ban_giao": {"da_ban_giao": False},
        "phuc_hoi": {"so_lan": 3, "lan_dau_luc": _dt.datetime(2026, 9, 24, 10).timestamp(),
                    "loai_loi_truoc": ""},
    })
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)

    moi = [_dong_de_xuat("https://youtu.be/NEW00000001", tieu_de="nguồn mới")]
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None,
        doc_danh_sach=_danh_sach_gia(moi), video_da_lam_nhom=lambda g, k: set())

    assert ket["ok"] is True
    assert ket["run"]["nguon"]["ma"] == "NEW00000001"

    bc_sau = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    cu = next(r for r in bc_sau["runs"] if r.get("ma_luot") == "0001")
    assert cu.get("bo") is True
    assert cu.get("ly_do_bo")

    thu_muc_luot_cu = auto.duong_luot(goc, "K1", "0001")
    assert any(t.startswith("BO-VI-") for t in os.listdir(thu_muc_luot_cu))


# ── L4: nhãn báo cáo dọn dùng đúng lý do thật ────────────────────────────────


def test_l4_dung_md_tat_ca_dung_ly_do_that(tmp_path):
    """`don-dep.log` từng ghi đúng "quá 3 lượt, chưa đăng" nhưng sổ ngày .md
    lại luôn in "video đã đăng quá hạn ân xá" — đo thật trên VPS ngày
    25/09/2026 (`CHANNEL/TL1-T7/tu-chay/don-dep.log` + `workspace/tu-chay/
    2026-09-25.md`)."""
    runs = [{
        "luc": "2026-09-25T01:00:02", "che_do": "that", "ket_qua": [],
        "don_dep": {"tong_bytes": 1_690_000_000, "theo_kenh": {"TL1-T7": 1_690_000_000},
                   "ly_do": ["xoá vì quá 3 lượt, chưa đăng"]},
    }]
    md = _dung_md_tat_ca("2026-09-25", runs)
    assert "xoá vì quá 3 lượt, chưa đăng" in md
    assert "quá hạn ân xá" not in md


def test_l4_dung_md_tat_ca_so_cu_khong_co_ly_do_giu_cau_cu(tmp_path):
    """Sổ CŨ (ghi trước bản vá) không có trường `ly_do` — vẫn hiện được, giữ
    nguyên câu cũ thay vì suy diễn ngược (đúng luật hai — cả hai luật cùng đi
    qua một cửa `don_theo_cai_dat`, nên không đoán bừa khi thiếu dữ liệu)."""
    runs = [{
        "luc": "2026-09-20T01:00:00", "che_do": "that", "ket_qua": [],
        "don_dep": {"tong_bytes": 500_000, "theo_kenh": {"K1": 500_000}},
    }]
    md = _dung_md_tat_ca("2026-09-20", runs)
    assert "đã đăng, quá hạn ân xá" in md


def test_l4_chay_tat_ca_gom_ly_do_that_tu_da_don(tmp_path):
    """Tích hợp: `chay_tat_ca` phải TỰ gom `ly_do` thật từ kết quả
    `don_theo_cai_dat_fn` (khoá `da_don[].ly_do`) vào sổ ngày dùng chung."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")

    def don_gia(goc_, ma):
        return {"kenh": ma, "chay": True, "tong_bytes": 900,
               "da_don": [{"kenh": ma, "luot": "0001", "ly_do": "xoá vì quá 3 lượt, chưa đăng"}]}

    bao_cao = chay_tat_ca(
        goc, che_do="thu", on_log=NO_LOG, danh_sach_kenh=["K1"],
        chay_mot_ngay_fn=lambda *a, **k: {"kenh": "K1", "ok": True, "tom_tat": "K1: ok"},
        don_theo_cai_dat_fn=don_gia,
        don_mo_rong_fn=lambda *a, **k: {},
    )
    assert bao_cao["don_dep"]["ly_do"] == ["xoá vì quá 3 lượt, chưa đăng"]
    duong_md = bao_cao["duong_bao_cao_md"]
    with open(duong_md, encoding="utf-8") as tep:
        noi_dung = tep.read()
    assert "xoá vì quá 3 lượt, chưa đăng" in noi_dung
    assert "quá hạn ân xá" not in noi_dung


# ── V2-tối-giản: cửa gói chờ đăng báo "chờ người", không phải "OK" ──────────


def test_v2_cua_so_san_xuat_bao_cho_nguoi_dung_ngay(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0001", "Ngày đăng": "20/09/2026", "Sẵn sàng": "x"})
    kenh = doc_kenh(goc, "K1")
    # Cố định `bay_gio` NGAY SAU "Ngày đăng" (còn trong 3 ngày ân hạn mặc định
    # của việc B, `cho_dang_toi_da_ngay`) — bài này chỉ kiểm V2 (nhãn "chờ
    # người"), không phải việc B ("thôi chặn vì quá hạn").
    cho_mo, ly_do, thong_tin = _cua_so_san_xuat(
        goc, "K1", kenh, bay_gio=_dt.datetime(2026, 9, 21, 10, 0))
    assert cho_mo is False
    assert thong_tin["cho_nguoi"] is True
    assert "chờ đăng từ 20/09" in ly_do
    assert "Đã đăng thủ công" in ly_do


def test_v2_chay_mot_ngay_cho_nguoi_khong_phai_loi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0001", "Ngày đăng": "20/09/2026", "Sẵn sàng": "x"})
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 26),
        bay_gio=_dt.datetime(2026, 9, 21, 10, 0), on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]))
    assert ket["ok"] is True  # KHÔNG phải lỗi
    assert ket["cho_nguoi"] is True  # nhưng cũng KHÔNG phải "không có gì phải làm"
    assert "chờ đăng từ 20/09" in ket["tom_tat"]


def test_v2_chay_nhieu_kenh_lan_truyen_co_cho_nguoi(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0001", "Ngày đăng": "20/09/2026", "Sẵn sàng": "x"})
    bao_cao = chay_nhieu_kenh(
        goc, ["K1"], che_do="thu", on_log=NO_LOG,
        bay_gio=_dt.datetime(2026, 9, 21, 10, 0),
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]))
    assert bao_cao["co_loi"] is False
    assert bao_cao["ket_qua"][0]["ok"] is True
    assert bao_cao["ket_qua"][0]["cho_nguoi"] is True


def test_v2_dung_md_tat_ca_nhan_cho_nguoi(tmp_path):
    runs = [{
        "luc": "2026-09-26T08:00:00", "che_do": "that",
        "ket_qua": [
            {"kenh": "K1", "ok": True, "cho_nguoi": True, "tom_tat": "K1: còn 1 video chờ đăng..."},
            {"kenh": "K2", "ok": True, "cho_nguoi": False, "tom_tat": "K2: xong video..."},
            {"kenh": "K3", "ok": False, "cho_nguoi": False, "tom_tat": "K3: lỗi..."},
        ],
    }]
    md = _dung_md_tat_ca("2026-09-26", runs)
    assert "[CHỜ NGƯỜI] K1:" in md
    assert "[OK] K2:" in md
    assert "[LỖI] K3:" in md


# ═══════════════════════════════════════════════════════════════════════════
# VÁ THẬT 28/09/2026 — hai lỗi bắt được TRÊN CHÍNH VPS sau khi triển khai bản
# vá 26/09 (xem workspace/ban-va/2026-09-26-luot-ket-tu-xu-ly/GHI-CHU.md):
#
#   (a) `bao_cao` CŨ bị `finalize()` ghi đè, xoá mất dòng "nhận con nuôi" (L1)
#       mà `_tim_run_chua_xong` vừa tự ghi — log thật in "[TỰ PHỤC HỒI]" nhưng
#       sổ ngày rốt cuộc trống trơn, TL1-T7/0003+0004 vẫn y nguyên trên đĩa.
#   (b) chỗ bắt "lỗi ngoài dự kiến" ghi `str(loi)` RỖNG cho những ngoại lệ
#       không mang thông điệp (`KeyError()`, `AssertionError()`) — log thật
#       16:00 26/09/2026 ghi "lỗi ngoài dự kiến: " trống trơn cho cả ba kênh.
# ═══════════════════════════════════════════════════════════════════════════


def test_va_28_09_khong_de_finalize_ghi_de_mat_dong_nhan_nuoi(tmp_path):
    """Đúng lỗi thật bắt được 27→28/09/2026: nhận nuôi lượt mồ côi (L1) rồi
    CHẠY TIẾP nó (không phải chọn nguồn mới), và dòng "nhận con nuôi" phải
    còn NGUYÊN trên sổ sau khi `chay_mot_ngay` xong việc — không bị
    `finalize()` ghi đè mất vì đọc `bao_cao` từ TRƯỚC lúc nhận nuôi."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 28)
    _tao_luot_mo_coi(goc, "K1", "0003", tao_luc=_dt.datetime(2026, 9, 26, 10).timestamp())

    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=hom_nay, on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]))

    assert ket["run"]["ma_luot"] == "0003"  # chạy tiếp lượt mồ côi, không chọn nguồn mới

    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert [r.get("ma_luot") for r in bc["runs"]] == ["0003"]
    assert bc["runs"][0].get("nhan_nuoi") is True
    # Đã được ghi nhận một lần phục hồi (L3) trong đúng lượt chạy vừa rồi.
    assert bc["runs"][0].get("phuc_hoi", {}).get("so_lan") == 1


def test_va_28_09_ta_loi_day_du_khong_bao_gio_rong(tmp_path):
    from core import tu_chay as tc

    assert tc._ta_loi_day_du(KeyError()) == "KeyError"
    assert tc._ta_loi_day_du(AssertionError()) == "AssertionError"
    assert tc._ta_loi_day_du(ValueError("sai định dạng")) == "ValueError: sai định dạng"


def test_va_28_09_chay_nhieu_kenh_khong_con_ghi_loi_cam(tmp_path):
    goc = str(tmp_path)

    def vo_no(*a, **k):
        raise KeyError()

    bao_cao = chay_nhieu_kenh(goc, ["K1"], chay_mot_ngay_fn=vo_no, on_log=NO_LOG)
    assert bao_cao["co_loi"] is True
    dong = bao_cao["ket_qua"][0]
    assert "KeyError" in dong["tom_tat"]
    assert not dong["tom_tat"].rstrip().endswith("—")  # không còn để trống sau gạch ngang
    assert "KeyError" in dong["loi"]


def test_va_28_09_log_traceback_day_du_ghi_duoc_nhieu_dong(tmp_path):
    from core import tu_chay as tc

    dong_ghi = []
    try:
        raise KeyError()
    except KeyError as loi:
        tc._log_traceback_day_du(dong_ghi.append, loi)
    assert len(dong_ghi) >= 2
    assert any("KeyError" in d for d in dong_ghi)


# ═══════════════════════════════════════════════════════════════════════════
# Việc B (chẩn đoán 28/09/2026) — "không bao giờ đứng im vì gói bị bỏ quên":
# gói "Sẵn sàng" mà chưa đăng quá `cho_dang_toi_da_ngay` ngày (mặc định 3)
# thì THÔI CHẶN cửa `_cua_so_san_xuat`, không xoá/đổi gì trong kế hoạch.
# ═══════════════════════════════════════════════════════════════════════════


def test_b_moc_ban_giao_goi_dung_ngay_gio_ke_hoach(tmp_path):
    moc = _moc_ban_giao_goi("K1-0001", "", "20/09/2026", "14:30")
    assert moc == _dt.datetime(2026, 9, 20, 14, 30)


def test_b_moc_ban_giao_goi_ngay_khong_kem_gio_thi_lay_00h(tmp_path):
    moc = _moc_ban_giao_goi("K1-0001", "", "20/09/2026", "")
    assert moc == _dt.datetime(2026, 9, 20, 0, 0)


def test_b_moc_ban_giao_goi_trong_thi_lui_ve_mtime_thu_muc_done(tmp_path):
    goc = str(tmp_path)
    thu_muc_done = os.path.join(goc, "DONE", "K1")
    thu_muc_goi = os.path.join(thu_muc_done, "K1-0001")
    os.makedirs(thu_muc_goi, exist_ok=True)
    mtime_gia = _dt.datetime(2026, 9, 18, 8, 0).timestamp()
    os.utime(thu_muc_goi, (mtime_gia, mtime_gia))

    moc = _moc_ban_giao_goi("K1-0001", thu_muc_done, "", "")
    assert moc == _dt.datetime.fromtimestamp(mtime_gia)


def test_b_moc_ban_giao_goi_khong_co_du_lieu_thi_none(tmp_path):
    assert _moc_ban_giao_goi("K1-0001", "", "", "") is None
    assert _moc_ban_giao_goi("K1-0001", os.path.join(str(tmp_path), "khong-ton-tai"), "", "") is None


def test_b_cua_so_san_xuat_thoi_chan_goi_qua_han(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=3)
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0005", "Ngày đăng": "20/09/2026",
                                "Giờ đăng": "08:00", "Sẵn sàng": "x"})
    kenh = doc_kenh(goc, "K1")
    bay_gio = _dt.datetime(2026, 9, 26, 10, 0)  # 6 ngày sau — quá hạn 3 ngày

    cho_mo, ly_do, thong_tin = _cua_so_san_xuat(goc, "K1", kenh, bay_gio=bay_gio)
    assert cho_mo is True  # KHÔNG còn chặn
    assert thong_tin.get("qua_han_cho_dang") == ["K1-0005"]
    assert thong_tin.get("so_video_dang_cho") == 0

    # Không đụng gì tới kế hoạch — dòng vẫn y nguyên "Sẵn sàng", không "bo".
    cot, hang = ke_hoach_dang.doc_bang(goc, "K1")
    dong = dict(zip(cot, hang[0]))
    assert dong["Sẵn sàng"] == "x"
    assert dong["Trạng thái đăng"] == ""


def test_b_cua_so_san_xuat_chua_qua_han_van_chan_binh_thuong(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=3)
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0005", "Ngày đăng": "20/09/2026",
                                "Giờ đăng": "08:00", "Sẵn sàng": "x"})
    kenh = doc_kenh(goc, "K1")
    bay_gio = _dt.datetime(2026, 9, 21, 10, 0)  # mới hơn 1 ngày — chưa quá hạn

    cho_mo, ly_do, thong_tin = _cua_so_san_xuat(goc, "K1", kenh, bay_gio=bay_gio)
    assert cho_mo is False
    assert thong_tin.get("cho_nguoi") is True
    assert not thong_tin.get("qua_han_cho_dang")


def test_b_cua_so_san_xuat_tat_van_thi_cho_vo_han_nhu_cu(tmp_path):
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=0)  # tắt hẳn van B
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0005", "Ngày đăng": "01/01/2020",
                                "Giờ đăng": "08:00", "Sẵn sàng": "x"})
    kenh = doc_kenh(goc, "K1")
    bay_gio = _dt.datetime(2026, 9, 26, 10, 0)  # rất lâu rồi vẫn phải chặn

    cho_mo, ly_do, thong_tin = _cua_so_san_xuat(goc, "K1", kenh, bay_gio=bay_gio)
    assert cho_mo is False
    assert not thong_tin.get("qua_han_cho_dang")


def test_b_chay_mot_ngay_ghi_dong_cho_qua_han_va_chon_nguon_moi(tmp_path):
    """Tích hợp: gói quá hạn không còn chặn — `chay_mot_ngay` ghi rõ một dòng
    "[CHỜ QUÁ HẠN]" vào nhật ký VÀ đi tiếp chọn nguồn mới (không phải
    "[CHỜ NGƯỜI]" nữa)."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=3)
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0005", "Ngày đăng": "20/09/2026",
                                "Giờ đăng": "08:00", "Sẵn sàng": "x"})
    moi = [_dong_de_xuat("https://youtu.be/QUAHAN00001", tieu_de="nguồn mới")]
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 26),
        bay_gio=_dt.datetime(2026, 9, 26, 10, 0), on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["ok"] is True
    assert ket.get("cho_nguoi") is not True
    assert ket["run"]["nguon"]["ma"] == "QUAHAN00001"
    assert any("[CHỜ QUÁ HẠN]" in dong and "K1-0005" in dong for dong in ket["nhat_ky"])


def test_b_don_dep_khong_bao_gio_xoa_goi_trong_done_vi_qua_so_luot(tmp_path):
    """Xác nhận lại (không phải viết mới): `core.don_dep.ung_vien_qua_so_luot`
    ("quá N lượt, chưa đăng") KHÔNG BAO GIỜ đưa gói trong `thu_muc_done` vào
    danh sách xoá — chỉ luật MỘT ("đã đăng, quá hạn ân xá",
    `core.don_dep.ung_vien_don`) mới đụng tới `thu_muc_done`, và chỉ khi
    video đã thật sự ĐÃ ĐĂNG. Việc B dựa vào đúng bất biến này: một gói vừa
    được "thôi chặn" (chưa đăng) không được dọn mất trong lúc chờ."""
    from core import don_dep

    goc = str(tmp_path)
    thu_muc_done = os.path.join(goc, "DONE", "K1")
    os.makedirs(os.path.join(thu_muc_done, "K1-0001"), exist_ok=True)
    with open(os.path.join(thu_muc_done, "K1-0001", "8-video.mp4"), "wb") as tep:
        tep.write(b"gia")

    # Hai lượt xong hết trên PROJECTS/AUTO, CHƯA đăng — "0001" đúng ca gói bị
    # "thôi chặn" bởi việc B, trong khi `giu_toi_da_luot=1` (luật hai) đẩy nó
    # ra khỏi diện "giữ lại" vì có "0002" mới hơn.
    for ma_luot, ten_khau_nang in (("0001", ("5-anh", "6-clip")), ("0002", ())):
        luot = auto.moi_luot(goc, "K1", ma_luot, {"link": "x", "tieu_de": "", "chu_bia": ""})
        for m in auto.MA_KHAU:
            luot.tt(m).trang_thai = auto.XONG
        auto.ghi_luot(luot)
        for m in ten_khau_nang:
            os.makedirs(os.path.join(auto.duong_luot(goc, "K1", ma_luot), m), exist_ok=True)

    ung_vien = don_dep.ung_vien_qua_so_luot(goc, "K1", giu=1)  # giữ 1 lượt mới nhất -> "0001" là ứng viên
    assert any(u["luot"] == "0001" for u in ung_vien), "test tự kiểm: '0001' phải là ứng viên"
    duong_xoa_tat_ca = [p for u in ung_vien for p in u["duong"]]
    assert not any(thu_muc_done in p for p in duong_xoa_tat_ca), (
        "luật 'quá N lượt' không được đụng tới gói trong thu_muc_done")


# ═══════════════════════════════════════════════════════════════════════════
# NHƯỜNG PHIÊN KÊNH (chẩn đoán 28/09/2026) — sản xuất không mở một lượt MỚI
# khi còn phiên kênh của vm/agent.py đến hạn chưa chạy hôm nay (quét Studio,
# hoặc ĐĂNG THEO LỊCH ĐÃ HẸN GIỜ) — cả hai dùng chung khoá máy `.khoa-may`.
# ═══════════════════════════════════════════════════════════════════════════


def _ghi_vm_config(goc, **cai):
    thu_muc = os.path.join(goc, "vm")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "config.json"), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


def _ghi_vm_trang_thai(goc, **cai):
    thu_muc = os.path.join(goc, "vm")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "trang-thai.json"), "w", encoding="utf-8") as tep:
        json.dump(cai, tep, ensure_ascii=False)


def test_nhuong_khong_chon_nguon_moi_khi_phien_kenh_den_han(tmp_path):
    """Không có lượt dở, còn kênh phiên K1 đến hạn chưa chạy hôm nay ->
    KHÔNG chọn nguồn mới, thoát sớm với "[NHƯỜNG]", `ok=True` (không lỗi)."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_vm_config(goc, cac_kenh=["K1"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@K1": "2026-09-27",
        "phien_muc_tieu@K1@2026-09-28": "07:30",
    })
    moi = [_dong_de_xuat("https://youtu.be/NHUONG00001", tieu_de="đừng chọn cái này")]
    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["ok"] is True
    assert ket["run"] is None  # KHÔNG chọn nguồn mới
    assert any("[NHƯỜNG]" in dong and "K1" in dong for dong in log)


def test_khong_nhuong_khi_luot_dang_thuc_su_dang_dang(tmp_path):
    """Lượt ĐÃ thật sự bắt tay vào làm (`san_xuat.da_chay=True`, đã trót đổ
    tiền/giờ) thì KHÔNG nhường — chạy tiếp bình thường dù có phiên đến hạn."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_vm_config(goc, cac_kenh=["K1"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@K1": "2026-09-27",
        "phien_muc_tieu@K1@2026-09-28": "07:30",
    })
    hom_nay = _dt.date(2026, 9, 28)
    luot = auto.moi_luot(goc, "K1", "0001", {"link": "https://youtu.be/DANGLAM0001",
                                             "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)  # chưa xong (mọi khâu "cho")
    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    bc["runs"].append({
        "ma_luot": "0001", "nguon": {"link": "https://youtu.be/DANGLAM0001", "tieu_de": "đang làm"},
        "ngan_sach": {}, "san_xuat": {"da_chay": True, "xong_het": False, "khau_hong": [], "loi": ""},
        "ban_giao": {"da_ban_giao": False},
    })
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)

    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=hom_nay,
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["run"]["ma_luot"] == "0001"  # chạy tiếp, không nhường
    assert not any("[NHƯỜNG]" in dong for dong in log)


def test_nhuong_ap_dung_cho_luot_mo_coi_vua_nhan_nuoi(tmp_path):
    """Lượt mồ côi VỪA được L1 nhận nuôi trong chính lượt gọi này
    (`san_xuat.da_chay` còn False — chưa hề bắt tay vào làm) vẫn phải NHƯỜNG,
    đúng ví dụ chẩn đoán chỉ ra ("nhận nuôi TL1/0003" là một ca "mở lượt sản
    xuất MỚI")."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_vm_config(goc, cac_kenh=["K1"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@K1": "2026-09-27",
        "phien_muc_tieu@K1@2026-09-28": "07:30",
    })
    _tao_luot_mo_coi(goc, "K1", "0003", tao_luc=_dt.datetime(2026, 9, 26, 10).timestamp())

    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["run"] is None
    assert any("[NHƯỜNG]" in dong for dong in log)
    # Việc nhận nuôi (L1, ghi sổ) vẫn xảy ra — chỉ sản xuất bị hoãn, không mất
    # dấu lượt mồ côi.
    bc = _doc_bao_cao_ngay(goc, "K1", "2026-09-28")
    assert any(r.get("ma_luot") == "0003" for r in bc["runs"])


def test_qua_tran_gio_cho_thi_khong_nhuong_nua(tmp_path):
    """Phiên kênh đến hạn quá lâu (agent có thể chết/treo) — thôi nhường, sản
    xuất chạy bình thường + ghi cảnh báo."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    _ghi_vm_config(goc, cac_kenh=["K1"])
    _ghi_vm_trang_thai(goc, **{
        "phien_cuoi@K1": "2026-09-20",
        "phien_muc_tieu@K1@2026-09-28": "00:00",  # quá 10 giờ tại bay_gio 10:00
    })
    moi = [_dong_de_xuat("https://youtu.be/QUATRAN0001", tieu_de="vẫn chọn được")]
    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["run"]["nguon"]["ma"] == "QUATRAN0001"
    assert any("[NHƯỜNG]" in dong and "treo" in dong for dong in log)


def test_khong_co_vm_thi_san_xuat_binh_thuong(tmp_path):
    """Máy không chạy `vm/` (không có `vm/config.json`) — không có gì để
    nhường, sản xuất diễn ra bình thường như trước bản vá."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    moi = [_dong_de_xuat("https://youtu.be/KHONGVM0001", tieu_de="vẫn chọn được")]
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 10, 0), on_log=NO_LOG,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set())
    assert ket["run"]["nguon"]["ma"] == "KHONGVM0001"


# ═══════════════════════════════════════════════════════════════════════════
# LỖI 1 (chẩn đoán 27→28/09/2026) — vượt cửa nhịp đăng: `tim_som is not None`
# (dấu vết MỘT lượt dở) bỏ qua cửa `_cua_so_san_xuat`, nhưng nếu `run` rốt
# cuộc KHÔNG PHẢI một lượt ĐANG THẬT SỰ CHẠY thì vẫn phải quay lại qua đúng
# cửa đó trước khi "2) Chọn nguồn…" mở nguồn mới — đúng ca thật TL1-T7 sản
# xuất 0006 rồi 0007 CÙNG một đề trong lúc còn gói "Sẵn sàng" chờ đăng.
# ═══════════════════════════════════════════════════════════════════════════


def test_va_28_09_l3_bo_luot_van_phai_qua_cua_nhip_dang(tmp_path):
    """L3 tự bỏ một lượt dở đã vượt trần phục hồi (`run` thành `None`) trong
    lúc còn gói "Sẵn sàng" CHƯA quá hạn chờ đăng — phải bị CHẶN y hệt nhánh
    `tim_som is None` bình thường, TUYỆT ĐỐI không rơi thẳng xuống "chọn
    nguồn mới" mà bỏ qua cửa."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=3)
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0099", "Ngày đăng": "27/09/2026",
                                "Giờ đăng": "20:00", "Sẵn sàng": "x"})

    luot = auto.moi_luot(goc, "K1", "0003", {"link": "https://youtu.be/KET00000003",
                                             "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)  # chưa xong — mọi khâu còn "cho"
    bc = _doc_bao_cao_ngay(goc, "K1", "2026-09-24")
    bc["runs"].append({
        "ma_luot": "0003", "nguon": {"link": "https://youtu.be/KET00000003", "tieu_de": "cũ"},
        "ngan_sach": {}, "san_xuat": {"da_chay": True, "xong_het": False, "khau_hong": [], "loi": ""},
        "ban_giao": {"da_ban_giao": False},
        "phuc_hoi": {"so_lan": 3, "lan_dau_luc": _dt.datetime(2026, 9, 24, 8, 0).timestamp()},
    })
    _ghi_bao_cao_ngay(goc, "K1", "2026-09-24", bc)

    moi = [_dong_de_xuat("https://youtu.be/KHONGDUOCC1", tieu_de="không được chọn")]
    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 5, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["run"] is None
    assert ket.get("cho_nguoi") is True
    assert any("[CHỜ NGƯỜI]" in dong for dong in log)
    # L3 vẫn đánh dấu bỏ lượt cũ (không liên quan tới việc chặn cửa) — không
    # xoá gì, chỉ đánh dấu.
    bc_sau = _doc_bao_cao_ngay(goc, "K1", "2026-09-24")
    assert bc_sau["runs"][0].get("bo") is True
    # KHÔNG có nguồn mới nào được mở trong sổ hôm nay.
    bc_hom_nay = _doc_bao_cao_ngay(goc, "K1", "2026-09-28")
    assert all(not (r.get("nguon") or {}).get("ma") for r in bc_hom_nay.get("runs", []))


def test_va_28_09_luot_nhan_nuoi_chua_chay_van_bi_chan_boi_cua_nhip_dang(tmp_path):
    """(LỖI 1c) Lượt mồ côi VỪA được L1 nhận nuôi (`san_xuat.da_chay` còn
    False — đúng ca TL1-T7/0003+0004, mồ côi từ khâu kịch bản dở) phải qua
    ĐÚNG cửa nhịp đăng y như nguồn mới — còn gói "Sẵn sàng" chưa quá hạn thì
    PHẢI CHẶN, không được chạy tiếp sản xuất ngay."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=3)
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0099", "Ngày đăng": "27/09/2026",
                                "Giờ đăng": "20:00", "Sẵn sàng": "x"})
    _tao_luot_mo_coi(goc, "K1", "0003", tao_luc=_dt.datetime(2026, 9, 26, 10).timestamp())

    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28),
        bay_gio=_dt.datetime(2026, 9, 28, 5, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]))

    assert ket["run"] is None
    assert ket.get("cho_nguoi") is True
    assert any("[CHỜ NGƯỜI]" in dong for dong in log)
    # L1 vẫn nhận nuôi (ghi sổ) — không mất dấu lượt mồ côi, chỉ KHÔNG được
    # chạy tiếp sản xuất cho tới khi qua cửa.
    bc = _doc_bao_cao_ngay(goc, "K1", "2026-09-28")
    assert any(r.get("ma_luot") == "0003" and r.get("nhan_nuoi") for r in bc["runs"])


def test_va_28_09_luot_dang_chay_that_khong_bi_chan_boi_cua_nhip_dang(tmp_path):
    """Đối chứng bắt buộc: lượt ĐÃ THẬT SỰ chạy dở (`san_xuat.da_chay=True`,
    đã trót đổ tiền/giờ) KHÔNG bị chặn lại bởi cửa nhịp đăng dù còn gói chờ —
    chạy tiếp bình thường, đúng chính sách LỖI 1c."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1", cho_dang_toi_da_ngay=3)
    _ghi_ke_hoach(goc, "K1", **{"Mã gói": "K1-0099", "Ngày đăng": "27/09/2026",
                                "Giờ đăng": "20:00", "Sẵn sàng": "x"})
    hom_nay = _dt.date(2026, 9, 28)
    luot = auto.moi_luot(goc, "K1", "0001", {"link": "https://youtu.be/DANGCHAY001",
                                             "tieu_de": "", "chu_bia": ""})
    auto.ghi_luot(luot)
    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    bc["runs"].append({
        "ma_luot": "0001", "nguon": {"link": "https://youtu.be/DANGCHAY001", "tieu_de": "đang làm"},
        "ngan_sach": {}, "san_xuat": {"da_chay": True, "xong_het": False, "khau_hong": [], "loi": ""},
        "ban_giao": {"da_ban_giao": False},
    })
    _ghi_bao_cao_ngay(goc, "K1", hom_nay.isoformat(), bc)

    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=hom_nay,
        bay_gio=_dt.datetime(2026, 9, 28, 5, 0), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia([]))

    assert ket["run"]["ma_luot"] == "0001"  # chạy tiếp bình thường, không chặn
    assert not any("[CHỜ NGƯỜI]" in dong or "[NHỊP ĐĂNG]" in dong for dong in log)


def test_va_28_09_chot_an_toan_tim_som_khong_tra_ra_run(tmp_path, monkeypatch):
    """(LỖI 1b) `_tim_run_chua_xong` trả về một `(ngày, mã)` nhưng sổ ngày đó
    KHÔNG thật sự có `run` khớp (dữ liệu bất thường — sổ mất dòng/hỏng) — tool
    phải DỪNG, ghi lỗi rõ (kèm tên lớp lỗi), TUYỆT ĐỐI không coi như "không
    có lượt dở" rồi âm thầm mở nguồn mới."""
    import core.tu_chay as tc

    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    hom_nay = _dt.date(2026, 9, 28)
    monkeypatch.setattr(tc, "_tim_run_chua_xong",
                        lambda *a, **k: ("2026-09-20", "BONG-MA-0001"))

    moi = [_dong_de_xuat("https://youtu.be/KHONGDUOCC2", tieu_de="không được chọn")]
    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=hom_nay, on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia(moi),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["ok"] is False
    assert ket["buoc_loi"] == "tim_run_chua_xong"
    assert ket["run"] is None
    assert any("[LỖI DỮ LIỆU]" in dong for dong in log)
    assert any("LookupError" in dong for dong in log)
    bc = _doc_bao_cao_ngay(goc, "K1", hom_nay.isoformat())
    assert bc["runs"] == []  # KHÔNG mở nguồn mới nào


# ═══════════════════════════════════════════════════════════════════════════
# LỖI 2 (chẩn đoán 27→28/09/2026) — chống làm trùng theo TIÊU ĐỀ, cạnh chống
# trùng theo MÃ VIDEO đã có. Đúng ca thật: TL1-T7-0006 (nguồn 8nPciHbf194) và
# TL1-T7-0007 (nguồn OmuR0oP6CYc) — hai mã khác hẳn, CÙNG một tiêu đề.
# ═══════════════════════════════════════════════════════════════════════════


def test_loi2_ung_vien_xep_hang_mot_nut_loai_trung_tieu_de(tmp_path):
    from core.tu_chay import ung_vien_xep_hang

    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    moi = [
        _dong_de_xuat("https://youtu.be/TRUNGDE0001", tieu_de="【心理学】夜中に目が覚める人の心理"),
        _dong_de_xuat("https://youtu.be/KHACDE00002", tieu_de="Một chủ đề hoàn toàn khác biệt"),
    ]
    da_lam_tieu_de = [("【雑学】夜中に目が覚める人の心理", "lượt K1/0001 (tiêu đề đã đặt)")]
    log = []
    ds = ung_vien_xep_hang(goc, "K1", False, set(),
                           doc_danh_sach=_danh_sach_gia_day_du(moi=moi), log=log.append,
                           da_lam_tieu_de=da_lam_tieu_de)
    ma_con_lai = {d["ma"] for d in ds}
    assert "TRUNGDE0001" not in ma_con_lai  # trùng đề — bị loại
    assert "KHACDE00002" in ma_con_lai       # đề khác — vẫn còn
    assert any("loại TRUNGDE0001 vì trùng tiêu đề" in dong for dong in log)


def test_loi2_ung_vien_xep_hang_khong_da_lam_tieu_de_thi_khong_loai_gi(tmp_path):
    """Không truyền `da_lam_tieu_de` (mặc định `None`) — hành vi giống HỆT
    trước bản vá, không loại ứng viên nào theo tiêu đề. Đảm bảo mọi nơi gọi
    CŨ (trạm `/loi-thoai/can-lay`, bài kiểm khác) không cần sửa gì."""
    from core.tu_chay import ung_vien_xep_hang

    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    moi = [_dong_de_xuat("https://youtu.be/BATKY000001", tieu_de="bất kỳ đề gì")]
    ds = ung_vien_xep_hang(goc, "K1", False, set(),
                           doc_danh_sach=_danh_sach_gia_day_du(moi=moi), log=NO_LOG)
    assert {d["ma"] for d in ds} == {"BATKY000001"}


def test_loi2_chon_nguon_content_chot_tay_bi_chan_neu_trung_tieu_de(tmp_path):
    """Content CHỐT TAY (`ui_qt` tab "Chọn content") cũng phải qua chống trùng
    tiêu đề — người vận hành chốt tay TRƯỚC khi biết kênh vừa remake đúng chủ
    đề đó qua nguồn khác mã vẫn là trùng nội dung, không phải ngoại lệ."""
    from core import chon_content as cc
    from core import tu_chay as tc

    goc = str(tmp_path)
    uv = cc.UngVien(
        cc.LUONG_DOI_THU, "TRUNGDETAY1", "【雑学】夜中に目が覚める人の心理", "Đối thủ A",
        "https://youtu.be/TRUNGDETAY1", 91, "Ưu tiên", "đang tăng nhanh")
    cc.chot(goc, "K1", uv)
    da_lam_tieu_de = [("【心理学】夜中に目が覚める人の心理", "lượt K1/0006 (tiêu đề nguồn)")]

    def khong_duoc_goi(*_a, **_k):
        raise AssertionError("nhánh chốt tay bị trùng đề thì không được rơi xuống chấm lại")

    log = []
    ket = tc._chon_nguon(
        goc, "K1", False, set(), cham_v7=khong_duoc_goi, doc_danh_sach=_danh_sach_gia_day_du(),
        log=log.append, da_lam_tieu_de=da_lam_tieu_de)

    assert ket is None  # không có bảng "Một nút" nào khác để rơi về -> None
    assert any("TRÙNG TIÊU ĐỀ" in dong for dong in log)
    # Không bị đánh dấu "đang sản xuất" — vẫn còn nguyên để người xem lại.
    assert cc.doc_lua_chon(goc, "K1").trang_thai != "đang sản xuất"


def test_loi2_end_to_end_chay_mot_ngay_loai_ung_vien_trung_de_da_lam_that(tmp_path):
    """Tích hợp đầu-cuối: một lượt ĐÃ LÀM thật trên đĩa (`0-doi-thu.txt`) rồi
    `chay_mot_ngay` chọn nguồn mới — ứng viên trùng đề với lượt đã làm phải bị
    loại, ứng viên đề khác vẫn được chọn."""
    goc = str(tmp_path)
    _ghi_kenh(goc, "K1")
    d = os.path.join(goc, "PROJECTS", "AUTO", "K1", "0001")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "0-doi-thu.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: 【心理学】夜中に目が覚める人の心理\nVIDEO_ID: aaaaaaaaaaa\n")

    moi = [
        _dong_de_xuat("https://youtu.be/TRUNGDE0003", tieu_de="【雑学】夜中に目が覚める人の心理",
                      view=500_000),
        _dong_de_xuat("https://youtu.be/DEKHAC00004", tieu_de="Một chủ đề hoàn toàn khác biệt",
                      view=1_000),
    ]
    log = []
    ket = chay_mot_ngay(
        goc, "K1", che_do="thu", hom_nay=_dt.date(2026, 9, 28), on_log=log.append,
        chay_mot_nut=lambda *a, **k: None, doc_danh_sach=_danh_sach_gia_day_du(moi=moi),
        video_da_lam_nhom=lambda g, k: set())

    assert ket["run"]["nguon"]["ma"] == "DEKHAC00004"  # KHÔNG chọn ứng viên trùng đề
    assert any("loại TRUNGDE0003 vì trùng tiêu đề" in dong for dong in log)

