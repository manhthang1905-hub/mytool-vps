"""Nghiên cứu CHUNG theo nhóm (29/09/2026) — bộ đệm dùng chung ở chỗ gọi mạng/AI.

Canh: đường kho có/không nhóm · bộ nhớ tra trang chủ chung (kênh 2 không tra lại) ·
AI lưỡng lự không hỏi lại + bộ đếm không âm · số đo kênh + phán quyết AI chung ·
gán tuyến không hỏi lại câu "chưa chắc" · ghi song song không hỏng JSON.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import loc_doi_thu as loc  # noqa: E402
from core import nghien_cuu_chung as ncc  # noqa: E402
from core import trang_chu as tc  # noqa: E402


def _kenh(goc, ma, nhom=""):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(d, "nghien-cuu"), exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ma: {0}\nngon_ngu: ja\n".format(ma) + ("nhom: {0}\n".format(nhom) if nhom else ""))


def _trang_chu(goc, ma, cac_ma):
    tc.luu(goc, ma, [{"Mã video": m} for m in cac_ma])


def test_duong_kho_co_va_khong_nhom(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "C")
    assert ncc.thu_muc(goc, "A").replace("\\", "/").endswith("CHANNEL/_NHOM/ng/nghien-cuu")
    assert ncc.thu_muc(goc, "C").replace("\\", "/").endswith("CHANNEL/C/nghien-cuu")


def _tra_dem(goi):
    def tra(ma, lang="", cancel=None):
        goi.append(ma)
        return {"tieu_de": "心理 " + ma, "ten_kenh": "K", "link_kenh": "https://www.youtube.com/@k"}
    return tra


def test_kenh_thu_hai_trong_nhom_khong_tra_lai(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "B", "ng")
    for k in ("A", "B"):
        _trang_chu(goc, k, ["aaaaaaaaaaa", "bbbbbbbbbbb"])
    goi = []
    tc.hoan_thien(goc, "A", tra=_tra_dem(goi))
    assert sorted(goi) == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    goi2 = []
    dem = tc.hoan_thien(goc, "B", tra=_tra_dem(goi2))
    assert goi2 == [] and dem["da_tra"] == 0
    assert os.path.isfile(os.path.join(ncc.thu_muc(goc, "A"), "trang-chu-tra.json"))


def test_lan_dau_gop_bo_nho_rieng_cua_thanh_vien(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "B", "ng")
    with open(os.path.join(goc, "CHANNEL", "A", "nghien-cuu", "trang-chu-tra.json"), "w", encoding="utf-8") as t:
        json.dump({"aaaaaaaaaaa": {"tieu_de": "x"}}, t)
    with open(os.path.join(goc, "CHANNEL", "B", "nghien-cuu", "trang-chu-tra.json"), "w", encoding="utf-8") as t:
        json.dump({"bbbbbbbbbbb": {"tieu_de": "y"}}, t)
    assert set(ncc.doc_tra(goc, "B")) == {"aaaaaaaaaaa", "bbbbbbbbbbb"}


def test_kenh_khong_nhom_giu_duong_cu(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "C")
    _trang_chu(goc, "C", ["aaaaaaaaaaa"])
    tc.hoan_thien(goc, "C", tra=_tra_dem([]))
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "C", "nghien-cuu", "trang-chu-tra.json"))
    assert not os.path.isdir(os.path.join(goc, "CHANNEL", "_NHOM"))


def test_ai_luong_lu_khong_hoi_lai_va_dem_khong_am(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "B", "ng")
    # 3 dòng cùng một tiêu đề lưỡng lự (không từ khoá mạnh) — bản cũ ra "lưỡng lự -2"
    tra = lambda ma, lang="", cancel=None: {"tieu_de": "今日の話", "ten_kenh": "K",  # noqa: E731
                                           "link_kenh": "https://www.youtube.com/@k"}
    for k in ("A", "B"):
        _trang_chu(goc, k, ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"])
    hoi = []

    def goi_ai(tds):
        hoi.append(list(tds))
        return {t: "dung" for t in tds}
    dem = tc.hoan_thien(goc, "A", tra=tra, goi_ai=goi_ai, nho_ai=True)
    assert hoi == [["今日の話"]] and dem["lung"] == 0 and dem["tam_ly"] == 3
    dem_b = tc.hoan_thien(goc, "B", tra=tra, goi_ai=goi_ai, nho_ai=True)
    assert len(hoi) == 1, "kênh B cùng nhóm hỏi lại AI đúng tiêu đề A vừa hỏi"
    assert dem_b["tam_ly"] == 3


class _Kenh:
    def __init__(self, link):
        from core.youtube import Channel, Video
        self.ch = Channel(input_url=link, name="心理の部屋", channel_url=link, subscribers=1000,
                          videos=[Video(video_id="v%02d" % i, title="心理 %d" % i, views=5000,
                                        duration_s=600) for i in range(5)])


def test_so_do_kenh_dung_chung_trong_nhom(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "B", "ng")
    goi = []

    def lay(link, max_videos=0, lang="", cancel=None):
        goi.append(link)
        return _Kenh(link).ch
    ch1 = ncc.lay_kenh_co_dem(goc, "A", lay)("https://www.youtube.com/@x", max_videos=40, lang="ja")
    ch2 = ncc.lay_kenh_co_dem(goc, "B", lay)("https://www.youtube.com/@x", max_videos=40, lang="ja")
    assert goi == ["https://www.youtube.com/@x"]
    assert ch2.name == ch1.name and len(ch2.videos) == 5 and ch2.videos[0].views == 5000


def test_phan_quyet_ai_kenh_dung_chung(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "B", "ng")
    goi = []

    def hoi(client, so_do, **k):
        goi.append(so_do.link)
        return loc.DanhGia(ket="khong", diem=10, ly_do="không tâm lý")
    so_do = loc.SoDo(ten="x", link="https://www.youtube.com/@x")
    a = ncc.hoi_ai_co_dem(goc, "A", hoi)(object(), so_do, mo_ta_kenh="")
    b = ncc.hoi_ai_co_dem(goc, "B", hoi)(object(), so_do, mo_ta_kenh="")
    assert len(goi) == 1 and a.ket == b.ket == "khong"
    # câu trả lời không đọc được → không nhớ
    so_do2 = loc.SoDo(ten="y", link="https://www.youtube.com/@y")
    hong = lambda c, s, **k: loc.DanhGia(ly_do="AI trả lời không đọc được")  # noqa: E731
    ncc.hoi_ai_co_dem(goc, "A", hong)(object(), so_do2)
    assert "https://www.youtube.com/@y" not in ncc.doc_json(os.path.join(ncc.thu_muc(goc, "A"), "kenh-ai.json"))


def test_nhan_tuyen_nho_ca_cau_chua_chac(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    ncc.nhan_tuyen_ghi(goc, "A", {"https://youtu.be/1": {"ma": "t1", "do_tin": 30, "ngay": "2000-01-01"},
                                  "https://youtu.be/2": {"ma": "t1", "do_tin": 30, "ngay": ncc._hom_nay()}})
    con = ncc.nhan_tuyen_doc(goc, "A")
    assert list(con) == ["https://youtu.be/2"], "câu quá hạn 14 ngày phải được hỏi lại"


_CON = r"""
import sys, os
sys.path.insert(0, sys.argv[1])
import core
core.__path__.insert(0, sys.argv[2])
from core import nghien_cuu_chung as ncc
for i in range(40):
    ncc.ghi_json_gop(sys.argv[3], {"%s%d" % (sys.argv[4], i): i})
"""


def test_hai_tien_trinh_ghi_cung_luc_khong_hong_json(tmp_path):
    import subprocess
    duong = str(tmp_path / "kho" / "x.json")
    os.makedirs(os.path.dirname(duong))
    goc_ma = os.path.dirname(os.path.dirname(os.path.abspath(loc.__file__)))
    thu_muc_ncc = os.path.dirname(os.path.abspath(ncc.__file__))
    tien = [subprocess.Popen([sys.executable, "-c", _CON, goc_ma, thu_muc_ncc, duong, tt])
            for tt in ("a", "b")]
    assert [p.wait(120) for p in tien] == [0, 0]
    du = ncc.doc_json(duong)
    assert isinstance(du, dict) and len(du) == 80
    assert not [t for t in os.listdir(os.path.dirname(duong)) if t.endswith((".tmp", ".khoa"))]

def test_quet_content_dung_lai_anh_chup_kenh_cua_nhom(tmp_path, monkeypatch):
    from core import youtube
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    _kenh(goc, "B", "ng")
    goi = []

    def fetch(link, max_videos=0, cancel=None, source="", lang=""):
        goi.append(link)
        ch = _Kenh(link).ch
        ch.channel_id = "UC" + str(len(goi))
        for v in ch.videos:
            v.url = "https://www.youtube.com/watch?v=" + v.video_id
        return ch
    monkeypatch.setattr(youtube, "fetch_channel", fetch)
    links = "https://www.youtube.com/@x\nhttps://www.youtube.com/@y"
    k1 = ncc.lay_du_lieu_co_dem(goc, "A")(links, so_video=60, mo_rong=False, chi_tiet=False, lang="ja")
    log = []
    k2 = ncc.lay_du_lieu_co_dem(goc, "B")(links, so_video=60, mo_rong=False, chi_tiet=False, lang="ja",
                                         on_log=log.append)
    assert len(goi) == 2, "kênh B quét lại đối thủ A vừa quét"
    assert k1.so_kenh == k2.so_kenh == 2 and len(k2.bang_video()) == len(k1.bang_video()) > 0
    assert any("dùng lại 2 kênh" in d for d in log)


def test_gan_tuyen_khong_hoi_lai_cau_chua_chac(tmp_path):
    from core import doi_thu_kenh as so
    from core import mot_nut
    from core import phan_tuyen as pt
    from core import tuyen_noi_dung as tn
    goc = str(tmp_path)
    _kenh(goc, "A", "ng")
    cot, _h = tn.doc(goc, "A")
    o = {c: i for i, c in enumerate(cot)}
    d1 = [""] * len(cot)
    d1[o["Mã"]], d1[o["Tên tuyến"]], d1[o["Trạng thái"]] = "t1", "T1", "đang đánh"
    tn.luu(goc, "A", cot, [d1])
    cot, _h = so.doc_bang(goc, "A")
    oc = {c: i for i, c in enumerate(cot)}
    hang = []
    for i, td in enumerate(("chắc", "không chắc")):
        d = [""] * len(cot)
        d[oc["Tiêu đề video"]], d[oc["Link video"]] = td, "https://youtu.be/%011d" % i
        hang.append(d)
    so.luu_bang(goc, "A", cot, hang)
    gui = []

    def gan(client, tieu_de, tuyen_co, **kw):
        gui.extend(tieu_de)
        return [pt.KetGan(ma="t1", do_tin=95 if t == "chắc" else 30) for t in tieu_de]
    d1_ = mot_nut.gan_tuyen_ai(goc, "A", object(), gan=gan, nho=True)
    assert sorted(gui) == ["chắc", "không chắc"] and d1_["ghi"] == 1
    gui.clear()
    d2_ = mot_nut.gan_tuyen_ai(goc, "A", object(), gan=gan, nho=True)
    assert gui == [] and d2_["da_hoi_bo_qua"] == 1
