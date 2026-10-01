"""Kiểm ngách + sức sống danh bạ đối thủ (30/09/2026) — không mạng, LLM giả.

Canh: cửa ngừng hoạt động (+ ngoại lệ đột biến) · cửa quá yếu tương đối nhóm (+ ngoại lệ video nổi,
tăng trưởng) · lượt LLM thường → lượt SÂU cho ca lưng chừng (bắt buộc giu/bo) · áp vào danh bạ
(bỏ = đổi trạng thái + giữ lịch sử Ghi chú, không xoá dòng) · kênh chỉ đề xuất không bị ghi ·
phán quyết ghi kho chung `kenh-ai.json` · gạt bảng `danh-sach-chon.json`.
"""

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import kiem_ngach_doi_thu as kn  # noqa: E402

HOM = dt.date(2026, 9, 30)


def _v(cach, view, tang=0.0, giay=900, td="t"):
    return ((HOM - dt.timedelta(days=cach)).isoformat(), view, giay, tang, td)


def test_ngung_hoat_dong_va_ngoai_le_dot_bien():
    s = kn.do_so_kenh([_v(40 + i, 5000) for i in range(10)], HOM)
    assert s.ngay_im == 40
    assert kn.cua_suc_song(s, {})[0] == kn.HET and "không còn làm" in kn.cua_suc_song(s, {})[1]
    s2 = kn.do_so_kenh([_v(40, 60000, tang=800)] + [_v(41 + i, 5000) for i in range(10)], HOM)
    assert s2.dot_bien_gan and kn.cua_suc_song(s2, {})[0] == "", "còn video đột biến → chưa bỏ"
    s3 = kn.do_so_kenh([_v(3, 5000, giay=60)] + [_v(40 + i, 5000) for i in range(5)], HOM)
    assert s3.ngay_im == 40, "Shorts không tính là 'còn đăng'"


def test_qua_yeu_tuong_doi_nhom_va_ngoai_le():
    nguong = {"trung_vi_gan": 2000.0, "view_thang": 10000.0}
    yeu = kn.do_so_kenh([_v(2 + i * 3, 800 + i) for i in range(12)], HOM)
    assert kn.cua_suc_song(yeu, nguong)[0] == kn.HET and "không còn phát triển" in kn.cua_suc_song(yeu, nguong)[1]
    noi = kn.do_so_kenh([_v(2, 9000)] + [_v(5 + i * 3, 800) for i in range(12)], HOM)
    assert kn.cua_suc_song(noi, nguong)[0] == "", "có video nổi ≥3× trung vị → giữ (tín hiệu VPH quý)"
    vuot = kn.do_so_kenh([_v(10, 1300)] + [_v(12 + i * 3, 800) for i in range(12)], HOM)
    assert vuot.vuot_gan and kn.cua_suc_song(vuot, nguong)[0] == "", "video gần đây ≥1,5× trung vị → còn phát triển"
    to = kn.do_so_kenh([_v(2 + i * 3, 8000 + i) for i in range(12)], HOM)
    assert kn.cua_suc_song(to, nguong)[0] == "", "kênh không bé thì không xét 'phát triển'"
    tang = kn.do_so_kenh([_v(1 + i, 1500) for i in range(10)] + [_v(20 + i, 300) for i in range(15)], HOM)
    assert tang.tang_truong >= 2 and kn.cua_suc_song(tang, nguong)[0] == "", "đang tăng trưởng nhanh → giữ"
    it = kn.do_so_kenh([_v(2, 100), _v(3, 100)], HOM)
    assert kn.cua_suc_song(it, nguong)[0] == "", "quá ít video → không đo 'quá yếu'"


def test_nguong_nhom_la_phan_vi():
    so_ = {str(i): kn.SoKenh(so_video_dai=10, trung_vi_gan=float(i * 100), view_thang=float(i * 1000)) for i in range(1, 11)}
    ng = kn.nguong_nhom(so_)
    assert ng["trung_vi_gan"] == 300.0 and ng["view_thang"] == 3000.0 and ng["so_mau"] == 10


def _goc(tmp_path, kenh_list=("A", "B")):
    goc = str(tmp_path)
    for k in kenh_list:
        d = os.path.join(goc, "CHANNEL", k)
        os.makedirs(os.path.join(d, "nghien-cuu"), exist_ok=True)
        with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
            t.write("ma: {0}\nngon_ngu: ja\nnhom: ng\n".format(k))
    return goc


def _danh_ba(goc, k, dong):
    cot, hang = db.doc(goc, k)
    hang = db.gop_cham(cot, hang, [db.BanGhi(ten=t, link=l) for t, l, _g in dong])
    hang = db.dat_trang_thai(cot, hang, [l for _t, l, _g in dong], db.THEO_DOI)
    for _t, l, g in dong:
        hang = db._dat_cot(cot, hang, [l], "Ghi chú", g)  # noqa: SLF001
    db.luu(goc, k, cot, hang)


def _content(goc, k, kenh_video):
    cot = so.cot_mac_dinh()
    o = {c: i for i, c in enumerate(cot)}
    hang = []
    n = 0
    for ten, videos in kenh_video.items():
        for cach, view, td in videos:
            d = [""] * len(cot)
            d[o["Kênh"]], d[o["Tiêu đề video"]] = ten, td
            d[o["Link video"]] = "https://www.youtube.com/watch?v=%011d" % n
            d[o["Ngày đăng"]], d[o["View"]], d[o["Thời lượng"]] = (dt.date.today() - dt.timedelta(days=cach)).isoformat(), str(view), "15:00"
            hang.append(d)
            n += 1
    so.luu_bang(goc, k, cot, hang)


def test_kiem_hai_luot_ap_danh_ba_va_kho_nhom(tmp_path):
    goc = _goc(tmp_path)
    L = {n: "https://www.youtube.com/@" + n for n in ("tam", "barry", "zatsu", "im", "tay")}
    _danh_ba(goc, "A", [("心理の部屋", L["tam"], "máy chấm: khớp tuyến 30%"),
                        ("Barry Nobles", L["barry"], "máy chấm: khớp tuyến 12% · già 0%"),
                        ("雑学の森", L["zatsu"], "thị trường (gần ngách)"),
                        ("静かな心理", L["im"], "máy chấm: x"),
                        ("手入れ", L["tay"], "bạn đưa — luôn quét")])
    _danh_ba(goc, "B", [("Barry Nobles", L["barry"], "máy chấm: khớp tuyến 10%")])
    moi = [(2 + i * 2, 5000, "一人が好きな人の特徴 %d" % i) for i in range(8)]
    _content(goc, "A", {"心理の部屋": moi, "Barry Nobles": moi, "雑学の森": moi, "手入れ": moi,
                        "静かな心理": [(50 + i, 5000, "t") for i in range(8)]})
    hoi = []

    def goi(client, msgs, **kw):
        de, chu = msgs[0]["content"], msgs[1]["content"]
        hoi.append(("SAU" if "QUYẾT DỨT KHOÁT" in de else "THUONG", chu))
        if "QUYẾT DỨT KHOÁT" in de:
            return json.dumps({"1": {"k": "giu", "ly_do": "phần lớn là chân dung tâm lý"}})
        tra = {}
        for i, dong in enumerate([x for x in chu.split("\n") if x[:1].isdigit()], 1):
            ten = dong.split("Kênh: ")[1].split(" (")[0]
            tra[str(i)] = {"k": {"心理の部屋": "giu", "Barry Nobles": "bo", "雑学の森": "nghi", "手入れ": "bo"}.get(ten, "giu"),
                           "ly_do": "lý do " + ten}
        return json.dumps(tra, ensure_ascii=False)
    kq = kn.kiem(goc, ["A", "B"], object(), sua=["A"], goi=goi)
    assert [h[0] for h in hoi] == ["THUONG", "SAU"] and "雑学の森" in hoi[1][1] and "hoạt động:" in hoi[1][1]
    ket = {d["kenh"]: d["ket"] for d in kq["theo_kenh"]["A"]}
    assert ket == {"心理の部屋": kn.GIU, "Barry Nobles": kn.BO, "雑学の森": kn.GIU, "静かな心理": kn.HET, "手入れ": kn.BO}
    cot, hang = db.doc(goc, "A")
    o = db.chi_so_cot(list(cot))
    tt = {h[o["Kênh"]]: (h[o["Trạng thái"]], h[o["Ghi chú"]]) for h in hang}
    assert tt["Barry Nobles"][0] == db.BO and tt["Barry Nobles"][1].startswith("AI kiểm ngách 30/09" if False else "AI kiểm ngách")
    assert "trước: máy chấm: khớp tuyến 12%" in tt["Barry Nobles"][1], "giữ lịch sử Ghi chú"
    assert tt["静かな心理"][0] == db.HET and tt["静かな心理"][1].startswith(kn.DAU_HET) \
        and "không còn làm" in tt["静かな心理"][1], "đúng chủ đề mà ngừng đăng → hết (không phải bỏ)"
    assert tt["心理の部屋"][0] == db.THEO_DOI and tt["心理の部屋"][1].startswith(kn.DAU_GIU)
    assert tt["手入れ"][0] == db.BO, "chủ dự án 30/09: kênh người đặt cũng tự quyết"
    assert len(hang) == 5, "không xoá dòng nào"
    # B chỉ đề xuất — không ghi
    cot_b, hang_b = db.doc(goc, "B")
    ob = db.chi_so_cot(list(cot_b))
    assert hang_b[0][ob["Trạng thái"]] == db.THEO_DOI
    assert kq["theo_kenh"]["B"][0]["ket"] == kn.BO
    # kho chung nhóm có phán quyết; lượt sau dùng lại, không hỏi LLM
    m = kn.phan_quyet_nhom(goc, "B", L["barry"])
    assert m and m["kiem_ngach"] == kn.BO
    hoi.clear()
    kn.kiem(goc, ["B"], object(), sua=[], goi=goi)
    assert hoi == []


def test_llm_hong_thi_khong_doi_gi(tmp_path):
    goc = _goc(tmp_path, ("A",))
    link = "https://www.youtube.com/@x"
    _danh_ba(goc, "A", [("心理X", link, "máy chấm: x")])
    _content(goc, "A", {"心理X": [(2 + i, 5000, "t") for i in range(8)]})

    def goi(client, msgs, **kw):
        raise RuntimeError("sập")
    kq = kn.kiem(goc, ["A"], object(), sua=["A"], goi=goi)
    assert kq["theo_kenh"]["A"][0]["ket"] == kn.NGHI
    cot, hang = db.doc(goc, "A")
    o = db.chi_so_cot(list(cot))
    assert hang[0][o["Trạng thái"]] == db.THEO_DOI and hang[0][o["Ghi chú"]] == "máy chấm: x"


def test_lam_sach_danh_sach_chon(tmp_path):
    goc = _goc(tmp_path, ("A",))
    _danh_ba(goc, "A", [("Tốt", "https://www.youtube.com/@t", "x"), ("Xấu", "https://www.youtube.com/@x", "x")])
    cot, hang = db.doc(goc, "A")
    hang = db.dat_trang_thai(cot, hang, ["https://www.youtube.com/@x"], db.BO)
    db.luu(goc, "A", cot, hang)
    p = os.path.join(goc, "CHANNEL", "A", "nghien-cuu", "danh-sach-chon.json")
    with open(p, "w", encoding="utf-8") as t:
        json.dump({"moi": [{"kenh": "Tốt"}, {"kenh": "Xấu"}], "vuot": [{"kenh": "Xấu"}], "luc": "x"}, t)
    assert kn.lam_sach_danh_sach_chon(goc, "A") == 2
    du = json.load(open(p, encoding="utf-8"))
    assert du["moi"] == [{"kenh": "Tốt"}] and du["vuot"] == [] and du["luc"] == "x"


# ── chuẩn 01/10/2026: hết / hồi sinh / làm bằng AI ────────────────────────────


class _Kenh:
    def __init__(self, videos):
        self.videos = videos


class _Vid:
    def __init__(self, cach, view, ma):
        self.upload_date = (dt.date.today() - dt.timedelta(days=cach)).isoformat()
        self.views, self.duration_s, self.title, self.video_id = view, 900, "心理 %s" % ma, ma


def _goi_giu(client, msgs, **kw):
    chu = msgs[-1]["content"]
    so_dong = [x for x in chu.split("\n") if x[:1].isdigit()]
    return json.dumps({str(i): {"k": "giu", "ly_do": "chân dung tâm lý"} for i in range(1, len(so_dong) + 1)})


def test_het_hoi_sinh_va_bo_suc_song_cu_thanh_het(tmp_path):
    goc = _goc(tmp_path, ("A",))
    L = {n: "https://www.youtube.com/@" + n for n in ("song", "chet", "cu")}
    _danh_ba(goc, "A", [("蘇る心理", L["song"], "Hết 30/09: không còn làm: x ‖ máy chấm: y"),
                        ("眠る心理", L["chet"], "máy chấm: z"),
                        ("古い心理", L["cu"], "AI kiểm ngách 30/09: ngừng hoạt động: video dài mới nhất 2026-08-21 "
                                              "· ngách: chân dung ‖ trước: máy chấm: w")])
    cot, hang = db.doc(goc, "A")
    hang = db.dat_trang_thai(cot, hang, [L["song"]], db.HET)
    hang = db.dat_trang_thai(cot, hang, [L["cu"]], db.BO)
    db.luu(goc, "A", cot, hang)
    _content(goc, "A", {"眠る心理": [(45 + i, 5000, "t") for i in range(8)]})
    chup = {L["song"]: _Kenh([_Vid(3 + i * 3, 6000, "s%010d" % i) for i in range(8)]),
            L["cu"]: _Kenh([_Vid(80 + i, 6000, "c%010d" % i) for i in range(8)])}
    goi_lay = []

    def lay(link, **kw):
        goi_lay.append(link)
        return chup[link]
    kq = kn.kiem(goc, ["A"], object(), sua=["A"], goi=_goi_giu, lay_kenh=lay)
    assert sorted(goi_lay) == sorted([L["song"], L["cu"]]), "chỉ kênh không còn quét mới chụp lại"
    o = db.chi_so_cot(list(db.doc(goc, "A")[0]))
    tt = {h[o["Kênh"]]: (h[o["Trạng thái"]], h[o["Ghi chú"]]) for h in db.doc(goc, "A")[1]}
    assert tt["蘇る心理"][0] == db.THEO_DOI and "(hồi sinh)" in tt["蘇る心理"][1] and tt["蘇る心理"][1].endswith("máy chấm: y")
    assert tt["眠る心理"][0] == db.HET and tt["眠る心理"][1].startswith(kn.DAU_HET)
    assert tt["古い心理"][0] == db.HET and tt["古い心理"][1].endswith("‖ máy chấm: w"), "bỏ-sức-sống cũ → hết, giữ lịch sử"
    assert kq["truoc"]["A"][db.HET] == 1 and kq["sau"]["A"][db.HET] == 2 and kq["sau"]["A"][db.THEO_DOI] == 1
    assert db.dang_theo_doi(goc, "A") == [L["song"]], "kênh hết không được quét"


def test_lam_bang_ai_thi_giac_co_dem_va_cot_ai(tmp_path):
    goc = _goc(tmp_path, ("A",))
    L = {n: "https://www.youtube.com/@" + n for n in ("may", "nguoi")}
    _danh_ba(goc, "A", [("AI心理", L["may"], "x"), ("先生の心理", L["nguoi"], "x")])
    moi = [(2 + i * 2, 5000, "心理 %d" % i) for i in range(8)]
    _content(goc, "A", {"AI心理": moi, "先生の心理": moi})
    hoi = []

    def goi_anh(client, msgs, **kw):
        noi = msgs[-1]["content"]
        hoi.append(noi)
        anh = [x for x in noi if x.get("type") == "image"]
        assert len(anh) == 2 * kn.SO_ANH_LAM_AI
        chu = " ".join(x["text"] for x in noi if x.get("type") == "text")
        assert "mô tả: kênh giải thích" in chu
        return json.dumps({"1": {"ai": "先生" not in chu.split("2. Kênh:")[0], "ly_do": "a"},
                           "2": {"ai": "先生" not in chu.split("2. Kênh:")[1], "ly_do": "b"}})

    def tai(url):
        return b"<meta property=\"og:description\" content=\"k\xc3\xaanh gi\xe1\xba\xa3i th\xc3\xadch\">" \
            if "i.ytimg" not in url else b"\xff\xd8jpg"
    kn.kiem(goc, ["A"], object(), sua=["A"], goi=_goi_giu, goi_anh=goi_anh, tai_anh=tai)
    assert len(hoi) == 1, "theo lô"
    o = db.chi_so_cot(list(db.doc(goc, "A")[0]))
    ai = {h[o["Kênh"]]: h[o[db.COT_AI]] for h in db.doc(goc, "A")[1]}
    assert ai == {"AI心理": "có", "先生の心理": "không"}
    kn.kiem(goc, ["A"], object(), sua=["A"], goi=_goi_giu, goi_anh=goi_anh, tai_anh=tai)
    assert len(hoi) == 1, "lượt sau dùng đệm kenh-lam-ai.json, không hỏi lại"
