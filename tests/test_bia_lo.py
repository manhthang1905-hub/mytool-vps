"""Bìa LÔ — vẽ vài chục rồi chọn (14/10/2026, `core/bia_lo.py`).

Đạo diễn ý tưởng (đọc + giới hạn), vẽ hàng loạt (trần ảnh, ≤ 4 job song song, khoá, dùng lại nền trên đĩa), lọc cứng
(hộp chữ đè đầu nhân vật → loại; chữ lạc trên nền → loại; cổng đọc được), giám khảo hai vòng (đọc JSON, xếp hạng),
tờ liên, xuất bộ bìa cho dây chuyền (CHON + chon-bia.json + bia-2/bia-3), `bia_lo: false` giữ đường cũ.

Ảnh TỔNG HỢP bằng PIL, LLM + mô hình ảnh GIẢ — không gọi mạng, không dữ liệu kênh thật."""

from __future__ import annotations

import io
import json
import os
import re
import threading
import time
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from core import bia_lo
from core import bia_theo_khuon as btk
from core import do_bia
from core.kenh import TEP_KENH, duong_kenh

KC = bia_lo.KHUON_HOP_MAC_DINH


@pytest.fixture(autouse=True)
def _khong_xoa_dau(monkeypatch):
    """Ảnh tổng hợp không có dấu sao nhà cung cấp — bỏ bước xoá dấu (đường dò chậm ~1 giây/ảnh, có bài kiểm riêng)."""
    from core import xoa_dau_anh
    monkeypatch.setattr(xoa_dau_anh, "xoa_dau_tep", lambda duong, *a, **k: None)


def _can_font():
    if not btk._tim_font("", "同じ車に長く", "ja", kieu="hop"):  # noqa: SLF001
        pytest.skip("máy không có phông bìa kiểu hộp")


def _nen(duong: str, x_dau: float = 0.70, chu_la: bool = False) -> str:
    """Nền phẳng be + nhân vật đầu tròn TRẮNG viền ĐEN (thân dưới đầu) + một vật manh mối, cỡ ảnh nhà cung cấp."""
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (238, 214, 190))
    d = ImageDraw.Draw(im)
    d.rectangle([0.62 * W, 0.66 * H, 0.97 * W, 0.86 * H], fill=(190, 110, 60), outline=(60, 30, 20), width=6)
    d.rounded_rectangle([(x_dau + 0.02) * W, 0.53 * H, (x_dau + 0.11) * W, 0.9 * H], radius=30, fill=(248, 248, 248),
                        outline=(12, 12, 12), width=8)
    d.ellipse([x_dau * W, 0.28 * H, (x_dau + 0.13) * W, 0.52 * H], fill=(250, 250, 250), outline=(12, 12, 12), width=8)
    d.ellipse([(x_dau + 0.04) * W, 0.37 * H, (x_dau + 0.05) * W, 0.39 * H], fill=(10, 10, 10))
    d.ellipse([(x_dau + 0.08) * W, 0.37 * H, (x_dau + 0.09) * W, 0.39 * H], fill=(10, 10, 10))
    if chu_la:
        d.text((40, 40), "LOAN", fill=(40, 40, 40))
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    im.save(duong)
    return duong


def _y(i: int) -> dict:
    return {"y": "claim {0}".format(i), "manh_moi": "clue object {0}".format(i), "doi_lap": "faded crowd",
            "canh": "the figure doing thing number {0} on the right in a bright room".format(i),
            "mat": "knowing smile", "tu_the": "standing"}


# ── 1) Đạo diễn ──────────────────────────────────────────────────────────────


def test_doc_y_tuong_loc_bo_va_tran():
    ds = [_y(i) for i in range(1, 13)]
    ds[1] = dict(ds[1], manh_moi="")                       # thiếu manh mối
    ds[2] = dict(ds[2], canh="the figure holds a sign 「節約」 on the right")  # chữ Nhật trong cảnh → dễ vẽ chữ
    ds[3] = dict(ds[3], canh=ds[0]["canh"])                # trùng cảnh
    ra = bia_lo.doc_y_tuong({"y_tuong": ds + ["rác", None]}, 20)
    assert len(ra) == bia_lo.SO_Y_TOI_DA, "trần 8 ý"
    assert all(y["manh_moi"] and not bia_lo._RE_CJK.search(y["canh"]) for y in ra)  # noqa: SLF001
    assert len({y["canh"] for y in ra}) == len(ra)
    assert [y["y"] for y in ra[:2]] == ["claim 1", "claim 5"]
    assert len(bia_lo.doc_y_tuong({"y_tuong": ds}, 3)) == 3 and bia_lo.doc_y_tuong("hỏng", 7) == []


def test_dao_dien_loi_nhac_day_du_va_luot_sua():
    lan = []

    def goi(loi_nhac, **kw):
        lan.append((loi_nhac, kw))
        y = [_y(1)] if len(lan) == 1 else [_y(i) for i in range(1, 8)]
        return "```json\n" + json.dumps({"chu": ["同じ車に長く|[乗る人の]|ほとんどが"], "y_tuong": y}) + "\n```"
    du = bia_lo.dao_dien(goi, tieu_de="TIEU-DE", chu_bia="同じ車に長く乗る人のほとんどが", kich_ban="KB" * 3000,
                         muc_luc=["chuong 1", "chuong 2"], so_y=7, khoa="k")
    assert len(du["y_tuong"]) == 7 and du["chu"] == ["同じ車に長く|[乗る人の]|ほとんどが"]
    p = lan[0][0]
    assert "TIEU-DE" in p and "同じ車に長く乗る人のほとんどが" in p and "chuong 1 / chuong 2" in p
    assert "お金持ちほど" in p and "7 DISTINCT" in p and "{" not in p.split("Return JSON")[0]
    assert len(p) < 12000, "kịch bản cắt ~4.000 ký tự"
    assert len(lan) == 2 and "only 1 usable" in lan[1][0] and lan[1][1]["khoa"] == "k:dao-dien:sua"


def _chu(tang) -> list:
    return [("*" if t.get("to") else "") + "".join(("^" if p.get("nho") else "") + p["chu"] for p in t["phan_mau"])
            for t in tang]


def test_doc_chu_bia_dau_tay_may_va_ai():
    t = bia_lo.doc_chu_bia("同じ車に長く|*乗る人の|ほとんどが", KC)
    assert _chu(t) == ["同じ車に長く", "*乗る人の", "ほとんどが"]
    assert all(x["khoi_nen"] and x["mau_khoi"] == "#BE392B" and x["canh"] == "trai" for x in t)
    assert _chu(bia_lo.doc_chu_bia("一人で『コレ』を|する人は上位1%の|*天才^かも", KC))[-1] == "*天才^かも"
    ai = bia_lo.doc_chu_bia("同じ車に長く乗る人のほとんどが", KC, cach_ai=["同じ車に|[長く乗る]|人のほとんどが"])
    assert "".join(btk.chu_cua_tang(x) for x in ai) == "同じ車に長く乗る人のほとんどが"
    may = bia_lo.doc_chu_bia("同じ車に長く乗る人のほとんどが", KC, cach_ai=["同じ車に|[乗る]|人"])  # AI bỏ chữ → máy
    assert _chu(may) == ["同じ車に長く", "*乗る人の", "ほとんどが"]
    assert bia_lo.chu_tron("一人で|*天才^かも") == "一人で天才かも"


# ── 2) Vẽ hàng loạt ──────────────────────────────────────────────────────────


def _ve_gia(dang=None, tre: float = 0.0, x_dau: float = 0.70):
    """Mô hình ảnh giả: ghi nền tổng hợp; đếm lượt, khoá, số job đồng thời."""
    st = {"goi": [], "dang": 0, "dinh": 0}
    khoa = threading.Lock()

    def ve(loi_nhac, n, k, cac_dich):
        with khoa:
            st["goi"].append((k, n, loi_nhac))
            st["dang"] += 1
            st["dinh"] = max(st["dinh"], st["dang"])
        time.sleep(tre)
        for d in cac_dich[:n]:
            _nen(d, x_dau=x_dau)
        with khoa:
            st["dang"] -= 1
        return list(cac_dich[:n])
    ve.st = st
    return ve


def test_sinh_hang_loat_tran_song_song_khoa_va_dung_lai(tmp_path):
    ve = _ve_gia(tre=0.15)
    dem: dict = {}
    ds = bia_lo.sinh_hang_loat(ve, [_y(i) for i in range(1, 9)], 4, str(tmp_path / "uv"), kc=KC, tran=22,
                               khoa="bia-lo:KH:0001", log=lambda s: None, dem=dem)
    assert sum(n for _k, n, _p in ve.st["goi"]) == 22 == len(ds) == dem["anh"], "trần ảnh mỗi video"
    assert ve.st["dinh"] <= bia_lo.SONG_SONG_ANH and ve.st["dinh"] >= 2, "song song nhưng ≤ 4 job"
    khoa = [k for k, _n, _p in ve.st["goi"]]
    assert len(set(khoa)) == len(khoa) and all(k.startswith("bia-lo:KH:0001:y") for k in khoa)
    p = ve.st["goi"][0][2]
    assert "NO writing" in p and "clue object" in p and "right side" in p and "faded crowd" in p
    assert {d["ma"] for d in ds} >= {"y01-1", "y06-2"} and all(Image.open(d["nen"]).size == (1280, 720) for d in ds)
    ve2 = _ve_gia()
    ds2 = bia_lo.sinh_hang_loat(ve2, [_y(i) for i in range(1, 9)], 4, str(tmp_path / "uv"), kc=KC, tran=22,
                                khoa="bia-lo:KH:0001", log=lambda s: None)
    assert ve2.st["goi"] == [] and len(ds2) == 22, "nền đã có trên đĩa → không trả tiền lần hai"
    # nhà cung cấp trả THIẾU ảnh (2/4) + lời nhắc đổi sau đó → vẫn không đặt lại job đã giao
    thieu = _ve_gia()
    thieu_ve = lambda ln, n, k, dich: thieu(ln, n, k, dich[:2])  # noqa: E731
    bia_lo.sinh_hang_loat(thieu_ve, [_y(1)], 4, str(tmp_path / "uv2"), kc=KC, log=lambda s: None)
    lai = _ve_gia()
    ds3 = bia_lo.sinh_hang_loat(lai, [dict(_y(1), canh="the figure on the right in another bright room")], 4,
                                str(tmp_path / "uv2"), kc=KC, log=lambda s: None)
    assert lai.st["goi"] == [] and len(ds3) == 2, "job giao thiếu ảnh không bị đặt lại (trả tiền hai lần)"


# ── 3) Lọc cứng ──────────────────────────────────────────────────────────────


def test_tim_dau_nhan_vat_tron_trang_vien_den(tmp_path):
    im = Image.open(_nen(str(tmp_path / "a.png"), x_dau=0.70)).resize((1280, 720))
    ImageDraw.Draw(im).ellipse([560, 230, 660, 330], fill=(245, 248, 250), outline=(90, 90, 95), width=5)  # bóng gương
    d = bia_lo.tim_dau(im)
    assert len(d) == 2 and abs(d[0][0] - 0.70 * 1280) < 30 and abs(d[0][1] - 0.28 * 720) < 30, d
    assert abs(d[1][0] - 565) < 15, "đầu thứ hai (bóng trong gương = manh mối) cũng được giữ"
    assert bia_lo.tim_dau(Image.new("RGB", (1280, 720), (250, 248, 245))) == [], "nền kem trơn không phải đầu"


def test_loc_cung_bo_tam_hop_chu_de_dau(tmp_path):
    _can_font()
    tang = bia_lo.doc_chu_bia("同じ車に長く|*乗る人の|ほとんどが", KC)
    tot = {"ma": "y01-1", "nen": _nen(str(tmp_path / "y01-1-nen.png"), x_dau=0.72)}
    bia_lo._chuan_nen(tot["nen"])  # noqa: SLF001
    bia_lo.dung_bia(tot, tang)
    assert tot["loai"] == "" and tot["che_dau"] <= bia_lo.CHE_DAU_TOI_DA and os.path.isfile(tot["tep"]), tot
    assert do_bia.cham_tep(tot["tep"])["dat"] is True and tot["tep"].endswith(".jpg")
    xau = {"ma": "y02-1", "nen": _nen(str(tmp_path / "y02-1-nen.png"), x_dau=0.33)}
    bia_lo._chuan_nen(xau["nen"])  # noqa: SLF001
    bia_lo.dung_bia(xau, tang)
    assert "đè đầu" in xau["loai"] and xau["bo_cuc"] == list(bia_lo.CACH_BO_CUC[-1]), "đã thử co/dời hết cách"


def test_xep_hop_ep_co_va_doi_doc():
    def do_rong(chu, co):
        return len(chu) * co
    dong = [{"chu": "一人で"}, {"chu": "天才", "to": True}, {"chu": "かも"}]  # ngắn: không bị bề ngang chặn
    goc = btk.xep_hop_chu(dong, 1280, 720, do_rong)
    assert goc == btk.xep_hop_chu(dong, 1280, 720, do_rong, ep_co=1.0, doc=0.5), "mặc định giữ y bố cục cũ"
    nho = btk.xep_hop_chu(dong, 1280, 720, do_rong, ep_co=0.8)
    assert all(abs(b["co"] - 0.8 * a["co"]) < 2 for a, b in zip(goc, nho))
    tren = btk.xep_hop_chu(dong, 1280, 720, do_rong, doc=0.0)
    duoi = btk.xep_hop_chu(dong, 1280, 720, do_rong, doc=1.0)
    assert tren[0]["hop"][1] < goc[0]["hop"][1] < duoi[0]["hop"][1] and duoi[-1]["hop"][3] <= 720


# ── 4) Giám khảo ─────────────────────────────────────────────────────────────


def test_doc_cham_json_va_thu_hang():
    du = {"ung_vien": [
        {"so": 1, "noi_dung": 8, "to_mo": 9, "ro_120": 7, "cam_xuc": 6, "phong_cach": 8, "loi": "none", "ly_do": "x"},
        {"so": 2, "noi_dung": 99, "to_mo": -3, "ro_120": 5, "cam_xuc": 5, "phong_cach": 5, "loi": ["stray text"]},
        {"so": 3, "noi_dung": 5},                           # thiếu mục → bỏ
        {"so": 9, "noi_dung": 5, "to_mo": 5, "ro_120": 5, "cam_xuc": 5, "phong_cach": 5}]}  # ngoài nhóm
    kq = bia_lo.doc_cham_1(du, 3)
    assert set(kq) == {1, 2} and kq[1]["loi"] == [] and kq[2]["loi"] == ["stray text"]
    assert kq[1]["tong"] == 79.0 and kq[2]["diem"]["noi_dung"] == 10 and kq[2]["diem"]["to_mo"] == 1
    assert bia_lo.doc_cham_2({"xep_hang": [3, "1", 3, 7, "x", 2]}, 3) == [3, 1, 2]
    assert bia_lo.doc_cham_2("hỏng", 3) == []


def test_chu_la_chi_tinh_chu_that_khong_tinh_cau_ta():
    """Lô thật 14/10: AI đọc mù ghi câu TẢ vào `chu_thua` — không được loại oan; chữ thật (LOAN, $, chữ trong ngoặc
    kép của câu tả) thì loại."""
    assert bia_lo.chu_la({"dong": [], "chu_thua": ["Lock-icon-like marks on the car key fob"]}) == ""
    assert bia_lo.chu_la({"dong": [], "chu_thua": ["✦ (faint four-point sparkle watermark, bottom right)"]}) == ""
    assert bia_lo.chu_la({"dong": ["(no text)"], "chu_thua": ["the figure's key and the man's hand"]}) == ""
    assert bia_lo.chu_la({"dong": ["LOAN"], "chu_thua": []}) == "LOAN"
    assert bia_lo.chu_la({"dong": [], "chu_thua": ["$", "a price tag reading \"¥980\" on the box"]}) == "$ ¥980"
    assert bia_lo.chu_la({"dong": [], "chu_thua": ["…", "—"]}) == ""


def _goi_gia(diem=None, xep=None, chu_nen=None):
    """LLM giả theo loại lời nhắc: đạo diễn / chấm vòng 1 (điểm theo vị trí) / đọc mù nền / xếp hạng vòng 2."""
    lan = []

    def goi(loi_nhac, **kw):
        lan.append((loi_nhac[:40], kw.get("khoa", ""), len(kw.get("anh") or [])))
        if "CONCEPT DIRECTOR" in loi_nhac:
            return json.dumps({"chu": [], "y_tuong": [_y(i) for i in range(1, 9)]})
        if "strict art director" in loi_nhac:
            n = len(kw["anh"]) - 2
            return json.dumps({"ung_vien": [dict({"so": i + 1, "noi_dung": 6, "to_mo": 6, "ro_120": 6, "cam_xuc": 6,
                                                  "phong_cach": 6, "loi": [], "ly_do": "ok"},
                                                 **((diem or {}).get(i + 1) or {})) for i in range(n)]})
        if "Read the text printed" in loi_nhac:
            ma = kw.get("khoa", "").split("doc-nen:")[-1].split(":")[0]
            return json.dumps({"dong": [(chu_nen or {}).get(ma, "")] if (chu_nen or {}).get(ma) else [],
                               "chu_thua": [], "ky_tu_hong": False, "vet_xoa": False})
        if "sheet of" in loi_nhac:
            return json.dumps({"xep_hang": xep or [], "ly_do": {"2": "tò mò nhất"}})
        return "{}"
    goi.lan = lan
    return goi


def _ung_vien(tmp_path, n: int) -> list:
    ds = []
    for i in range(1, n + 1):
        p = str(tmp_path / "y{0:02d}-1.jpg".format(i))
        Image.new("RGB", (1280, 720), (200, 100 + 10 * i, 80)).save(p)
        ds.append({"ma": "y{0:02d}-1".format(i), "y": i, "bien": 1, "tep": p, "nen": p, "loai": ""})
    return ds


def test_cham_hai_vong_loai_chu_la_va_xep_hang(tmp_path):
    mau = [str(tmp_path / "m1.jpg"), str(tmp_path / "m2.jpg")]
    for m in mau:
        Image.new("RGB", (1280, 720), (240, 220, 200)).save(m)
    ds = _ung_vien(tmp_path, 7)
    ds[6]["loai"] = "hộp chữ đè đầu nhân vật (40%)"          # lọc cứng loại sẵn → giám khảo không thấy
    goi = _goi_gia(diem={1: {"to_mo": 9, "noi_dung": 9}, 2: {"to_mo": 8}, 3: {"loi": ["face covered"]},
                         4: {"to_mo": 7}, 5: {"to_mo": 7.5}},
                   chu_nen={"y02-1": "LOAN"}, xep=[3, 1, 2])
    dem: dict = {}
    xh = bia_lo.cham(goi, ds, mau=mau, tieu_de="t", chu_bia="c", thu_muc=str(tmp_path), log=lambda s: None, dem=dem)
    by = {u["ma"]: u for u in xh}
    assert "face covered" in by["y03-1"]["loai"] and "LOAN" in by["y02-1"]["loai"]
    assert by["y07-1"].get("tong") is None, "tấm lọc cứng đã loại không tốn lượt chấm"
    v1 = [x for x in goi.lan if x[0].startswith("You are the strict")]
    assert len(v1) == 1 and v1[0][2] == 2 + 6, "một nhóm 6 tấm + 2 bìa thắng"
    v2 = [x for x in goi.lan if x[0].startswith("The first")]
    assert len(v2) == 1 and v2[0][2] == 3, "vòng 2: 2 bìa thắng + MỘT tờ cạnh nhau"
    con = [u["ma"] for u in xh if not u.get("loai")]
    # sau loại: y01 (85), y05, y04, y06, y07 → vòng 2 đưa số 3 (y04) lên đầu, rồi 1 (y01), 2 (y05)
    assert con[:3] == ["y04-1", "y01-1", "y05-1"], con
    assert by["y05-1"]["ly_do_2"] == "tò mò nhất" and by["y04-1"]["hang_2"] == 1
    assert dem["llm"] == len(goi.lan) <= bia_lo.TRAN_GOI_CHAM + bia_lo.TRAN_DOC_CHU
    assert len([x for x in goi.lan if "doc-nen" in x[1]]) <= bia_lo.TRAN_DOC_CHU


def test_to_lien(tmp_path):
    ds = _ung_vien(tmp_path, 5)
    for i, u in enumerate(ds):
        u.update(tong=80 - i, diem={k: 7 for k in bia_lo.TRONG_SO}, hang_2=i + 1)
    d = bia_lo.to_lien(ds, str(tmp_path / "to-lien.jpg"))
    im = Image.open(d)
    assert im.format == "JPEG" and im.size == (3 * 640 + 4 * 12, 2 * (360 + 52 + 12) + 12)
    assert im.getpixel((12 + 30, 12 + 30)) != (200, 110, 80), "có ô số thứ tự ở góc"


# ── 5) Cả lô + xuất bộ bìa cho dây chuyền ───────────────────────────────────


def _goc_gia(tmp_path) -> str:
    goc = str(tmp_path / "goc")
    os.makedirs(duong_kenh(goc, "KH"), exist_ok=True)
    with io.open(os.path.join(duong_kenh(goc, "KH"), TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "KH"\n')
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
    os.makedirs(os.path.join(luot, "7-thumbnail"), exist_ok=True)
    with io.open(os.path.join(luot, "1-tieu-de.txt"), "w", encoding="utf-8") as tep:
        tep.write("TITLE: 同じ車に長く乗る人の特徴\nTHUMB: 同じ車に長く乗る人のほとんどが\n")
    with io.open(os.path.join(luot, "1-kich-ban.txt"), "w", encoding="utf-8") as tep:
        tep.write("あなたの車、今年で何年目になりますか。")
    with io.open(os.path.join(luot, "3-muc-luc.json"), "w", encoding="utf-8") as tep:
        json.dump({"x": {"nhan": ["愛着", "比べない"]}}, tep, ensure_ascii=False)
    for i in (1, 2):
        Image.new("RGB", (1280, 720), (240, 220, 200)).save(os.path.join(goc, "thang{0}.jpg".format(i)))
    return goc


def test_chay_ca_lo_dung_lai_va_xuat_goi(tmp_path):
    _can_font()
    goc = _goc_gia(tmp_path)
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
    ra = str(tmp_path / "ra")
    mau = [os.path.join(goc, "thang1.jpg"), os.path.join(goc, "thang2.jpg")]
    ve, goi = _ve_gia(), _goi_gia(xep=[2, 1, 3])
    kq = bia_lo.chay(goc, "KH", thu_muc_luot=luot, ra=ra, so_y=3, moi_y=2, goi=goi, ve=ve, mau=mau,
                     log=lambda s: None)
    assert kq["chi_phi"]["anh_dat_moi"] == 6 == kq["chi_phi"]["anh_tong"] and kq["chi_phi"]["llm"] == len(goi.lan)
    assert len(kq["top"]) == 3 and kq["top"][0]["hang_2"] == 1 and kq["chu_ve"] == "同じ車に長く乗る人のほとんどが"
    for t in ("xep-hang.json", "to-lien.jpg", "top-1.jpg", "top-3.jpg", "y-tuong.json"):
        assert os.path.isfile(os.path.join(ra, t)), t
    assert len([t for t in os.listdir(os.path.join(ra, "ung-vien")) if t.endswith(".jpg")]) == 6
    assert "CONCEPT DIRECTOR" in goi.lan[0][0] or goi.lan[0][1].endswith(":dao-dien")
    # chạy lại: không vẽ, không gọi LLM
    ve2, goi2 = _ve_gia(), _goi_gia()
    kq2 = bia_lo.chay(goc, "KH", thu_muc_luot=luot, ra=ra, so_y=3, moi_y=2, goi=goi2, ve=ve2, mau=mau,
                      log=lambda s: None)
    assert ve2.st["goi"] == [] and goi2.lan == [] and [t["ma"] for t in kq2["top"]] == [t["ma"] for t in kq["top"]]
    # xuất cho dây chuyền
    from core import chon_bia, ho_so_video
    tm = os.path.join(luot, "7-thumbnail")
    chon = bia_lo.xuat_goi(kq, tm)
    assert chon["chon_boi"] == "ai" and chon["tep"] == "CHON-thumb_001.jpg" and chon["bia_lo"]
    du = chon_bia.doc_chon_bia(tm)
    diem = [u["tong_diem"] for u in du["ung_vien"]]
    assert diem == sorted(diem, reverse=True) and len(set(diem)) == 3, "điểm giảm đúng theo hạng chung cuộc"
    assert do_bia.cham_tep(os.path.join(tm, "CHON-thumb_001.jpg"))["dat"] is True
    kh = btk.doc_ke_hoach(tm)
    assert kh["muc"][0]["chu_du_kien"] == "同じ車に長く乗る人のほとんどが" and kh["muc"][0]["chu_tang"]
    assert all(os.path.isfile(os.path.join(tm, "znen-thumb_00{0}.png".format(i))) for i in (1, 2, 3))
    b2 = ho_so_video._sao_luu_bia_2(goc, "KH", "KH-0001", os.path.join(tm, "CHON-thumb_001.jpg"))  # noqa: SLF001
    assert b2["tep"] == "thumb_002.jpg" and b2["bia_3"]["tep"] == "thumb_003.jpg"
    assert os.path.isfile(ho_so_video.duong_bia_2_ho_so(goc, "KH", "KH-0001")[:-5] + "3.jpg")


# ── 6) Kiểu chữ CỦA kênh: hộp (TL4) / chữ trần (TL2/TL3) — 14/10/2026 ───────


def _tang_tran(*phan) -> dict:
    return {"vi_tri": "duoi", "mau": [m for _c, m in phan], "phan_mau": [{"chu": c, "mau": m} for c, m in phan],
            "vien": "thick black outline", "khoi_nen": False}


#: Khuôn chữ TRẦN giả (chữ giả): dải trên trắng, dải dưới đỏ + trắng + vàng, nhân vật giữa, nền tím.
KC_TRAN = {"nhan_vat": {"vi_tri": "giua"}, "nen_mau_chu_dao": "dark purple #10041C", "nen_do_sang": "toi",
           "nen_hieu_ung": ["purple glow halo", "digital UI overlay", "particle noise"], "diem_hut_mat": "glow",
           "chu": {"tang": [dict(_tang_tran(("あいうえ", "#FFFFFF")), vi_tri="tren"),
                            _tang_tran(("かき", "#FF0000"), ("く", "#FFFFFF"), ("けこ", "#FFFF00"))]}}


def test_kieu_chu_hop_tran_bo_cuc_mau():
    assert bia_lo.kieu_chu(KC) == "hop" and bia_lo.kieu_chu({}) == "hop" and bia_lo.kieu_chu(KC_TRAN) == "tran"
    assert bia_lo.kieu_chu({"chu": {"tang": [dict(t, khoi_nen=True) for t in KC_TRAN["chu"]["tang"]]}}) == "hop", \
        "tầng có khối nền (chưa đo màu hộp) vẫn là kiểu hộp"
    assert bia_lo.bo_cuc_tran(KC_TRAN) == "dai"
    assert bia_lo.bo_cuc_tran(dict(KC_TRAN, nhan_vat={"vi_tri": "phai"})) == "trai"
    assert bia_lo.bo_cuc_tran(dict(KC_TRAN, nhan_vat={"vi_tri": "trai"})) == "phai"
    assert bia_lo.bo_cuc_tran({"chu": KC_TRAN["chu"], "vi_tri_chu": "Left side stacked"}) == "trai"
    assert bia_lo.mau_tran(KC_TRAN) == ("#FFFFFF", "#FF0000", "#FFFF00")
    assert bia_lo.mau_tran({}) == ("#FFFFFF", bia_lo.MAU_DO_MAC_DINH, bia_lo.MAU_VANG_MAC_DINH)
    nen = bia_lo.nen_tu_khuon(KC_TRAN)
    assert "dark purple #10041C" in nen and "glow" in nen and "UI" not in nen, "hiệu ứng dễ thành chữ lạc bị bỏ"
    assert bia_lo._uu_tien_vien(KC_TRAN) == bia_lo.UU_TIEN_VIEN_DEN  # noqa: SLF001


def _hs_tran(bo: str = "dai") -> dict:
    nen, do, vang = bia_lo.mau_tran(KC_TRAN)
    return {"kieu": "tran", "kc": KC_TRAN, "bo_cuc": bo, "mau_nen": nen, "mau_do": do, "mau_vang": vang,
            "uu_tien": bia_lo.UU_TIEN_VIEN_DEN, "mau_dau": None, "nhan_vat": "a round-headed figure",
            "nen": "dark purple background", "mau": "- 「MAU-KENH-GIA」: a fake winner description", "bia_mau": []}


def test_doc_chu_bia_tran_mau_thu_bac_va_lui_may():
    hs = _hs_tran("dai")
    t = bia_lo.doc_chu_bia_tran("朝の習慣を変える人", hs, cach_ai=["朝の習慣を|[<変える>{人}]"])
    assert [btk.chu_cua_tang(x) for x in t] == ["朝の習慣を", "変える人"]
    assert [x["vi_tri"] for x in t] == ["tren", "duoi"] and all(x["can"] == "giua" and x["mot_dong"] for x in t)
    assert t[1]["to"] and t[1]["chinh"] and "co_toi_da_pct" not in t[1], "dòng cực to: tầng chính, trần 30% của bộ vẽ"
    assert not t[0].get("to") and t[0]["co_toi_da_pct"] == bia_lo.TRAN_CO_VUA_PCT
    assert t[1]["phan_mau"] == [{"chu": "変える", "mau": "#FF0000"}, {"chu": "人", "mau": "#FFFF00"}]
    assert t[0]["phan_mau"] == [{"chu": "朝の習慣を", "mau": "#FFFFFF"}]
    # cột trái: dòng cuối xếp từ dưới, canh trái
    c = bia_lo.doc_chu_bia_tran("朝の習慣を変える人", _hs_tran("trai"), cach_ai=["朝の|習慣を|[<変える>人]"])
    assert [x["vi_tri"] for x in c] == ["tren", "tren", "duoi"] and {x["can"] for x in c} == {"trai"}
    # AI bỏ chữ → chia máy, giữ TRỌN chữ bìa; không dấu màu → tô máy dòng cực to (đỏ/vàng)
    may = bia_lo.doc_chu_bia_tran("朝の習慣を変える人", hs, cach_ai=["朝の|[<習慣>]"])
    assert "".join(btk.chu_cua_tang(x) for x in may) == "朝の習慣を変える人"
    to = [x for x in may if x.get("to")]
    assert len(to) == 1 and {p["mau"] for p in to[0]["phan_mau"]} <= {"#FF0000", "#FFFF00"}
    # dấu tay kiểu hộp ("*" = dòng cực to) cũng nhận
    tay = bia_lo.doc_chu_bia_tran("朝の習慣を|*変える人", hs)
    assert [bool(x.get("to")) for x in tay] == [False, True]


def _nen_tran(duong: str, x_dau: float = 0.72, tim: bool = False) -> str:
    """Nền chữ trần: kem sáng (hoặc tím tối) + nhân vật đầu tròn trắng viền đen bên phải + manh mối."""
    W, H = 1376, 768
    im = Image.new("RGB", (W, H), (20, 6, 34) if tim else (246, 236, 214))
    d = ImageDraw.Draw(im)
    d.ellipse([0.80 * W, 0.62 * H, 0.95 * W, 0.86 * H], fill=(230, 180, 40), outline=(60, 40, 10), width=6)
    d.rounded_rectangle([(x_dau + 0.02) * W, 0.53 * H, (x_dau + 0.11) * W, 0.95 * H], radius=30, fill=(40, 50, 80),
                        outline=(12, 12, 12), width=8)
    d.ellipse([x_dau * W, 0.26 * H, (x_dau + 0.13) * W, 0.50 * H], fill=(250, 250, 250), outline=(12, 12, 12), width=8)
    for dx in (0.04, 0.08):
        d.ellipse([(x_dau + dx) * W, 0.35 * H, (x_dau + dx + 0.01) * W, 0.37 * H], fill=(10, 10, 10))
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    im.save(duong)
    return duong


def test_dung_bia_tran_ve_chu_tran_hop_giu_nguyen(tmp_path, monkeypatch):
    """Khuôn chữ TRẦN → bộ vẽ chữ trần của khuôn (không khung, viền đen trước, cột chữ né đầu); khuôn HỘP → bộ vẽ hộp
    như cũ."""
    _can_font()
    goi_ve, goi_hop = [], []
    that_ve, that_hop = btk.ve_chu_len_anh, btk._ve_bia_hop  # noqa: SLF001

    def spy_ve(*a, **k):
        goi_ve.append(k)
        return that_ve(*a, **k)

    def spy_hop(*a, **k):
        goi_hop.append(k)
        return that_hop(*a, **k)
    monkeypatch.setattr(btk, "ve_chu_len_anh", spy_ve)
    monkeypatch.setattr(btk, "_ve_bia_hop", spy_hop)
    hs = _hs_tran("trai")
    tang = bia_lo.doc_chu_bia_tran("朝の習慣を変える人", hs, cach_ai=["朝の|習慣を|[<変える>{人}]"])
    uv = {"ma": "y01-1", "nen": _nen_tran(str(tmp_path / "y01-1-nen.png"))}
    bia_lo._chuan_nen(uv["nen"])  # noqa: SLF001
    bia_lo.dung_bia(uv, tang, ho_so=hs)
    assert uv["loai"] == "" and uv["kieu_chu"] == "tran" and os.path.isfile(uv["tep"]), uv
    assert goi_hop == [], "chữ trần không đi bộ vẽ hộp"
    k = goi_ve[0]
    assert k["cho_khung"] is False and tuple(k["uu_tien_kieu"]) == bia_lo.UU_TIEN_VIEN_DEN and not k.get("kieu_phong")
    assert k["khung_chu"] == (0.0, 0.0, 0.60, 1.0) and uv["che_dau"] <= bia_lo.CHE_DAU_TOI_DA and uv["dau"]
    bc = do_bia.doc_bao_cao(uv["tep"])
    assert bc and not bc.get("hop_chu") and all(not (d.get("khung") or {}) for d in bc["dong"])
    assert all(d["hop"][2] <= 0.62 * 1280 for d in bc["dong"]), "chữ nằm trong cột trái, không lấn sang nhân vật"
    im = Image.open(uv["tep"]).convert("RGB")
    do = sum(1 for x in range(0, 760, 4) for y in range(0, 720, 4)
             if (lambda p: p[0] > 200 and p[1] < 70 and p[2] < 70)(im.getpixel((x, y))))
    assert do > 50, "từ khoá tô ĐỎ của khuôn"
    # khuôn HỘP: bộ vẽ hộp y như cũ
    goi_ve.clear()
    tang_hop = bia_lo.doc_chu_bia("同じ車に長く|*乗る人の|ほとんどが", KC)
    uv2 = {"ma": "y02-1", "nen": _nen(str(tmp_path / "y02-1-nen.png"), x_dau=0.72)}
    bia_lo._chuan_nen(uv2["nen"])  # noqa: SLF001
    bia_lo.dung_bia(uv2, tang_hop, ho_so={"kieu": "hop", "kc": KC, "mau_dau": None})
    assert len(goi_hop) >= 1 and uv2["loai"] == "" and do_bia.doc_bao_cao(uv2["tep"]).get("hop_chu")


def test_tim_dau_mau_va_noi(tmp_path):
    """Đầu CAM viền đen (TL3) bắt bằng màu đo trên nv1.png; đầu trắng ám ấm viền mảnh (TL2) bắt ở chế độ nới."""
    im = Image.new("RGB", (1280, 720), (24, 8, 40))
    d = ImageDraw.Draw(im)
    d.ellipse([540, 200, 760, 420], fill=(248, 144, 22), outline=(10, 10, 10), width=12)
    d.ellipse([600, 280, 620, 300], fill=(10, 10, 10))
    d.line([600, 360, 700, 360], fill=(10, 10, 10), width=8)
    assert bia_lo.tim_dau(im) == []
    cam = bia_lo.tim_dau(im, (250, 143, 18))
    assert len(cam) == 1 and abs(cam[0][0] - 540) < 20 and abs(cam[0][3] - 420) < 20, cam
    am = Image.new("RGB", (1280, 720), (190, 120, 60))
    d = ImageDraw.Draw(am)
    d.ellipse([900, 150, 1060, 310], fill=(246, 234, 206), outline=(70, 60, 50), width=3)
    d.ellipse([950, 210, 965, 225], fill=(20, 20, 20))
    assert bia_lo.tim_dau(am) == [] and len(bia_lo.tim_dau(am, noi=True)) == 1
    # màu đầu đo trên ảnh nhân vật (nền trắng)
    for mau, mong in (((248, 144, 22), True), ((250, 250, 250), False)):
        nv = Image.new("RGB", (700, 400), (255, 255, 255))
        d = ImageDraw.Draw(nv)
        d.ellipse([280, 40, 420, 180], fill=mau, outline=(10, 10, 10), width=8)
        d.rectangle([340, 180, 360, 380], fill=(10, 10, 10))
        p = str(tmp_path / "nv.png")
        nv.save(p)
        ra = bia_lo.mau_dau_nv(p)
        assert (ra is not None and ra[0] > 200 and 100 < ra[1] < 190 and ra[2] < 80) if mong else ra is None, ra


def _goc_tran(tmp_path, kc=None) -> str:
    """Gốc giả: kênh KH có khuôn chữ trần + bìa khuôn + style.yaml + nv1.png + một lượt."""
    goc = _goc_gia(tmp_path)
    kenh = duong_kenh(goc, "KH")
    os.makedirs(os.path.join(kenh, "nghien-cuu"), exist_ok=True)
    os.makedirs(os.path.join(kenh, "nv"), exist_ok=True)
    tep = os.path.join(kenh, "bia-khuon.jpg")
    Image.new("RGB", (1280, 720), (30, 10, 50)).save(tep)
    nv = Image.new("RGB", (700, 400), (255, 255, 255))
    ImageDraw.Draw(nv).ellipse([280, 40, 420, 180], fill=(250, 250, 250), outline=(10, 10, 10), width=8)
    nv.save(os.path.join(kenh, "nv", "nv1.png"))
    with io.open(os.path.join(kenh, "style.yaml"), "w", encoding="utf-8") as f:
        f.write('default_character_lock: "round off-white head, two dot eyes, short straight neutral mouth, navy '
                'sweater, warm cream ground, hands relaxed at sides"\n')
    with io.open(os.path.join(kenh, "nghien-cuu", "khuon-bia-thang.json"), "w", encoding="utf-8") as f:
        json.dump({"video_id": "VIDGIA0001", "sha1_that": "s1", "ctr": 9.0, "imp": 20000, "tep": tep, "nguon": "kenh",
                   "anh_that": True, "khuon_chu": kc or KC_TRAN}, f, ensure_ascii=False)
    return goc


def _anh(duong: str, mau=(240, 220, 200)) -> str:
    Image.new("RGB", (1280, 720), mau).save(duong)
    return duong


def test_mau_thang_rieng_kenh_lap_cache_va_lam_moi(tmp_path, monkeypatch):
    goc = _goc_tran(tmp_path)
    kenh = duong_kenh(goc, "KH")
    tep_k = os.path.join(kenh, "bia-khuon.jpg")
    bia = [{"video_id": "VIDGIA0001", "ctr": 9.0, "imp": 20000, "tep": tep_k, "khuon": True},
           {"video_id": "VIDGIA0002", "ctr": 6.0, "imp": 90000, "tep": _anh(os.path.join(kenh, "b2.jpg"))},
           {"video_id": "VIDGIA0003", "ctr": 5.0, "imp": 50000, "tep": _anh(os.path.join(kenh, "b3.jpg"), (35, 12, 55))}]
    monkeypatch.setattr(bia_lo, "bia_thang", lambda goc_, kenh_, kh=None, **k: list(bia))
    lan = []

    def goi(loi_nhac, **kw):
        lan.append((loi_nhac, kw))
        return json.dumps({"bia": [{"so": 1, "kieu_chu": "bare", "chu": "あいうえ|かきくけこ", "ta": "TA-MOT"},
                                   {"so": 2, "kieu_chu": "box", "chu": "さしす", "ta": "TA-HAI"},
                                   {"so": 3, "kieu_chu": "bare", "chu": "たちつ", "ta": "TA-BA"}],
                           "hinh": "HINH-KENH", "nen": "NEN-KENH."})
    hs = bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)
    assert len(lan) == 1 and len(lan[0][1]["anh"]) == 3 and "best-performing" in lan[0][0]
    cache = bia_lo._doc_json(bia_lo.duong_mau_thang(goc, "KH"))  # noqa: SLF001
    assert cache["khoa"] and [b["kieu_chu"] for b in cache["bia"]] == ["tran", "hop", "tran"]
    assert hs["nguon_mau"] == "kenh" and "TA-MOT" in hs["mau"] and "TA-HAI" in hs["mau"] and "お金持ちほど" not in hs["mau"]
    assert hs["hinh_them"] == "HINH-KENH" and "NEN-KENH" in hs["nen"] and "dark purple" in hs["nen"]
    assert hs["bia_mau"] == [tep_k, bia[2]["tep"]], "bìa khuôn + bìa CÙNG kiểu chữ trần (bỏ bìa hộp)"
    assert hs["nhan_vat"] and not re.search(r"ground|neutral|relaxed", hs["nhan_vat"])
    assert hs["bang_chung"] == " (20k-90k impressions)"
    assert bia_lo.mau_cua_kenh(goc, "KH", ho_so=hs) == hs["bia_mau"]
    # khuôn không đổi → không gọi lại
    bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)
    assert len(lan) == 1
    # bìa khuôn đổi (sha1 bìa thật) → tả lại; không có hàm gọi thì dùng bản cũ
    tep_khuon = os.path.join(kenh, "nghien-cuu", "khuon-bia-thang.json")
    kh = bia_lo._doc_json(tep_khuon)  # noqa: SLF001
    kh["sha1_that"] = "s2"
    bia_lo._ghi_json(tep_khuon, kh)  # noqa: SLF001
    assert bia_lo.ho_so_kieu(goc, "KH", log=lambda s: None)["nguon_mau"] == "kenh-cu"
    bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)
    assert len(lan) == 2 and bia_lo._doc_json(bia_lo.duong_mau_thang(goc, "KH"))["khoa"] != cache["khoa"]  # noqa: SLF001
    # kênh kiểu HỘP chưa có cache, không hàm gọi → mẫu TL4 viết tay như cũ
    goc2 = _goc_tran(tmp_path / "hop", kc=KC)
    hs2 = bia_lo.ho_so_kieu(goc2, "KH", log=lambda s: None)
    assert hs2["kieu"] == "hop" and hs2["mau"] == bia_lo.MAU_THANG and "bia_mau" not in hs2


def test_chay_tran_dao_dien_va_giam_khao_dung_mau_cua_kenh(tmp_path, monkeypatch):
    """Cả lô kênh chữ trần: đạo diễn đọc mẫu tả CỦA kênh, ảnh nền theo lời nhắc chữ trần, giám khảo so với bìa thắng
    CỦA kênh (bìa khuôn đầu tiên), lời chấm không nói "red boxes"; xuất gói ghi kiểu khuôn "tran"."""
    _can_font()
    goc = _goc_tran(tmp_path, kc=dict(KC_TRAN, nhan_vat={"vi_tri": "phai"}))
    kenh = duong_kenh(goc, "KH")
    tep_k = os.path.join(kenh, "bia-khuon.jpg")
    b2 = _anh(os.path.join(kenh, "b2.jpg"), (36, 14, 52))
    kh = bia_lo._doc_json(os.path.join(kenh, "nghien-cuu", "khuon-bia-thang.json"))  # noqa: SLF001
    bia_lo._ghi_json(bia_lo.duong_mau_thang(goc, "KH"), {  # noqa: SLF001 — cache còn mới
        "khoa": bia_lo._khoa_mau(kh), "mau": "- 「MAU-KENH-GIA」: fake channel winner", "hinh": "", "nen": "",  # noqa: SLF001
        "bia": [{"video_id": "VIDGIA0001", "tep": tep_k, "imp": 20000, "kieu_chu": "tran", "chu": "x", "ta": "y"},
                {"video_id": "VIDGIA0002", "tep": b2, "imp": 50000, "kieu_chu": "tran", "chu": "x", "ta": "y"}]})
    luot = os.path.join(goc, "PROJECTS", "AUTO", "KH", "0001")
    cap = []
    goc_goi = _goi_gia(xep=[2, 1, 3])

    def goi(loi_nhac, **kw):
        cap.append((loi_nhac, kw.get("anh")))
        return goc_goi(loi_nhac, **kw)
    lan_ve = []

    def ve(loi_nhac, n, k, cac_dich):
        lan_ve.append(loi_nhac)
        for d in cac_dich[:n]:
            _nen_tran(d)
        return list(cac_dich[:n])
    kq = bia_lo.chay(goc, "KH", thu_muc_luot=luot, ra=str(tmp_path / "ra"), so_y=3, moi_y=2, goi=goi, ve=ve,
                     log=lambda s: None)
    assert kq["kieu_chu"] == "tran" and kq["bo_cuc"] == "trai" and kq["nguon_mau"] == "kenh"
    dd = next(p for p, _a in cap if "CONCEPT DIRECTOR" in p)
    assert "MAU-KENH-GIA" in dd and "お金持ちほど" not in dd and "deep-red text boxes" not in dd
    assert "BARE lettering" in dd and "< >" in dd and "(20k-50k impressions)" in dd
    assert all("big outlined lettering" in p and "red text boxes" not in p for p in lan_ve)
    cham = [(p, a) for p, a in cap if p.startswith("You are the strict")]
    assert cham and all("red boxes" not in p and "huge outlined lettering" in p for p, _a in cham)
    mau_url = [bia_lo._url_anh(t) for t in (tep_k, b2)]  # noqa: SLF001
    assert all(a[:2] == mau_url for _p, a in cham), "giám khảo so với bìa thắng CỦA kênh (bìa khuôn trước)"
    assert kq["mau"] == [tep_k, b2] and kq["top"]
    tm = os.path.join(luot, "7-thumbnail")
    bia_lo.xuat_goi(kq, tm)
    k2 = btk.doc_ke_hoach(tm)
    assert k2["kieu_khuon"] == "tran" and k2["muc"][0]["chu_tang"][0]["mot_dong"]


def test_bia_lo_tat_giu_duong_cu(tmp_path, monkeypatch):
    from core import auto_khau as ak
    goc = _goc_gia(tmp_path)
    da = []
    monkeypatch.setattr(ak, "_sinh_lo_bia", lambda bc, luot, tt: da.append("cu") or ("d", "t", "c", {}, 3))
    monkeypatch.setattr(ak, "_bia_lo_luot", lambda bc, luot: da.append("lo") or ("d", "t", "c", {}, 3))
    monkeypatch.setattr(ak, "_cong_doc_duoc_bia", lambda *a: {})
    monkeypatch.setattr(ak, "_cong_chu_bia", lambda *a: {"dat": True})
    bc = SimpleNamespace(goc=goc, kenh=SimpleNamespace(ma="KH"))
    tep = os.path.join(duong_kenh(goc, "KH"), TEP_KENH)
    for them, mong in (("", ["cu"]), ("bia_lo: false\n", ["cu"]), ("bia_lo: true\n", ["lo"])):
        with io.open(tep, "w", encoding="utf-8") as f:
            f.write('ma: "KH"\n' + them)
        da.clear()
        assert ak._mot_lo_bia(bc, None, None)["chu_bia_giao"] == {"dat": True}  # noqa: SLF001
        assert da == mong, (them, da)
    monkeypatch.setattr(ak, "_bia_lo_luot", lambda bc, luot: da.append("lo") or None)  # không có bìa mẫu
    da.clear()
    ak._mot_lo_bia(bc, None, None)  # noqa: SLF001
    assert da == ["lo", "cu"], "bật bia_lo mà chưa có bìa thắng làm mẫu → đường cũ"


# ── 7) Thư mục bìa thắng chủ chọn + ghi đè kiểu/bố cục (16/10/2026) ─────────


def test_thu_muc_mau_kenh_yaml_thu_hang_cache_va_ghi_de(tmp_path):
    """`kenh.yaml: bia_lo_mau` (thư mục bìa thắng thật, `thang.json` xếp hạng) → mẫu tả few-shot, ảnh tham chiếu + mẫu
    so của giám khảo lấy từ ĐÚNG thư mục ấy (cache trong thư mục, không đụng `nghien-cuu/`); `bia_lo_bo_cuc` /
    `bia_lo_kieu` ghi đè bố cục / kiểu chữ đo từ khuôn."""
    goc = _goc_tran(tmp_path, kc=dict(KC_TRAN, nhan_vat={"vi_tri": "trai"}))   # khuôn: nhân vật trái → cột phải
    tm = os.path.join(goc, "workspace", "bia-kh", "thang")
    os.makedirs(tm, exist_ok=True)
    for i, mau in enumerate([(200, 150, 90), (180, 120, 60), (240, 230, 210)], 1):
        _anh(os.path.join(tm, "{0}.jpg".format(i)), mau)
    with io.open(os.path.join(tm, bia_lo.TEP_DS_THANG), "w", encoding="utf-8") as f:
        json.dump({"bia": [{"tep": "2.jpg", "video_id": "VIDGIA0002", "imp": 35000, "ctr": 5.3},
                           {"tep": "1.jpg", "video_id": "VIDGIA0001", "imp": 14000, "ctr": 6.8},
                           {"tep": "3.jpg", "imp": 7000, "ctr": 6.2}]}, f)
    yaml = os.path.join(duong_kenh(goc, "KH"), TEP_KENH)
    with io.open(yaml, "a", encoding="utf-8") as f:
        f.write('bia_lo_mau: "workspace/bia-kh/thang"\nbia_lo_bo_cuc: "dai"\n')
    lan = []

    def goi(loi_nhac, **kw):
        lan.append(kw)
        return json.dumps({"bia": [{"so": 1, "kieu_chu": "box", "chu": "a", "ta": "TA-MOT"},
                                   {"so": 2, "kieu_chu": "bare", "chu": "b", "ta": "TA-HAI"},
                                   {"so": 3, "kieu_chu": "bare", "chu": "c", "ta": "TA-BA"}],
                           "hinh": "H", "nen": "warm room"})
    hs = bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)
    tm = os.path.abspath(tm)
    assert hs["kieu"] == "tran" and hs["bo_cuc"] == "dai" and hs["thu_muc_mau"] == tm
    assert hs["bia_mau"] == [os.path.join(tm, t) for t in ("2.jpg", "1.jpg")], "theo thứ hạng của thang.json"
    assert len(lan) == 1 and len(lan[0]["anh"]) == 3 and "TA-MOT" in hs["mau"] and "warm room" in hs["nen"]
    assert os.path.isfile(os.path.join(tm, bia_lo.TEP_MAU_THANG)), "cache nằm trong thư mục mẫu"
    assert not os.path.isfile(bia_lo.duong_mau_thang(goc, "KH")), "không ghi cache vào nghien-cuu/ của kênh"
    assert hs["bang_chung"] == " (7k-35k impressions)"
    assert bia_lo.mau_cua_kenh(goc, "KH", ho_so=hs) == hs["bia_mau"]
    assert bia_lo.mau_cua_kenh(goc, "KH", [tm]) == hs["bia_mau"], "--mau DIR cũng đi đường thư mục"
    assert bia_lo.thu_muc_mau(str(tmp_path / "goc-khac"), "KX", [os.path.join(tm, "1.jpg")]) == tm, \
        "chay() nhận danh sách TỆP của thư mục mẫu (có thang.json) → vẫn là thư mục ấy (không rơi về cache kênh)"
    bia_lo.ho_so_kieu(goc, "KH", goi=goi, log=lambda s: None)
    assert len(lan) == 1, "thư mục không đổi → không tả lại"
    with io.open(yaml, "a", encoding="utf-8") as f:
        f.write('bia_lo_kieu: "hop"\n')
    assert bia_lo.ho_so_kieu(goc, "KH", log=lambda s: None)["kieu"] == "hop"


def test_bo_cuc_tran_hai_dai_ngang_tren_duoi():
    kc = dict(KC_TRAN, nhan_vat={"vi_tri": "trai"},
              vi_tri_chu="Two horizontal text tiers: top header read first, bottom conclusion read second.")
    assert bia_lo.bo_cuc_tran(kc) == "dai", "chữ hai dải ngang dù nhân vật lệch trái"
    assert bia_lo.bo_cuc_tran(dict(kc, vi_tri_chu="Left side stacked vertically")) == "phai"
    assert bia_lo.bo_cuc_tran(dict(kc, vi_tri_chu="")) == "phai"
