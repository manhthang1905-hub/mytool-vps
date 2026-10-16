"""Việc tự động 100% (16/10/2026 — chủ: "mục đích cuối VPS này auto 100%"; duyệt "Cho tự đổi, có rào" + "Cho tự xoá").

Bộ phân loại người/máy của "Việc của bạn", ghim (mục gộp tuỳ chọn sau 7 ngày + ghim bù video cũ), đổi tiêu đề tự áp có
rào, dọn bản Chrome cũ, đề xuất bộ não / cò sức khoẻ → hàng việc máy có kiểu, ổ đĩa chỉ báo người khi máy hết cách.

Cô lập: mọi thứ trong `tmp_path`; không mạng, không Chrome, không tiến trình thật. Mã video / kênh đều giả.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
import time
from pathlib import Path

import pytest

GOC_KHO = Path(__file__).resolve().parent.parent
if str(GOC_KHO / "vm") not in sys.path:
    sys.path.insert(0, str(GOC_KHO / "vm"))

import may_cmt_dom as mcd  # noqa: E402

import core.giam_doc as gd  # noqa: E402
from core import bang_dieu_khien as bdk  # noqa: E402
from core import don_chrome_cu, don_dia, vm_cai_dat  # noqa: E402
from core.giam_doc import cuu_ctr  # noqa: E402
from core.giam_doc.du_lieu import BangSo  # noqa: E402
from core.giam_doc.suc_khoe import VIEC_CUA_BAN as VIEC_SUC_KHOE  # noqa: E402

BAY = dt.datetime(2026, 10, 16, 12, 0)
V1, V2, V3, V4 = "FAKEvid0001", "FAKEvid0002", "FAKEvid0003", "FAKEvid0004"


def _ghi(p, du):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _k(ma):
    return {"ma": ma, "tu_chay": False, "bay_gio": {"chu": "", "muc": "nghi"}, "video": {}, "ke_hoach": []}


def _anh(kenh, con_gb=100.0):
    return {"kenh": [_k(m) for m in kenh], "kenh_khac": [], "o_dia": {"con_gb": con_gb}}


def _viec(goc, kenh=(), con_gb=100.0, bay=BAY):
    may = []
    ds = bdk.viec_cua_ban(goc, anh=_anh(list(kenh), con_gb), bay_gio=bay, gio_lich="02:00",
                          thu_muc_vm=os.path.join(goc, "vm"), may_tu_lam=may)
    return ds, may


# ═══ 1. BỘ PHÂN LOẠI NGƯỜI / MÁY ═════════════════════════════════════════════

@pytest.mark.parametrize("muc,ky_vong", [
    ({"khoa": "ghim:" + V1, "chu": "Ghim bình luận"}, "may"),
    ({"khoa": "duyet-sua:s-1", "chu": "Giám đốc kênh: Đổi tiêu đề video"}, "may"),
    ({"khoa": "giam-doc:K:abc", "chu": "Giám đốc kênh: " + VIEC_SUC_KHOE}, "may"),
    ({"khoa": "giam-doc:K:abc", "chu": "Giám đốc kênh: Đổi tiêu đề video X “a” thành “b”."}, "may"),
    ({"khoa": "giam-doc:K:abc", "chu": "Giám đốc kênh: Quyết định lớn chờ bạn duyệt: chien_luoc"}, "nguoi"),
    ({"khoa": "giam-doc:K:abc", "chu": "Giám đốc kênh: Đăng nhập lại Google trên Chrome kênh K"}, "nguoi"),
    ({"khoa": "nao:n001", "kenh": "KA", "chu": "Bộ não đề xuất: Bật Thử nghiệm và so sánh (bìa) cho " + V1}, "may"),
    ({"khoa": "nao:n001", "chu": "Bộ não đề xuất: Bật Thử nghiệm và so sánh (bìa) cho " + V1}, "nguoi"),  # không biết kênh
    ({"khoa": "nao:n003", "kenh": "KA", "chu": "Bộ não đề xuất: Thử nghiệm và so sánh cho " + V1 + " — cần đăng nhập lại"},
     "nguoi"),
    ({"khoa": "nao:n002", "chu": "Bộ não đề xuất: Đổi ngách kênh K sang chủ đề tiền bạc"}, "nguoi"),
    ({"khoa": "vi", "chu": "Ví còn 50.000₫"}, "nguoi"),
    ({"khoa": "dang-nhap", "chu": "Chưa đăng nhập ví"}, "nguoi"),
    ({"khoa": "viec-la:1", "chu": "Mục lạ chưa có bộ chạy máy"}, "nguoi"),
    ({"khoa": "x", "chu": "gì cũng được", "loai_viec": "may"}, "may"),
])
def test_bo_phan_loai_duy_nhat(muc, ky_vong):
    assert bdk.phan_loai_muc(muc) == ky_vong


def test_cong_cuoi_chuyen_viec_may_sang_dong_may_dang_tu_lam(tmp_path):
    """Đề xuất não máy làm được không lên Việc của bạn; đề xuất chiến lược thì vẫn lên."""
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), {"KA/KA-0001": {"video_id": V1},
                                                              "KA/KA-0002": {"video_id": V2}})
    _ghi(os.path.join(goc, "nao", "hanh-dong.json"), {"hanh_dong": [
        {"id": "n001", "luc": "2026-10-15T06:00:00", "lenh": "de-xuat", "trang_thai": "mo",
         "tham_so": {"kenh": "", "noi_dung": "Bật Thử nghiệm và so sánh (bìa) trong Studio cho {0}, {1}".format(V1, V2)}},
        {"id": "n002", "luc": "2026-10-15T06:00:00", "lenh": "de-xuat", "trang_thai": "mo",
         "tham_so": {"kenh": "KA", "noi_dung": "Đổi ngách kênh KA sang chủ đề tiền bạc"}}]})
    ds, may = _viec(goc)
    assert [v["khoa"] for v in ds] == ["nao:n002"]
    assert [x["khoa"] for x in may] == ["nao:n001"]
    bdk.danh_dau_xong(goc, "nao:n002")          # khoá cũ vẫn ẩn được
    assert _viec(goc)[0] == []


# ═══ 2. GHIM: không còn mục từng video; mục gộp tuỳ chọn sau ≥ 7 ngày bị chặn ═══

def _so_cmt(goc, chan_tu, cuoi, them=None):
    so = {"_kenh:KA": {"can_xac_minh": cuoi, "cho_xac_minh_tu": chan_tu},
          V1: {"kenh": "KA", "ma": "KA-0001", "da_dang_moi": "2026-10-01 07:00:00", "trang_thai": "cho-xac-minh",
               "ghim_cho_xac_minh": cuoi},
          V2: {"kenh": "KA", "ma": "KA-0002", "da_dang_moi": "2026-10-02 07:00:00", "trang_thai": "cho-xac-minh",
               "ghim_cho_xac_minh": cuoi},
          V3: {"kenh": "KB", "ma": "KB-0001", "da_dang_moi": "2026-10-01 07:00:00", "trang_thai": "da-dang"}}
    so.update(them or {})
    _ghi(os.path.join(goc, "vm", "logs", "cmt-dom.json"), so)
    for k in ("KA", "KB"):
        vm_cai_dat.luu(goc, k, ghim_dom=True)


def test_ghim_khong_con_tung_video_muc_gop_chi_sau_7_ngay(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "KA", "can-ghim.md"),
         "- [2026-10-10 16:11] **a** — https://www.youtube.com/watch?v={0}\n  > x\n"
         "- [2026-10-10 16:11] **b** — https://www.youtube.com/watch?v={1}\n  > y\n".format(V1, V2))
    _so_cmt(goc, "", "2026-10-16 01:00:00")        # đầu đợt lấy từ can-ghim.md: 10/10 → 6 ngày
    ds, may = _viec(goc, ["KA", "KB"])
    assert not [v for v in ds if v["khoa"].startswith("ghim")], "6 ngày: chưa nhắc, không mục từng video"
    assert any(x["khoa"] == "may:ghim" and "3 video" in x["chu"] for x in may)
    ds, _ = _viec(goc, ["KA", "KB"], bay=BAY + dt.timedelta(days=1, hours=6))
    gop = [v for v in ds if v["khoa"].startswith("ghim")]
    assert [v["khoa"] for v in gop] == ["ghim-xac-minh"], "MỘT mục gộp cho cả máy"
    assert "Tuỳ chọn" in gop[0]["chu"] and "KA" in gop[0]["chu"] and "2 video" in gop[0]["chu"]
    assert "KB" not in gop[0]["chu"] and "tự thử lại" in gop[0]["chu"]
    assert ("Chép link", "chep_link", {"url": "https://www.youtube.com/verify"}) in gop[0]["nut"]
    # bấm "Đã xử lý" → ẩn 7 ngày rồi nhắc lại nếu vẫn bị chặn
    bdk.danh_dau_xong(goc, "ghim-xac-minh", bay_gio=BAY + dt.timedelta(days=1, hours=6))
    assert not [v for v in _viec(goc, ["KA"], bay=BAY + dt.timedelta(days=2))[0] if v["khoa"] == "ghim-xac-minh"]


def test_ghim_muc_gop_tat_khi_da_ghim_duoc_hoac_het_bi_chan(tmp_path):
    goc = str(tmp_path)
    _so_cmt(goc, "2026-10-01 01:00:00", "2026-10-16 01:00:00",
            {V4: {"kenh": "KA", "ma": "KA-0003", "da_dang_moi": "x", "da_ghim": "2026-10-16 03:00:00"}})
    assert not [v for v in _viec(goc, ["KA"])[0] if v["khoa"] == "ghim-xac-minh"], "đã ghim được sau lần chặn cuối"
    _so_cmt(goc, "2026-10-01 01:00:00", "2026-10-10 01:00:00")
    assert not [v for v in _viec(goc, ["KA"])[0] if v["khoa"] == "ghim-xac-minh"], "lần chặn cuối quá 3 ngày"
    _so_cmt(goc, "2026-10-01 01:00:00", "2026-10-16 01:00:00")
    assert [v["khoa"] for v in _viec(goc, ["KA"])[0]] == ["ghim-xac-minh"]
    vm_cai_dat.luu(goc, "KA", ghim_dom=False)
    assert _viec(goc, ["KA"])[0] == [], "kênh tắt ghim: không nhắc"


# ═══ 3. GHIM BÙ video cũ chưa từng thử ghim ════════════════════════════════════

def test_chon_ghim_bu_video_cu_chua_thu_ghim():
    bay = dt.datetime(2026, 10, 16, 20, 0)
    so = {
        "_kenh:K": {"cap_nhat": "x"},
        "v_cu_1": {"kenh": "K", "ma": "K-0001", "da_dang_moi": "2026-09-30 05:00:00", "trang_thai": "da-dang",
                   "ghim": "tat", "lan_thu_ghim": 0},
        "v_cu_2": {"kenh": "K", "ma": "K-0002", "da_dang_moi": "2026-10-02 05:00:00", "trang_thai": "da-dang"},
        "v_ghim": {"kenh": "K", "ma": "K-0003", "da_dang_moi": "2026-10-02 05:00:00", "da_ghim": "x"},
        "v_tat": {"kenh": "K", "ma": "K-0004", "da_dang_moi": "x", "trang_thai": "tat-binh-luan"},
        "v_tran": {"kenh": "K", "ma": "K-0005", "da_dang_moi": "x", "lan_thu_ghim": mcd.TRAN_THU_GHIM},
        "v_mat": {"kenh": "K", "ma": "K-0006", "da_dang_moi": "x", "lan_kiem_lai": 3},
        "v_hom_nay": {"kenh": "K", "ma": "K-0007", "da_dang_moi": "x", "bu_ghim_luc": "2026-10-16 08:00:00"},
        "v_bu_het": {"kenh": "K", "ma": "K-0008", "da_dang_moi": "x", "trang_thai": "da-dang",
                     "lan_bu_ghim": mcd.TRAN_BU_GHIM},
        "v_xm": {"kenh": "K", "ma": "K-0009", "da_dang_moi": "2026-10-01 05:00:00", "trang_thai": "cho-xac-minh",
                 "ghim_cho_xac_minh": "2026-10-15 01:00:00", "lan_bu_ghim": 9},
        "v_xm_nay": {"kenh": "K", "ma": "K-0010", "da_dang_moi": "x", "trang_thai": "cho-xac-minh",
                     "ghim_cho_xac_minh": "2026-10-16 01:00:00"},
        "v_chua_moi": {"kenh": "K", "ma": "K-0011", "trang_thai": "dang-gui"},
        "v_khac": {"kenh": "K2", "ma": "K2-0001", "da_dang_moi": "x", "trang_thai": "da-dang"},
    }
    ra = mcd.chon_ghim_bu(so, "K", bay)
    assert [g["video_id"] for g in ra] == ["v_cu_2", "v_xm", "v_cu_1"], "mới trước; cho-xac-minh thử mãi mỗi ngày"
    assert all(g["bu_ghim"] and g["ma"] for g in ra)
    assert [g["video_id"] for g in mcd.chon_ghim_bu(so, "K", bay, bo_vid={"v_cu_2"})] == ["v_xm", "v_cu_1"]
    # hôm nay đã biết kênh bị chặn ghim → không thử bù gì cả
    so["_kenh:K"]["can_xac_minh"] = "2026-10-16 09:00:00"
    assert mcd.chon_ghim_bu(so, "K", bay) == []
    # cửa sổ mồi 7 ngày KHÔNG thấy video cũ (vì sao trước đây chúng không bao giờ được ghim)
    hang = [{"Mã gói": "K-0001", "Ngày đăng": "30/09/2026", "Giờ đăng": "05:00", "Trạng thái đăng": "ĐÃ ĐĂNG",
             "Video ID": "v_cu_1", "Tiêu đề": "t"}]
    assert mcd.chon_goi_can_moi(hang, {}, {"v_cu_1": so["v_cu_1"]}, "K", bay) == []


def test_ghim_bu_chi_ghim_binh_luan_co_san_khong_gui_moi(tmp_path):
    from test_vm_may_cmt_dom import HANDLE_URL, SEED, VID, TrangGia, _may

    chu = SEED.replace("🌱", "")
    tr = TrangGia(luong_xem=[{"id": "m", "noi_dung": chu, "tac_gia_href": HANDLE_URL, "ghim": False,
                              "cua_minh": True, "hrefs": [HANDLE_URL]}])

    def tra_kenh(*_a):
        raise AssertionError("ghim bù không tra danh sách Studio (mồi đã lên = video đã công khai)")
    may = _may(tmp_path, tr, tra_kenh=tra_kenh, cai={"ghim_dom": True})
    may.so.cap_nhat(VID, kenh="K", ma="K-0005", da_dang_moi="2026-09-30 05:00:00", trang_thai="da-dang", ghim="tat",
                    lan_gui=1, van_ban=SEED)
    goi = mcd.chon_ghim_bu(may.so.doc(), "K", dt.datetime.now())
    assert [g["video_id"] for g in goi] == [VID]
    ket = may.dang_va_ghim(dict(goi[0], can_kiem_cong_khai=False))
    assert "có sẵn" in ket and "ĐÃ GHIM" in ket and tr.da_gui == []
    assert may.so.lay(VID)["da_ghim"] and may.so.lay("_kenh:K")["ghim_duoc"]
    # kênh bị chặn ghim: ghi đầu đợt; cùng ngày không thử bù nữa
    tr2 = TrangGia(xac_minh=True, luong_xem=[{"id": "m", "noi_dung": chu, "tac_gia_href": HANDLE_URL,
                                              "ghim": False, "cua_minh": True, "hrefs": [HANDLE_URL]}])
    may2 = _may(tmp_path / "b", tr2, tra_kenh=tra_kenh, cai={"ghim_dom": True})
    may2.so.cap_nhat(VID, kenh="K", ma="K-0005", da_dang_moi="2026-09-30 05:00:00", trang_thai="da-dang", lan_gui=1,
                     van_ban=SEED)
    assert "CHƯA GHIM" in may2.dang_va_ghim(dict(mcd.chon_ghim_bu(may2.so.doc(), "K", dt.datetime.now())[0],
                                                 can_kiem_cong_khai=False))
    k = may2.so.lay("_kenh:K")
    assert k["cho_xac_minh_tu"] and k["can_xac_minh"] and mcd.chon_ghim_bu(may2.so.doc(), "K", dt.datetime.now()) == []
    # không đọc thấy bình luận mồi (kể cả sổ thiếu `lan_gui`) → KHÔNG BAO GIỜ gửi mồi mới khi ghim bù
    tr3 = TrangGia()
    may3 = _may(tmp_path / "c", tr3, tra_kenh=tra_kenh, cai={"ghim_dom": True})
    may3.so.cap_nhat(VID, kenh="K", ma="K-0005", da_dang_moi="2026-09-30 05:00:00", trang_thai="da-dang", van_ban=SEED)
    ket = may3.dang_va_ghim(dict(mcd.chon_ghim_bu(may3.so.doc(), "K", dt.datetime.now())[0], can_kiem_cong_khai=False))
    assert "không gửi mới" in ket and tr3.da_gui == [] and may3.so.lay(VID)["lan_kiem_lai"] == 1


# ═══ 4. ĐỔI TIÊU ĐỀ TỰ ÁP CÓ RÀO ═══════════════════════════════════════════════

K = "GDR"


def _bs(goc="", *, ctr_hong=2.0, xem_hong=60, n_ref=3, n_cung_tuoi=3, lich_su=None, thang=False):
    hong = {"id": V1, "ma_goi": K + "-0007", "tieu_de": "【脳科学】tiêu đề cũ", "cum": [], "ket_luan": "truot",
            "thang": thang, "tuoi_gio": 70.0, "lich_su_sua": list(lich_su or []), "tieu_de_da_cham": [],
            "tu_tool": True,
            "chup": [{"tuoi": 66.0, "moc": "66h", "hien_thi": 3000, "ctr": 3.0, "ctr_browse": ctr_hong, "xem": xem_hong}]}
    bs = BangSo(goc=goc, ma_kenh=K, bay_gio=BAY, cai={"giam_doc": "goi_y", "giam_doc_studio": True}, ctr_muc_tieu=5.0)
    bs.pct_de_xuat_kenh = 10.0
    ref = [{"id": "FAKEref%04d" % i, "ma_goi": K + "-000%d" % i, "tieu_de": "ref", "cum": [], "ket_luan": "truot",
            "thang": False, "tuoi_gio": 200.0, "lich_su_sua": [], "tieu_de_da_cham": [], "tu_tool": True,
            "chup": [{"tuoi": 64.0, "moc": "64h", "hien_thi": 4000, "ctr": 4.0, "ctr_browse": 4.5, "xem": 200},
                     {"tuoi": 150.0, "moc": "150h", "hien_thi": 9000, "ctr": 4.0, "ctr_browse": 5.0, "xem": 500}]}
           for i in range(1, n_ref + 1)]
    for r in ref[n_cung_tuoi:]:
        r["chup"] = r["chup"][1:]          # không có bản chụp cùng tuổi (chỉ bản 150h)
    bs.video = [hong] + ref
    return bs


def test_rao_qua_khi_duoi_trung_vi_ca_ctr_lan_xem_cung_tuoi():
    r = cuu_ctr.kiem_rao(_bs(), _bs().video[0], [])
    assert r["duoc"] and r["so"]["loai_ctr"] == "trang chủ" and r["so"]["n_ctr"] == 3 and r["so"]["xem_trung_vi"] == 200


@pytest.mark.parametrize("bs,chua", [
    (_bs(thang=True), "thắng"),
    (_bs(ctr_hong=4.6), "≥ trung vị"),                     # CTR trang chủ ≥ trung vị kênh cùng tuổi
    (_bs(xem_hong=250), "lượt xem"),                        # lượt xem ≥ trung vị kênh cùng tuổi
    (_bs(n_ref=2), "chua_du"),                              # < 3 video của kênh: chẩn đoán cổng chưa đủ
    (_bs(n_cung_tuoi=2), "cùng tuổi để so CTR"),           # 3 video nhưng < 3 có bản chụp CÙNG TUỔI
    (_bs(lich_su=[{"loai": "tieu_de", "luc": "2026-10-05T03:00:00"}]), "14 ngày"),
])
def test_rao_chan(bs, chua):
    r = cuu_ctr.kiem_rao(bs, bs.video[0], [])
    assert not r["duoc"] and not r["cho"] and chua in r["ly_do"]


def test_rao_14_ngay_tinh_dung_moc_va_tran_ngay_kenh():
    bs = _bs(lich_su=[{"loai": "tieu_de", "luc": "2026-10-01T11:00:00"}])     # 15 ngày trước → qua
    assert cuu_ctr.kiem_rao(bs, bs.video[0], [])["duoc"]
    ds = [{"id": "s-x", "video_id": "FAKEkhac001", "trang_thai": "da_xep", "tu_ap_luc": "2026-10-16T00:10:00"}]
    r = cuu_ctr.kiem_rao(bs, bs.video[0], ds)
    assert not r["duoc"] and r["cho"], "trần 1 lần / kênh / ngày → hoãn, không bỏ"
    ds = [{"id": "s-y", "video_id": V1, "trang_thai": "da_sua", "luc": "2026-09-20T00:10:00"}]
    assert "14 ngày" in cuu_ctr.kiem_rao(bs, bs.video[0], ds)["ly_do"], "mục đang chạy của chính video"


def test_muc_cho_duyet_cu_tu_chay_theo_rao_va_ghi_nao(tmp_path, monkeypatch):
    """3 mục chờ duyệt cũ chảy tự động: mục qua rào → tu_ap (dong_bo xếp hàng sửa); mục thứ hai cùng ngày → cho_rao;
    mục rào chặn → bo. Mỗi quyết định ghi não bộ phận "tieu-de"."""
    from core import nao_bo_phan

    nao = []
    monkeypatch.setattr(nao_bo_phan, "ghi", lambda goc, bo_phan, loai, **kw: nao.append((bo_phan, loai, kw)) or True)
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", K, "kenh.yaml"), 'ma: "{0}"\ngiam_doc: "goi_y"\ngiam_doc_studio: true\n'.format(K))
    bs = _bs(goc)
    bs.video.append(dict(bs.video[0], id=V2, ma_goi=K + "-0008"))
    bs.video.append(dict(bs.video[0], id=V3, ma_goi=K + "-0009", thang=True))
    muc = lambda vid, i: {"id": "s-%s-%d" % (vid, i), "video_id": vid, "ma_goi": "", "tieu_de_cu": "cũ",  # noqa: E731
                          "tieu_de_moi": "mới", "trang_thai": "cho_duyet", "duyet_boi": "", "luc": "2026-10-13T00:00:00"}
    _ghi(cuu_ctr.duong_duyet(goc, K), {"kenh": K, "muc": [muc(V1, 1), muc(V2, 2), muc(V3, 3)]})
    assert cuu_ctr.xu_ly(goc, K, bs, [], None) == []
    tt = {m["video_id"]: m["trang_thai"] for m in cuu_ctr.doc_duyet(goc, K)}
    assert tt == {V1: "tu_ap", V2: "cho_rao", V3: "bo"} and not cuu_ctr.cho_duyet(goc, K)
    assert [x[0] for x in nao] == ["tieu-de"] * 3 and {x[2]["so"]["quyet"] for x in nao} == {"tu_ap", "cho_rao", "bo"}
    assert cuu_ctr.dong_bo(goc, bay_gio=BAY)["xep"] == 1, "tu_ap → hàng sửa giờ vắng (đo trước/sau + tự đổi lại)"
    # hôm sau: mục hoãn được xét lại → tu_ap (mục hôm qua không còn tính vào trần ngày)
    bs.bay_gio = BAY + dt.timedelta(days=1)
    cuu_ctr.xu_ly(goc, K, bs, [], None)
    assert {m["video_id"]: m["trang_thai"] for m in cuu_ctr.doc_duyet(goc, K)}[V2] == "tu_ap"


def test_bang_dieu_khien_khong_con_muc_duyet_sua(tmp_path):
    goc = str(tmp_path)
    _ghi(cuu_ctr.duong_duyet(goc, "KA"), {"kenh": "KA", "muc": [
        {"id": "s-1", "video_id": V1, "tieu_de_cu": "a", "tieu_de_moi": "b", "trang_thai": "cho_duyet"}]})
    ds, may = _viec(goc, ["KA"])
    assert not [v for v in ds if v["khoa"].startswith("duyet-sua")]
    assert any(x["khoa"] == "may:doi-tieu-de" and "1 mục" in x["chu"] for x in may)


# ═══ 5. DỌN BẢN CHROME CŨ ═══════════════════════════════════════════════════════

def _cay_chrome(cha, ten="KA"):
    b = os.path.join(cha, ten, "App", "Chrome-bin")
    for t in (os.path.join(cha, ten, ten + ".exe"), os.path.join(b, "chrome.exe"), os.path.join(b, "new_chrome.exe"),
              os.path.join(cha, ten, "Data", "profile", "Default", "Cookies")):
        _ghi(t, "x")
    for ban in ("1.0.0.1", "2.0.0.1", "3.0.0.1", "4.0.0.1"):
        _ghi(os.path.join(b, ban, "chrome.dll"), "0" * 1000)
        _ghi(os.path.join(b, ban, "Locales", "vi.pak"), "0" * 500)
    _ghi(os.path.join(b, "chrome.VisualElementsManifest.xml"), "<x Square150x150Logo='4.0.0.1\\VisualElements\\Logo.png'/>")
    os.chmod(os.path.join(b, "1.0.0.1", "Locales", "vi.pak"), 0o444)     # tệp chỉ-đọc vẫn xoá được
    return b


def _ban(duong):
    return {"chrome.exe": "3.0.0.1", "new_chrome.exe": "4.0.0.1"}.get(os.path.basename(duong), "")


def test_chrome_cu_thu_khong_xoa_that_xoa_ban_cu_giu_ban_dung(tmp_path):
    cha = str(tmp_path / "TL")
    b = _cay_chrome(cha)
    os.makedirs(os.path.join(cha, "MyTool"))
    os.makedirs(os.path.join(cha, "KhongPhaiChrome", "App"))
    dang_chay = [os.path.join(b, "2.0.0.1", "notification_helper.exe")]
    goc = os.path.join(cha, "MyTool")
    kq = don_chrome_cu.chay(goc, thu=True, doc_phien_ban=_ban, tien_trinh=lambda: dang_chay)
    assert [x["ten"] for x in kq["bo"]] == ["KA"] and kq["bo"][0]["giu"] == ["3.0.0.1", "4.0.0.1"]
    ket = {v["ten"]: v["ket"] for v in kq["bo"][0]["xoa"]}
    assert ket == {"1.0.0.1": "se_xoa", "2.0.0.1": "dang_chay"} and kq["bytes"] == 1500
    assert all(os.path.isdir(os.path.join(b, x)) for x in ("1.0.0.1", "2.0.0.1", "3.0.0.1", "4.0.0.1")), "thử: không xoá"
    kq = don_chrome_cu.chay(goc, thu=False, doc_phien_ban=_ban, tien_trinh=lambda: dang_chay)
    assert sorted(os.listdir(b)) == ["2.0.0.1", "3.0.0.1", "4.0.0.1", "chrome.VisualElementsManifest.xml",
                                     "chrome.exe", "new_chrome.exe"]
    assert kq["so_ban"] == 1 and kq["bytes"] == 1500 and "đã xoá" in don_chrome_cu.tom_tat(kq)
    assert os.path.isfile(os.path.join(cha, "KA", "Data", "profile", "Default", "Cookies")), "không đụng hồ sơ"
    assert os.path.isfile(os.path.join(cha, "KA", "KA.exe"))


def test_chrome_cu_khong_chac_thi_giu_het(tmp_path):
    cha = str(tmp_path / "TL")
    b = _cay_chrome(cha)
    goc = os.path.join(cha, "MyTool")
    kq = don_chrome_cu.chay(goc, thu=False, doc_phien_ban=lambda p: "", tien_trinh=lambda: [])
    assert kq["bo"][0]["bo_qua"] and kq["so_ban"] == 0 and os.path.isdir(os.path.join(b, "1.0.0.1"))
    kq = don_chrome_cu.chay(goc, thu=False, doc_phien_ban=_ban, tien_trinh=lambda: None)
    assert kq["loi"] and kq["so_ban"] == 0 and os.path.isdir(os.path.join(b, "1.0.0.1")), "không liệt kê được tiến trình"


@pytest.mark.skipif(sys.platform != "win32", reason="khoá tệp đang mở là hành vi Windows")
def test_chrome_cu_tep_dang_mo_thi_bo_qua_khong_xoa_do(tmp_path):
    cha = str(tmp_path / "TL")
    b = _cay_chrome(cha)
    goc = os.path.join(cha, "MyTool")
    with open(os.path.join(b, "1.0.0.1", "chrome.dll"), "rb"):
        kq = don_chrome_cu.chay(goc, thu=False, doc_phien_ban=_ban, tien_trinh=lambda: [])
    ket = {v["ten"]: v["ket"] for v in kq["bo"][0]["xoa"]}
    assert ket["1.0.0.1"] == "dang_dung" and ket["2.0.0.1"] == "da_xoa"
    assert os.path.isfile(os.path.join(b, "1.0.0.1", "Locales", "vi.pak")), "đang dùng: nguyên vẹn, không xoá dở"
    # thư mục xoá dở lần trước (.dang-xoa) → lượt sau xoá tiếp
    _ghi(os.path.join(b, "0.9.0.1.dang-xoa", "a.pak"), "0" * 10)
    kq = don_chrome_cu.chay(goc, thu=False, doc_phien_ban=_ban, tien_trinh=lambda: [])
    assert sorted(t for t in os.listdir(b) if t[0].isdigit()) == ["3.0.0.1", "4.0.0.1"]


def test_don_dia_goi_chrome_va_ghi_ket_qua(tmp_path, monkeypatch):
    goc = str(tmp_path / "MyTool")
    os.makedirs(goc)
    kq = don_dia.chay(goc, thu=True, danh_sach_kenh=[], con_trong_gb_fn=lambda _g: 20.0,
                      goc_chrome=str(tmp_path / "khong-co"))
    assert "chrome" in kq and kq["chrome"]["so_ban"] == 0
    du = don_dia.ghi_ket_qua(goc, kq, bay_gio=BAY.timestamp(), con_sau_gb=31.0)
    assert don_dia.doc_ket_qua(goc)["con_sau_gb"] == 31.0 and du["con_truoc_gb"] == 20.0


# ═══ 6. Ổ ĐĨA: chỉ việc người khi máy đã dọn mà vẫn dưới ngưỡng ═════════════════

def _kq_dia(goc, gio_truoc, con_sau):
    _ghi(don_dia.tep_ket_qua(goc), {"luc": (BAY - dt.timedelta(hours=gio_truoc)).timestamp(), "luc_doc": "16/10 09:00",
                                    "con_sau_gb": con_sau, "kenh_chua_tu_don": ["KB"]})


def test_o_dia_may_lo_duoc_thi_khong_bao_nguoi(tmp_path):
    goc = str(tmp_path)
    ds, may = _viec(goc, con_gb=21.0)                       # chưa có lượt dọn, chưa tới mức hỏng
    assert not [v for v in ds if v["khoa"] == "dia"] and any(x["khoa"] == "may:dia" for x in may)
    assert [v["muc"] for v in _viec(goc, con_gb=5.0)[0] if v["khoa"] == "dia"] == [bdk.HONG]
    _kq_dia(goc, 1, 31.0)                                    # lượt dọn vừa rồi lên được trên ngưỡng
    assert not [v for v in _viec(goc, con_gb=21.0)[0] if v["khoa"] == "dia"]
    _kq_dia(goc, 1, 20.0)                                    # dọn rồi vẫn dưới ngưỡng → người (nâng ổ)
    v = [v for v in _viec(goc, con_gb=20.0)[0] if v["khoa"] == "dia"][0]
    assert "nâng dung lượng ổ VPS" in v["goi_y"] and "KB" in v["goi_y"] and "hết phần dọn được" in v["chu"]
    _kq_dia(goc, 10, 31.0)                                   # máy dọn không chạy 10 giờ → người
    assert "không chạy" in [v for v in _viec(goc, con_gb=21.0)[0] if v["khoa"] == "dia"][0]["chu"]


# ═══ 7. ĐỀ XUẤT NÃO / CÒ SỨC KHOẺ → HÀNG VIỆC MÁY CÓ KIỂU ═══════════════════════

def test_kieu_viec_may_tach_theo_kenh_va_bo_chu_khong_phai_ma_video():
    chu = ("Bật Thử nghiệm và so sánh (bìa) trong Studio cho 3 video mới: {0}, {1} (KA); {2} (KB). Bìa hạng nhì có "
           "sẵn trong CHANNEL/<kênh>/ho-so-video/anh/*-bia-2.jpg").format(V1, V2, V3)
    ra = gd.kieu_viec_may(chu, "", {V1: "KA", V2: "KA", V3: "KB"})
    assert ra == [{"loai": "studio_test_compare", "kenh": "KA", "video_ids": [V1, V2]},
                  {"loai": "studio_test_compare", "kenh": "KB", "video_ids": [V3]}]
    assert [v["video_ids"] for v in gd.kieu_viec_may(chu, "KX")] == [[V1, V2, V3]], "không sổ: đoán mã, bỏ ho-so-video"
    assert gd.kieu_viec_may(VIEC_SUC_KHOE, "KA") == [{"loai": "studio_kiem_suc_khoe", "kenh": "KA", "video_ids": []}]
    assert gd.kieu_viec_may("Đổi ngách sang chủ đề tiền bạc", "KA") == []


def test_dinh_tuyen_de_xuat_nao_vao_hang_may_mot_lan(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"),
         {"KA/KA-0001": {"video_id": V1}, "KA/KA-0002": {"video_id": V2}, "KB/KB-0001": {"video_id": V3}})
    _ghi(os.path.join(goc, "nao", "hanh-dong.json"), [
        {"id": "n038", "luc": "2026-10-15T06:50:36", "lenh": "de-xuat", "trang_thai": "mo",
         "tham_so": {"kenh": "", "noi_dung": "Bật Thử nghiệm và so sánh (bìa) trong Studio cho {0}, {1} (KA); {2} (KB)"
                     .format(V1, V2, V3)}}])
    assert gd.dinh_tuyen_de_xuat_nao(goc, bay_gio=BAY) == 2
    assert gd.dinh_tuyen_de_xuat_nao(goc, bay_gio=BAY + dt.timedelta(hours=1)) == 0, "một lần"
    vk = gd.doc_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE)
    assert [(m["kenh"], m["video_ids"], m["nguon"], m["trang_thai"]) for m in vk] == [
        ("KA", [V1, V2], "nao:n038", "cho"), ("KB", [V3], "nao:n038", "cho")]
    assert gd.doc_viec_cho_nao(goc, BAY) == [], "việc có kiểu không lẫn vào hàng chữ cho bộ não"
    ds, may = _viec(goc)
    assert ds == [] and any(x["khoa"] == "may:studio_test_compare" and "KA, KB (3 video)" in x["chu"] for x in may)
    assert not any(x["khoa"] == "nao:n038" for x in may), "không lặp hai dòng cho cùng việc"


def test_suc_khoe_vao_hang_may_chi_bao_nguoi_khi_thay_canh_bao(tmp_path):
    goc = str(tmp_path)
    assert gd.ghi_viec_may(goc, "KA", VIEC_SUC_KHOE, gd.phan_loai_viec(VIEC_SUC_KHOE), bay_gio=BAY)
    assert not gd.ghi_viec_may(goc, "KA", VIEC_SUC_KHOE, "may", bay_gio=BAY + dt.timedelta(hours=4))
    m = gd.doc_viec_may_kieu(goc)[0]
    assert (m["loai"], m["kenh"], m["video_ids"], m["trang_thai"]) == ("studio_kiem_suc_khoe", "KA", [], "cho")
    assert _viec(goc, ["KA"])[0] == [], "chưa đọc Studio: không phải việc người"
    # bộ đọc Studio: không thấy gì → xong; 3 ngày sau cò vẫn báo → mở lại
    gd.cap_nhat_viec_may_kieu(goc, m["id"], trang_thai="xong", ket={"canh_bao": False}, bay_gio=BAY)
    assert not gd.ghi_viec_may(goc, "KA", VIEC_SUC_KHOE, "may", bay_gio=BAY + dt.timedelta(days=1))
    assert gd.ghi_viec_may(goc, "KA", VIEC_SUC_KHOE, "may", bay_gio=BAY + dt.timedelta(days=3))
    # thấy cảnh báo → MỘT việc người; bấm Đã xử lý thì ẩn
    gd.cap_nhat_viec_may_kieu(goc, m["id"], trang_thai="can_nguoi", ket={"canh_bao": True, "chi_tiet": "1 gậy"})
    ds = _viec(goc, ["KA"])[0]
    assert [v["khoa"] for v in ds] == ["suc-khoe:" + m["id"]] and "1 gậy" in ds[0]["chu"]
    bdk.danh_dau_xong(goc, ds[0]["khoa"])
    assert _viec(goc, ["KA"])[0] == []


def test_bo_chay_loi_qua_tran_thi_bo(tmp_path):
    goc = str(tmp_path)
    gd.ghi_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE, "KA", video_ids=[V1], nguon="nao:n1", bay_gio=BAY)
    i = gd.doc_viec_may_kieu(goc)[0]["id"]
    for _ in range(4):
        gd.cap_nhat_viec_may_kieu(goc, i, trang_thai="loi")
    assert gd.doc_viec_may_kieu(goc)[0]["trang_thai"] == "loi"
    gd.cap_nhat_viec_may_kieu(goc, i, trang_thai="loi")
    assert gd.doc_viec_may_kieu(goc) == [] and gd.doc_viec_may_kieu(goc, trang_thai="bo")[0]["lan_thu"] == 5
    assert not gd.ghi_viec_may_kieu(goc, gd.LOAI_TEST_COMPARE, "KA", video_ids=[], bay_gio=BAY), "thiếu video → không"
