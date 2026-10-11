"""Một cảnh bị máy chủ "nhận việc rồi bỏ đó" lặp lại không được giữ cả video hàng giờ.

TL1-T7/0026 (11–12/10/2026): 172/173 clip xong, cảnh 37 lần nào cũng treo 12 phút. Mỗi lần chạy khâu
bắn lại ĐÚNG tấm ảnh + lời nhắc ấy (khoá đầu + 2 khoá mới × 12'), ba lượt thử khâu, rồi vòng cứu còn "thử
y nguyên" thêm lần nữa trước khi viết lại lời nhắc → lỡ khe 05:00. Nay: treo đủ `TRAN_TREO_CLIP` lần với
cùng (ảnh, lời nhắc) → thôi gửi y nguyên (đếm qua khoá mới và qua các lần chạy khâu, sổ `_treo-clip.json`),
đi thẳng đường cứu: viết lại lời nhắc clip → vẽ lại ảnh BỐ CỤC MỚI. Vẫn chỉ clip thật (luật 07/10/2026).

Không gọi mạng: `_tao_job`/`_cho_job`/tải về đều là đồ giả.
"""

from __future__ import annotations

import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import auto_khau as ak  # noqa: E402
from core import su_co  # noqa: E402
from core.auto import LuotChay  # noqa: E402
from core.kenh import Kenh  # noqa: E402
from core.viet_lai_prompt import _BO_CUC  # noqa: E402

LOI_NHAC_CLIP = "a quiet cat walks slowly through the misty garden at dawn, soft light"
LOI_NHAC_MOI = "a quiet cat strolls slowly through the misty garden at dawn, gentle soft light"
LOI_NHAC_MOI_2 = "a quiet cat strolls gently through the misty garden at sunrise, gentle soft light"
LOI_NHAC_ANH = "a quiet cat in a misty garden at dawn, watercolor"


def _anh(duong, mau=(30, 90, 160)):
    from PIL import Image

    os.makedirs(os.path.dirname(duong), exist_ok=True)
    Image.new("RGB", (64, 36), mau).save(duong, "PNG")
    return duong


def _luot(tmp_path, so=3):
    d = tmp_path / "luot"
    canh = []
    for i in range(1, so + 1):
        _anh(str(d / "5-anh" / "{0}.png".format(i)))
        canh.append({"scene_id": i, "video_prompt": LOI_NHAC_CLIP, "img_prompt": LOI_NHAC_ANH,
                     "srt_start": "00:00:0{0},000".format(i - 1),
                     "srt_end": "00:00:0{0},800".format(i - 1)})
    (d / "6-clip").mkdir(parents=True)
    (d / "4-canh.json").write_text(json.dumps(canh), encoding="utf-8")
    return LuotChay(ma_kenh="K1", ma_luot="0001", thu_muc=str(d))


@pytest.fixture()
def cong(tmp_path, monkeypatch):
    """Cổng giả: `treo(so_canh, loi_nhac, dau_anh)` True → job treo (LoiKetJob sau 12' giả)."""
    luot = _luot(tmp_path)
    nhat_ky = []
    trang = {"gui": [], "phut": 0.0, "treo": lambda *_a: False, "ve_anh": [], "goi_ai": [],
             "phut_anh_moi": None}

    def url_anh(_bc, _luot, so, duong, **_k):
        return "https://anh.invalid/{0}-{1}.png".format(so, ak._dau_tep(duong))

    def tao_job(_bc, _ham, **kw):
        return dict(kw)

    def cho_job(_bc, job, **_k):
        so_canh = int(str(job["image_url"]).rsplit("/", 1)[1].split("-")[0])
        dau_anh = str(job["image_url"]).rsplit("-", 1)[1][:-4]
        trang["gui"].append((so_canh, job["idempotency_key"]))
        if trang["treo"](so_canh, job["prompt"], dau_anh):
            trang["phut"] += 12.0
            raise ak.LoiKetJob("đợi 12 phút mà máy chủ vẫn chưa trả kết quả")
        trang["phut"] += 2.0
        return {"id": "job-{0}".format(len(trang["gui"]))}

    def tai(_bc, _goi, dich, _dat_lai, _ten=""):
        with open(dich, "wb") as t:
            t.write(b"clip")
        return dich

    def goi_chat(loi_nhac, **_k):
        trang["goi_ai"].append(loi_nhac)
        if "text-to-video" not in loi_nhac:
            return "a calm cat in a misty garden, watercolor"
        return LOI_NHAC_MOI_2 if LOI_NHAC_MOI in loi_nhac else LOI_NHAC_MOI

    def lam_anh_gia(_bc, _luot, c, tep, _hop, so=None):
        trang["ve_anh"].append((int(c["scene_id"]), c["img_prompt"]))
        if trang["phut_anh_moi"] is None:
            trang["phut_anh_moi"] = trang["phut"]
        _anh(tep, mau=(200, 40 + 30 * len(trang["ve_anh"]), 10))      # tấm MỚI: nội dung khác

    monkeypatch.setattr(ak, "_url_anh_canh", url_anh)
    monkeypatch.setattr(ak, "_tao_job", tao_job)
    monkeypatch.setattr(ak, "_cho_job", cho_job)
    monkeypatch.setattr(ak, "_tai_ket_qua_dat_lai", tai)
    monkeypatch.setattr(ak, "_kiem_media", lambda *_a, **_k: None)
    monkeypatch.setattr(ak, "_lam_anh_canh", lam_anh_gia)
    monkeypatch.setattr(ak, "ThamChieu", lambda bc: ak._HopTrong())
    monkeypatch.setattr(ak, "_so_luong", lambda *a, **k: 2)
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=Kenh(ma="K1"), goi_chat=goi_chat,
                    client=types.SimpleNamespace(videos=types.SimpleNamespace(create=None)),
                    on_log=nhat_ky.append, ngu=lambda _g: None)
    return types.SimpleNamespace(bc=bc, luot=luot, trang=trang, nhat_ky=nhat_ky)


def _canh(luot, so):
    ds = json.loads(open(os.path.join(luot.thu_muc, "4-canh.json"), encoding="utf-8").read())
    return next(c for c in ds if int(c["scene_id"]) == so)


def _mot_clip(cong, so=2):
    c = _canh(cong.luot, so)
    anh = os.path.join(cong.luot.thu_muc, "5-anh", "{0}.png".format(so))
    ak._lam_clip(cong.bc, cong.luot, c, anh, os.path.join(cong.luot.thu_muc, "6-clip", "{0}.mp4".format(so)), 8)


# ── 1. `_lam_clip`: trần treo theo (ảnh, lời nhắc), nhớ qua các lần chạy ──────


def test_treo_hai_lan_thi_thoi_khong_dat_khoa_thu_ba(cong):
    cong.trang["treo"] = lambda *_a: True
    with pytest.raises(ak.LoiClipTreoLap):
        _mot_clip(cong)
    assert len(cong.trang["gui"]) == ak.TRAN_TREO_CLIP == 2, "khoá đầu + 1 khoá mới, không tới nấc (2/2)"
    assert cong.trang["phut"] == 24.0
    so_treo = json.loads(open(os.path.join(cong.luot.thu_muc, ak.TEP_TREO_CLIP), encoding="utf-8").read())
    assert so_treo["2"]["lan"] == 2


def test_lan_chay_khau_sau_khong_gui_lai_y_nguyen(cong):
    cong.trang["treo"] = lambda *_a: True
    with pytest.raises(ak.LoiClipTreoLap):
        _mot_clip(cong)
    truoc = len(cong.trang["gui"])
    with pytest.raises(ak.LoiClipTreoLap, match="máy chủ vẫn chưa trả kết quả"):
        _mot_clip(cong)       # lượt thử khâu / lượt nhặt lại: ném NGAY, không gọi máy chủ
    assert len(cong.trang["gui"]) == truoc


def test_treo_tinh_qua_ca_lan_chay_khau(cong):
    """Một lần treo ở lần chạy trước + một lần ở lần này = đủ trần (không reset theo tiến trình)."""
    lan = {"n": 0}

    def treo(*_a):
        lan["n"] += 1
        return True

    cong.trang["treo"] = treo
    ak._dem_treo(cong.luot, 2, ak._dau_treo_clip(_canh(cong.luot, 2), os.path.join(
        cong.luot.thu_muc, "5-anh", "2.png"), None), ak.LoiKetJob("đợi 12 phút"))
    with pytest.raises(ak.LoiClipTreoLap):
        _mot_clip(cong)
    assert lan["n"] == 1


def test_doi_loi_nhac_hoac_doi_anh_thi_dem_lai(cong):
    cong.trang["treo"] = lambda *_a: True
    with pytest.raises(ak.LoiClipTreoLap):
        _mot_clip(cong)
    c = _canh(cong.luot, 2)
    c["video_prompt"] = LOI_NHAC_MOI
    cong.trang["treo"] = lambda *_a: False
    anh = os.path.join(cong.luot.thu_muc, "5-anh", "2.png")
    ak._lam_clip(cong.bc, cong.luot, c, anh, os.path.join(cong.luot.thu_muc, "6-clip", "2.mp4"), 8)
    assert os.path.exists(os.path.join(cong.luot.thu_muc, "6-clip", "2.mp4"))
    so_treo = json.loads(open(os.path.join(cong.luot.thu_muc, ak.TEP_TREO_CLIP), encoding="utf-8").read())
    assert "2" not in so_treo, "clip ra rồi thì quên sổ treo của cảnh"


def test_cau_loi_khong_phai_su_co_may_chu_cung_khong_phai_noi_dung():
    e = ak.LoiClipTreoLap("cảnh 3: máy chủ nhận việc rồi bỏ đó 2 lần với cùng ảnh và lời nhắc clip "
                          "(máy chủ vẫn chưa trả kết quả) — thôi gửi lại y nguyên")
    assert su_co.phan_loai(e) == su_co.CHO_TIEP        # L3 không coi là CHET
    assert not ak._la_su_co_may_chu(e) and not ak._la_loi_noi_dung_clip(e)


# ── 2. khâu clip: cảnh treo lặp đi thẳng đường cứu, bố cục mới ───────────────


def test_tl1_0026_canh_treo_di_thang_viet_lai_roi_bo_cuc_moi(cong):
    """Cảnh 2 treo với ảnh gốc (dù lời nhắc nào) — chỉ ảnh vẽ lại mới ra. Các cảnh khác bình thường."""
    dau_goc = ak._dau_tep(os.path.join(cong.luot.thu_muc, "5-anh", "2.png"))
    cong.trang["treo"] = lambda so, _ln, dau_anh: so == 2 and dau_anh == dau_goc
    ket = ak._khau_clip(cong.bc)(cong.luot, cong.luot.tt("clip"))
    assert ket == {"so_clip": 3}
    gui_2 = [k for s, k in cong.trang["gui"] if s == 2]
    # mẻ: 2 lần treo (khoá đầu + 1 khoá mới) · cứu: KHÔNG thử y nguyên · viết lại lời nhắc: 2 lần treo
    # · ảnh bố cục mới: 1 lần ra.
    assert len(gui_2) == 5, gui_2
    assert len(set(gui_2)) == 5, "không khoá nào gửi lại y nguyên"
    assert cong.trang["phut_anh_moi"] == pytest.approx(48.0 + 2.0 * 2), \
        "ảnh bố cục mới sau 4 lần treo × 12' (+2 clip lành song song)"
    [(so, ln_anh)] = cong.trang["ve_anh"]
    assert so == 2 and ln_anh.startswith(_BO_CUC[0]), ln_anh
    assert not any("refused" in x for x in cong.trang["goi_ai"]), "không nhờ AI 'làm dịu' lời nhắc ảnh lành"
    c2 = _canh(cong.luot, 2)
    assert c2["video_prompt"] == LOI_NHAC_MOI and c2["img_prompt"] == ln_anh
    assert os.path.exists(os.path.join(cong.luot.thu_muc, "6-clip", "2.mp4"))


def test_het_vong_cuu_van_dung_bao_nguoi_va_lan_sau_nem_ngay(cong, monkeypatch):
    from core import bao_dong

    bao = []
    monkeypatch.setattr(bao_dong, "bao_dong_khan", lambda *a, **k: bao.append(a) or True)
    cong.trang["treo"] = lambda so, *_a: so == 2       # treo với mọi ảnh, mọi lời nhắc
    with pytest.raises(ak.LoiCanhKhongLamDuoc):
        ak._khau_clip(cong.bc)(cong.luot, cong.luot.tt("clip"))
    gui_2 = [k for s, k in cong.trang["gui"] if s == 2]
    # mẻ 2 + mỗi vòng (viết lại 2 + bố cục mới 2) × SO_VONG_CUU_CANH — có trần, không vòng vô hạn
    assert len(gui_2) == 2 + 4 * ak.SO_VONG_CUU_CANH
    assert len(cong.trang["ve_anh"]) == ak.SO_VONG_CUU_CANH
    assert [ln for _s, ln in cong.trang["ve_anh"]] == [_BO_CUC[0] + ": " + LOI_NHAC_ANH,
                                                       _BO_CUC[1] + ": " + LOI_NHAC_ANH],         "vòng 2 bố cục khác vòng 1, không chồng hai góc máy"
    assert [a[0] for a in bao] == ["clip_canh_khong_lam_duoc"]
    truoc = len(cong.trang["gui"])
    with pytest.raises(ak.LoiCanhKhongLamDuoc):
        ak._khau_clip(cong.bc)(cong.luot, cong.luot.tt("clip"))
    assert len(cong.trang["gui"]) == truoc, "lượt thử khâu sau: không gửi lại gì cho cảnh đã hết vòng"


def test_nhieu_canh_cung_treo_la_su_co_chung_khong_vao_cuu(cong, monkeypatch):
    """Cả mẻ treo (quá trần thiếu cho phép) = máy chủ treo → ném cho lượt thử khâu như cũ, quên sổ treo
    để lần sau gửi lại; không viết lại lời nhắc, không vẽ lại ảnh."""
    cong.trang["treo"] = lambda *_a: True
    with pytest.raises(ak.LoiClipTreoLap):
        ak._khau_clip(cong.bc)(cong.luot, cong.luot.tt("clip"))
    assert cong.trang["goi_ai"] == [] and cong.trang["ve_anh"] == []
    so_treo = json.loads(open(os.path.join(cong.luot.thu_muc, ak.TEP_TREO_CLIP), encoding="utf-8").read())
    assert so_treo == {}
    assert not os.path.exists(os.path.join(cong.luot.thu_muc, ak.TEP_CUU_CANH))


def test_het_han_muc_van_quay_ve_cho(cong, monkeypatch):
    """Đường hết hạn mức không đổi: chờ engine, không đốt vòng cứu, không đếm treo."""
    het = {"con": 1}
    cau = ("Kho tài khoản video đã dùng hết hạn mức credit hôm nay, dự kiến có lại từ khoảng 20:54 "
           "giờ Việt Nam. Bạn không bị trừ tiền.")
    goc = ak._cho_job

    def cho_job(bc, job, **k):
        if het["con"] > 0 and "/2-" in str(job["image_url"]):
            het["con"] -= 1
            raise RuntimeError(cau)
        return goc(bc, job, **k)

    monkeypatch.setattr(ak, "_cho_job", cho_job)
    monkeypatch.setattr(ak, "_ngu_cho_clip", lambda *_a, **_k: None)
    ket = ak._khau_clip(cong.bc)(cong.luot, cong.luot.tt("clip"))
    assert ket == {"so_clip": 3}
    assert cong.trang["goi_ai"] == [] and cong.trang["ve_anh"] == []
    assert any("hết hạn mức" in x for x in cong.nhat_ky)
