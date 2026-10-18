"""Cổng chữ ĐÚNG của ảnh bìa (16/10/2026, `core/cong_chu.py` + nối dây `auto_khau`, `chon_bia`, `bia_lo`, `do_bia`,
`studio_may`, `ho_so_video`, `ky_nang`) — chủ dự án: "bìa sai chữ là tối kỵ".

Chữ bìa đúng trước khi vẽ (soát + kanji ngoài tiêu đề/kịch bản phải được xác nhận, sai không sửa được → viết lại), ảnh
đạt/trượt bằng HAI lượt đọc khớp tuyệt đối (sai kanji, lặp chữ, thiếu chữ, chữ lạc → trượt; chỉ khác xuống dòng → đạt;
hai lượt vênh → trượt; AI hỏng → chưa kiểm), dấu theo sha1 (cũ/thiếu → cửa ra từ chối), bìa dự phòng chữ vẽ bằng mã.

Ảnh TỔNG HỢP (PIL), AI GIẢ (đọc ảnh theo MÀU nền) — không mạng, không chữ/mã kênh thật."""

from __future__ import annotations

import base64
import io
import json
import os
import types

import pytest
from PIL import Image, ImageDraw

from core import auto_khau, chon_bia, cong_chu, do_bia, soat_bia
from core import bia_theo_khuon as btk
from core.auto import LuotChay

DUNG = "人を惹きつける 意外な習慣"
SAI = "人を意きつける 意外な習慣"          # kanji giống hình / đồng âm
LAP = "頭がいい人の 変わった 変わった"        # mô hình ảnh vẽ lặp chữ, mất đuôi
MONG_LAP = "頭がいい人の 変わったクセ7選"
TIEU_DE = "人を惹きつける人がしている意外な習慣"
KICH_BAN = "人を惹きつける人には、意外な習慣があります。"


# ── AI giả ───────────────────────────────────────────────────────────────────


def _mau_tb(url: str):
    raw = base64.b64decode(url.split(",", 1)[1])
    im = Image.open(io.BytesIO(raw)).convert("RGB").resize((8, 8))
    px = list(im.getdata())
    return tuple(sum(p[i] for p in px) // len(px) for i in range(3))


class AiGia:
    """Biên tập viên + người đọc ảnh giả. Đọc ảnh: theo màu nền gần nhất trong `theo_mau` (mỗi lượt có thể khác:
    `theo_lan[i]`); soát chữ: chữ có 意き → sai (bản sửa 惹き trừ khi `khong_sua`); xác nhận kanji: bác mục trong
    `bac`. `hong_doc` = mọi lượt đọc ảnh lỗi mạng."""

    def __init__(self, theo_mau=None, theo_lan=None, hong_doc=False, khong_sua=False, bac=(), viet_lai="",
                 lac_de=()):
        self.theo_mau, self.theo_lan = theo_mau or {}, list(theo_lan or [])
        self.hong_doc, self.khong_sua, self.bac, self.viet = hong_doc, khong_sua, set(bac), viet_lai
        self.lac_de = set(lac_de)        # 16/10/2026: chữ nào bị xét LẠC chủ đề (kiểm đúng chủ đề)
        self.lan: list = []

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        self.lan.append((loi_nhac[:30], khoa, mo_hinh))
        if loi_nhac.startswith("You check that the"):
            chu = loi_nhac.split("TO CHECK: 「", 1)[1].split("」", 1)[0]
            return json.dumps({"hop": chu not in self.lac_de, "ly_do": "gia"})
        if loi_nhac.startswith("Read the text printed"):
            if self.hong_doc:
                raise RuntimeError("mạng rớt")
            if self.theo_lan:
                chu = self.theo_lan.pop(0)
            else:
                m = _mau_tb(anh[0])
                chu = min(self.theo_mau.items(), key=lambda kv: sum(abs(a - b) for a, b in zip(kv[0], m)))[1]
            return json.dumps({"dong": chu.split(" "), "chu_thua": [], "ky_tu_hong": False, "vet_xoa": False},
                              ensure_ascii=False)
        if "machine check flagged" in loi_nhac:
            chu = loi_nhac.split("THUMBNAIL TEXT (a space only marks a line break): 「", 1)[1].split("」", 1)[0]
            bac = [m for m in self.bac if m in chu]
            return json.dumps({"dung": not bac, "xac_nhan": [{"muc": m, "dung": False} for m in bac],
                               "chu_sua": ""}, ensure_ascii=False)
        if "THUMBNAIL TEXT" in loi_nhac:
            chu = loi_nhac.split("THUMBNAIL TEXT (a space only marks a line break): 「", 1)[1].split("」", 1)[0]
            if "意き" in chu:
                return json.dumps({"dung": False, "loi": [{"sai": "意", "dung": "惹", "ly_do": "wrong kanji"}],
                                   "chu_sua": "" if self.khong_sua else chu.replace("意き", "惹き")}, ensure_ascii=False)
            return json.dumps({"dung": True, "loi": [], "chu_sua": ""})
        if "THUMB: <text>" in loi_nhac:
            return "THUMB: " + self.viet
        return "{}"

    def so_doc(self) -> int:
        return sum(1 for x in self.lan if x[0].startswith("Read the text"))


def _anh(duong, mau=(40, 40, 160), co=(1280, 720)) -> str:
    os.makedirs(os.path.dirname(str(duong)), exist_ok=True)
    Image.new("RGB", co, mau).save(str(duong))
    return str(duong)


# ── 1) chuẩn hoá + so ────────────────────────────────────────────────────────


def test_khop_tuyet_doi_chi_bo_xuong_dong_dau_cau_va_nfkc():
    assert cong_chu.khop("人を惹きつける\n意外な習慣", DUNG)                   # chỉ khác xuống dòng → đạt
    assert cong_chu.khop("「人を惹きつける」 意外な習慣！", DUNG)               # dấu câu bỏ
    assert cong_chu.khop("ク セ ７ 選", "クセ7選")                             # NFKC + khoảng trắng
    assert cong_chu.khop("本当のピークは〇〇歳", "本当のピークは◯◯歳")           # vòng tròn che chữ: cùng nghĩa
    assert not cong_chu.khop(SAI, DUNG)                                        # một kanji sai → trượt
    assert not cong_chu.khop(LAP, MONG_LAP)                                    # lặp chữ, mất đuôi → trượt
    assert not cong_chu.khop("くく" + DUNG, DUNG), "luật cũ cho thừa 2 ký tự đầu — luật chặt KHÔNG"
    assert not cong_chu.khop("人を惹きつける", DUNG)                             # thiếu chữ


def test_xet_doc_chu_lac_ky_tu_hong_vet_xoa():
    tot = {"chu": DUNG, "chu_thua": ["✦ (faint sparkle watermark)", "a cup on the table"]}
    assert cong_chu.xet_doc(tot, DUNG) == []
    assert cong_chu.xet_doc(dict(tot, chu_thua=["SALE"]), DUNG)[0].startswith("chữ thừa")
    assert "ký tự vỡ" in cong_chu.xet_doc(dict(tot, ky_tu_hong=True), DUNG)[0]
    assert cong_chu.xet_doc({"chu": ""}, "") == ["không có chữ đã soát để so"]


# ── 2) chữ bìa đúng TRƯỚC khi vẽ ─────────────────────────────────────────────


def test_can_xac_nhan_bat_kanji_va_cum_ngoai_nguon():
    nguon = TIEU_DE + KICH_BAN
    assert "意きつける" in cong_chu.can_xac_nhan(SAI, nguon), "意 có trong nguồn nhưng 意き thì không"
    assert cong_chu.can_xac_nhan(DUNG, nguon) == []
    assert cong_chu.can_xac_nhan("猫の秘密 7選", nguon) == ["猫", "秘", "密", "選"]


def test_soat_chat_sua_sai_kanji_va_bac_kanji_khong_sua_duoc():
    ai = AiGia()
    r = cong_chu.soat_chat(ai, SAI, tieu_de=TIEU_DE, ngu_canh=KICH_BAN, thang=("m",))
    assert r["ok"] is True and r["sua"] and r["chu"] == DUNG and r["phien"] == cong_chu.PHIEN_SOAT
    # biên tập viên nói "đúng" nhưng kanji ngoài nguồn bị bác ở lượt xác nhận, không có bản sửa → sai (phải viết lại)
    ai2 = AiGia(bac={"猫"})
    r2 = cong_chu.soat_chat(ai2, "猫の秘密", tieu_de=TIEU_DE, ngu_canh=KICH_BAN, thang=("m",))
    assert r2["ok"] is False and r2["can_xac_nhan"] == ["猫", "秘", "密"]
    assert sum(1 for x in ai2.lan if x[0].startswith("You are a meticulous")) == 3, "soát + hai phiếu xác nhận cùng bác"
    # xác nhận được → đúng
    assert cong_chu.soat_chat(AiGia(), "猫の秘密", tieu_de=TIEU_DE, thang=("m",))["ok"] is True


def test_chot_chu_khong_sua_duoc_thi_viet_lai_roi_soat_lai():
    ai = AiGia(khong_sua=True, viet_lai="人を惹きつける 習慣の正体")
    r = cong_chu.chot_chu(ai, SAI, tieu_de=TIEU_DE, ngu_canh=KICH_BAN, thang=("m",))
    assert r["ok"] is True and r["viet_lai"] and r["chu"] == "人を惹きつける 習慣の正体"
    assert [x["ok"] for x in r["lich_su"]] == [False, True]
    r = cong_chu.chot_chu(AiGia(khong_sua=True, viet_lai="x"), SAI, tieu_de=TIEU_DE, thang=("m",))
    assert r["ok"] is False, "viết lại ngoài khung → vẫn sai, nơi gọi giữ bìa"


class AiPhieu:
    """Lượt xác nhận kanji giả: trả lần lượt các phiếu `phieu` (dict hoặc None = lỗi mạng); soát chính tả luôn "đúng"."""

    def __init__(self, phieu):
        self.phieu, self.goi = list(phieu), []

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        if "machine check flagged" in loi_nhac:
            self.goi.append(khoa)
            p = self.phieu.pop(0) if self.phieu else None
            if p is None:
                raise RuntimeError("mạng rớt")
            return json.dumps(p, ensure_ascii=False)
        if loi_nhac.startswith("You check that the"):
            return json.dumps({"hop": True, "ly_do": "gia"})
        return json.dumps({"dung": True, "loi": [], "chu_sua": ""})


_DUNG_XN = {"xac_nhan": [{"muc": "賢", "loai": "dung"}], "chu_sua": ""}
_BAC_OAN = {"xac_nhan": [{"muc": "賢", "loai": "khong_trong_kich_ban", "dung": False,
                          "ly_do": "タイトルに出現しない"}], "chu_sua": "頭がいい人ほど 夜に眠らない"}
_BAC_THAT = {"xac_nhan": [{"muc": "腎", "loai": "giong_hinh", "dung_la": "賢"}], "chu_sua": "賢い人ほど 夜に眠らない"}


def test_doc_xac_nhan_chi_loai_loi_chu_moi_la_sai():
    assert cong_chu.doc_xac_nhan(_DUNG_XN, ["賢"])["sai"] == {}
    assert set(cong_chu.doc_xac_nhan(_BAC_THAT, ["腎"])["sai"]) == {"腎"}
    assert cong_chu.doc_xac_nhan(_BAC_THAT, ["腎"])["sai"]["腎"]["dung_la"] == "賢"
    # loai lạ + dung False / mục bị bỏ sót → chặt: coi là sai (phiếu khác phân xử)
    assert set(cong_chu.doc_xac_nhan(_BAC_OAN, ["賢"])["sai"]) == {"賢"}
    assert set(cong_chu.doc_xac_nhan({"xac_nhan": [{"muc": "賢", "loai": "dung"}]}, ["賢", "恋"])["sai"]) == {"恋"}
    assert cong_chu.doc_xac_nhan({"dung": True, "xac_nhan": []}, ["賢"])["sai"] == {}, "dạng cũ: đúng hết"
    assert cong_chu.doc_xac_nhan("rác", ["賢"]) is None and cong_chu.doc_xac_nhan({}, ["賢"]) is None


def test_xac_nhan_kanji_mot_phieu_bac_oan_thi_phieu_khac_phan_xu_cho_qua():
    # TL3 18/10: 「賢」 không có trong tiêu đề/kịch bản (kịch bản viết 頭がいい) — một phiếu bác oan, hai phiếu kia: đúng
    ai = AiPhieu([_BAC_OAN, _DUNG_XN, _DUNG_XN])
    r = cong_chu.soat_chat(ai, "賢い人ほど 夜に眠らない", tieu_de="頭がいい人ほど夜に眠らない理由", thang=("a", "b", "c"))
    assert r["ok"] is True and r["chu"] == "賢い人ほど 夜に眠らない" and not r.get("sua")
    assert len(ai.goi) == 3 and len(set(ai.goi)) == 3, "ba phiếu, ba khoá khác nhau"
    # phiếu 1 đúng → không cần phiếu 2
    ai = AiPhieu([_DUNG_XN])
    assert cong_chu.soat_chat(ai, "賢い人ほど 夜に眠らない", tieu_de="人ほど夜に眠らない", thang=("a",))["ok"] is True and len(ai.goi) == 1


def test_xac_nhan_kanji_loi_that_hai_phieu_cung_bac_van_chan():
    ai = AiPhieu([_BAC_THAT, _BAC_THAT, {"xac_nhan": [{"muc": "賢", "loai": "dung"}]}])
    r = cong_chu.soat_chat(ai, "腎い人ほど 夜に眠らない", tieu_de="頭がいい人ほど夜に眠らない理由", thang=("a", "b"))
    # bác → bản sửa 「賢い人ほど…」 soát lại (賢 ngoài nguồn → phiếu 3 xác nhận đúng) → đạt bằng bản SỬA, không bao giờ bản sai
    assert r["ok"] is True and r["sua"] and r["chu"] == "賢い人ほど 夜に眠らない"
    assert any(x["sai"] == "腎" and x["dung"] == "賢" for x in r["loi"])
    ai = AiPhieu([_BAC_THAT, _BAC_THAT, _BAC_THAT, _BAC_THAT])
    r = cong_chu.soat_chat(ai, "腎い人ほど 夜に眠らない", tieu_de="x", thang=("a", "b"))
    assert r["ok"] is False or r["chu"] != "腎い人ほど 夜に眠らない"


def test_xac_nhan_kanji_ai_hong_la_chua_soat_khong_bao_gio_dat():
    r = cong_chu.soat_chat(AiPhieu([_BAC_OAN, None]), "賢い人ほど 夜に眠らない", tieu_de="x", thang=("a", "b"))
    assert r["ok"] is None
    r = cong_chu.soat_chat(AiPhieu([None]), "賢い人ほど 夜に眠らない", tieu_de="x", thang=("a",))
    assert r["ok"] is None


def test_viet_lai_ngoai_khung_hoi_lai_mot_lan():
    tra = iter(["THUMB: 頭脳 恋遠", "THUMB: 賢い人ほど 夜に眠らない"])
    kh = []

    def goi(loi_nhac, mo_hinh="", khoa="", toi_da_token=0):
        kh.append((khoa, loi_nhac))
        return next(tra)
    assert cong_chu.viet_lai(goi, "x", tieu_de="t", khoa="vl") == "賢い人ほど 夜に眠らない"
    assert kh[0][0] != kh[1][0] and "has 4 characters" in kh[1][1]


# ── 3) ảnh: hai lượt đọc, đạt/trượt ──────────────────────────────────────────


def test_hai_luot_doc_deu_phai_khop(tmp_path):
    tep = _anh(tmp_path / "a.png")
    ai = AiGia(theo_lan=[DUNG.replace(" ", "\n"), DUNG])
    r = cong_chu.kiem_anh(ai, tep, DUNG)
    assert r["ok"] is True and len(r["doc"]) == 2
    mo_hinh = [x[2] for x in ai.lan]
    assert mo_hinh[0] != mo_hinh[1], "hai lượt độc lập: mô hình đứng đầu khác nhau"
    assert all(DUNG not in x[0] for x in ai.lan), "lời nhắc đọc không lộ chữ mong đợi"
    assert cong_chu.kiem_anh(AiGia(theo_lan=[DUNG, SAI]), tep, DUNG)["ok"] is False, "hai lượt vênh → trượt"
    r = cong_chu.kiem_anh(AiGia(theo_lan=[SAI]), tep, DUNG)
    assert r["ok"] is False and "≠ chữ đã soát" in r["ly_do"][0], "sai kanji — dừng ngay lượt đầu"
    assert cong_chu.kiem_anh(AiGia(theo_lan=[LAP, LAP]), tep, MONG_LAP)["ok"] is False, "chữ lặp → trượt"
    assert cong_chu.kiem_anh(AiGia(hong_doc=True), tep, DUNG)["ok"] is None, "AI hỏng = CHƯA kiểm, không phải đạt"
    assert cong_chu.kiem_anh(None, tep, DUNG)["ok"] is None


# ── 4) dấu ──────────────────────────────────────────────────────────────────


def test_dau_dung_sha1_cu_thi_tu_choi_va_song_qua_bao_cao(tmp_path):
    tep = _anh(tmp_path / "thumb_001.png")
    assert "chưa có dấu" in cong_chu.kiem_dau(tep)
    kq = cong_chu.xac_minh(AiGia(theo_lan=[DUNG, DUNG]), tep, DUNG, goc=str(tmp_path), kenh="KX", ma_goi="KX-0001")
    assert kq["ok"] is True and cong_chu.kiem_dau(tep) == "" and cong_chu.kiem_dau(tep, DUNG) == ""
    assert "khác chữ mong đợi" in cong_chu.kiem_dau(tep, SAI)
    du = json.load(open(do_bia.duong_bao_cao(tep), encoding="utf-8"))
    assert du["chu_khop"]["ok"] is True and du["chu_khop"]["sha1"] == cong_chu.sha1_tep(tep)
    # có dấu → không gọi AI lần hai
    ai = AiGia()
    assert cong_chu.xac_minh(ai, tep, DUNG)["da_co"] and ai.lan == []
    # đo lại báo cáo độ đọc được KHÔNG làm mất dấu
    do_bia.ghi_bao_cao(tep, {"dong": [], "dat": True, "diem": 90})
    assert cong_chu.kiem_dau(tep) == ""
    # tệp đổi sau khi đóng dấu (dấu CŨ) → từ chối
    _anh(tmp_path / "thumb_001.png", (41, 40, 160))
    assert "chưa có dấu" in cong_chu.kiem_dau(tep)
    # bản xuất lại do mã (jpg) mang dấu; ảnh khác bức thì không
    tep2 = _anh(tmp_path / "b.png", (200, 30, 30))
    cong_chu.ghi_dau(tep2, DUNG, doc=[DUNG, DUNG])
    jpg = str(tmp_path / "CHON-b.jpg")
    chon_bia._xuat_jpg(tep2, jpg)  # noqa: SLF001
    assert cong_chu.chuyen_dau(tep2, jpg) and cong_chu.kiem_dau(jpg, DUNG) == ""
    khac = _anh(tmp_path / "c.png", (10, 220, 10))
    assert not cong_chu.chuyen_dau(tep2, khac) and cong_chu.kiem_dau(khac)
    # dấu luật cũ / chưa soát → không hợp lệ
    cong_chu.ghi_dau(khac, DUNG, soat=False)
    assert "không hợp lệ" in cong_chu.kiem_dau(khac)


def test_xac_minh_ghi_nao_bo_phan_bia(tmp_path):
    tep = _anh(tmp_path / "a.png")
    cong_chu.xac_minh(AiGia(theo_lan=[SAI]), tep, DUNG, goc=str(tmp_path), kenh="KX", ma_goi="KX-0001")
    import sqlite3
    con = sqlite3.connect(os.path.join(str(tmp_path), "nao", "bo-phan.db"))
    dong = con.execute("select bo_phan, loai from su_kien").fetchall()
    con.close()
    assert ("bia", "loi") in dong


# ── 5) bộ vẽ bằng mã: bảo đảm + bìa dự phòng ─────────────────────────────────


def _can_font():
    if not btk._tim_font("", "人を惹きつける", "ja"):  # noqa: SLF001
        pytest.skip("máy không có phông Nhật")


def test_bao_dam_ma_chu_cat_hoac_thieu_net(monkeypatch):
    _can_font()
    assert cong_chu.bao_dam_ma(DUNG.replace(" ", ""), DUNG) == ""
    assert "≠ chữ đã soát" in cong_chu.bao_dam_ma("意外な習慣", DUNG), "bộ tách cắt mất chữ → không bảo đảm"
    monkeypatch.setattr(btk, "_font_du_chu", lambda duong, chu: False)
    assert "thiếu nét" in cong_chu.bao_dam_ma(DUNG, DUNG)


def _nen_sach(duong) -> str:
    im = Image.new("RGB", (1280, 720), (60, 40, 30))
    d = ImageDraw.Draw(im)
    d.ellipse([900, 250, 1100, 450], fill=(245, 245, 245), outline=(10, 10, 10), width=8)
    os.makedirs(os.path.dirname(str(duong)), exist_ok=True)
    im.save(str(duong))
    return str(duong)


def test_bia_ma_du_phong_ve_chu_da_soat_roi_doc_lai(tmp_path):
    _can_font()
    tm = str(tmp_path / "7-thumbnail")
    _nen_sach(os.path.join(tm, "znen-thumb_002.png"))
    with open(os.path.join(tm, "chon-bia.json"), "w", encoding="utf-8") as f:
        json.dump({"ung_vien": [{"so": 2, "tong_diem": 70}]}, f)
    assert cong_chu.tim_nen_sach(tm) == [os.path.join(tm, "znen-thumb_002.png")]
    ai = AiGia(theo_lan=[DUNG, DUNG])
    kq = cong_chu.bia_ma_du_phong(ai, tm, DUNG, goc=str(tmp_path))
    assert kq["tep"].endswith("thumb_090.jpg") and cong_chu.kiem_dau(kq["tep"], DUNG) == ""
    assert do_bia.cham_tep(kq["tep"])["dat"] is True
    assert not [t for t in os.listdir(tm) if ".ve." in t], "không để rác bản nháp"
    # đọc lại sai → không ra bìa; AI hỏng → chưa kiểm (nơi gọi giữ)
    assert cong_chu.bia_ma_du_phong(AiGia(theo_lan=[SAI]), tm, DUNG, so_dau=95) == {}
    assert cong_chu.bia_ma_du_phong(AiGia(hong_doc=True), tm, DUNG, so_dau=96) == {"chua_kiem": True}


# ── 6) cổng cuối của khâu bìa (auto_khau) ────────────────────────────────────


def _bc(goc, ai, dong):
    kenh = types.SimpleNamespace(ma="KX", ngon_ngu="ja", che_do_tieu_de="nguyen_goc", mo_hinh="m",
                                 chon_bia_ai=True, so_luot_cham_bia=1, mo_hinh_cham_bia="", bia_kham_pha=False)
    return auto_khau.BoiCanh(goc=goc, kenh=kenh, goi_chat=ai, on_log=dong.append, ngu=lambda _s: None)


def _luot(tmp_path, chu=DUNG):
    d = tmp_path / "PROJECTS" / "AUTO" / "KX" / "0001"
    (d / "7-thumbnail").mkdir(parents=True)
    (d / "1-tieu-de.txt").write_text("TITLE: {0}\nTHUMB: {1}\n".format(TIEU_DE, chu), encoding="utf-8")
    (d / "1-kich-ban.txt").write_text(KICH_BAN, encoding="utf-8")
    return LuotChay(ma_kenh="KX", ma_luot="0001", thu_muc=str(d)), str(d / "7-thumbnail")


_MAU = {1: (40, 40, 160), 2: (160, 40, 40), 3: (40, 160, 40)}


def _bo_bia(tm, chon_so=2):
    for so, mau in _MAU.items():
        _anh(os.path.join(tm, "thumb_{0:03d}.png".format(so)), mau)
    chon_bia._xuat_jpg(os.path.join(tm, "thumb_{0:03d}.png".format(chon_so)),  # noqa: SLF001
                       os.path.join(tm, "CHON-thumb_{0:03d}.jpg".format(chon_so)))
    with open(os.path.join(tm, "chon-bia.json"), "w", encoding="utf-8") as f:
        json.dump({"chon": {"so": chon_so, "tep": "CHON-thumb_{0:03d}.jpg".format(chon_so), "chon_boi": "ai"},
                   "ung_vien": [{"so": so, "tong_diem": {2: 90, 1: 70, 3: 50}[so], "loai": ""} for so in _MAU]}, f)


def test_cong_cuoi_dong_dau_tam_giao_va_tam_du_phong(tmp_path):
    luot, tm = _luot(tmp_path)
    _bo_bia(tm)
    ai = AiGia(theo_mau={_MAU[1]: DUNG, _MAU[2]: DUNG, _MAU[3]: SAI})
    r = auto_khau._cong_chu_bia(_bc(str(tmp_path), ai, []), luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert r["dat"] is True
    assert cong_chu.kiem_dau(os.path.join(tm, "CHON-thumb_002.jpg"), DUNG) == "", "tấm giao có dấu"
    assert cong_chu.kiem_dau(os.path.join(tm, "thumb_001.png"), DUNG) == "", "tấm hạng nhì có dấu (A/B, bìa-2)"
    assert cong_chu.kiem_dau(os.path.join(tm, "thumb_003.png")), "tấm sai chữ KHÔNG có dấu"
    n = ai.so_doc()
    assert auto_khau._cong_chu_bia(_bc(str(tmp_path), ai, []), luot, tm, DUNG, TIEU_DE)["dat"] is True  # noqa: SLF001
    assert ai.so_doc() == n, "chạy lại: dấu + sổ — không đọc lại"


def test_cong_cuoi_hai_luot_vench_la_truot_doi_tam(tmp_path):
    luot, tm = _luot(tmp_path)
    _bo_bia(tm)
    ai = AiGia(theo_lan=[DUNG, SAI, DUNG, DUNG])     # tấm 2: lượt 1 đúng, lượt 2 sai → trượt; tấm 1: đúng cả hai
    r = auto_khau._cong_chu_bia(_bc(str(tmp_path), ai, []), luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert r.get("doi") and r["tep"] == "CHON-thumb_001.jpg"


def test_cong_cuoi_het_tam_dung_chu_thi_ve_lo_moi_khong_du_phong_chung(tmp_path):
    """19/10/2026: bìa dự phòng chữ-vẽ-bằng-mã kiểu chung ĐÃ TẮT (bỏ qua khuôn kênh, lên sóng thật xấu) — hết tấm
    có chữ đúng thì HetBiaDat (vẽ lô mới theo khuôn kênh), không bao giờ ra CHON-thumb_09N."""
    _can_font()
    luot, tm = _luot(tmp_path)
    _bo_bia(tm)
    _nen_sach(os.path.join(tm, "znen-thumb_002.png"))
    ai = AiGia(theo_mau={_MAU[1]: SAI, _MAU[2]: SAI, _MAU[3]: SAI, (60, 40, 30): DUNG, (120, 100, 90): DUNG})
    bc = _bc(str(tmp_path), ai, [])
    with pytest.raises(auto_khau.HetBiaDat):
        for _ in range(6):
            r = auto_khau._cong_chu_bia(bc, luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
            assert not str(r.get("tep") or "").startswith("CHON-thumb_09"), r
    assert not [f for f in os.listdir(tm) if f.startswith("CHON-thumb_09")]


def test_cong_cuoi_ai_hong_la_giu_khong_phai_dat(tmp_path):
    luot, tm = _luot(tmp_path)
    _bo_bia(tm)
    with pytest.raises(RuntimeError) as e:
        auto_khau._cong_chu_bia(_bc(str(tmp_path), AiGia(hong_doc=True), []), luot, tm, DUNG, TIEU_DE)  # noqa: SLF001
    assert not isinstance(e.value, auto_khau.HetBiaDat) and "GIỮ" in str(e.value)
    assert cong_chu.kiem_dau(os.path.join(tm, "CHON-thumb_002.jpg"))


def test_soat_truoc_khi_ve_chu_sai_khong_sua_duoc_thi_viet_lai(tmp_path):
    luot, tm = _luot(tmp_path, chu=SAI)
    dong: list = []
    r = auto_khau._soat_chu_bia_luot(_bc(str(tmp_path), AiGia(khong_sua=True, viet_lai="人を惹きつける 習慣の正体"),  # noqa: SLF001
                                         dong), luot)
    assert r["ok"] is True and r["chu"] == "人を惹きつける 習慣の正体"
    assert "THUMB: 人を惹きつける 習慣の正体" in open(os.path.join(luot.thu_muc, "1-tieu-de.txt"), encoding="utf-8").read()
    luot2, _tm2 = _luot(tmp_path / "b", chu=SAI)
    with pytest.raises(RuntimeError, match="GIỮ"):
        auto_khau._soat_chu_bia_luot(_bc(str(tmp_path / "b"), AiGia(khong_sua=True, viet_lai="x"), []), luot2)  # noqa: SLF001


# ── 7) cổng trước giám khảo (chon_bia) ───────────────────────────────────────


def _giam_khao(ai: AiGia):
    def goi(loi_nhac, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        if loi_nhac.startswith("Read the text printed"):
            return ai(loi_nhac, mo_hinh=mo_hinh, khoa=khoa, toi_da_token=toi_da_token, anh=anh)
        ai.lan.append(("judge", khoa, len(anh or [])))
        d = {k: 8 for k in chon_bia.TRONG_SO}
        return json.dumps({"cac_anh": [{"nhan": c, "diem": d, "chu_doc_ra": "", "loi_nang": []} for c in "ABCDEFG"]})
    return goi


def test_chon_bia_loai_tam_sai_chu_truoc_giam_khao(tmp_path):
    goc = str(tmp_path)
    tm = str(tmp_path / "thumb")
    for so, mau in _MAU.items():
        _anh(os.path.join(tm, "thumb_{0:03d}.png".format(so)), mau)
    ai = AiGia(theo_mau={_MAU[1]: DUNG, _MAU[2]: SAI, _MAU[3]: LAP})
    ket = chon_bia.chon(goc, "KX", tm, ten_kieu_theo_so={1: "a", 2: "b", 3: "c"}, chu_bia=DUNG,
                        goi_chat=_giam_khao(ai), so_luot_cham=1, seed=1)
    assert ket["so"] == 1
    du = chon_bia.doc_chon_bia(tm)
    loai = {u["so"]: u["loai"] for u in du["ung_vien"]}
    assert loai[2].startswith("cổng chữ") and loai[3].startswith("cổng chữ") and loai[1] == ""
    assert {u["so"]: (u.get("chu_khop") or {}).get("ok") for u in du["ung_vien"]} == {1: True, 2: False, 3: False}


def test_chon_bia_moi_tam_sai_chu_thi_ve_chu_bang_ma_hoac_khong_xuat(tmp_path):
    goc = str(tmp_path)
    tm = str(tmp_path / "thumb")
    for so, mau in _MAU.items():
        _anh(os.path.join(tm, "thumb_{0:03d}.png".format(so)), mau)
    ai = AiGia(theo_mau={m: SAI for m in _MAU.values()})
    ket = chon_bia.chon(goc, "KX", tm, ten_kieu_theo_so={}, chu_bia=DUNG, goi_chat=_giam_khao(ai), so_luot_cham=1)
    assert ket["het_hop_le"] and not [t for t in os.listdir(tm) if t.startswith("CHON-")], "không nền sạch → lô mới"
    _can_font()
    _nen_sach(os.path.join(tm, "znen-thumb_001.png"))
    os.remove(os.path.join(tm, "chon-bia.json"))
    ket = chon_bia.chon(goc, "KX", tm, ten_kieu_theo_so={}, chu_bia=DUNG, goi_chat=_giam_khao(ai), so_luot_cham=1)
    assert ket["so"] == 90 and ket["kieu"] == "bia_ma", "tấm chữ vẽ bằng mã trên nền sạch"


def test_chon_bia_tam_chu_ma_khong_ton_luot_doc(tmp_path):
    _can_font()
    tm = str(tmp_path / "thumb")
    _anh(os.path.join(tm, "thumb_001.png"), _MAU[1])
    ai = AiGia(theo_mau={_MAU[1]: SAI})
    chon_bia.chon(str(tmp_path), "KX", tm, ten_kieu_theo_so={1: "k"}, chu_bia=DUNG, goi_chat=_giam_khao(ai),
                  so_luot_cham=1, ma_theo_so={1: DUNG.replace(" ", "")})
    assert ai.so_doc() == 0 and chon_bia.doc_chon_bia(tm)["chon"]["so"] == 1


# ── 8) bìa lô: bộ vẽ không bảo đảm chữ → dừng trước khi trả tiền ảnh ─────────


def test_bia_lo_chu_ve_khac_chu_bia_thi_dung_truoc_khi_ve(tmp_path, monkeypatch):
    from core import bia_lo
    from core.kenh import TEP_KENH, duong_kenh
    goc = str(tmp_path / "goc")
    os.makedirs(duong_kenh(goc, "KH"), exist_ok=True)
    with io.open(os.path.join(duong_kenh(goc, "KH"), TEP_KENH), "w", encoding="utf-8") as f:
        f.write('ma: "KH"\n')
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
    os.makedirs(luot)
    with io.open(os.path.join(luot, "1-tieu-de.txt"), "w", encoding="utf-8") as f:
        f.write("TITLE: t\nTHUMB: {0}\n".format(DUNG))
    mau = _anh(os.path.join(goc, "m.jpg"), (240, 220, 200))
    monkeypatch.setattr(bia_lo, "doc_chu_bia", lambda chu, kc, cach_ai=(): [
        {"vi_tri": "tren", "phan_mau": [{"chu": "意外な習慣"}]}])                    # bộ tách cắt mất nửa chữ
    monkeypatch.setattr(bia_lo, "dao_dien", lambda *a, **k: {"y_tuong": [{"y": "y", "manh_moi": "m", "canh": "c",
                                                                            "mat": "m"}], "chu": []})
    ve = []
    with pytest.raises(cong_chu.ChuKhongKhop):
        bia_lo.chay(goc, "KH", thu_muc_luot=luot, ra=str(tmp_path / "ra"), goi=lambda *a, **k: "{}",
                    ve=lambda *a, **k: ve.append(a) or [], mau=[mau], log=lambda s: None)
    assert ve == [], "không đặt ảnh nào khi chữ vẽ không khớp chữ bìa"


# ── 9) cửa ra YouTube: A/B (studio_may) + tệp tải lên mang dấu ───────────────


def test_studio_may_tu_choi_bia_khong_dau_va_ban_tai_len_mang_dau(tmp_path):
    from core import studio_may as sm
    K, MA = "KX1-T7", "KX1-T7-0001"
    g = str(tmp_path / "goc")
    hs = os.path.join(g, "CHANNEL", K, "ho-so-video")
    os.makedirs(hs)
    with open(os.path.join(hs, MA + ".json"), "w", encoding="utf-8") as f:
        json.dump({"video_id": "FAKEvid0001", "bia_2": {"tong_diem": 60}}, f)
    b2 = _anh(os.path.join(hs, "anh", MA + "-bia-2.jpg"), (0, 200, 0))
    b3 = _anh(os.path.join(hs, "anh", MA + "-bia-3.jpg"), (0, 0, 200))
    cong_chu.ghi_dau(b3, DUNG, doc=[DUNG, DUNG])
    chon, bo = sm.ung_vien_bia(g, K, MA, (), cham=lambda p: {"dat": True, "diem": 80})
    assert [os.path.basename(u["tep"]) for u in chon] == [MA + "-bia-3.jpg"]
    assert any("cổng chữ" in u["ly_do"] for u in bo if u["tep"] == b2)
    p = _anh(tmp_path / "x.png", (0, 0, 200), co=(1376, 768))
    cong_chu.ghi_dau(p, DUNG, doc=[DUNG, DUNG])
    t = sm.tep_tai_len(p, str(tmp_path / "ra"))
    assert t != p and cong_chu.kiem_dau(t, DUNG) == "", "bản tải lên do mã xuất lại mang dấu"


def test_studio_may_dom_khong_dat_tep_khong_dau(tmp_path, monkeypatch):
    import sys
    vm = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vm")
    if vm not in sys.path:
        sys.path.insert(0, vm)
    import studio_may_dom as sdm
    from core import studio_may as sm
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: ({"title": "t"}, {"nut": [{"chu": "A/B", "x": 1, "y": 1}]}))
    monkeypatch.setattr(sdm, "_tim_khoa", lambda S, k, han=2.0: None)
    S = types.SimpleNamespace(st=types.SimpleNamespace(ghi_bang_chung=lambda k: {}))   # không có bam → bấm là vỡ
    p = _anh(tmp_path / "b.jpg")
    r = sdm.test_mot_video(S, "FAKEvid0001", {"chon": [{"tep": p}]}, lambda s: None)
    assert r["ket"] == sm.KV_LOI and "cổng chữ" in r["ly_do"]


# ── 10) gói chờ đăng (skill S05) ─────────────────────────────────────────────


def _goi_cho(tmp_path, chu=DUNG, mau=(40, 40, 160)):
    g = str(tmp_path / "goc")
    k, ma = "KX", "KX-0001"
    os.makedirs(os.path.join(g, "CHANNEL", k, "ke-hoach-dang"))
    with open(os.path.join(g, "CHANNEL", k, "ke-hoach-dang", "ke-hoach.csv"), "w", encoding="utf-8-sig") as f:
        f.write("Mã gói,Ngày đăng,Giờ đăng,Tiêu đề,Mô tả,Thẻ SEO,Link card 1,Link card 2,Link card 3,Link card 4,"
                "Sẵn sàng,Trạng thái đăng,Ghi chú,Video ID\n{0},17/10/2026,20:00,t,m,s,,,,,,EDIT XONG,,\n".format(ma))
    goi = os.path.join(g, "DONE", k, ma)
    os.makedirs(goi)
    _anh(os.path.join(goi, "CHON-thumb_001.jpg"), mau)
    d = os.path.join(g, "PROJECTS", "AUTO", k, "0001")
    os.makedirs(os.path.join(d, "7-thumbnail"))
    with open(os.path.join(d, "1-tieu-de.txt"), "w", encoding="utf-8") as f:
        f.write("TITLE: {0}\nTHUMB: {1}\n".format(TIEU_DE, chu))
    with open(os.path.join(d, "1-kich-ban.txt"), "w", encoding="utf-8") as f:
        f.write(KICH_BAN)
    return g, k, ma, goi


def test_goi_cho_dang_dong_dau_hoac_giu(tmp_path):
    from core import ky_nang as kn
    g, k, ma, goi = _goi_cho(tmp_path)
    assert [x["ma"] for x in cong_chu.goi_cho_dang(g, k)] == [ma]
    assert kn.k_dau_bia(g, k)[0] == kn.CHO and kn.d_dau_bia(g, k)[0] is True
    r = cong_chu.dau_goi(AiGia(hong_doc=True), g, k, ma, goi, log=lambda s: None)
    assert r["ok"] is None and cong_chu.kiem_dau(cong_chu.anh_goi(goi)), "AI hỏng → GIỮ, không dấu"
    r = cong_chu.dau_goi(AiGia(theo_lan=[DUNG, DUNG]), g, k, ma, goi, log=lambda s: None)
    assert r["ok"] is True and cong_chu.kiem_dau(cong_chu.anh_goi(goi), DUNG) == ""
    assert kn.k_dau_bia(g, k)[0] == kn.DAT


def test_goi_cho_dang_bia_sai_chu_thay_bang_bia_ve_bang_ma(tmp_path):
    _can_font()
    g, k, ma, goi = _goi_cho(tmp_path)
    tm = os.path.join(g, "PROJECTS", "AUTO", k, "0001", "7-thumbnail")
    _nen_sach(os.path.join(tm, "znen-thumb_001.png"))
    ai = AiGia(theo_mau={(40, 40, 160): SAI, (60, 40, 30): DUNG, (120, 100, 90): DUNG})
    r = cong_chu.dau_goi(ai, g, k, ma, goi, log=lambda s: None)
    assert r["ok"] is True and r.get("thay")
    anh = cong_chu.anh_goi(goi)
    assert os.path.basename(anh) == "CHON-thumb_090.jpg" and cong_chu.kiem_dau(anh, DUNG) == ""
    assert os.path.isfile(os.path.join(goi, "_bi-loai", "CHON-thumb_001.jpg")), "bìa sai chữ cũ dời đi, không xoá"


def test_tep_bia_co_tim_ca_jpg_cua_bia_lo_va_chon_tep_moi_hon(tmp_path):
    # 18/10/2026 — bìa lô xuất thumb_00N.jpg; cổng chữ chỉ tìm .png nên không bao giờ thử hạng nhì/ba
    d = str(tmp_path)
    assert auto_khau._tep_bia_co(d, 2).endswith("thumb_002.png")  # noqa: SLF001 — chưa có tệp: đường vẽ cũ
    jpg = _anh(os.path.join(d, "thumb_002.jpg"))
    assert auto_khau._tep_bia_co(d, 2) == jpg  # noqa: SLF001
    png = _anh(os.path.join(d, "thumb_002.png"))
    os.utime(png, (1, 1))
    assert auto_khau._tep_bia_co(d, 2) == jpg, "lô bìa lô (jpg) mới hơn png của lô cũ"  # noqa: SLF001
    os.utime(jpg, (0, 0))
    assert auto_khau._tep_bia_co(d, 2) == png  # noqa: SLF001



# ── 18/10/2026: S05 gói bàn giao TRƯỚC cổng chữ — so CHỮ THẬT trên ảnh, lượt đọc hỏng = chưa kiểm ──────────────────


class AiRong(AiGia):
    """Như AiGia nhưng `rong` lượt đọc ảnh đầu tiên trả RỖNG (không dòng nào) — như lượt đọc sau 409 của ShopAPI."""

    def __init__(self, rong=0, **kw):
        super().__init__(**kw)
        self.rong, self.khoa_doc = rong, []

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        if loi_nhac.startswith("Read the text printed"):
            self.khoa_doc.append(khoa)
            if self.rong > 0:
                self.rong -= 1
                self.lan.append((loi_nhac[:30], khoa, mo_hinh))
                return json.dumps({"dong": [], "chu_thua": [], "ky_tu_hong": False, "vet_xoa": False})
        return super().__call__(loi_nhac, mo_hinh=mo_hinh, khoa=khoa, toi_da_token=toi_da_token, anh=anh)


def test_goi_cu_chu_ho_so_lech_thi_dau_bang_chu_that_tren_anh(tmp_path):
    # hồ sơ/THUMB của lượt ghi chữ CŨ; bìa thật in chữ khác, đúng chính tả + đúng chủ đề → đóng dấu chữ thật
    g, k, ma, goi = _goi_cho(tmp_path, chu="人を惹きつける 習慣の正体")
    r = cong_chu.dau_goi(AiGia(theo_lan=[DUNG, DUNG]), g, k, ma, goi, log=lambda s: None)
    assert r["ok"] is True and r["chu"] == DUNG and "đọc 2 lượt khớp" in r["ly_do"]
    assert cong_chu.kiem_dau(cong_chu.anh_goi(goi), DUNG) == ""
    # chữ thật CHÉP chữ bìa đối thủ → không dấu chữ ấy; chữ mong đợi khác ảnh, lượt đã dọn nền → GIỮ (None, không "hỏng")
    g2, k2, ma2, goi2 = _goi_cho(tmp_path / "b", chu="人を惹きつける 習慣の正体")
    with open(os.path.join(g2, "PROJECTS", "AUTO", k2, "0001", cong_chu.TEP_CHU_BIA_DOI_THU), "w",
              encoding="utf-8") as f:
        f.write(DUNG)
    r2 = cong_chu.dau_goi(AiGia(theo_lan=[DUNG, DUNG]), g2, k2, ma2, goi2, log=lambda s: None)
    assert r2["ok"] is None and "chữ bìa đối thủ" in r2["ly_do"] and cong_chu.kiem_dau(cong_chu.anh_goi(goi2))


def test_goi_luot_doc_rong_hoac_hong_la_chua_kiem_khong_phai_truot(tmp_path):
    g, k, ma, goi = _goi_cho(tmp_path)
    # một lượt rỗng → đọc lại MỘT lần bằng khoá mới → đạt
    ai = AiRong(rong=1, theo_lan=[DUNG, DUNG])
    r = cong_chu.dau_goi(ai, g, k, ma, goi, log=lambda s: None)
    assert r["ok"] is True and ai.khoa_doc[1] == ai.khoa_doc[0] + ":lai"
    g2, k2, ma2, goi2 = _goi_cho(tmp_path / "b")
    r2 = cong_chu.dau_goi(AiRong(rong=9), g2, k2, ma2, goi2, log=lambda s: None)
    assert r2["ok"] is None and "chưa đọc được" in r2["ly_do"] and "≠" not in r2["ly_do"], r2
    assert cong_chu.kiem_dau(cong_chu.anh_goi(goi2)), "không bao giờ dấu khi chưa đọc được"
    # khoá theo GIỜ: lượt S05 sau không phát lại kết quả đọc cũ
    assert cong_chu._khoa_lan(ma) != "dau-goi:" + ma and cong_chu._khoa_lan(ma).startswith("dau-goi:" + ma + ":")  # noqa: SLF001
    # kiem_anh: hai lượt rỗng → chưa kiểm (None), không phải TRƯỢT 「」 ≠ X
    kq = cong_chu.kiem_anh(AiRong(rong=9), cong_chu.anh_goi(goi2), DUNG)
    assert kq["ok"] is None


def test_dau_goi_cli_giu_la_ma_hoan(tmp_path, monkeypatch):
    from core import ky_nang_tu
    g, k, ma, goi = _goi_cho(tmp_path)
    monkeypatch.setattr(cong_chu, "_goi_that", lambda goc: AiRong(rong=99))
    assert cong_chu.main(["dau-goi", "--kenh", k, "--goc", g]) == 10 and 10 in ky_nang_tu.MA_HOAN
    monkeypatch.setattr(cong_chu, "_goi_that", lambda goc: AiGia(theo_lan=[DUNG, DUNG]))
    assert cong_chu.main(["dau-goi", "--kenh", k, "--goc", g]) == 0


def test_goi_da_don_khong_con_cho_dang(tmp_path):
    g, k, ma, goi = _goi_cho(tmp_path)
    assert [x["ma"] for x in cong_chu.goi_cho_dang(g, k)] == [ma]
    with open(os.path.join(goi, "da-don.json"), "w", encoding="utf-8") as f:
        json.dump({"ma_goi": ma, "ly_do": "DONE: gói Bỏ", "xoa": ["8-video.mp4", "thumb_001.png"]}, f)
    assert cong_chu.goi_cho_dang(g, k) == [], "gói đã dọn (Bỏ / đã lên YouTube) không còn chờ đăng"


# ── 18/10/2026: dòng NHIỀU MÀU đọc là MỘT dòng; cổng cuối soát chữ bìa CÓ chỗ xuống dòng ──────────────────────────────


def test_dong_nhieu_mau_doc_tach_doan_van_la_mot_dong():
    mong = "朝の散歩で 足りないのは時間じゃない"
    # người đọc tách từng đoạn màu 「時間」「じゃ」「ない」 thành mục riêng → vẫn khớp tuyệt đối (bỏ khoảng trắng/xuống dòng)
    assert cong_chu.xet_doc({"chu": "朝の散歩で 足りないのは 時間 じゃ ない"}, mong) == []
    assert cong_chu.xet_doc({"chu": "朝の散歩で\n足りないのは\n時間\nじゃ\nない"}, mong) == []
    assert cong_chu.xet_doc({"chu": "朝の散歩で 足りないのは 時間 じゃ"}, mong), "thiếu đoạn vẫn trượt"
    assert cong_chu.xet_doc({"chu": "朝の散歩で 足りないのは 時間 じゃ ない ない"}, mong), "lặp đoạn vẫn trượt"


def test_cong_cuoi_soat_chu_bia_co_cho_xuong_dong_khong_soat_chuoi_noi_lien(tmp_path, monkeypatch):
    """TL2-T7-0031: chữ dự kiến của bìa lô là các dòng/đoạn màu NỐI LIỀN → biên tập viên "sửa" thêm 「で」 → tấm đầu bị
    loại oan. Cùng chữ (bỏ khoảng) với chữ bìa → soát + đóng dấu bằng CHỮ BÌA có chỗ xuống dòng."""
    from core import bia_theo_khuon as btk
    chu = "朝の散歩で 足りないのは時間じゃない"
    luot, tm = _luot(tmp_path, chu=chu)
    _bo_bia(tm)
    btk.ghi_ke_hoach(tm, {"che_do": "bia_lo", "muc": [{"so": s, "chu_du_kien": chu.replace(" ", "")} for s in _MAU]})
    soat, doc = [], []
    monkeypatch.setattr(auto_khau, "_soat_chu_luu", lambda bc, l, t, c, td: soat.append(c) or {"ok": True, "chu": c})
    monkeypatch.setattr(auto_khau, "_xac_minh_chu_so",
                        lambda bc, l, t, tep, c: doc.append(c) or {"dat": True, "ly_do": []})
    monkeypatch.setattr(auto_khau, "_dau_du_phong", lambda *a, **k: None)
    r = auto_khau._cong_chu_bia(_bc(str(tmp_path), AiGia(), []), luot, tm, chu, TIEU_DE)  # noqa: SLF001
    assert r["dat"] is True and soat == [chu] and doc == [chu], (soat, doc)
    # chữ dự kiến KHÁC chữ bìa (bìa rút gọn) → giữ chữ dự kiến
    soat.clear()
    btk.ghi_ke_hoach(tm, {"che_do": "bia_lo", "muc": [{"so": s, "chu_du_kien": "朝の散歩で 時間じゃない"} for s in _MAU]})
    auto_khau._cong_chu_bia(_bc(str(tmp_path), AiGia(), []), luot, tm, chu, TIEU_DE)  # noqa: SLF001
    assert soat == ["朝の散歩で 時間じゃない"]
