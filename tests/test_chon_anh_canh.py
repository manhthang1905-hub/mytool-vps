"""Ảnh cảnh chọn tốt nhất N ứng viên + giám khảo nội dung/giọng + viết lại lời nhắc (17/10/2026).

Mọi lời gọi ảnh/LLM đều giả. Xem `core/chon_anh_canh.py`.
"""
import json
import os
from types import SimpleNamespace

import pytest

from core import auto_khau
from core import chon_anh_canh as cac


def _muc(so, nd=8, gi=8, lo=8, pc=8, nv=None, kd=False, ly="ok"):
    return {"so": so, "noi_dung": nd, "giong": gi, "loi": lo, "phong_cach": pc, "nhan_vat": nv, "kinh_di": kd,
            "dau_hieu": ["faceless figure"] if kd else [], "loi_ve": [], "ly_do": ly}


# ═══ ĐỌC ĐIỂM GIÁM KHẢO ═══

def test_doc_cham_lay_muc_thap_nhat_va_bo_tam_thieu_muc():
    du = {"ung_vien": [_muc(1, nd=4, gi=9), _muc(2, nv=6), {"so": 3, "noi_dung": 9}, _muc(9), "rác"],
          "sua": "show the phone on the table"}
    kq = cac.doc_cham(du, 3)
    assert set(kq) == {1, 2}
    assert kq[1]["tong"] == 4.0          # mục tệ nhất chặn trần
    assert kq[2]["tong"] == 6.0          # nhân vật có điểm thì tính
    assert kq[1]["diem"]["nhan_vat"] is None
    assert kq[1]["sua"] == "show the phone on the table"


def test_doc_cham_kep_thang_va_co_kinh_di_dang_chu():
    kq = cac.doc_cham({"ung_vien": [dict(_muc(1, nd=14, gi=-2), kinh_di="true")]}, 1)
    assert kq[1]["diem"]["noi_dung"] == 10.0 and kq[1]["diem"]["giong"] == 0.0
    assert kq[1]["kinh_di"] is True and kq[1]["tong"] == 0.0


def test_doc_cham_giu_cau_ta_va_nhan_ve_len_anh(tmp_path):
    kq = cac.doc_cham({"ung_vien": [dict(_muc(1), ta="a grid of nine small panels", loi=0)]}, 1)
    assert kq[1]["ta"] == "a grid of nine small panels" and kq[1]["tong"] == 0.0
    from PIL import Image
    p = tmp_path / "a.png"
    Image.new("RGB", (1376, 768), (250, 250, 250)).save(p)
    import base64, io
    du = base64.b64decode(cac.anh_data_url(str(p), 768, nhan="2").split(",", 1)[1])
    im = Image.open(io.BytesIO(du))
    assert im.size == (768, 429)
    assert im.getpixel((5, 5))[0] > 150 and im.getpixel((5, 5))[1] < 100        # ô nhãn đỏ ở góc trên trái
    assert im.getpixel((700, 400)) >= (240, 240, 240)


def test_doc_cham_rac_thi_rong():
    assert cac.doc_cham(None, 3) == {} and cac.doc_cham({"x": 1}, 3) == {} and cac.doc_cham("abc", 3) == {}


def test_xep_hang_tam_sach_thang_tam_ron_diem_cao():
    ds = [{"tep": "a", "vong": 0, "so": 1, "cham": cac.doc_cham({"ung_vien": [_muc(1, 9, 9, 9, 9, kd=True)]}, 1)[1]},
          {"tep": "b", "vong": 0, "so": 2, "cham": cac.doc_cham({"ung_vien": [_muc(1, 6, 7, 7, 7)]}, 1)[1]},
          {"tep": "c", "vong": 0, "so": 3, "cham": None}]
    assert [u["tep"] for u in cac.xep_hang(ds)] == ["b", "a", "c"]


def test_loi_nhac_cham_co_cau_doc_va_tham_chieu():
    ln = cac.loi_nhac_cham(loi_doc="既読はついたのに", mo_ta="Close-up of the reference character", phong_cach="flat",
                           so_tham_chieu=1, so_ung_vien=3)
    assert "既読はついたのに" in ln and "The first 1 image(s) are REFERENCE" in ln and "1..3" in ln
    assert "kinh_di" in ln
    ln0 = cac.loi_nhac_cham(loi_doc="x", mo_ta="y", phong_cach="", so_tham_chieu=0, so_ung_vien=2)
    assert "REFERENCE" not in ln0 and "no character reference" in ln0


# ═══ CÂU GIỮ GIỌNG ═══

def test_cau_giu_giong_noi_mot_lan_va_kenh_dat_rieng():
    p = cac.ap_giong_an_toan("Close-up of a cup, flat style", cac.GIONG_AN_TOAN)
    assert p.endswith(cac.GIONG_AN_TOAN) and cac.ap_giong_an_toan(p, cac.GIONG_AN_TOAN) == p
    assert cac.giong_an_toan({}) == cac.GIONG_AN_TOAN
    assert cac.giong_an_toan({"tone_guard": "sunny  mood"}) == "sunny mood"
    assert cac.giong_an_toan({"tone_guard": ""}) == ""
    assert cac.ap_giong_an_toan("abc", "") == "abc"


def test_tach_than_duoi_theo_image_style():
    st = {"image_style": "Clean flat-vector minimalist psychology illustration matching the reference"}
    p = "Close-up of the reference character holding a phone with blue accent, " + st["image_style"] + ", no text"
    than, duoi = cac.tach_than_duoi(p, st)
    assert than == "Close-up of the reference character holding a phone with blue accent"
    assert duoi.startswith("Clean flat-vector")
    assert cac.tach_than_duoi("just a scene", st) == ("just a scene", "")


def test_viet_lai_canh_giu_reference_character_va_loai_rac():
    than = "Close-up of the reference character in a dark room with a looming shadow"
    tot = "Medium shot of the reference character smiling at a phone on a sunny kitchen table with orange accent"
    assert cac.viet_lai_canh(lambda l: "Prompt: " + tot, than, loi_doc="x", ghi_chu="-") == tot
    assert cac.viet_lai_canh(lambda l: "Medium shot of a woman smiling at a phone in a bright kitchen", than,
                             loi_doc="x", ghi_chu="-") == ""          # mất "the reference character"
    assert cac.viet_lai_canh(lambda l: "ok", than, loi_doc="x", ghi_chu="-") == ""
    assert cac.viet_lai_canh(lambda l: (_ for _ in ()).throw(RuntimeError("x")), than, loi_doc="", ghi_chu="") == ""
    assert cac.viet_lai_canh(None, than, loi_doc="", ghi_chu="") == ""


# ═══ VÒNG CHỌN ═══

class _May:
    """Máy vẽ + giám khảo + người viết lại giả. `diem[vong]` = list điểm (nd) từng tấm của vòng ấy."""

    def __init__(self, tmp_path, diem, n=3, kinh_di=None, cham_hong=False):
        self.tmp, self.diem, self.n = tmp_path, diem, n
        self.kinh_di = kinh_di or {}
        self.cham_hong = cham_hong
        self.ve_goi, self.cham_goi, self.viet_goi = [], [], []

    def ve(self, prompt, vong):
        self.ve_goi.append((prompt, vong))
        ra = []
        for i in range(self.n):
            p = self.tmp / "v{0}-{1}.png".format(vong, i + 1)
            p.write_bytes(b"png")
            ra.append(str(p))
        return ra

    def cham(self, tep, prompt):
        self.cham_goi.append((list(tep), prompt))
        if self.cham_hong:
            return {}
        vong = int(os.path.basename(tep[0])[1])
        du = {"ung_vien": [_muc(i + 1, nd=d, kd=self.kinh_di.get((vong, i + 1), False))
                           for i, d in enumerate(self.diem[vong])], "sua": "show it literally"}
        return cac.doc_cham(du, len(tep))

    def viet_lai(self, prompt, ghi_chu):
        self.viet_goi.append((prompt, ghi_chu))
        return "REWRITE{0} of the reference character".format(len(self.viet_goi))


def _chay(may, so=None, **kw):
    return cac.chon_canh(so_canh=5, prompt="Close-up of the reference character", loi_doc="既読", ve=may.ve,
                         cham=may.cham, viet_lai=may.viet_lai, so=so, ghi=lambda *_: None, **kw)


def test_dat_ngay_vong_dau_thi_khong_viet_lai(tmp_path):
    may = _May(tmp_path, {0: [6, 8, 7]})
    kq = _chay(may)
    assert len(may.ve_goi) == 1 and may.viet_goi == [] and len(may.cham_goi) == 1
    assert kq["chon"]["so"] == 2 and kq["chon"]["tong"] == 8.0 and kq["canh_bao"] == ""
    assert kq["so_anh"] == 3 and kq["so_cham"] == 1


def test_duoi_nguong_thi_viet_lai_va_chon_tam_cua_vong_sau(tmp_path):
    may = _May(tmp_path, {0: [4, 5, 3], 1: [6, 9, 5]})
    kq = _chay(may)
    assert [v for _p, v in may.ve_goi] == [0, 1]
    assert may.ve_goi[1][0] == "REWRITE1 of the reference character"
    assert "candidate 2: 5.0/10" in may.viet_goi[0][1] and "show it literally" in may.viet_goi[0][1]
    assert kq["chon"]["vong"] == 1 and kq["chon"]["so"] == 2 and kq["chon"]["prompt"].startswith("REWRITE1")
    assert kq["canh_bao"] == ""


def test_tran_hai_vong_viet_lai_canh_bao_khong_chan(tmp_path):
    may = _May(tmp_path, {0: [3, 6, 2], 1: [5, 4, 4], 2: [5, 5, 1]})
    kq = _chay(may)
    assert len(may.ve_goi) == 3 and len(may.viet_goi) == 2           # vòng 0 + 2 vòng viết lại, không hơn
    assert kq["chon"]["vong"] == 0 and kq["chon"]["so"] == 2           # tấm tốt nhất của MỌI vòng
    assert "sau 2 vòng viết lại vẫn 6.0/10" in kq["canh_bao"] and kq["xong"] is True


def test_co_ron_ep_viet_lai_du_diem_cao(tmp_path):
    may = _May(tmp_path, {0: [9, 9, 9], 1: [8, 7, 7]}, kinh_di={(0, 1): True, (0, 2): True, (0, 3): True})
    kq = _chay(may)
    assert len(may.ve_goi) == 2 and "CREEPY" in may.viet_goi[0][1]
    assert kq["chon"]["vong"] == 1 and kq["chon"]["kinh_di"] is False


def test_giam_khao_hong_thi_giu_tam_dau_khong_viet_lai(tmp_path):
    may = _May(tmp_path, {0: [1, 1, 1]}, cham_hong=True)
    kq = _chay(may)
    assert may.viet_goi == [] and len(may.ve_goi) == 1
    assert kq["chon"]["so"] == 1 and "không chấm được" in kq["canh_bao"]


def test_vong_dau_hong_thi_nem_vong_sau_hong_thi_giu_tam_tot(tmp_path):
    def ve_hong(prompt, vong):
        raise RuntimeError("máy chủ sập")
    with pytest.raises(RuntimeError, match="sập"):
        cac.chon_canh(so_canh=1, prompt="p", loi_doc="", ve=ve_hong, cham=lambda t, p: {}, ghi=lambda *_: None)
    may = _May(tmp_path, {0: [4, 5, 3]})
    goc_ve = may.ve

    def ve(prompt, vong):
        if vong == 1:
            raise RuntimeError("máy chủ sập")
        return goc_ve(prompt, vong)
    may.ve = ve
    kq = _chay(may)
    assert kq["chon"]["vong"] == 0 and "không vẽ được" in kq["canh_bao"]


def test_dung_giua_chung_thi_nem_len(tmp_path):
    class Cancelled(Exception):
        pass
    may = _May(tmp_path, {0: [4, 4, 4]})
    goc_ve = may.ve

    def ve(prompt, vong):
        if vong == 1:
            raise Cancelled()
        return goc_ve(prompt, vong)
    may.ve = ve
    with pytest.raises(Cancelled):
        _chay(may)


def test_chay_tiep_dung_lai_vong_da_co_khong_ve_lai(tmp_path):
    so = cac.SoChon(str(tmp_path))
    may = _May(tmp_path, {0: [4, 5, 3], 1: [8, 9, 5]})
    goc_ve = may.ve

    class Cancelled(Exception):
        pass

    def ve_dung(prompt, vong):
        if vong == 1:
            raise Cancelled()
        return goc_ve(prompt, vong)
    may.ve = ve_dung
    with pytest.raises(Cancelled):
        _chay(may, so=so)
    assert so.lay(5)["vong"][0]["cham"]                       # vòng 0 đã ghi sổ kèm điểm
    may2 = _May(tmp_path, {0: [1, 1, 1], 1: [8, 9, 5]})
    kq = _chay(may2, so=so)
    assert [v for _p, v in may2.ve_goi] == [1]                # vòng 0 KHÔNG vẽ lại
    assert all(int(os.path.basename(t[0][0])[1]) == 1 for t in may2.cham_goi)   # vòng 0 không chấm lại
    assert kq["chon"]["vong"] == 1 and kq["chon"]["tong"] == 8.0
    assert cac.tom_tat(str(tmp_path))["so_canh"] == 1


def test_ve_tra_loi_nhac_that_da_dung(tmp_path):
    may = _May(tmp_path, {0: [9, 9, 9]})
    goc_ve = may.ve
    may.ve = lambda p, v: (goc_ve(p, v), "SAFE " + p)
    kq = _chay(may)
    assert kq["chon"]["prompt"] == "SAFE Close-up of the reference character"
    assert may.cham_goi[0][1].startswith("SAFE")


def test_tom_tat_dem_dung(tmp_path):
    so = cac.SoChon(str(tmp_path))
    _chay(_May(tmp_path, {0: [4, 4, 4], 1: [8, 8, 8]}), so=so)
    tt = cac.tom_tat(str(tmp_path))
    assert tt["so_canh"] == 1 and tt["viet_lai"] == 1 and tt["thang_nho_viet_lai"] == 1
    assert tt["diem_tb"] == 8.0 and tt["diem_tb_vong_dau"] == 4.0 and tt["so_anh"] == 6 and tt["so_cham"] == 2
    assert cac.tom_tat(str(tmp_path / "khong")) == {}


def test_so_ung_vien_doc_kenh():
    assert cac.so_ung_vien(SimpleNamespace()) == 0
    assert cac.so_ung_vien(SimpleNamespace(so_ung_vien_canh=3)) == 3
    assert cac.so_ung_vien(SimpleNamespace(so_ung_vien_canh=99)) == cac.TRAN_UNG_VIEN
    assert cac.anh_uoc_moi_canh(0) == 1.0 and cac.anh_uoc_moi_canh(3) > 3


def test_kenh_mac_dinh_ba_ung_vien(tmp_path):
    from core.kenh import Kenh
    assert Kenh.__dataclass_fields__["so_ung_vien_canh"].default == 3


# ═══ NỐI VÀO DÂY CHUYỀN (auto_khau) ═══

ST = {"image_style": "Clean flat-vector minimalist psychology illustration matching the attached reference",
      "scene_plan_style": "warm cream flat", "palette": "cream, navy"}


def _bc(tmp_path, goi_ai):
    nv = tmp_path / "nv1.png"
    nv.write_bytes(b"nv")
    kenh = SimpleNamespace(mo_hinh="claude-sonnet-5", che_do_ke="", anh_nv=[str(nv)], engine="veo3",
                           so_ung_vien_canh=3, style=dict(ST), ma="X")
    nhat = []
    return SimpleNamespace(kenh=kenh, ghi=nhat.append, _nhat=nhat, kiem_dung=lambda: None, goc=str(tmp_path),
                           on_log=None, ngu=lambda _s: None,
                           goi_chat=lambda loi_nhac, **kw: goi_ai(loi_nhac, kw), client=object())


class _Hop:
    def lay(self):
        return ["https://x/nv1.png"]


def _luot(tmp_path, canh):
    d = tmp_path / "0001"
    d.mkdir()
    (d / "4-canh.json").write_text(json.dumps(canh, ensure_ascii=False), encoding="utf-8")
    return SimpleNamespace(thu_muc=str(d), ma_luot="0001", ma_kenh="x")


def test_lam_anh_canh_chon_tam_tot_nhat_sau_viet_lai(tmp_path, monkeypatch):
    goc_prompt = "Close-up of the reference character in a dark hallway, " + ST["image_style"] + ", no text"
    c = {"scene_id": 7, "img_prompt": goc_prompt, "srt_text": "返事が来ない"}
    luot = _luot(tmp_path, [c])
    tao, cham_anh = [], []

    def tao_anh(bc, luot_, prompt, hop, khoa, ten_hien="", so=None, n=1):
        tao.append((prompt, n, khoa))
        return {"id": "job{0}".format(len(tao))}

    def tai(bc, goi, i, dich):
        with open(dich, "wb") as f:
            f.write("{0}-{1}".format(goi["id"], i).encode())
        return dich

    def goi_ai(loi_nhac, kw):
        if "art director of a Japanese YouTube channel" in loi_nhac:
            cham_anh.append(kw.get("anh"))
            if len(cham_anh) == 1:
                return json.dumps({"ung_vien": [_muc(1, 3), _muc(2, 5, kd=True), _muc(3, 4)], "sua": "brighter"})
            return json.dumps({"ung_vien": [_muc(1, 6), _muc(2, 9), _muc(3, 7)]})
        assert "You rewrite ONE scene image prompt" in loi_nhac
        return "Medium shot of the reference character smiling at a phone on a sunny table with blue accent"

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh)
    monkeypatch.setattr(auto_khau, "_tai_ket_qua", tai)
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda bc, tep: None)
    monkeypatch.setattr(auto_khau, "xin_nhip", lambda *a, **k: None)
    bc = _bc(tmp_path, goi_ai)
    tep = os.path.join(luot.thu_muc, "5-anh", "7.png")
    os.makedirs(os.path.dirname(tep))
    auto_khau._lam_anh_canh(bc, luot, c, tep, _Hop())

    assert len(tao) == 2 and all(n == 3 for _p, n, _k in tao), bc._nhat
    assert all(cac.GIONG_AN_TOAN in p for p, _n, _k in tao)              # câu giữ giọng nối vào MỌI lời nhắc
    assert tao[0][2] != tao[1][2]                                       # mỗi vòng một khoá
    assert tao[1][0].startswith("Medium shot of the reference character smiling")
    assert ST["image_style"] in tao[1][0]                               # đuôi phong cách giữ nguyên
    assert len(cham_anh) == 2 and len(cham_anh[0]) == 4                 # 1 tham chiếu + 3 ứng viên, MỘT lượt
    assert open(tep, "rb").read() == b"job2-1"                          # tấm 2 của vòng 1
    assert c["img_prompt"].startswith("Medium shot") and cac.GIONG_AN_TOAN not in c["img_prompt"]
    with open(os.path.join(luot.thu_muc, "4-canh.json"), encoding="utf-8") as f:
        assert json.load(f)[0]["img_prompt"].startswith("Medium shot")
    so = json.load(open(os.path.join(luot.thu_muc, cac.TEP_SO), encoding="utf-8"))["7"]
    assert so["xong"] and so["chon"]["vong"] == 1 and so["so_anh"] == 6 and so["so_cham"] == 2
    assert not os.path.exists(os.path.join(luot.thu_muc, cac.THU_MUC_UV, "7"))   # ứng viên thua đã dọn


def test_lam_anh_canh_bi_tu_choi_viet_lai_cho_lanh(tmp_path, monkeypatch):
    c = {"scene_id": 3, "img_prompt": "Close-up of the reference character with cheeks flushing", "srt_text": "x"}
    luot = _luot(tmp_path, [c])
    tao = []

    def tao_anh(bc, luot_, prompt, hop, khoa, ten_hien="", so=None, n=1):
        tao.append(prompt)
        if "flushing" in prompt:
            raise RuntimeError("content_rejected: bộ lọc an toàn")
        return {"id": "j"}

    def goi_ai(loi_nhac, kw):
        if "art director" in loi_nhac:
            return json.dumps({"ung_vien": [_muc(1, 9), _muc(2, 8), _muc(3, 8)]})
        return "Close-up of the reference character with rosy cheeks"

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh)
    monkeypatch.setattr(auto_khau, "_tai_ket_qua", lambda bc, g, i, d: open(d, "wb").write(b"p"))
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda bc, tep: None)
    monkeypatch.setattr(auto_khau, "xin_nhip", lambda *a, **k: None)
    bc = _bc(tmp_path, goi_ai)
    tep = str(tmp_path / "3.png")
    auto_khau._lam_anh_canh(bc, luot, c, tep, _Hop())
    assert len(tao) == 2 and "rosy" in tao[1] and os.path.exists(tep)
    assert c["img_prompt"] == "Close-up of the reference character with rosy cheeks"


def test_kenh_tat_so_ung_vien_di_duong_mot_tam(tmp_path, monkeypatch):
    c = {"scene_id": 1, "img_prompt": "a cat"}
    luot = _luot(tmp_path, [c])
    tao = []
    monkeypatch.setattr(auto_khau, "_tao_anh", lambda bc, l, p, h, k, ten_hien="", so=None: tao.append(p) or {"id": 1})
    monkeypatch.setattr(auto_khau, "_tai_ket_qua", lambda bc, g, i, d: open(d, "wb").write(b"p"))
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda bc, tep: None)
    bc = _bc(tmp_path, lambda l, kw: pytest.fail("không được gọi AI"))
    bc.kenh.so_ung_vien_canh = 0
    auto_khau._lam_anh_canh(bc, luot, c, str(tmp_path / "1.png"), _Hop())
    assert len(tao) == 1 and tao[0].startswith("a cat, ") and cac.GIONG_AN_TOAN in tao[0]


# ═══ KHÚC CHIA CẢNH GHI GIÂY THAY SỐ DÒNG (thử thật 17/10) ═══

def test_chia_canh_ghi_giay_thay_so_dong_thi_hoi_lai():
    cue = [{"index": i, "start": i * 2.0, "end": i * 2.0 + 2, "text": "x"} for i in range(57, 85)]
    giay = [{"srt_from": 175.57, "srt_to": 182.09}, {"srt_from": 183.19, "srt_to": 188.15}]
    dung = [{"srt_from": 57, "srt_to": 60}, {"srt_from": "61", "srt_to": 84}]
    assert auto_khau._ngoai_dai_dong(giay, cue) is True
    assert auto_khau._ngoai_dai_dong(dung, cue) is False
    assert auto_khau._ngoai_dai_dong([{"img_prompt": "x"}], cue) is False      # không ghi số → để canh_lai lo
    assert auto_khau._ngoai_dai_dong(dung + [{"srt_from": 1, "srt_to": 3}], cue) is False   # một cảnh lệch thôi
