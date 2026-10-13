"""Tầng đối thủ của sổ chung (`core/so_doi_thu_chung.py`, 13/10/2026) + lượt quét theo tầng.

Canh: luật tầng (lõi đủ cỡ + còn sống, trần xếp điểm; đang lên theo tín hiệu radar / video gần / kênh trẻ / vượt quy mô
có sàn view; nhẹ; ngoài = bỏ/hết/chết/sai tiếng ở mọi kênh ta) · bạn đưa không dưới tầng 2, không ra ngoài trừ chết /
hết / sai tiếng · xếp tầng không đụng ghi chú / phán quyết riêng · video nổ radar kéo kênh lên tầng 2 và dính
`NGAY_DOT_BIEN_TANG` ngày qua các lần gộp · khoá `/channel/UC…` giữ hoa thường (nối được phán quyết kho `kenh-ai.json`
ghi khoá thường) · CSV có cột Tầng, thống kê đếm tầng · `loc_quet`: hạn theo tầng tính từ mốc quét từng kênh, tầng 1
trước, link trùng kênh bỏ, kênh mới quét ngay, ảnh chụp nhóm còn tươi / trang chủ vừa đẩy video mới → quét sớm, chưa có
mốc → quét đủ, `MYTOOL_QUET_THEO_TANG=0` tắt · `den_han_do_lai`: kênh ngoài đo lại hằng tháng. Toàn bộ mã kênh, link,
tên kênh là GIẢ.
"""

import copy
import csv
import datetime as _dt
import io
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import so_doi_thu_chung as sdc  # noqa: E402

NHOM = "ngach-gia-tang"
HOM = _dt.date(2026, 10, 13)


def _uc(ten):
    """Mã kênh GIẢ đúng dạng UC… (24 ký tự)."""
    return ("UCfake" + ten + "x" * 30)[:24]


def _kenh(goc, ma, nhom=NHOM):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(d, "nghien-cuu"), exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ma: {0}\nngon_ngu: ja\n".format(ma) + ("nhom: {0}\n".format(nhom) if nhom else ""))


def _so(goc, ma, dong):
    cot = list(db.COT)
    db.luu(goc, ma, cot, [[str(d.get(c, "")) for c in cot] for d in dong])


def _ngay(cach, moc=HOM):
    return (moc - _dt.timedelta(days=cach)).isoformat()


def _e(k, tt=(db.THEO_DOI, db.THEO_DOI), *, subs="", tv="", vuot="", song=None, ban_dua=False, lq=None, ten=None):
    """Một dòng sổ chung giả (hai kênh ta A, B)."""
    return {"khoa": k, "uc": k, "ten": ten or ("Ten-" + k[-6:]), "so": {"Subs": subs, "View TV": tv, "Vượt quy mô": vuot},
            "song": {"ket": song} if song else None, "ban_dua": ban_dua, "lien_quan": lq or {},
            "theo_kenh": {"A": {"tt": tt[0], "ghi": "ghi tay của A ‖ giữ nguyên"}, "B": {"tt": tt[1], "ghi": ""}},
            "trang_thai": tt[0]}


def _anh(cach_moi, **kw):
    """Tóm ảnh chụp giả: video mới nhất cách HOM `cach_moi` ngày, chụp hôm HOM."""
    t = {"luc": time.mktime(_dt.datetime(HOM.year, HOM.month, HOM.day, 12).timetuple()), "moi": _ngay(cach_moi),
         "cu": _ngay(400), "du": False, "n": 40, "tv": 500.0, "vt": 1000, "bung": 0.0, "bung_view": 0, "subs": -1}
    t.update(kw)
    return t


def test_phan_tang_luat_co_ban():
    K = {x: _uc(x) for x in ("Lon", "Radar", "Nho", "Im", "Bo", "Het", "Chet", "Lech", "BdNho", "BdBo", "BdHet",
                             "Tre", "Bung", "VuotNho")}
    kenh = {
        K["Lon"]: _e(K["Lon"], subs="50000", tv="8000"),
        K["Radar"]: _e(K["Radar"], subs="800", tv="300"),
        K["Nho"]: _e(K["Nho"], subs="900", tv="400"),
        K["Im"]: _e(K["Im"], subs="90000", tv="20000"),
        K["Bo"]: _e(K["Bo"], (db.BO, db.BO), subs="99000", tv="9000"),
        K["Het"]: _e(K["Het"], (db.HET, db.THEO_DOI), subs="20000", song="het"),
        K["Chet"]: _e(K["Chet"], song="chet"),
        K["Lech"]: _e(K["Lech"], song="lech_tieng", subs="70000"),
        K["BdNho"]: _e(K["BdNho"], subs="100", tv="50", ban_dua=True),
        K["BdBo"]: _e(K["BdBo"], (db.BO, db.BO), subs="100", ban_dua=True),
        K["BdHet"]: _e(K["BdHet"], song="het", ban_dua=True),
        K["Tre"]: _e(K["Tre"], subs="2000", tv="1500"),
        K["Bung"]: _e(K["Bung"], subs="3000", tv="900"),
        K["VuotNho"]: _e(K["VuotNho"], subs="300", tv="200", vuot="40"),   # 40 × 300 = 12.000 < sàn 50.000
    }
    du = {"kenh": kenh}
    truoc = copy.deepcopy({k: (e["theo_kenh"], e["trang_thai"]) for k, e in kenh.items()})
    anh = {k: _anh(2) for k in K.values()}
    anh[K["Im"]] = _anh(60)
    anh[K["Tre"]] = _anh(1, du=True, cu=_ngay(90), vt=80000)
    anh[K["Bung"]] = _anh(1, bung=8.0, bung_view=30000)
    radar = {K["Radar"]: {"ngay": _ngay(1), "muc": 2, "boi": 12.0, "nguon": "radar"}}
    dem = sdc.phan_tang(du, anh=anh, radar=radar, hom_nay=HOM)
    tang = {x: kenh[k]["tang"] for x, k in K.items()}
    assert tang == {"Lon": "1", "Radar": "2", "Nho": "3", "Im": "3", "Bo": "ngoai", "Het": "ngoai", "Chet": "ngoai",
                    "Lech": "ngoai", "BdNho": "2", "BdBo": "2", "BdHet": "ngoai", "Tre": "2", "Bung": "2",
                    "VuotNho": "3"}, {x: kenh[k]["tang_ly_do"] for x, k in K.items()}
    assert dem == {"1": 1, "2": 5, "3": 3, "ngoai": 5}
    assert kenh[K["Lon"]]["tang_ly_do"].startswith("lõi #1")
    assert "radar ×12" in kenh[K["Radar"]]["tang_ly_do"] and kenh[K["Radar"]]["dot_bien"]["muc"] == 2
    assert "im 60 ngày" in kenh[K["Im"]]["tang_ly_do"]
    assert "kênh trẻ" in kenh[K["Tre"]]["tang_ly_do"] and "video gần ×8" in kenh[K["Bung"]]["tang_ly_do"]
    assert "hằng tháng" in kenh[K["Het"]]["tang_ly_do"] and "không quét lại" in kenh[K["Chet"]]["tang_ly_do"]
    assert "bạn đưa" in kenh[K["BdNho"]]["tang_ly_do"] and kenh[K["Lon"]]["dang_moi"] == _ngay(2)
    # xếp tầng không đụng phần riêng của kênh ta (ghi chú, trạng thái)
    assert {k: (e["theo_kenh"], e["trang_thai"]) for k, e in kenh.items()} == truoc


def test_tran_tang_1_xep_diem_phan_du(monkeypatch):
    monkeypatch.setattr(sdc, "TRAN_TANG_1", 2)
    K = {x: _uc(x) for x in ("A1", "A2", "A3", "CoMat")}
    kenh = {K["A1"]: _e(K["A1"], subs="300000", tv="90000"), K["A2"]: _e(K["A2"], subs="100000", tv="30000"),
            K["A3"]: _e(K["A3"], subs="20000", tv="6000"),
            # nhỏ nhưng có mặt dày ở pool khán giả ta → ứng viên tầng 1, ngoài trần mà nhỏ → tầng 3
            K["CoMat"]: _e(K["CoMat"], subs="200", tv="100", lq={"A": {"tc": 3, "pool": 6}})}
    sdc.phan_tang({"kenh": kenh}, anh={k: _anh(1) for k in K.values()}, radar={}, hom_nay=HOM)
    assert [kenh[K[x]]["tang"] for x in ("A1", "A2", "A3", "CoMat")] == ["1", "1", "2", "3"]
    assert "ngoài trần 2" in kenh[K["A3"]]["tang_ly_do"] and "có mặt" in kenh[K["CoMat"]]["tang_ly_do"]
    assert kenh[K["A1"]]["tang_diem"] > kenh[K["A2"]]["tang_diem"] > kenh[K["A3"]]["tang_diem"]


def test_dot_bien_dinh_qua_lan_gop_roi_het_han():
    k = _uc("Dinh")
    anh = {k: _anh(2)}
    cu = {"kenh": {k: {"dot_bien": {"ngay": _ngay(5), "muc": 3, "boi": 30.0, "nguon": "radar"}}}}
    du = {"kenh": {k: _e(k, subs="500", tv="200")}}
    sdc.phan_tang(du, cu=cu, anh=anh, radar={}, hom_nay=HOM)
    assert du["kenh"][k]["tang"] == "2" and du["kenh"][k]["dot_bien"]["ngay"] == _ngay(5)
    cu["kenh"][k]["dot_bien"]["ngay"] = _ngay(sdc.NGAY_DOT_BIEN_TANG + 1)
    du = {"kenh": {k: _e(k, subs="500", tv="200")}}
    sdc.phan_tang(du, cu=cu, anh=anh, radar={}, hom_nay=HOM)
    assert du["kenh"][k]["tang"] == "3" and "dot_bien" not in du["kenh"][k]


def _kenh_do(goc, cac):
    """Ảnh chụp kênh giả trong kho nhóm: `[(input_url, channel_id, cách ngày video mới nhất)]` — chụp hôm nay."""
    p = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "nghien-cuu", "kenh-do.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    hom = _dt.date.today()
    du = {}
    for l, cid, cach in cac:
        vids = [{"video_id": "vidTang{0:04d}".format(i), "views": 300, "upload_date": _ngay(cach + 7 * i, hom)}
                for i in range(6)]
        du["{0}|40|ja".format(l)] = {"ngay": hom.isoformat(), "ch": {
            "input_url": l, "channel_id": cid, "channel_url": "https://www.youtube.com/channel/" + cid,
            "subscribers": 400, "videos": vids}}
    with open(p, "w", encoding="utf-8") as t:
        json.dump(du, t)


def test_gop_doc_radar_va_quyet_dinh_keo_tang_3_len_tang_2(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    X, Y = _uc("RadarX"), _uc("QuyetY")
    LX, LY = "https://www.youtube.com/@kenhgia-x", "https://www.youtube.com/@kenhgia-y"
    _kenh_do(goc, [(LX, X, 1), (LY, Y, 2)])
    ghi_x = "✓ AI kiểm ngách 12/10: chân dung tâm lý ‖ ghi tay của chủ"
    for m in ("A", "B"):
        _so(goc, m, [{"Kênh": "KenhNhoX", "Link kênh": LX, "Trạng thái": db.THEO_DOI, "Subs": "400", "View TV": "300",
                      "Ghi chú": ghi_x if m == "A" else "", "Quét lúc": "2026-10-12 05:00"},
                     {"Kênh": "KenhNhoY", "Link kênh": LY, "Trạng thái": db.THEO_DOI, "Subs": "400", "View TV": "300",
                      "Quét lúc": "2026-10-12 05:00"}])
    du = sdc.gop(goc, NHOM)
    assert du["kenh"][X]["tang"] == "3" and du["kenh"][Y]["tang"] == "3", du["kenh"][X]["tang_ly_do"]
    assert du["thong_ke"]["tang"] == {"1": 0, "2": 0, "3": 2, "ngoai": 0}
    d = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "radar")
    os.makedirs(d, exist_ok=True)
    hom = _dt.date.today().isoformat()
    with open(os.path.join(d, "radar-moi-nhat.json"), "w", encoding="utf-8") as t:
        json.dump({"luc": hom + "T08:00:00", "dong": [{"kenh_khoa": X, "kenh_nguon": "KenhNhoX", "muc": 3, "boi": 25}]}, t)
    with open(os.path.join(d, "quyet-dinh.jsonl"), "w", encoding="utf-8") as t:
        t.write(json.dumps({"luc": hom + "T08:00:00", "kenh_nguon": "KenhNhoY", "muc": 2, "boi": 11, "quyet": "bo"}) + "\n")
    du = sdc.gop(goc, NHOM)
    ex, ey = du["kenh"][X], du["kenh"][Y]
    assert ex["tang"] == "2" and ex["dot_bien"]["nguon"] == "radar" and "radar ×25" in ex["tang_ly_do"]
    assert ey["tang"] == "2" and ey["dot_bien"]["nguon"] == "quyết định radar"
    assert ex["theo_kenh"]["A"]["ghi"] == ghi_x                       # ghi chú tay nguyên văn
    os.remove(os.path.join(d, "radar-moi-nhat.json"))
    os.remove(os.path.join(d, "quyet-dinh.jsonl"))
    du = sdc.gop(goc, NHOM)
    assert du["kenh"][X]["tang"] == "2", "mốc đột biến phải dính qua lần gộp sau"
    with io.open(os.path.join(goc, "CHANNEL", "_NHOM", NHOM, sdc.TEP_CSV), encoding="utf-8-sig", newline="") as t:
        rows = list(csv.DictReader(t))
    assert "Tầng" in rows[0] and "Lý do tầng" in rows[0] and {r["Tầng"] for r in rows} == {"2"}


def test_khoa_channel_uc_giu_hoa_thuong_va_noi_kho_kenh_ai(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    uc = _uc("HoaThuong")
    link = "https://www.youtube.com/channel/" + uc
    _so(goc, "A", [{"Kênh": "KenhHoaThuong", "Link kênh": link, "Trạng thái": db.THEO_DOI, "Ghi chú": "",
                    "Quét lúc": "2026-10-12 05:00"}])
    p = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "nghien-cuu", "kenh-ai.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as t:   # kho phán quyết ghi khoá = link hạ chữ thường
        json.dump({link.lower(): {"ket": "doi_thu", "kiem_ngach": "giu", "ngay": "2026-10-12", "ly_do": "đúng ngách"}}, t)
    du = sdc.gop(goc, NHOM)
    assert list(du["kenh"]) == [uc], list(du["kenh"])                 # không còn khoá `channel/uc…` hạ chữ thường
    e = du["kenh"][uc]
    assert e["uc"] == uc and e["ngach"]["nguon"] == "kenh-ai" and e["ngach"]["ket"] == "giu"
    assert sdc.tra(goc, NHOM, link.lower())["khoa"] == uc
    assert sdc.khoa_chuan(link + "/videos", {}) == uc


def _du_quet(rows, bi=None):
    return {"kenh": {k: {"khoa": k, "tang": t} for k, t in rows.items()}, "bi_danh": bi or {}}


def test_loc_quet_theo_tang_va_den_han(tmp_path, monkeypatch):
    monkeypatch.delenv("MYTOOL_QUET_THEO_TANG", raising=False)
    goc = str(tmp_path)
    _kenh(goc, "A")
    now = time.time()
    U6 = _uc("AnhTuoi")
    L = {"t1": "https://www.youtube.com/@giat1", "t2": "https://www.youtube.com/@giat2",
         "t3": "https://www.youtube.com/@giat3", "t3b": "https://www.youtube.com/@giat3-ban-sao",
         "moi": "https://www.youtube.com/@giamoi", "t5": "https://www.youtube.com/@giat5",
         "t6": "https://www.youtube.com/channel/" + U6}
    du = _du_quet({"@giat1": "1", "@giat2": "2", "@giat3": "3", "@giat5": "3", U6: "2"},
                  bi={"@giat3-ban-sao": "@giat3", db.khoa(L["t6"]): U6})
    so.luu_cai(goc, "A", quet_kenh={db.khoa(L[x]): now - 86400 for x in ("t1", "t2", "t3", "t5", "t6")})
    # ảnh chụp nhóm của U6 vừa chụp 2 giờ trước (kênh anh em quét) — sổ A chưa ăn
    q = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "nghien-cuu", "quet-kenh")
    os.makedirs(q, exist_ok=True)
    with open(os.path.join(q, "gia.json"), "w", encoding="utf-8") as t:
        json.dump({"luc": now - 7200, "ch": {"channel_id": U6, "videos": [{"views": 10, "upload_date": "2026-10-12"}]}}, t)
    links = [L[x] for x in ("t3", "t3b", "t2", "t5", "t6", "moi", "t1")]
    nhat = []
    ra, dem = sdc.loc_quet(goc, "A", links, du=du, bay_gio=now, trang_chu={"@giat5": now - 3600}, on_log=nhat.append)
    # tầng 1 (tới hạn) → kênh mới → tầng 2 (ảnh chụp nhóm còn tươi) → tầng 3 (trang chủ vừa đẩy video mới)
    assert ra == [L["t1"], L["moi"], L["t6"], L["t5"]], (ra, dem)
    assert dem["trung"] == 1 and dem["hoan"] == 2 and dem["som"] == {"ảnh chụp nhóm còn tươi": 1, "trang chủ vừa thấy": 1}
    assert nhat and "quét theo tầng" in nhat[0]
    ra3, _ = sdc.loc_quet(goc, "A", links, du=du, bay_gio=now + 3 * 86400, trang_chu={})
    assert L["t2"] in ra3 and L["t3"] not in ra3                     # 3 ngày: tầng 2 tới hạn, tầng 3 chưa
    ra7, _ = sdc.loc_quet(goc, "A", links, du=du, bay_gio=now + 7 * 86400, trang_chu={})
    assert L["t3"] in ra7 and L["t3b"] not in ra7
    monkeypatch.setenv("MYTOOL_QUET_THEO_TANG", "0")
    assert sdc.loc_quet(goc, "A", links, du=du, bay_gio=now)[0] == links
    monkeypatch.delenv("MYTOOL_QUET_THEO_TANG")
    so.luu_cai(goc, "A", quet_kenh={})                               # sổ chưa có mốc từng kênh → quét đủ một lượt
    ra0, _ = sdc.loc_quet(goc, "A", links, du=du, bay_gio=now, trang_chu={})
    assert sorted(ra0) == sorted(set(links) - {L["t3b"]})


def test_loc_quet_khong_nhom_hoac_chua_co_tang_quet_du(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "C", nhom="")
    links = ["https://www.youtube.com/@giax", "https://www.youtube.com/@giay"]
    assert sdc.loc_quet(goc, "C", links)[0] == links
    _kenh(goc, "A")
    assert sdc.loc_quet(goc, "A", links, du={"kenh": {"@giax": {"khoa": "@giax"}}})[0] == links


def test_den_han_do_lai_kenh_ngoai_hang_thang(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    H1, H2, H3 = _uc("Het10"), _uc("Het40"), _uc("Tang3")
    p = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "nghien-cuu", "kenh-do.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    hom = _dt.date.today()
    with open(p, "w", encoding="utf-8") as t:
        json.dump({"{0}|40|ja".format(cid): {"ngay": _ngay(cach, hom), "ch": {
            "channel_id": cid, "videos": [{"views": 5, "upload_date": _ngay(cach + 50, hom)}]}}
            for cid, cach in ((H1, 10), (H2, 40), (H3, 2))}, t)
    du = {"kenh": {H1: {"khoa": H1, "tang": "ngoai"}, H2: {"khoa": H2, "tang": "ngoai"}, H3: {"khoa": H3, "tang": "3"}},
          "bi_danh": {}}
    links = ["https://www.youtube.com/channel/" + x for x in (H1, H2, H3)]
    assert sdc.den_han_do_lai(goc, "A", links, du=du) == {links[1], links[2]}
    _kenh(goc, "C", nhom="")
    assert sdc.den_han_do_lai(goc, "C", links) == set(links)


def test_radar_theo_ten_uu_tien_dong_tang_cao_khi_trung_ten():
    from core import radar_dot_bien as rd

    so_chung = {"kenh": {"k-bo": {"khoa": "k-bo", "ten": "TenTrungGia", "tang": "ngoai", "trang_thai": db.BO},
                         "k-td": {"khoa": "k-td", "ten": "TenTrungGia", "tang": "1", "trang_thai": db.THEO_DOI}}}
    assert rd._theo_ten(so_chung)["TenTrungGia"]["khoa"] == "k-td"   # noqa: SLF001


def test_gop_bang_tang_ngay_chia_theo_khoang_cua_kenh():
    from core.doi_thu import COT_VIDEO

    cot = so.cot_mac_dinh()
    link = "https://www.youtube.com/watch?v=vidTangNgay"
    cu = [[{"Link video": link, "View": "1000", "Kênh": "KenhGia"}.get(c, "") for c in cot]]
    moi = [[{"Link video": link, "View": "8000", "Kênh": "KenhGia"}.get(c, "") for c in COT_VIDEO]]
    o = cot.index(so.COT_TANG)
    assert so.gop_bang(cot, cu, moi, ngay_cach_nhau=1.0)[0][o] == "7000"
    assert so.gop_bang(cot, cu, moi, ngay_cach_nhau=1.0, ngay_cach_theo_link={link: 7.0})[0][o] == "1000"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
