"""Khởi tạo VPS mới cho ngách mới (22/10/2026) — `core/khoi_tao_vps` + `core/tuyen_thi_truong`.

Chạy khô cả luồng với đồ giả (kho Chrome, AI, yt-dlp, Một nút, tạo kênh thương hiệu): đầu vào → mã kênh từ kho → ngách
→ nuôi trang chủ (chờ tới khi sổ nuôi "đạt") → đối thủ từ ô trang chủ → tuyến → chia kênh → luồng mở kênh → xong.
Chỉ `tmp_path`, không mạng, không ví, không Chrome.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os

from core import khoi_tao_vps as ktv
from core import tuyen_thi_truong as ttt

HO_SO = """mo_ta_ngach: "Life stories — narrated stories"
mau_tieu_de: "kênh YouTube truyện kể tiếng Anh"
chu_de_rong: "storytelling"
tep_khan_gia:
  - {ma: tam-thoi, ten: "Tạm", ten_ngan: "Tạm"}
thi_truong: {quoc_gia: US, ngon_ngu: en}
"""


def _ghi(duong, chu):
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write(chu)


def test_doc_dau_vao():
    nc = ktv.doc_ngach_txt("chu_de: truyện kể đời người\nquoc_gia: us\nngon_ngu: EN\nkhán giả: người lớn 35-65\n"
                           "khong_nham: trẻ em; học sinh\n# ghi chú\nKênh kể chuyện có lời đọc, mỗi video 20 phút.\n")
    assert (nc["chu_de"], nc["quoc_gia"], nc["ngon_ngu"], nc["tien_to"]) == ("truyện kể đời người", "US", "en", "K")
    assert nc["khan_gia"] == "người lớn 35-65" and nc["khong_nham"] == ["trẻ em", "học sinh"]
    assert "20 phút" in nc["mo_ta"]
    g = ktv.doc_giong_txt("AbCdEfGhIjKlMnOpQrSt  # giọng nữ ấm\nkhông-phải-voice\nAbCdEfGhIjKlMnOpQrSt\nZyXwVuTsRqPoNmLkJiHg\n")
    assert [x["voice_id"] for x in g] == ["AbCdEfGhIjKlMnOpQrSt", "ZyXwVuTsRqPoNmLkJiHg"] and g[0]["ghi_chu"] == "giọng nữ ấm"
    d = ktv.doc_doi_thu_txt("https://www.youtube.com/@KenhMot/videos\n@kenh_hai\nyoutube.com/@KenhMot\nrác\n")
    assert d == ["https://www.youtube.com/@KenhMot", "https://www.youtube.com/@kenh_hai"]


def test_phan_kenh_danh_muc_khong_an_view_nhau():
    so_do = [{"ma": "a", "toi_da": 2}, {"ma": "b", "toi_da": 1}, {"ma": "c", "toi_da": 1}, {"ma": "d", "toi_da": 0}]
    assert ttt.phan_kenh(["K1", "K2", "K3"], so_do) == {"K1": "a", "K2": "b", "K3": "c"}         # phủ tuyến trước
    assert ttt.phan_kenh(["K1", "K2", "K3", "K4"], so_do)["K4"] == "a"                           # rồi sức chứa
    ra = ttt.phan_kenh(["K1", "K2", "K3", "K4", "K5", "K6"], so_do)
    assert sorted(ra.values()).count("a") >= 2 and "d" not in ra.values()                         # tuyến 0 nguồn: không
    assert ttt.phan_kenh(["K1", "K2"], so_do, {"K1": "c"}) == {"K1": "c", "K2": "a"}              # giữ tuyến đã có


def _content(goc, kenh, dong):
    duong = os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", "content.csv")
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8-sig", newline="") as tep:
        w = csv.writer(tep)
        w.writerow(["Kênh", "Tiêu đề video", "Link video", "Ngày đăng", "Thời lượng", "View", "Tăng/ngày"])
        w.writerows(dong)


class _AI:
    """Đồ giả `BoGoiAI.hoi`: chia 2 tuyến; gán theo chữ trong tiêu đề."""

    def __init__(self):
        self.so_luot = 0

    def hoi(self, buoc, loi_nhac, **_k):
        self.so_luot += 1
        if buoc.startswith("tuyen-thi-truong"):
            return json.dumps({"tuyen": [{"ma": "gia-dinh", "ten": "Gia đình", "ten_ngan": "Gia đình", "mo_ta": "chuyện nhà"},
                                         {"ma": "cong-so", "ten": "Công sở", "ten_ngan": "Công sở", "mo_ta": "chuyện sở"},
                                         {"ma": "1", "ten": "Số trơn", "mo_ta": "mã số trơn phải đổi"}]})
        ra = {}
        for dong in loi_nhac.split("TIÊU ĐỀ (số|tiêu đề):\n")[1].split("\n\n")[0].splitlines():
            so, _, td = dong.partition("|")
            ra[so] = "gia-dinh" if "family" in td else ("cong-so" if "boss" in td else "lac")
        return json.dumps(ra)


def _dung_content(goc, kenh="K1"):
    hom = dt.date.today()
    dong = []
    for i in range(40):
        ngay = (hom - dt.timedelta(days=5 + i)).isoformat()
        dong.append(["Kênh A", "My family secret {0}".format(i), "https://www.youtube.com/watch?v=fam{0:08d}".format(i),
                     ngay, "20:00", 100000 if i < 12 else 2000, 0])
        dong.append(["Kênh B", "The boss fired me {0}".format(i), "https://www.youtube.com/watch?v=bos{0:08d}".format(i),
                     ngay, "18:00", 5000 if i < 2 else 1000, 0])
    dong.append(["Kênh C", "a short", "https://www.youtube.com/watch?v=sho00000001", hom.isoformat(), "0:40", 9, 0])
    _content(goc, kenh, dong)


def test_tuyen_thi_truong_chia_gan_do_ghi(tmp_path):
    goc = str(tmp_path)
    _ghi(os.path.join(goc, "CHANNEL", "_NHOM", "truyen", "ngach.yaml"), HO_SO)
    _ghi(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"), 'nhom: "truyen"\nngon_ngu: en\n')
    _dung_content(goc)
    ai = _AI()
    kq = ttt.chay(goc, "truyen", ai=ai, ghi_ho_so_ngach=True, log=lambda *_: None)
    ma = [d["ma"] for d in kq["tuyen"]]
    assert ma[0] == "gia-dinh" and "cong-so" in ma and "1" not in ma                   # số trơn → slug khác
    gd = kq["tuyen"][0]
    assert gd["so_video"] == 40 and gd["nguon_no_thang"] > 0 and gd["toi_da"] >= 1
    tt = json.load(io.open(os.path.join(goc, ttt.TEP_THI_TRUONG), encoding="utf-8"))
    assert tt["nguon"].startswith(ttt.DAU_NGUON) and "gia-dinh" in tt["tep"]
    from core.ho_so_ngach import doc_ngach
    assert [t["ma"] for t in doc_ngach(goc, "K1").tep_khan_gia][:1] == ["gia-dinh"]
    n = ai.so_luot
    ttt.chay(goc, "truyen", ai=ai, log=lambda *_: None)                                  # chạy lại: nhớ đệm, 0 lượt
    assert ai.so_luot == n
    # tệp thị trường KHÔNG do module ghi (máy đầu: số tay) → không đè
    _ghi(os.path.join(goc, ttt.TEP_THI_TRUONG), json.dumps({"nguon": "tay", "tep": {"1": {}}}))
    assert ttt.ghi_thi_truong(goc, "truyen", kq["tuyen"], 1) == ""


def test_khoi_tao_vps_chay_kho_toi_xong(tmp_path):
    goc = os.path.join(str(tmp_path), "MyTool")
    os.makedirs(goc)
    dv = {"thu_muc": "-", "ngach": ktv.doc_ngach_txt("chu_de: truyện kể\nquoc_gia: US\nngon_ngu: en\nkhan_gia: người lớn\n"),
          "giong": ktv.doc_giong_txt("AbCdEfGhIjKlMnOpQrSt\nZyXwVuTsRqPoNmLkJiHg\n"),
          "doi_thu": ["https://www.youtube.com/@kenhmot"]}
    nhom = ktv.nhom_tu_dau_vao(dv["ngach"])
    dat = {}

    def lap_dat(g, ten, ma):
        dat[ma] = ten
        _ghi(os.path.join(os.path.dirname(g), ma, ma + ".exe"), "x")
        return "da_dat", "ok"

    def khoi_tao(g, yc, **_k):
        _ghi(os.path.join(g, "CHANNEL", "_NHOM", yc.nhom, "ngach.yaml"), HO_SO)
        _ghi(os.path.join(g, "CHANNEL", yc.ma_kenh, "kenh.yaml"),
             'ten: "Story"\nnhom: "{0}"\nngon_ngu: en\ntep: "tam-thoi"\nthiet_lap_kenh: true\n'.format(yc.nhom))
        _dung_content(g, yc.ma_kenh)

    goi = []
    cam = dict(quet=lambda g: [{"ten": "chrome-b", "loai": "moi"}, {"ten": "chrome-a", "loai": "moi"},
                               {"ten": "x", "loai": "chua_dang_nhap"}],
               giu=lambda g, ten, ma: True, lap_dat=lap_dat, co_vi=lambda g: "", khoi_tao=khoi_tao, client=object(),
               tra=lambda vid, lang="": {"link_kenh": "https://www.youtube.com/@moi" + vid[-1]},
               mot_nut=lambda *a, **k: goi.append("mot_nut"),
               chay_tuyen=lambda g, n, **k: ttt.chay(g, n, ai=_AI(), ghi_ho_so_ngach=True, log=lambda *_: None),
               chay_tao_kenh=lambda g, m: goi.append("tao:" + m) or 0)
    log = []
    b = ktv.nhip(goc, dau_vao=dv, log=log.append, **cam)
    so = ktv.doc_so(goc)
    assert b == "nuoi" and dat == {"K1": "chrome-a", "K2": "chrome-b"}, (b, so.get("loi"))
    assert so["kenh"]["K1"]["giong"] == "AbCdEfGhIjKlMnOpQrSt" and so["kenh"]["K2"]["giong"] == "ZyXwVuTsRqPoNmLkJiHg"
    assert any("chưa đăng nhập Gmail" in v["chu"] for v in ktv.viec_cua_ban(goc))
    y1 = io.open(os.path.join(goc, "CHANNEL", "K1", "kenh.yaml"), encoding="utf-8").read()
    assert "thiet_lap_kenh: false" in y1 and "AbCdEfGhIjKlMnOpQrSt" in y1 and "nuoi_trang_chu: true" in y1
    assert os.path.isfile(os.path.join(goc, "workspace", "chuan-bi-K2", "CHANNEL", "K2", "kenh.yaml"))
    kho_giong = json.load(io.open(os.path.join(goc, "CHANNEL", "_NHOM", nhom, "kho-giong.json"), encoding="utf-8"))
    assert len(kho_giong["giong"]) == 2
    them = io.open(os.path.join(goc, "CHANNEL", "_NHOM", nhom, "doi-thu-them.txt"), encoding="utf-8").read()
    assert "@kenhmot" in them

    # nuôi chưa đạt → chờ; đạt → đi tiếp tới mở kênh
    assert ktv.nhip(goc, dau_vao=dv, log=log.append, **cam) == "nuoi"
    for ma in ("K1", "K2"):
        _ghi(os.path.join(goc, "vm", "logs", "nuoi-trang-chu", ma + ".json"),
             json.dumps({"trang_thai": "dat", "cache": {"vidA0000001": "dung_ngach", "vidB0000002": "lac_de"}}))
    b = ktv.nhip(goc, dau_vao=dv, log=log.append, **cam)
    so = ktv.doc_so(goc)
    assert b == "mo_kenh", (b, so.get("loi"), log[-5:])
    assert goi[:1] == ["mot_nut"] and so["doi_thu_tra"]["kenh"] == 1
    from core import mo_kenh
    st = mo_kenh.doc_trang_thai(goc)
    assert {so["kenh"]["K1"]["tuyen"], so["kenh"]["K2"]["tuyen"]} == {"gia-dinh", "cong-so"}
    for ma in ("K1", "K2"):
        d = st["kenh"][ma]
        assert d["loai"] == ktv.LOAI_MO_KENH and d["can_thuong_hieu"] and d["kenh_goc"] == "K1" and d["tu_dong"]
        assert mo_kenh.giong_cua_hang(d)["voice_id"] == so["kenh"][ma]["giong"]
    assert "gia-dinh" in io.open(os.path.join(goc, "CHANNEL", "K1", "nghien-cuu", "tuyen.csv"), encoding="utf-8-sig").read()

    # mo_kenh chuẩn bị xong (có tên gợi ý) → một lượt DOM tạo kênh thương hiệu mỗi nhịp; mọi kênh xong → xong
    for ma in ("K1", "K2"):
        st["kenh"][ma].update(trang_thai="cho_chrome", ten_goi_y="Story " + ma)
    mo_kenh.luu_trang_thai(goc, st)
    ktv.nhip(goc, dau_vao=dv, log=log.append, **cam)
    assert [x for x in goi if x.startswith("tao:")] == ["tao:K1"]
    for ma in ("K1", "K2"):
        st["kenh"][ma]["trang_thai"] = "xong"
    mo_kenh.luu_trang_thai(goc, st)
    assert ktv.nhip(goc, dau_vao=dv, log=log.append, **cam) == "xong"
    assert ktv.viec_cua_ban(goc) == []
    assert ktv.can_lam(goc)[0] is False                                                  # vừa đo thị trường

    # MỞ RỘNG: kho thêm 2 Chrome mới + giong.txt thêm 1 giọng → thêm ĐÚNG 1 kênh (chừa 1 Chrome cho D20 thay kênh hỏng)
    dv["giong"] = ktv.doc_giong_txt("AbCdEfGhIjKlMnOpQrSt\nZyXwVuTsRqPoNmLkJiHg\nQqQqQqQqQqQqQqQqQqQq\n")
    cam["quet"] = lambda g: [{"ten": t, "loai": "moi"} for t in ("chrome-a", "chrome-b", "chrome-c", "chrome-d")]
    assert ktv.so_mo_rong(goc, ktv.doc_so(goc), dv, cam["quet"]) == 1
    b = ktv.nhip(goc, dau_vao=dv, log=log.append, **cam)
    so = ktv.doc_so(goc)
    assert b == "nuoi" and sorted(so["kenh"]) == ["K1", "K2", "K3"] and dat["K3"] == "chrome-c", (b, so.get("loi"))
    assert so["kenh"]["K3"]["giong"] == "QqQqQqQqQqQqQqQqQqQq" and so["kenh"]["K1"]["tuyen"] == "gia-dinh"
    assert os.path.isfile(os.path.join(goc, "workspace", "chuan-bi-K3", "CHANNEL", "K3", "kenh.yaml"))


def test_can_lam_va_kiem_khong_ghi(tmp_path):
    goc = os.path.join(str(tmp_path), "MyTool")
    os.makedirs(goc)
    assert ktv.can_lam(goc)[0] is False
    k = ktv.kiem(goc, {"thu_muc": "-", "ngach": ktv.doc_ngach_txt(""), "giong": [], "doi_thu": []},
                 quet=lambda g: [], co_vi=lambda g: "chưa có khoá")
    assert any("ngach.txt" in x for x in k["loi"]) and any("kho Chrome" in x for x in k["loi"])
    assert any("ShopAPI" in x for x in k["viec_nguoi"])
    assert not os.path.exists(os.path.join(goc, "workspace"))
