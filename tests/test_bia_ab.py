"""Bìa A/B «tự chơi» (G4, 21/10/2026): `core/bia_ab.py` + bước phiên `vm/bia_ab_dom.py`.

Phủ: đọc gói `videoCreatorExperiment` khuôn thật (STARTED + NOT_ENOUGH_DATA vẫn đang chạy; FINISHED + winnerArm; phần
thời gian xem theo ARM_N), sửa đọc nhầm của A/B tiêu đề; kế hoạch phiên (video công khai ≤ 72 giờ, đủ bìa có dấu, không
đang thắng, chưa có thử nghiệm tiêu đề; video hẹn lịch chỉ thăm dò); khung cấm; sổ đặt / đọc / đóng quá hạn; bìa thắng
YouTube áp → hồ sơ theo (dấu cổng chữ giữ); A/B tiêu đề nhường; cặp họ kiểu chữ → hậu nghiệm `bia_du_lieu`; giám khảo ↔
người xem → `hieu_chuan`; tự kiểm; bước DOM với trang giả (không việc → không nối Chrome); agent có bước trong phiên.

Cô lập trong `tmp_path`; không mạng, không Chrome, không AI. Mã video / kênh đều GIẢ.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

GOC_KHO = Path(__file__).resolve().parent.parent
for _p in (str(GOC_KHO), str(GOC_KHO / "vm")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bia_ab_dom as bad  # noqa: E402
import studio_may_dom as sdm  # noqa: E402

from core import ab_tieu_de as ab  # noqa: E402
from core import bia_ab as ba  # noqa: E402
from core import bia_du_lieu as bd  # noqa: E402
from core import cong_chu  # noqa: E402
from core import hieu_chuan as hc  # noqa: E402

K = "BAX-T7"
V1, V2, V3, V4 = "FAKEbab0001", "FAKEbab0002", "FAKEbab0003", "FAKEbab0004"
BAY = dt.datetime(2026, 10, 22, 7, 40)


def _ghi(p, du):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    with io.open(str(p), "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


def _anh(p, mau):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    Image.new("RGB", (1280, 720), mau).save(str(p), format="JPEG", quality=90)
    return str(p)


def _goi(goc, ma, vid, luot, *, dau=True, mau=0):
    hs = Path(goc) / "CHANNEL" / K / "ho-so-video"
    _ghi(hs / (ma + ".json"), {"ma_goi": ma, "video_id": vid, "luot": luot,
                                "thumbnail": {"tep": "CHON-thumb_001.jpg", "kieu": "bia_lo", "diem_giam_khao": 74.0},
                                "bia_2": {"tep": "thumb_002.jpg", "so": 2, "tong_diem": 73.0,
                                          "bia_3": {"tep": "thumb_003.jpg", "so": 3, "tong_diem": 70.0}}})
    for i, (ten, m) in enumerate(((ma + ".jpg", (200, mau, 0)), (ma + "-bia-2.jpg", (0, 200, mau)),
                                  (ma + "-bia-3.jpg", (mau, 0, 200)))):
        p = _anh(hs / "anh" / ten, m)
        if dau:
            cong_chu.ghi_dau(p, "chu gia", doc=["chu gia", "chu gia"])
    _ghi(Path(goc) / "PROJECTS" / "AUTO" / K / luot / "7-thumbnail" / "_lo" / "xep-hang.json",
         {"top": [{"ma": "y01-1", "kieu_chu": "tran", "tong": 74.0, "diem": {"bam_nhu_thang": 7.0}},
                  {"ma": "y02-3", "kieu_chu": "dai", "tong": 73.0, "diem": {"bam_nhu_thang": 8.0}},
                  {"ma": "y03-2", "kieu_chu": "tran", "tong": 70.0, "diem": {"bam_nhu_thang": 6.0}}]})


@pytest.fixture()
def goc(tmp_path):
    g = tmp_path / "MyTool"
    _ghi(g / "CHANNEL" / K / "kenh.yaml", "giam_doc: goi_y\ngiam_doc_studio: true\n")
    _goi(str(g), K + "-0001", V1, "0001", mau=10)            # công khai 05:00 hôm nay (2h40 tuổi)
    _goi(str(g), K + "-0002", V2, "0002", mau=40)            # công khai 4 ngày trước — quá tuổi
    _goi(str(g), K + "-0003", V3, "0003", mau=70)            # hẹn lịch ngày mai 05:00
    _ghi(g / "vm" / "logs" / "so-video-id.json", {
        K + "/" + K + "-0001": {"video_id": V1, "lich": "22/10/2026 05:00"},
        K + "/" + K + "-0002": {"video_id": V2, "lich": "18/10/2026 05:00"},
        K + "/" + K + "-0003": {"video_id": V3, "lich": "23/10/2026 05:00"}})
    return str(g)


def _exp(state="CREATOR_EXPERIMENT_STATE_STARTED", rs="CREATOR_EXPERIMENT_RESULT_STATE_NOT_ENOUGH_DATA",
         winner="CREATOR_EXPERIMENT_ARM_UNSPECIFIED", selected="CREATOR_EXPERIMENT_ARM_UNSPECIFIED", phan=None, n=3):
    r = {"resultState": rs, "winnerArm": winner}
    if phan:
        r["armResults"] = [{"arm": "CREATOR_EXPERIMENT_ARM_{0}".format(i + 1), "watchtimeFraction": f}
                           for i, f in enumerate(phan)]
    return {"armCount": "CREATOR_EXPERIMENT_ARM_COUNT_{0}".format(n), "state": state, "selectedArm": selected,
            "experimentArmData": [{"thumbnail": {"thumbnails": [{"url": "https://i9.ytimg.com/vi/x/mq_custom_{0}.jpg"
                                                                 .format(i + 1)}]}} for i in range(n)],
            "experimentStartTime": {"seconds": "1792255089"}, "result": r,
            "experimentConfiguration": {"hasThumbnails": True, "hasTitles": False}, "experimentId": 1}


# ═══ 1. đọc gói thử nghiệm khuôn thật ═══════════════════════════════════════

def test_doc_thu_nghiem_khuon_that():
    k = ba.doc_thu_nghiem(_exp())
    assert k["co"] and k["dang_chay"] and not k["xong"] and k["so_nhanh"] == 3 and k["thang"] is None
    k = ba.doc_thu_nghiem(_exp("CREATOR_EXPERIMENT_STATE_FINISHED", "CREATOR_EXPERIMENT_RESULT_STATE_NO_WINNER",
                               selected="CREATOR_EXPERIMENT_ARM_1", phan=[0.34, 0.33, 0.33]))
    assert k["xong"] and k["thang"] is None and k["chon"] == 0 and k["ti_phan"] == {0: 0.34, 1: 0.33, 2: 0.33}
    k = ba.doc_thu_nghiem(_exp("CREATOR_EXPERIMENT_STATE_FINISHED", "CREATOR_EXPERIMENT_RESULT_STATE_WINNER_FOUND",
                               winner="CREATOR_EXPERIMENT_ARM_2", selected="CREATOR_EXPERIMENT_ARM_2",
                               phan=[0.3, 0.45, 0.25]))
    assert k["xong"] and k["thang"] == 1 and k["chon"] == 1 and k["co_bia"] is True
    assert ba.doc_thu_nghiem({})["co"] is False


def test_ab_tieu_de_khong_dong_nham_thu_nghiem_dang_chay():
    """21/10: STARTED + NOT_ENOUGH_DATA bị A/B tiêu đề đóng «không kết luận» khi thử nghiệm còn chạy."""
    exp = _exp(n=2)
    exp["experimentArmData"] = [{"title": {"textSegments": [{"text": "【A】tiêu đề một"}]}},
                                {"title": {"textSegments": [{"text": "【A】tiêu đề hai"}]}}]
    assert ab.doc_ket_thu_nghiem(exp)["xong"] is False
    xong = dict(exp, state="CREATOR_EXPERIMENT_STATE_FINISHED",
                result={"resultState": "CREATOR_EXPERIMENT_RESULT_STATE_WINNER", "winnerArm": "CREATOR_EXPERIMENT_ARM_2",
                        "armResults": [{"arm": "CREATOR_EXPERIMENT_ARM_1", "watchtimeFraction": 0.4},
                                       {"arm": "CREATOR_EXPERIMENT_ARM_2", "watchtimeFraction": 0.6}]})
    k = ab.doc_ket_thu_nghiem(xong)
    assert k["xong"] and k["thang"] == 1 and not k["khong_ket_luan"]
    assert k["nhanh"][1]["so"]["watchtimeFraction"] == 0.6 and k["nhanh"][0]["tieu_de"] == "【A】tiêu đề một"


# ═══ 2. kế hoạch phiên + khung cấm ═════════════════════════════════════════

def test_ke_hoach_chon_video_cong_khai_moi_va_tham_do_hen_lich(goc):
    kh = ba.ke_hoach(goc, K, BAY, cai=dict(ba.CAI_DAT_MAC_DINH))
    assert [v["video_id"] for v in kh["dat"]] == [V1]
    bt = kh["dat"][0]["bien_the"]
    assert [b["nhan"] for b in bt] == ["A", "B", "C"] and all(b["dau_ok"] for b in bt)
    assert [b["ho"] for b in bt] == ["tran", "dai", "tran"] and bt[1]["diem_gk"] == 73.0 and bt[1]["ma"] == "y02-3"
    assert kh["tham_do_len_lich"] == V3 and kh["doc"] == [] and kh["bo"] == []


def test_ke_hoach_kenh_tat_da_co_ab_tieu_de_va_dang_thang(goc, monkeypatch):
    _ghi(Path(goc) / "CHANNEL" / K / "kenh.yaml", "giam_doc: goi_y\n")              # như TL4-T7: không giam_doc_studio
    assert ba.ke_hoach(goc, K, BAY)["dat"] == []
    _ghi(Path(goc) / "CHANNEL" / K / "kenh.yaml", "giam_doc_studio: true\nbia_ab: true\n")
    monkeypatch.setattr(ba, "_ab_tieu_de_muc", lambda g, k, v: {"trang_thai": "da_dat"} if v == V1 else None)
    kh = ba.ke_hoach(goc, K, BAY)
    assert kh["dat"] == [] and kh["bo"][0]["trang_thai"] == ba.TT_DA_CO
    monkeypatch.setattr(ba, "_ab_tieu_de_muc", lambda g, k, v: None)
    monkeypatch.setattr(ba, "_dang_thang", lambda g, k, m: "CTR 9% ≥ trung vị")
    kh = ba.ke_hoach(goc, K, BAY)
    assert kh["dat"] == [] and "THẮNG" in kh["bo"][0]["ly_do"]
    assert ba.ghi_bo(goc, K, kh["bo"], BAY) == 1 and ba.ke_hoach(goc, K, BAY)["bo"] == []     # một lần


def test_ke_hoach_bia_a_chua_dau_la_tam(goc):
    os.remove(cong_chu.duong_dau(os.path.join(goc, "CHANNEL", K, "ho-so-video", "anh", K + "-0001.jpg")))
    kh = ba.ke_hoach(goc, K, BAY)
    assert kh["dat"] == [] and kh["bo"] == [] and "chưa có dấu" in kh["hoan"][0]["ly_do"]


def test_trong_gio_cam(goc):
    cai = dict(ba.CAI_DAT_MAC_DINH)
    assert "khung cấm" in ba.trong_gio_cam(goc, dt.datetime(2026, 10, 22, 3, 0), cai)
    assert ba.trong_gio_cam(goc, BAY, cai) == ""
    sv = {"X/X-1": {"video_id": "FAKEx", "lich": "22/10/2026 08:20"}}
    assert "hẹn công khai" in ba.trong_gio_cam(goc, BAY, cai, so_video=sv)


# ═══ 3. sổ: đặt → đọc → bìa thắng → hồ sơ + học ══════════════════════════════

def _bien(goc, ma):
    return [dict(b, sha1=ba.sha1_tep(b["tep"])) for b in ba.bien_the_goi(goc, K, ma)]


def test_dat_doc_ket_qua_bia_thang_ap_ho_so(goc, monkeypatch):
    from core import nao_bo_phan, ho_so_video
    nao = []
    monkeypatch.setattr(nao_bo_phan, "ghi", lambda *a, **kw: nao.append((a, kw)) or True)
    m = ba.ghi_dat(goc, K, V1, K + "-0001", _bien(goc, K + "-0001"), {"ket": "da_dat", "so_bia": 3}, BAY)
    assert m["trang_thai"] == ba.TT_DANG and m["so_bien_the"] == 3 and ba.dang_chay(goc, K, V1)
    assert nao[-1][0][1:] == ("bia", "chon")
    assert ba.uu_tien_bia(goc, K, V1, K + "-0001", BAY)                     # A/B tiêu đề nhường
    assert ba.can_doc_ket_qua(ba.doc_so(goc, K), BAY + dt.timedelta(days=1)) == []
    nay = BAY + dt.timedelta(days=3)
    assert ba.can_doc_ket_qua(ba.doc_so(goc, K), nay) == [V1]
    assert ba.ghi_ket_qua(goc, K, V1, _exp(phan=[0.3, 0.4, 0.3]), nay) is None          # còn chạy
    assert ba.can_doc_ket_qua(ba.doc_so(goc, K), nay + dt.timedelta(hours=3)) == []    # ≤ 1 lần / ngày
    anh_hs = ho_so_video.duong_anh_ho_so(goc, K, K + "-0001")
    sha_b = ba.sha1_tep(os.path.join(os.path.dirname(anh_hs), K + "-0001-bia-2.jpg"))
    kq = ba.ghi_ket_qua(goc, K, V1, _exp("CREATOR_EXPERIMENT_STATE_FINISHED", "CREATOR_EXPERIMENT_RESULT_STATE_WINNER",
                                         winner="CREATOR_EXPERIMENT_ARM_2", selected="CREATOR_EXPERIMENT_ARM_2",
                                         phan=[0.3, 0.5, 0.2]), nay + dt.timedelta(days=1))
    assert kq["ket_luan"] == ba.KL_THANG and kq["thang"] == "B" and kq["chon"] == "B"
    assert kq["ti_phan"] == {"A": 0.3, "B": 0.5, "C": 0.2} and "đổi theo bìa B" in kq["ap_ho_so"]
    assert ba.sha1_tep(anh_hs) == sha_b and cong_chu.kiem_dau(anh_hs) == ""           # hồ sơ = bìa đang chạy, CÓ DẤU
    assert os.path.isfile(os.path.join(os.path.dirname(anh_hs), "_truoc-do-bia", os.path.basename(anh_hs)))
    hs = ho_so_video.doc_ho_so(goc, K, K + "-0001")
    assert hs["lich_su_sua"][-1]["loai"] == "bia" and hs["thumbnail"]["chu_khop"]["ok"] is True
    assert nao[-1][0][1:] == ("bia", "ket_qua") and nao[-1][1]["so"]["thang"] == "B"
    assert not ba.dang_chay(goc, K, V1) and ba.uu_tien_bia(goc, K, V1, K + "-0001", BAY)   # xong: tiêu đề vẫn nhường
    # cặp + họ: B (dai) thắng A, C (tran) → 2 cặp khác họ
    assert ba.thong_ke_ho_ab(goc, K) == {"tran": {"thang": 0.0, "thua": 2.0, "n_thu": 1.0},
                                         "dai": {"thang": 2.0, "thua": 0.0, "n_thu": 1.0}}


def test_ghi_dat_loi_thu_lai_roi_bo_va_khong_quyen(goc):
    bt = _bien(goc, K + "-0001")
    for i in range(ba.SO_LOI_TOI_DA - 1):
        assert ba.ghi_dat(goc, K, V1, K + "-0001", bt, {"ket": "loi", "ly_do": "hộp không mở"}, BAY)["trang_thai"] == ba.TT_LOI
    assert [v["video_id"] for v in ba.ke_hoach(goc, K, BAY)["dat"]] == [V1]               # còn thử lại
    assert ba.ghi_dat(goc, K, V1, K + "-0001", bt, {"ket": "loi"}, BAY)["trang_thai"] == ba.TT_BO
    assert ba.ke_hoach(goc, K, BAY)["dat"] == [] and ba.uu_tien_bia(goc, K, V1, K + "-0001", BAY) == ""
    ba.ghi_dat(goc, K, V2, K + "-0002", bt, {"ket": "khong_quyen", "ly_do": "cần tính năng nâng cao"}, BAY)
    kh = ba.ke_hoach(goc, K, BAY)
    assert kh["dat"] == [] and "chưa dùng được" in kh["ly_do"]


def test_dong_qua_han_va_khong_con_thu_nghiem(goc):
    bt = _bien(goc, K + "-0001")
    ba.ghi_dat(goc, K, V1, K + "-0001", bt, {"ket": "da_dat"}, BAY)
    assert ba.dong_qua_han(goc, K, BAY + dt.timedelta(days=10)) == []
    assert len(ba.dong_qua_han(goc, K, BAY + dt.timedelta(days=22))) == 1
    m = ba.muc_cua(ba.doc_so(goc, K), V1)
    assert m["trang_thai"] == ba.TT_XONG and m["ket_qua"]["ket_luan"] == ba.KL_KHONG
    ba.ghi_dat(goc, K, V2, K + "-0002", _bien(goc, K + "-0002"), {"ket": "da_dat"}, BAY)
    kq = ba.ghi_ket_qua(goc, K, V2, {}, BAY + dt.timedelta(days=4))                       # Studio gỡ thử nghiệm
    assert kq["ket_luan"] == ba.KL_KHONG and "gỡ" in kq["ly_do"]


# ═══ 4. học: họ kiểu chữ, giám khảo ═══════════════════════════════════════

def _xong(goc, vid, ma, phan, thang=None, chon=None, diem=(74.0, 73.0, 70.0)):
    bt = _bien(goc, ma)
    for b, d in zip(bt, diem):
        b["diem_gk"] = d
    ba.ghi_dat(goc, K, vid, ma, bt, {"ket": "da_dat"}, BAY)
    w = "CREATOR_EXPERIMENT_ARM_{0}".format("ABC".index(thang) + 1) if thang else "CREATOR_EXPERIMENT_ARM_UNSPECIFIED"
    return ba.ghi_ket_qua(goc, K, vid, _exp("CREATOR_EXPERIMENT_STATE_FINISHED", "X", winner=w, phan=phan,
                                            selected="CREATOR_EXPERIMENT_ARM_1"), BAY + dt.timedelta(days=4),
                          ap_ho_so=False)


def test_cap_mem_khi_khong_ket_luan_va_dich_hau_nghiem(goc):
    _xong(goc, V1, K + "-0001", [0.40, 0.35, 0.25])
    cap = ba.cap_ab(ba.muc_cua(ba.doc_so(goc, K), V1))
    assert {(c["thang"], c["thua"]) for c in cap} == {("A", "B"), ("A", "C"), ("B", "C")}
    assert max(c["w"] for c in cap) == ba.W_MEM and min(c["w"] for c in cap) == pytest.approx(0.125)
    ho = ba.thong_ke_ho_ab(goc, K)
    assert ho["tran"]["thang"] > 0 and ho["dai"]["thua"] > 0
    assert ba.dich_hau_nghiem({}, "tran", 1.0) == 0.0
    assert ba.dich_hau_nghiem({"dai": {"thang": 6.0, "thua": 0.0}}, "dai", 2.0) == pytest.approx((7 / 8 - 0.5) * 2.0)
    tk = {"trung_vi_ctr": 5.0, "do_lech_ctr": 1.0, "trung_vi_imp": 1000.0,
          "ho": {"tran": {"n": 4, "imp": 4000, "ctr": 5.0}, "dai": {"n": 4, "imp": 4000, "ctr": 5.0}}}
    a = bd.hau_nghiem(tk, ["tran", "dai"])
    b = bd.hau_nghiem(dict(tk, ab={"dai": {"thang": 6.0, "thua": 0.0}, "tran": {"thang": 0.0, "thua": 6.0}}),
                      ["tran", "dai"])
    assert a["tran"][0] == a["dai"][0] and b["dai"][0] > a["dai"][0] > b["tran"][0]


def test_giam_khao_va_hieu_chuan(goc):
    _xong(goc, V1, K + "-0001", [0.5, 0.3, 0.2], thang="A")                # giám khảo xếp A nhất: đúng
    _xong(goc, V2, K + "-0002", [0.2, 0.3, 0.5], thang="C")                # sai, ngược hoàn toàn
    do = ba.do_giam_khao(goc, [K])
    c = do["chung"]
    assert c["co_thang"] == 2 and c["top1"] == 0.5 and c["ngau_nhien"] == pytest.approx(1 / 3, abs=1e-3)
    assert c["n"] == 2 and c["tau"] == 0.0
    ts = {"chung": {}, "kenh": {}}
    hc.them_bia_ab(goc, ts, [K])
    assert ts["chung"][hc.BO_CHAM_AB]["n"] == 2 and ts["chung"][hc.BO_CHAM_AB]["muc"] == "chua_du"
    assert "bia_lo_ab" in hc.LUI["bia_lo"] and "bia_lo_ab" in hc.LUI["bia_lo_bam"]


def test_trong_so_bia_lo_lui_ve_ab(tmp_path):
    goc = str(tmp_path)
    os.makedirs(os.path.join(goc, *hc.THU_MUC))
    _ghi(hc.duong_trong_so(goc), {"chung": {"bia_lo": {"w": 1.0, "muc": "chua_du", "n": 3},
                                            "bia_lo_ab": {"w": 0.25, "muc": "khong_du_bao", "rho": -0.1, "n": 12}},
                                  "kenh": {}})
    x = hc.trong_so(goc, "KA", "bia_lo")
    assert x["bo_cham"] == "bia_lo_ab" and x["w"] == 0.25


# ═══ 5. tự kiểm ════════════════════════════════════════════════════════════

def test_tu_kiem_ket_chua_dat_va_viec_nguoi(goc, monkeypatch):
    nay = BAY + dt.timedelta(hours=40)                                     # V1 công khai 42 giờ, chưa đặt
    assert ba.muc_tu_kiem(goc, nay, [K], ghi=False) == []                  # bước phiên chưa chạy lần nào: không đòi
    ba.danh_dau_phien(goc, K, BAY - dt.timedelta(days=1))
    ds = ba.muc_tu_kiem(goc, nay, [K], ghi=False)
    assert [x["khoa"] for x in ds] == ["bia_ab:chua_dat:" + V1] and ds[0]["tt"] == "hong"
    ba.ghi_dat(goc, K, V1, K + "-0001", _bien(goc, K + "-0001"), {"ket": "da_dat"}, BAY - dt.timedelta(days=31))
    ds = ba.muc_tu_kiem(goc, nay, [K], ghi=False)
    assert ds[0]["khoa"] == "bia_ab:chay:" + V1 and ds[0]["tt"] == "hong" and "KẸT" in ds[0]["bang_chung"]
    monkeypatch.setattr(ab, "kenh_khong_ab", lambda g, k, b=None, ds=None: "kênh chưa bật tính năng nâng cao")
    ds = ba.muc_tu_kiem(goc, nay, [K], ghi=False)
    q = [x for x in ds if x["khoa"] == "bia_ab:quyen:" + K][0]
    assert q["nguoi"] and "youtube.com/verify" in q["can_lam"]


def test_tu_kiem_bia_song_trung_tam_thang(goc):
    _xong(goc, V1, K + "-0001", [0.3, 0.5, 0.2], thang="B")
    so = ba.doc_toan_so(goc, K)
    so["muc"][-1]["ket_qua"]["chon"] = "B"
    ba.ghi_toan_so(goc, K, so)
    vt = lambda p: [1] * 256 if p and p.endswith("-bia-2.jpg") or "tai-len" in str(p) else [0] * 256  # noqa: E731
    ds = ba.muc_tu_kiem(goc, BAY + dt.timedelta(days=5), [K], ghi=False, bia_song=lambda v: [1] * 256, van_tay=vt)
    s = [x for x in ds if x["khoa"] == "bia_ab:song:" + V1][0]
    assert s["tt"] == "dat"
    ds = ba.muc_tu_kiem(goc, BAY + dt.timedelta(days=5), [K], ghi=False, bia_song=lambda v: [0] * 256, van_tay=vt)
    assert [x for x in ds if x["khoa"] == "bia_ab:song:" + V1][0]["tt"] == "hong"
    ds = ba.muc_tu_kiem(goc, BAY + dt.timedelta(days=5), [K], ghi=False, bia_song=lambda v: 1 / 0, van_tay=vt,
                        can_kiem=lambda k: False)
    assert [x for x in ds if x["khoa"] == "bia_ab:song:" + V1][0]["giu"] is True


# ═══ 6. A/B tiêu đề nhường · đổi bìa trực tiếp bị chặn khi đang thử ═════════════

def test_ab_tieu_de_nhuong_video_co_bia_ab(goc):
    assert ba.uu_tien_bia(goc, K, V1, K + "-0001", BAY).startswith("chờ phiên kênh")    # chưa có mục, đủ bìa
    for p in ("-bia-2.jpg", "-bia-3.jpg"):
        os.remove(cong_chu.duong_dau(os.path.join(goc, "CHANNEL", K, "ho-so-video", "anh", K + "-0001" + p)))
    assert ba.uu_tien_bia(goc, K, V1, K + "-0001", BAY) == ""                           # không thử bìa được


def test_doi_bia_bi_chan_khi_dang_thu(goc):
    from core import do_bia
    ba.ghi_dat(goc, K, V1, K + "-0001", _bien(goc, K + "-0001"), {"ket": "da_dat"}, BAY)
    moi = _anh(Path(goc) / "tam" / "moi.jpg", (9, 9, 9))
    with pytest.raises(RuntimeError, match="Thử nghiệm A/B bìa"):
        do_bia.xep_doi_bia(goc, K, K + "-0001", moi, ly_do="thử")
    import may_dang_dom as mdd
    assert mdd.bia_ab_dang_chay_vm(goc, K, V1) and mdd.bia_ab_dang_chay_vm(goc, K, V2) == ""


# ═══ 7. bước DOM (trang giả) + agent ══════════════════════════════════════════

class _St:
    def __init__(self, nut=None):
        self.bo = {"phan_tu": {"ab_nut": {}}}
        self.nut = nut
        self.chup = []

    def tim(self, khoa, han=0, cho_tat=False):
        return self.nut

    def ghi_bang_chung(self, ten):
        self.chup.append(ten)
        return {"anh": ""}


class _S:
    def __init__(self, nut=None):
        self.st = _St(nut)

    def chup(self, ten):
        pass


@pytest.fixture()
def buoc(goc, monkeypatch):
    monkeypatch.setattr(bad, "GOC_TOOL", goc)
    monkeypatch.setattr(sdm, "tai_bia_a", lambda g, k, v, ghi, tai=None: "")
    monkeypatch.setattr(sdm, "thu_muc_so", lambda: os.path.join(goc, "vm", "logs", "studio-may"))
    from core import studio_may as sm
    monkeypatch.setattr(sm, "_cham_mac_dinh", lambda p: {"dat": True, "diem": 90})

    def vt(p):                                  # vân tay giả theo nội dung (ảnh màu trơn có dHash trùng nhau)
        import hashlib
        with open(p, "rb") as tep:
            return list(hashlib.sha256(tep.read()).digest()) * 2
    monkeypatch.setattr(sm, "_van_tay", vt)
    return goc


def _chay(nhat, **kw):
    return bad.chay_buoc(K, bay=BAY, ghi=nhat.append, dau_lai=None, khoa=lambda: True, **kw)


def test_buoc_dat_doc_va_tham_do(buoc, monkeypatch):
    goc = buoc
    dat = []

    def mot(S, vid, kh, ghi, thu=False, khong_luu=False):
        dat.append((vid, [os.path.basename(u["tai_len"]) for u in kh["chon"]], kh["tieu_de"]))
        return {"ket": "da_dat", "so_bia": 1 + len(kh["chon"]), "che_do": "bia", "trang_thai": "dang_chay"}
    monkeypatch.setattr(sdm, "test_mot_video", mot)
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: ({"videoCreatorExperiment": {}},
                                                              {"nut": [{"chu": "Thử nghiệm A/B", "tat": True}], "chu": ""}))
    nhat = []
    ma, bc = _chay(nhat, phien=lambda k, tu_giu, ghi, lam: (0, lam(_S({"tat": True}), None)))
    assert ma == bad.MA_XONG and dat and dat[0][0] == V1 and len(dat[0][1]) == 2 and dat[0][2] == []
    m = ba.muc_cua(ba.doc_so(goc, K), V1)
    assert m["trang_thai"] == ba.TT_DANG and [b["nhan"] for b in m["bien_the"]] == ["A", "B", "C"]
    assert [b["ho"] for b in m["bien_the"]] == ["tran", "dai", "tran"] and all(b["sha1"] for b in m["bien_the"])
    assert bc["len_lich"]["video_id"] == V3
    assert ba.doc_toan_so(goc, K)["meta"]["len_lich"]["tt"] == "khong"                 # nút tắt trên video hẹn lịch
    # phiên sau (3 ngày): đọc kết quả, không đặt lại, không thăm dò lại
    dat.clear()
    exp = _exp("CREATOR_EXPERIMENT_STATE_FINISHED", "X", winner="CREATOR_EXPERIMENT_ARM_1",
               selected="CREATOR_EXPERIMENT_ARM_1", phan=[0.5, 0.3, 0.2])
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: ({"videoCreatorExperiment": exp}, {}))
    ma, bc = bad.chay_buoc(K, bay=BAY + dt.timedelta(days=3), ghi=nhat.append, dau_lai=None, khoa=lambda: True,
                           phien=lambda k, tu_giu, ghi, lam: (0, lam(_S(), None)))
    assert all(d[0] != V1 for d in dat) and [d[0] for d in dat] == [V3]       # V3 nay đã công khai → đặt
    assert bc["doc"][V1]["ket"] == ba.KL_THANG and bc["doc"][V1]["thang"] == "A" and not bc["len_lich"]


def test_buoc_khong_viec_khong_noi_chrome(buoc, monkeypatch):
    _ghi(Path(buoc) / "CHANNEL" / K / "kenh.yaml", "giam_doc: tat\n")
    nhat = []
    ma, bc = _chay(nhat, phien=lambda *a, **k: pytest.fail("không việc thì không được nối Chrome"))
    assert ma == bad.MA_XONG and "tắt" in bc["ly_do"]


def test_buoc_khung_cam_khong_noi_chrome(buoc):
    nhat = []
    ma, bc = bad.chay_buoc(K, bay=dt.datetime(2026, 10, 22, 4, 30), ghi=nhat.append, dau_lai=None, khoa=lambda: True,
                           phien=lambda *a, **k: pytest.fail("khung cấm"))
    assert ma == bad.MA_XONG and "khung cấm" in bc["ly_do"]


def test_buoc_loi_mot_video_ghi_loi_va_bo_ung_vien_truot(buoc, monkeypatch):
    goc = buoc
    monkeypatch.setattr(sdm, "test_mot_video", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("hộp không mở")))
    monkeypatch.setattr(sdm, "dong_hop_khong_luu", lambda S, ghi: None)
    monkeypatch.setattr(sdm, "luu_dang_tat", lambda S: True)
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: (None, {}))
    nhat = []
    ma, bc = _chay(nhat, phien=lambda k, tu_giu, ghi, lam: (0, lam(_S(), None)))
    assert ma == bad.MA_HONG and ba.muc_cua(ba.doc_so(goc, K), V1)["trang_thai"] == ba.TT_LOI
    assert bad.tam_thoi("chưa qua cổng chữ: đọc lại 「x」: chưa kiểm được") and not bad.tam_thoi("trùng bìa A đang chạy")


def test_phien_agent_co_buoc_bia_ab_sau_cong_su_truoc_dong_chrome(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("vm_agent_bia_ab", GOC_KHO / "vm" / "agent.py")
    ag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ag)
    goi = []
    monkeypatch.setattr(ag, "GOC", str(GOC_KHO / "vm"))
    monkeypatch.setattr(ag, "_mo_chrome_viec_dang", lambda ch: True)
    monkeypatch.setattr(ag, "dong_chrome_kenh", lambda ch: goi.append("dong"))
    monkeypatch.setattr(ag, "doi_viec_khoa_may", lambda v: None)
    monkeypatch.setattr(ag, "_doc_trang_thai", lambda c: {})
    monkeypatch.setattr(ag, "co_token_oauth", lambda k: False)
    monkeypatch.setattr(ag, "_chay_mot_lan", lambda duong, kenh, nhan, han_giay, co_gi_them=("--mot-lan",):
                        goi.append((Path(duong).name, tuple(co_gi_them))) or ("ok", 0))
    ag.chay_mot_phien({}, {"kenh": "K", "cach_dang": "anh", "tu_dang": True}, "K")
    ten = [g[0] if isinstance(g, tuple) else g for g in goi]
    assert ("bia_ab_dom.py", ("--phien", "--trong-phien")) in goi
    assert ten.index("bia_ab_dom.py") > ten.index("cong_su_dom.py") and ten[-1] == "dong"
    goi.clear()
    ag.chay_mot_phien({"phien_bia_ab": False}, {"kenh": "K", "cach_dang": "anh", "tu_dang": True}, "K")
    assert "bia_ab_dom.py" not in [g[0] if isinstance(g, tuple) else g for g in goi]


def test_du_bao_chi_doc(goc):
    db = ba.du_bao(goc, [K], BAY, ngay=2)
    assert db["so_goi"] == 2 and db["se_thu"] == 2                          # V1 (công khai) + V3 (hẹn lịch)
    assert db["uoc_tuan"]["video"] == 7 and db["uoc_tuan"]["cap_so_sanh"] == pytest.approx(21.0)


def test_may_dang_tham_do_nut_ab_trong_hop_tai_len(tmp_path, monkeypatch):
    """CHỈ ĐỌC trong bước Chi tiết của hộp tải lên: ghi có/không nút «Thử nghiệm A/B» — không bấm gì."""
    import may_dang_dom as mdd
    monkeypatch.setattr(mdd, "THU_MUC_LOG", str(tmp_path))

    class Ta:
        def js_tho(self, bt):
            assert "click" not in bt
            return {"co": True, "so": 1, "tat": False, "chu": "Thử nghiệm A/B"}

    m = object.__new__(mdd.MayDangDom)
    m.kenh, m.nk = K, (lambda s: None)
    mdd.MayDangDom._tham_do_ab_upload(m, Ta(), K + "-0009")
    du = json.loads((tmp_path / "bia-ab-upload.json").read_text(encoding="utf-8"))
    assert du[K]["co"] is True and du[K]["tat"] is False and du[K]["ma"] == K + "-0009"

    class TaHong:
        def js_tho(self, bt):
            raise RuntimeError("tab đóng")
    mdd.MayDangDom._tham_do_ab_upload(m, TaHong(), K + "-0010")         # hỏng thì thôi, không ném


def test_skill_d27_khai_va_doc(goc):
    from core import ky_nang as kn
    k = kn.theo_ma("D27")
    assert k is not None and "bia_ab_dom.py" in k.lenh
    assert kn.k_bia_ab(goc, K)[0] == kn.CHO
    ba.ghi_dat(goc, K, V1, K + "-0001", _bien(goc, K + "-0001"), {"ket": "da_dat"}, BAY)
    assert kn.k_bia_ab(goc, K) == (kn.DAT, "1 dang_chay")
