"""A/B tiêu đề + bìa (16/10/2026 — chủ duyệt «Cho dùng») + chữ bìa không chép đối thủ / đúng chủ đề + bộ đọc bảng danh
sách phát.

Phủ: công tắc kênh `ab_tieu_de`; chọn chế độ («Tiêu đề và hình thu nhỏ» / «Chỉ tiêu đề» / «Chỉ hình thu nhỏ»); luật
tiêu đề (soát chữ, độ dài, nhãn đầu, không chép đối thủ, khác hẳn A); cò (a) video mới + trần ngày; cò (b) video trượt →
A/B thay đổi trực tiếp, kênh không có A/B → đổi trực tiếp; không đụng video đang có thử nghiệm; đọc lại tiêu đề; chữ bìa
chép đối thủ / lạc chủ đề → viết lại; bìa nhì/ba chưa dấu → dấu trên BẢN SAO.

Cô lập trong `tmp_path`; AI GIẢ; không mạng, không Chrome. Mã video / kênh / tiêu đề đều GIẢ.
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
if str(GOC_KHO / "vm") not in sys.path:
    sys.path.insert(0, str(GOC_KHO / "vm"))

import studio_may_dom as sdm  # noqa: E402

from core import ab_tieu_de as ab  # noqa: E402
from core import cong_chu, studio_may as sm  # noqa: E402
from core import giam_doc as gd  # noqa: E402
from core.giam_doc import cuu_ctr  # noqa: E402
from core.giam_doc.du_lieu import BangSo  # noqa: E402

K = "ABX-T7"
BAY = dt.datetime(2026, 10, 16, 15, 35)
A = "【脳科学】感情的にならない人が持つ静かな強さ"
KB = "感情的にならない人は、怒りを感じても一呼吸おきます。静かな強さとは、反応を選ぶ力です。頭のいい人ほど距離を取ります。"
DOI_THU = "冷静な人ほど怒らない。会議でも一瞬で要点を見抜く人の決定的な違い"


def _ghi(p, du):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    with io.open(str(p), "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du, ensure_ascii=False))


class AiGia:
    """Biên tập viên / giám đốc / người đọc ảnh GIẢ. `lac_de`: chữ bị xét lạc chủ đề; `sai`: chữ soát chính tả sai
    (không sửa được); `tieu_de`: danh sách giám đốc trả; `doc`: chữ "trên ảnh"; `hong_chu_de`: lượt xét chủ đề lỗi."""

    def __init__(self, tieu_de=(), lac_de=(), sai=(), doc="", hong_chu_de=False, cuu=""):
        self.tieu_de, self.lac_de, self.sai, self.doc = list(tieu_de), set(lac_de), set(sai), doc
        self.hong_chu_de, self.cuu = hong_chu_de, cuu
        self.lan = []

    def __call__(self, ln, mo_hinh="", khoa="", toi_da_token=0, anh=None):
        self.lan.append(ln[:40])
        if ln.startswith("You check that the"):
            if self.hong_chu_de:
                raise RuntimeError("cổng rớt")
            chu = ln.split("TO CHECK: 「", 1)[1].split("」", 1)[0]
            return json.dumps({"hop": chu not in self.lac_de, "ly_do": "gia"})
        if "machine check flagged" in ln:
            return json.dumps({"dung": True, "xac_nhan": [], "chu_sua": ""})
        if "THUMBNAIL TEXT (a space only marks a line break): 「" in ln:
            chu = ln.split("THUMBNAIL TEXT (a space only marks a line break): 「", 1)[1].split("」", 1)[0]
            if chu in self.sai:
                return json.dumps({"dung": False, "loi": [{"sai": "x", "dung": "y", "ly_do": "sai"}], "chu_sua": ""})
            return json.dumps({"dung": True, "loi": [], "chu_sua": ""})
        if ln.startswith("Read the text printed"):
            return json.dumps({"dong": self.doc.split(" "), "chu_thua": [], "ky_tu_hong": False, "vet_xoa": False},
                              ensure_ascii=False)
        if "THUMB: <text>" in ln:
            return "THUMB: 静かな強さの正体 反応を選ぶ力"
        if ln.startswith("THỬ NGHIỆM A/B TIÊU ĐỀ"):
            return json.dumps({"tieu_de": self.tieu_de, "ly_do": "thử góc khác", "do_tin": 0.6}, ensure_ascii=False)
        if ln.startswith("CỨU VIDEO CTR THẤP"):
            return json.dumps({"tieu_de_moi": self.cuu, "khung": "to_mo", "ly_do": "CTR thấp"}, ensure_ascii=False)
        return "{}"


@pytest.fixture(autouse=True)
def _khong_hoi_dong(monkeypatch):
    monkeypatch.setenv("SHOPAPI_HOI_DONG", "0")
    from core import bien_tap_content
    monkeypatch.setattr(bien_tap_content, "thang_mo_hinh", lambda _g, _k: ["m1"])


# ═══ 1. CÔNG TẮC + CHẾ ĐỘ + LUẬT TIÊU ĐỀ ═══════════════════════════════════════

def test_cong_tac_kenh_ab_tieu_de():
    assert ab.bat({"giam_doc": "goi_y", "giam_doc_studio": True}) is True           # mặc định theo giam_doc_studio
    assert ab.bat({"giam_doc": "goi_y"}) is False                                   # như TL4-T7: không khai → tắt
    assert ab.bat({"giam_doc": "goi_y", "giam_doc_studio": "true", "ab_tieu_de": False}) is False
    assert ab.bat({"giam_doc": "goi_y", "ab_tieu_de": "true"}) is True              # khai riêng thắng
    assert ab.bat({"giam_doc": "tat", "giam_doc_studio": True, "ab_tieu_de": True}) is False


@pytest.mark.parametrize("nt,nb,mong", [
    (2, 2, ("tieu_de_bia", 3)), (2, 1, ("tieu_de_bia", 2)), (1, 2, ("tieu_de_bia", 2)),
    (2, 0, ("tieu_de", 3)), (1, 0, ("tieu_de", 2)), (0, 2, ("bia", 3)), (0, 0, ("", 0)), (5, 5, ("tieu_de_bia", 3)),
])
def test_chon_che_do(nt, nb, mong):
    assert ab.chon_che_do(nt, nb) == mong


def test_luat_tieu_de_do_dai_nhan_khac_han_va_khong_chep():
    tot = "【脳科学】怒らない人だけが知っている反応を選ぶ技術"
    assert ab.kiem_tieu_de(tot, A, (), [DOI_THU]) == ""
    assert "dài" in ab.kiem_tieu_de("【脳科学】" + "静" * 120, A)
    assert "nhãn đầu" in ab.kiem_tieu_de("怒らない人だけが知っている反応を選ぶ技術", A)
    assert "cấm" in ab.kiem_tieu_de("【脳科学】怒らない人<秘密>", A)
    assert "trùng" in ab.kiem_tieu_de("【脳科学】 感情的にならない人が持つ静かな強さ！", A)
    assert "gần như giống" in ab.kiem_tieu_de("【脳科学】感情的にならない人が持つ静かな強さの正体", A)
    assert "chép" in ab.kiem_tieu_de("【脳科学】冷静な人ほど怒らない。会議でも一瞬で要点を見抜く", A, (), [DOI_THU])
    assert "gần như giống" in ab.kiem_tieu_de("【脳科学】怒らない人だけが知っている反応を選ぶ技術とは", A, [tot])
    assert ab.chuan_nhan("怒らない人の技術", A) == "【脳科学】怒らない人の技術"
    assert ab.chuan_nhan("【心理学】怒らない人の技術", A) == "【脳科学】怒らない人の技術"


def test_soat_tieu_de_chinh_ta_chu_de_va_ai_hong():
    t1, t2, t3 = "【脳科学】怒らない人だけが知っている反応を選ぶ技術", "【脳科学】一呼吸おける人の距離の取り方", \
        "【脳科学】お金が貯まる人の財布の秘密"
    r = ab.soat_tieu_de(AiGia(sai={t2}, lac_de={t3}), [t1, t2, t3], tieu_de_a=A, ngu_canh=KB, thang=("m",), toi_da=3)
    assert r["dat"] == [t1] and not r["chua"]
    ly = {b["tieu_de"]: b["ly_do"] for b in r["bo"]}
    assert "soát chữ" in ly[t2] and "chủ đề" in ly[t3]
    r = ab.soat_tieu_de(AiGia(hong_chu_de=True), [t1], tieu_de_a=A, ngu_canh=KB, thang=("m",))
    assert r["dat"] == [] and r["chua"] is True                                    # AI hỏng → để lượt sau


# ═══ 2. CÒ (a) VIDEO MỚI · CÒ (b) VIDEO TRƯỢT · RÀO ĐỔI TRỰC TIẾP ═══════════════

def _goc(tmp_path, yaml="giam_doc: \"goi_y\"\ngiam_doc_studio: true\n"):
    g = str(tmp_path)
    _ghi(os.path.join(g, "CHANNEL", K, "kenh.yaml"), 'ma: "{0}"\n'.format(K) + yaml)
    for i in range(1, 6):
        d = os.path.join(g, "PROJECTS", "AUTO", K, "%04d" % i)
        _ghi(os.path.join(d, "1-tieu-de.txt"), "TITLE: {0}\nTHUMB: 静かな強さ 反応を選ぶ\n".format(A))
        _ghi(os.path.join(d, "1-kich-ban.txt"), KB)
        _ghi(os.path.join(d, "0-doi-thu.txt"), "TITLE: {0}\nVIDEO_ID: FAKEsrc0001\n".format(DOI_THU))
    return g


def _bs_moi(goc, n=3, cai=None):
    bs = BangSo(goc=goc, ma_kenh=K, bay_gio=BAY, cai=cai or {"giam_doc": "goi_y", "giam_doc_studio": True,
                                                              "ngon_ngu": "ja"})
    bs.video = [{"id": "FAKEmoi%04d" % i, "ma_goi": "{0}-{1:04d}".format(K, i), "tieu_de": A, "tuoi_gio": 5.0 + i,
                 "tu_tool": True, "chup": [], "lich_su_sua": [], "tieu_de_da_cham": [], "thang": False}
                for i in range(1, n + 1)]
    bs.video.append({"id": "FAKEcu00001", "ma_goi": K + "-0005", "tieu_de": A, "tuoi_gio": 300.0, "tu_tool": True,
                     "chup": [], "lich_su_sua": [], "tieu_de_da_cham": [], "thang": False})
    return bs


def test_co_a_video_moi_lap_ab_tran_ngay_va_viec_may(tmp_path):
    goc = _goc(tmp_path)
    bs = _bs_moi(goc)
    ai = AiGia(tieu_de=["怒らない人だけが知っている反応を選ぶ技術", "一呼吸おける人の距離の取り方"])
    ra = ab.xu_ly_moi(goc, K, bs, ai)
    assert [m["video_id"] for m in ra] == ["FAKEmoi0001", "FAKEmoi0002"]           # mới trước; trần 2/ngày; cũ > 72h bỏ
    m = ra[0]
    assert m["nguon"] == "moi" and m["trang_thai"] == ab.TT_CHO and m["soat"]["ok"]
    assert m["tieu_de_them"] == ["【脳科学】怒らない人だけが知っている反応を選ぶ技術", "【脳科学】一呼吸おける人の距離の取り方"]
    viec = gd.doc_viec_may_kieu(goc, gd.LOAI_AB_TIEU_DE)
    assert len(viec) == 2 and viec[0]["kenh"] == K and m["viec"] == viec[0]["id"]
    assert sm.dieu_kien_test(goc, K)[0] is True                                     # skill D13 thấy việc A/B
    assert ab.xu_ly_moi(goc, K, bs, ai) == []                                       # hôm nay đủ trần
    bs.bay_gio = BAY + dt.timedelta(days=1)
    assert [m["video_id"] for m in ab.xu_ly_moi(goc, K, bs, ai)] == ["FAKEmoi0003"]  # mai: video còn lại, không lặp
    assert ab.chan_doi_truc_tiep(goc, K, "FAKEmoi0001")


def test_co_a_tat_khi_kenh_tat_hoac_khong_co_ab_hoac_ai_hong(tmp_path):
    goc = _goc(tmp_path)
    ai = AiGia(tieu_de=["怒らない人だけが知っている反応を選ぶ技術"])
    assert ab.xu_ly_moi(goc, K, _bs_moi(goc, cai={"giam_doc": "goi_y"}), ai) == []      # như TL4-T7
    assert ab.xu_ly_moi(goc, K, _bs_moi(goc), AiGia(tieu_de=["怒らない人だけが知っている反応を選ぶ技術"],
                                                    hong_chu_de=True)) == []          # AI hỏng → lượt sau, không ghi
    assert ab.doc_so(goc, K) == []
    ab.ghi_so(goc, K, [{"video_id": "FAKExxx0001", "trang_thai": ab.TT_KHONG_QUYEN, "luc": BAY.isoformat(),
                        "ly_do": "nút tắt"}])
    assert "chưa dùng được" in ab.kenh_khong_ab(goc, K, BAY)
    assert ab.xu_ly_moi(goc, K, _bs_moi(goc), ai) == []


def _bs_truot(goc, ab_bat=True):
    from tests.test_cuu_ctr import _bs_hong, _them_cung_tuoi
    bs = _them_cung_tuoi(_bs_hong(goc, ab=ab_bat))
    bs.ma_kenh = K
    bs.cai["ngon_ngu"] = "ja"
    for v in bs.video:
        v["ma_goi"] = v["ma_goi"].replace("GDX", K)
    bs.video[0]["tieu_de"] = A
    return bs


def _td(bs):
    return [dict(d, plugin="cuu_ctr", duoc=True) for d in cuu_ctr.de_xuat(bs, cuu_ctr.quan_sat(bs))]


def test_co_b_video_truot_thanh_ab_thay_doi_truc_tiep(tmp_path):
    goc = _goc(tmp_path)
    bs = _bs_truot(goc)
    ai = AiGia(tieu_de=["一呼吸おける人の距離の取り方"], cuu="怒らない人だけが知っている反応を選ぶ技術")
    ra = cuu_ctr.xu_ly(goc, K, bs, _td(bs), ai)
    assert len(ra) == 1 and ra[0]["trang_thai"] == "ab" and ra[0]["ab_id"]
    e = ab.muc_cua(goc, K, "FAKEhong001")
    assert e["nguon"] == "truot" and e["tieu_de_them"][0] == "【脳科学】怒らない人だけが知っている反応を選ぶ技術"
    assert len(e["tieu_de_them"]) == 2
    assert cuu_ctr.dong_bo(goc, bay_gio=BAY)["xep"] == 0 and cuu_ctr.doc_hang(goc) == []   # không vào hàng đổi trực tiếp
    r = cuu_ctr.kiem_rao(bs, bs.video[0], [])
    assert not r["duoc"] and "A/B" in r["ly_do"]                                   # đang A/B → không đổi trực tiếp
    # A/B không đặt được (Studio: không quyền) → đường lùi đổi trực tiếp
    ab.cap_nhat(goc, K, "FAKEhong001", trang_thai=ab.TT_KHONG_QUYEN, ket={"ly_do": "nút tắt"})
    cuu_ctr.dong_bo(goc, bay_gio=BAY)
    assert cuu_ctr.doc_duyet(goc, K)[0]["trang_thai"] == "cho_rao"
    cuu_ctr.xu_ly(goc, K, bs, [], None)
    assert cuu_ctr.doc_duyet(goc, K)[0]["trang_thai"] == "tu_ap"


def test_co_b_kenh_khong_ab_doi_truc_tiep_va_tieu_de_truot_soat_khong_doi(tmp_path):
    goc = _goc(tmp_path)
    bs = _bs_truot(goc, ab_bat=False)
    ra = cuu_ctr.xu_ly(goc, K, bs, _td(bs), AiGia(cuu="怒らない人だけが知っている反応を選ぶ技術"))
    assert ra[0]["trang_thai"] == "tu_ap" and ab.doc_so(goc, K) == []             # kênh tắt A/B: như cũ
    goc2 = _goc(tmp_path / "b")
    bs2 = _bs_truot(goc2)
    t = "怒らない人だけが知っている反応を選ぶ技術"
    ra = cuu_ctr.xu_ly(goc2, K, bs2, _td(bs2), AiGia(cuu=t, tieu_de=[], lac_de={"【脳科学】" + t}))
    assert ra[0]["trang_thai"] == "bo" and "A/B" in ra[0]["ly_do_bo"]              # không đổi bằng tiêu đề trượt soát


# ═══ 3. BỘ CHẠY DOM: việc A/B, video đang thử nghiệm, điền + đọc lại tiêu đề ════

def test_phan_tich_va_doc_lai_tieu_de():
    exp = {"state": "CREATOR_EXPERIMENT_STATE_STARTED",
           "variants": [{"title": {"text": A}}, {"title": {"text": "【脳科学】怒らない人の技術"}}]}
    tn = sdm.phan_tich_thu_nghiem(exp)
    assert tn["trang_thai"] == "dang_chay" and tn["so_bia"] == 2 and A in tn["tieu_de"]
    assert sdm.tieu_de_doc_lai_khop(tn["tieu_de"], [A, "【脳科学】怒らない人の技術"]) == []
    assert sdm.tieu_de_doc_lai_khop(tn["tieu_de"], [A, "【脳科学】別の題"]) == ["【脳科学】別の題"]
    assert sdm.tieu_de_doc_lai_khop([], [A]) == []                                   # gói không ghi tiêu đề: không phán


class _St:
    def __init__(self, o):
        self.o, self.bo, self.dang = o, {"phan_tu": {}}, None

    def bam(self, pt):
        self.dang = pt["i"]

    def _ctrl_a(self):
        pass

    def _chen(self, t):
        self.o[self.dang] = t.replace("技術", "技") if "HONG" in self.o[0] else t

    def ghi_bang_chung(self, nhan):
        return {"anh": ""}

    def doc_chu(self, k):
        return self.o[0]


class _S:
    def __init__(self, o):
        self.st = _St(list(o))

    def js(self, bt):
        if bt == sdm._JS_O_TIEU_DE_HOP:  # noqa: SLF001
            return [{"i": i, "pt": {"i": i}, "chu": c} for i, c in enumerate(self.st.o)]
        return None

    def ngu(self, s):
        pass


def test_dien_tieu_de_o1_phai_la_tieu_de_dang_chay_va_doc_lai():
    S = _S([A, "", ""])
    assert sdm.dien_tieu_de(S, "v", A, ["【脳科学】怒らない人の技術", "【脳科学】距離の取り方"], lambda s: None) == 3
    assert S.st.o[1:] == ["【脳科学】怒らない人の技術", "【脳科学】距離の取り方"]
    with pytest.raises(sdm.tl.LoiMuc, match="không phải tiêu đề đang chạy"):
        sdm.dien_tieu_de(_S(["khác", "", ""]), "v", A, ["x" * 10], lambda s: None)
    with pytest.raises(sdm.tl.LoiMuc, match="đọc lại lệch"):
        sdm.dien_tieu_de(_S(["HONG", ""]), "v", "HONG", ["【脳科学】怒らない人の技術"], lambda s: None)
    with pytest.raises(sdm.tl.LoiMuc, match="chỉ có 2 ô"):
        sdm.dien_tieu_de(_S([A, ""]), "v", A, ["a" * 8, "b" * 8], lambda s: None)


def test_video_dang_thu_nghiem_khong_dung(monkeypatch):
    goi = {"title": A, "videoCreatorExperiment": {"state": "CREATOR_EXPERIMENT_STATE_STARTED"}}
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: (goi, {"nut": [], "chu": ""}))
    S = _S([A])
    kq = sdm.test_mot_video(S, "v", {"tieu_de": ["【脳科学】怒らない人の技術"], "chon": []}, lambda s: None)
    assert kq["ket"] == sm.KV_DA_CO and S.st.dang is None                          # không bấm gì


def test_tieu_de_them_soat_lai_voi_tieu_de_dang_chay(monkeypatch):
    """A đã bị đổi (= tiêu đề thêm) từ lúc lập → bản ấy bị bỏ; không còn gì để thử → không ứng viên, không mở hộp."""
    t = "【脳科学】怒らない人だけが知っている反応を選ぶ技術"
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: ({"title": t, "videoCreatorExperiment": {}},
                                                              {"nut": [{"chu": "Thử nghiệm A/B", "tat": False, "x": 1,
                                                                        "y": 1}], "chu": ""}))
    kq = sdm.test_mot_video(_S([t]), "v", {"tieu_de": [t], "chon": []}, lambda s: None)
    assert kq["ket"] == sm.KV_KHONG_UNG_VIEN


def test_chay_test_viec_ab_truyen_tieu_de_va_ghi_so(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    monkeypatch.setattr(sdm, "GOC", os.path.join(goc, "vm"))
    monkeypatch.setattr(sdm, "GOC_TOOL", goc)
    monkeypatch.setattr(sdm, "_kiem_dung", lambda agent, kenh: None)
    monkeypatch.setattr(sdm, "tai_bia_a", lambda *a, **kw: "")
    _ghi(os.path.join(goc, "vm", "logs", "so-video-id.json"), {K + "/" + K + "-0001": {"video_id": "FAKEmoi0001"}})
    ab.lap(goc, K, video_id="FAKEmoi0001", ma_goi=K + "-0001", tieu_de_a=A,
           tieu_de_them=["【脳科学】怒らない人だけが知っている反応を選ぶ技術"], nguon="moi", bay_gio=BAY)
    seen = {}

    def mot(S, vid, kh, ghi, thu=False, khong_luu=False):
        seen[vid] = kh
        return {"ket": sm.KV_DA_DAT, "che_do": "tieu_de", "so_bien_the": 2, "tieu_de": [A] + kh["tieu_de"],
                "trang_thai": "dang_chay", "tieu_de_doc_lai": [A] + kh["tieu_de"]}
    monkeypatch.setattr(sdm, "test_mot_video", mot)
    ma = sdm.chay_test(K, lambda s: None, phien=lambda k, g, lam, c, **kw: (0, lam(object(), None, None)))
    assert ma == sdm.MA_XONG and seen["FAKEmoi0001"]["tieu_de"] == ["【脳科学】怒らない人だけが知っている反応を選ぶ技術"]
    e = ab.muc_cua(goc, K, "FAKEmoi0001")
    assert e["trang_thai"] == ab.TT_DA_DAT and e["ket"]["che_do"] == "tieu_de" and A in e["ket"]["tieu_de_doc_lai"]
    m = gd.doc_viec_may_kieu(goc, gd.LOAI_AB_TIEU_DE, None)[0]
    assert m["trang_thai"] == "xong" and "Chỉ" not in m["ket"]["ly_do"] and "biến thể" in m["ket"]["ly_do"]


# ═══ 4. CHỮ BÌA: không chép đối thủ, đúng chủ đề ═══════════════════════════════

BO_CUC = ("TEXT PLACEMENT: The text block is positioned on the left, 3 lines. Line 1: 'いちばん手軽で' (height ~22%), "
          "Line 2: 'いちばん効く習慣' (height ~24%), Line 3: 'それが散歩' (height ~26%). The character's book is open.\n"
          "TEXT COLOURS AND BACKING: white #FFFFFF, yellow #FFE600.\n")


def test_chu_bia_doi_thu_tu_bo_cuc_va_tep_ocr(tmp_path):
    d = str(tmp_path)
    _ghi(os.path.join(d, cong_chu.TEP_BIA_DOI_THU), BO_CUC)
    ds = cong_chu.chu_bia_doi_thu(d)
    assert "いちばん手軽で いちばん効く習慣 それが散歩" in ds and "それが散歩" in ds
    assert not any("character" in x for x in ds)
    _ghi(os.path.join(d, cong_chu.TEP_CHU_BIA_DOI_THU), "読める 文字\n")
    assert cong_chu.chu_bia_doi_thu(d)[0] == "読める 文字"
    assert cong_chu.chu_bia_doi_thu(str(tmp_path / "khong")) == []


def test_kiem_chep_trung_chua_tron_va_ti_le():
    dt_ = ["いちばん手軽で いちばん効く習慣 それが散歩"]
    assert "nguyên văn" in cong_chu.kiem_chep("いちばん手軽で いちばん効く 習慣 それが散歩", dt_)
    assert "nguyên văn" in cong_chu.kiem_chep("いちばん効く習慣", dt_)          # chứa trọn
    assert "chuỗi 3 ký tự" in cong_chu.kiem_chep("いちばん手軽でいちばん効く方法です", dt_)   # tỉ lệ > 0,6
    assert cong_chu.kiem_chep("静かな強さの正体 反応を選ぶ力", dt_) == ""
    assert cong_chu.kiem_chep("静かな強さ", []) == ""


def test_soat_chat_chep_doi_thu_va_lac_de_thi_viet_lai():
    dt_ = ["いちばん手軽で いちばん効く習慣 それが散歩"]
    ai = AiGia()
    r = cong_chu.soat_chat(ai, dt_[0], tieu_de=A, ngu_canh=KB, thang=("m",), doi_thu=dt_)
    assert r["ok"] is False and r["chep_doi_thu"] and "đối thủ" in r["viet_lai_vi"] and ai.lan == []   # không tốn AI
    ai = AiGia(lac_de={"お金が貯まる 財布の秘密"})
    r = cong_chu.soat_chat(ai, "お金が貯まる 財布の秘密", tieu_de=A, ngu_canh=KB, thang=("m",))
    assert r["ok"] is False and "chủ đề" in r["viet_lai_vi"] and r["chu_de"]["hop"] is False
    r = cong_chu.soat_chat(AiGia(hong_chu_de=True), "静かな強さ 反応を選ぶ", tieu_de=A, ngu_canh=KB, thang=("m",))
    assert r["ok"] is None                                                          # AI hỏng: giữ, thử lại
    assert cong_chu.soat_chat(AiGia(), "静かな強さ 反応を選ぶ", tieu_de=A, ngu_canh=KB, thang=("m",))["ok"] is True
    # chot_chu: chữ chép đối thủ → viết lại (lý do chép đi vào lời nhắc) → bản mới qua soát
    ai = AiGia()
    r = cong_chu.chot_chu(ai, dt_[0], tieu_de=A, ngu_canh=KB, thang=("m",), doi_thu=dt_)
    assert r["ok"] is True and r["viet_lai"] and r["chu"] == "静かな強さの正体 反応を選ぶ力"


def test_viet_chu_bia_rieng_khong_nhan_ban_chep():
    goi = lambda ln, **kw: "THUMB: いちばん手軽で いちばん効く習慣"               # noqa: E731
    assert cong_chu.viet_chu_bia_rieng(goi, tieu_de=A, chu_doi_thu="いちばん手軽で いちばん効く習慣 それが散歩") == ""
    goi2 = lambda ln, **kw: "THUMB: 静かな強さの正体 反応を選ぶ力"                     # noqa: E731
    assert cong_chu.viet_chu_bia_rieng(goi2, tieu_de=A, chu_doi_thu="それが散歩") == "静かな強さの正体 反応を選ぶ力"
    assert cong_chu.viet_chu_bia_rieng(None, tieu_de=A) == ""


# ═══ 5. BÌA NHÌ/BA CHƯA DẤU → DẤU TRÊN BẢN SAO ════════════════════════════════

def _anh(p, mau):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    Image.new("RGB", (1280, 720), mau).save(str(p), format="JPEG", quality=90)
    return str(p)


def test_dau_ung_vien_tren_ban_sao_khong_ghi_channel(tmp_path):
    goc = _goc(tmp_path)
    ma = K + "-0001"
    hs = os.path.join(goc, "CHANNEL", K, "ho-so-video")
    _ghi(os.path.join(hs, ma + ".json"), {"video_id": "FAKEmoi0001", "chu_bia": "静かな強さ 反応を選ぶ",
                                          "bia_2": {"so": 2, "tong_diem": 60.0, "bia_3": {"so": 3, "tong_diem": 50.0}}})
    b2 = _anh(os.path.join(hs, "anh", ma + "-bia-2.jpg"), (0, 200, 0))
    b3 = _anh(os.path.join(hs, "anh", ma + "-bia-3.jpg"), (0, 0, 200))
    thu = os.path.join(goc, "vm", "logs", "studio-may", K, "dau-lai")
    goi = []

    def dau_lai(p):
        goi.append(p)
        return sm.dau_ung_vien(goc, K, ma, p, thu, AiGia(doc="静かな強さ 反応を選ぶ"))
    chon, bo = sm.ung_vien_bia(goc, K, ma, [], cham=lambda p: {"dat": True, "diem": 80}, dau_lai=dau_lai, toi_da=1)
    assert len(chon) == 1 and goi == [b2]                                           # chỉ đóng dấu đủ `toi_da` tấm tốt nhất
    ban = chon[0]["tep"]
    assert ban.startswith(thu) and chon[0]["tep_goc"] == b2 and cong_chu.kiem_dau(ban) == ""
    assert not [t for t in os.listdir(os.path.join(hs, "anh")) if t.endswith(".do-bia.json")]   # CHANNEL không đổi
    assert any("đủ 1 ứng viên" in b["ly_do"] for b in bo) and os.path.isfile(b3)
    # đọc ra chữ khác → không dấu, không dùng
    ly, ban2 = sm.dau_ung_vien(goc, K, ma, b3, thu, AiGia(doc="ちがう 文字"))
    assert ban2 == "" and "đọc lại" in ly


# ═══ 6. BẢNG DANH SÁCH PHÁT STUDIO ═════════════════════════════════════════════

def test_so_video_hang_doc_dung_cot_khong_lay_luot_xem():
    import danh_sach_phat_dom as dd
    cot = ["Danh sách phát", "Loại", "Chế độ hiển thị", "Lần cập nhật gần nhất", "Số lượng video", "Lượt xem"]
    o = ["8 Ten 1｜phu", "Danh sách phát", "Công khai", "16 thg 10, 2026", "8", "0"]
    assert dd.so_video_hang("\n".join(o), o, cot) == 8
    chu = "8\nTen 1｜phu\nmo ta\nDanh sách phát\nCông khai\n16 thg 10, 2026\n41\n103"
    assert dd.so_video_hang(chu) == 41                                              # không có ô: dòng áp chót
    assert dd.so_video_hang("Ten\nCông khai\n12 thg 10, 2026\n7") == 7               # khuôn cũ một số
    assert dd.so_video_hang("x", ["a", "1.234"], ["Danh sách phát", "Số lượng video"]) == 1234


def test_gop_ten_bo_trung_nua_kho_toan_kho():
    import danh_sach_phat_dom as dd
    ten = dd.gop_ten(["Chu de A｜phu", "Mot minh"], ["Chu de A|phu", "mot minh", "Moi"])
    assert ten == ["Chu de A｜phu", "Mot minh", "Moi"]


def test_moi_luot_mot_kenh_viec_ab(tmp_path, monkeypatch):
    """Bộ tự kích hoạt: hai kênh cùng có việc A/B tiêu đề → lượt này chạy MỘT kênh (D13), kênh kia lượt sau."""
    from core import ky_nang as kn
    from core import ky_nang_tu as knt
    goc = str(tmp_path)
    monkeypatch.setattr(kn, "_san_sang_dom", lambda goc, kenh: "")
    monkeypatch.setattr(kn, "_gio", lambda: BAY)
    monkeypatch.setattr(knt, "khoa_may_ban", lambda goc: "")
    monkeypatch.setattr(knt, "cong_tac_bat", lambda goc: True)
    gd.ghi_viec_may_kieu(goc, gd.LOAI_AB_TIEU_DE, "KX1-T7", video_ids=["FAKEab00001"], bay_gio=BAY)
    gd.ghi_viec_may_kieu(goc, gd.LOAI_AB_TIEU_DE, "KX2-T7", video_ids=["FAKEab00002"], bay_gio=BAY)
    monkeypatch.setattr(kn, "DANH_MUC", [kn.theo_ma("D13")])
    monkeypatch.setattr(kn, "_cac_kenh", lambda goc: ["KX1-T7", "KX2-T7"])
    chay = []
    knt.tu_kich_hoat(goc, chay_lenh=lambda lenh, cwd, han: (chay.append(lenh), (10, "hoãn"))[1], in_ra=lambda s: None)
    assert len(chay) == 1 and chay[0][-1] == "--test-compare"


# ═══ 6. KẾT QUẢ THỬ NGHIỆM (20/10/2026): đọc lại → sổ → não "tieu-de" → trục kieu_tieu_de → lời nhắc ═══════════

B_THEM = "【脳科学】なぜ感情的にならない人は損をしないのか？"           # nhãn câu hỏi (khác A)
EXP_CHAY = {"state": "CREATOR_EXPERIMENT_STATE_STARTED", "resultState": "CREATOR_EXPERIMENT_RESULT_STATE_NOT_CONCLUSIVE_YET",
            "arms": [{"armId": "a1", "title": A}, {"armId": "a2", "title": B_THEM}]}


def _dat(goc, vid="FAKEmoi0001", luc=BAY):
    m = ab.lap(goc, K, video_id=vid, ma_goi=K + "-0001", tieu_de_a=A, tieu_de_them=[B_THEM], nguon="moi", bay_gio=luc)
    gd.cap_nhat_viec_may_kieu(goc, m["viec"], trang_thai="xong")         # việc đặt đã xong (bộ chạy đã đặt)
    ab.cap_nhat(goc, K, vid, trang_thai=ab.TT_DA_DAT, bay_gio=luc,
                ket={"ket": "da_dat", "che_do": "tieu_de", "tieu_de": [A, B_THEM], "trang_thai": "dang_chay"})


def test_doc_ket_thu_nghiem_rong_dang_chay_thang_va_khong_ket_luan():
    assert ab.doc_ket_thu_nghiem({})["xong"] is False
    k = ab.doc_ket_thu_nghiem(EXP_CHAY)
    assert k["xong"] is False and [n["tieu_de"] for n in k["nhanh"]] == [A, B_THEM]
    xong = dict(EXP_CHAY, state="CREATOR_EXPERIMENT_STATE_COMPLETED", resultState="CREATOR_EXPERIMENT_RESULT_STATE_WINNER",
                arms=[{"armId": "a1", "title": A, "watchTimeShare": 0.41},
                      {"armId": "a2", "title": B_THEM, "isWinner": True, "watchTimeShare": 0.59}])
    k = ab.doc_ket_thu_nghiem(xong)
    assert k["xong"] and k["thang"] == 1 and not k["khong_ket_luan"] and k["nhanh"][1]["so"]["watchTimeShare"] == 0.59
    ref = dict(xong, winningArmId="a1", arms=[{"armId": "a1", "title": A}, {"armId": "a2", "title": B_THEM}])
    assert ab.doc_ket_thu_nghiem(ref)["thang"] == 0                       # khoá "winning…" tham chiếu id nhánh
    so = dict(xong, arms=[{"title": A, "sharePercent": "38%"}, {"title": B_THEM, "sharePercent": "62%"}])
    k = ab.doc_ket_thu_nghiem(so)
    assert k["thang"] == 1 and k["suy_ra"] is True                         # không cờ: suy từ % thời gian xem
    hoa = dict(EXP_CHAY, state="CREATOR_EXPERIMENT_STATE_COMPLETED",
               resultState="CREATOR_EXPERIMENT_RESULT_STATE_INCONCLUSIVE")
    k = ab.doc_ket_thu_nghiem(hoa)
    assert k["xong"] and k["khong_ket_luan"] and k["ro_khong_ket_luan"] and k["thang"] is None


def test_can_doc_ket_qua_theo_tuoi_va_nhip(tmp_path):
    goc = _goc(tmp_path)
    _dat(goc)
    assert ab.can_doc_ket_qua(goc, K, BAY + dt.timedelta(days=1)) == []                # chưa đủ 2 ngày
    nay = BAY + dt.timedelta(days=3)
    assert ab.can_doc_ket_qua(goc, K, nay) == ["FAKEmoi0001"]
    assert ab.ghi_doc_ket_qua(goc, K, "FAKEmoi0001", ab.doc_ket_thu_nghiem(EXP_CHAY), nay) is None   # còn chạy
    assert ab.muc_cua(goc, K, "FAKEmoi0001")["trang_thai"] == ab.TT_DA_DAT
    assert ab.can_doc_ket_qua(goc, K, nay + dt.timedelta(hours=5)) == []                # đọc ≤ 1 lần / ngày
    assert ab.can_doc_ket_qua(goc, K, nay + dt.timedelta(hours=25)) == ["FAKEmoi0001"]
    ok, ly = sm.dieu_kien_test(goc, K)                                                  # D13 chạy để đọc
    assert ok and "đọc kết quả" in ly


def test_ket_qua_thang_ghi_so_nao_tu_hoc_va_loi_nhac(tmp_path, monkeypatch):
    from core import nao_bo_phan, tu_hoc
    goc = _goc(tmp_path)
    _dat(goc)
    ghi_nao = []
    monkeypatch.setattr(nao_bo_phan, "ghi", lambda *a, **kw: ghi_nao.append((a, kw)) or True)
    xong = dict(EXP_CHAY, state="CREATOR_EXPERIMENT_STATE_COMPLETED",
                arms=[{"title": A}, {"title": B_THEM, "isWinner": True}])
    kq = ab.ghi_doc_ket_qua(goc, K, "FAKEmoi0001", ab.doc_ket_thu_nghiem(xong), BAY + dt.timedelta(days=4))
    assert kq["ket_luan"] == ab.KL_THANG and kq["thang"] == "B" and kq["tieu_de_thua"] == [A]
    m = ab.muc_cua(goc, K, "FAKEmoi0001")
    assert m["trang_thai"] == ab.TT_XONG and m["doc_kq_tho"] and ab.chan_doi_truc_tiep(goc, K, "FAKEmoi0001")
    (_g, bp, loai), kw = ghi_nao[-1]
    assert (bp, loai, kw["so"]["ket"], kw["so"]["thang_la"]) == ("tieu-de", "ket_qua", "thang", "B")
    nt, na = kq["nhan_thang"], tu_hoc.nhan_tieu_de_regex(A)
    assert nt == "cau_hoi" and na != nt
    bd = tu_hoc.bang_diem(goc, K)["kieu_tieu_de"]
    assert bd[nt]["a"] == 2.0 and bd[na]["b"] == 2.0 and bd[nt]["thang_ab"] == 1          # Beta(1,1) + 1 cặp
    khoi = ab.khoi_thang(goc, K)
    assert "KẾT QUẢ A/B TIÊU ĐỀ" in khoi and B_THEM[:20] in khoi and A[:15] in khoi
    assert ab.ghi_doc_ket_qua(goc, K, "FAKEmoi0001", ab.doc_ket_thu_nghiem(xong)) is None   # đã xong: không ghi lại


def test_thu_nghiem_go_khoi_trang_sua_suy_tu_tieu_de_hien_va_dong_qua_han(tmp_path):
    goc = _goc(tmp_path)
    _dat(goc)
    nay = BAY + dt.timedelta(days=5)
    kq = ab.ghi_doc_ket_qua(goc, K, "FAKEmoi0001", ab.kt_khong_con(), nay, tieu_de_hien=B_THEM)
    assert kq["ket_luan"] == ab.KL_THANG and kq["thang"] == "B" and kq["suy_ra"] == "tieu_de_hien"
    _dat(goc, vid="FAKEmoi0002")
    kq = ab.ghi_doc_ket_qua(goc, K, "FAKEmoi0002", ab.kt_khong_con(), nay, tieu_de_hien=A)
    assert kq["ket_luan"] == ab.KL_KHONG                                  # tiêu đề vẫn A: không phân biệt được
    _dat(goc, vid="FAKEmoi0003")
    assert ab.dong_qua_han(goc, K, BAY + dt.timedelta(days=10)) == []
    dong = ab.dong_qua_han(goc, K, BAY + dt.timedelta(days=15))
    assert [m["video_id"] for m in dong] == ["FAKEmoi0003"] and dong[0]["ket_qua"]["ket_luan"] == ab.KL_KHONG
    assert ab.can_doc_ket_qua(goc, K, BAY + dt.timedelta(days=16)) == []
    assert [k["video_id"] for k in ab.ket_qua_xong(goc, K)] == ["FAKEmoi0001"]


def test_chay_test_chi_doc_ket_qua_cung_phien(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    monkeypatch.setattr(sdm, "GOC", os.path.join(goc, "vm"))
    monkeypatch.setattr(sdm, "GOC_TOOL", goc)
    monkeypatch.setattr(sdm, "_kiem_dung", lambda agent, kenh: None)
    _dat(goc, luc=dt.datetime.now() - dt.timedelta(days=3))
    xong = dict(EXP_CHAY, state="CREATOR_EXPERIMENT_STATE_COMPLETED",
                arms=[{"title": A}, {"title": B_THEM, "isWinner": True}])
    monkeypatch.setattr(sdm, "doc_trang_sua", lambda S, vid: ({"videoId": vid, "title": B_THEM,
                                                                "videoCreatorExperiment": xong}, {}))
    monkeypatch.setattr(sdm, "test_mot_video", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("không đặt")))
    phien = []
    ma = sdm.chay_test(K, lambda s: None, phien=lambda k, g, lam, c, **kw: (phien.append(c), (0, lam(object(), None, None)))[1])
    assert ma == sdm.MA_XONG and phien == ["test"]
    assert ab.muc_cua(goc, K, "FAKEmoi0001")["ket_qua"]["thang"] == "B"
    assert sdm.chay_test(K, lambda s: None, phien=lambda *a, **kw: (_ for _ in ()).throw(AssertionError("thừa"))) \
        == sdm.MA_KHONG_CAN                                                # đã đọc xong: không mở phiên nữa
