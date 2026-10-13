"""Radar đột biến thị trường (`core/radar_dot_bien.py`, 12/10/2026) + đường ép chọn / ghi công đi kèm.

Canh: mức đột biến · đường cong kỳ vọng của CHÍNH kênh khi đủ quan sát (không thì của ngách) · tính radar trên cây giả
(gấp × kỳ vọng ở tuổi thật, gán chủ vùng) · kênh không được phát không được gán · ép chọn: trần 1/kênh/ngày, không ép
nguồn kênh anh em đã làm, chạy thử không tạo hành động · `nao.ep_chon` dựng dòng radar khi sổ content chưa có + ghi
công H-RADAR qua `chia_khe.chot_nguon` · đặc trưng `radar_*` + giả thuyết H-RADAR · panel trực quan · nạp vào sổ
content kênh được gán · đệm ghi `kenh-do.json` dùng chung trong tiến trình. Mọi mã video / kênh / link là GIẢ.
"""

import datetime as _dt
import json
import os
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import nao  # noqa: E402
from core import nghien_cuu_chung as ncc  # noqa: E402
from core import radar_dot_bien as rd  # noqa: E402
from core.phong_thi_nghiem import chia_khe, dac_trung, gia_thuyet  # noqa: E402

NHOM = "ngach-gia"
KDT = "KenhDoiThuGia"
L_KDT = "https://www.youtube.com/@kenhdoithugia"
MA_NO = "vidRadarNo1"        # 11 ký tự, giả


def _kenh(goc, ma, nhom=NHOM, them=""):
    d = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(d, "nghien-cuu"), exist_ok=True)
    with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
        t.write("ma: {0}\nngon_ngu: ja\ntu_chay: true\n".format(ma) + ("nhom: {0}\n".format(nhom) if nhom else "") + them)


def _ngay(cach):
    return (_dt.date.today() - _dt.timedelta(days=cach)).isoformat()


def _content(goc, ma, dong):
    cot = so.cot_mac_dinh()
    hang = [[str(d.get(c, "")) for c in cot] for d in dong]
    so.luu_bang(goc, ma, cot, hang)


def _video(ma_v, view, cach, tuyen="", td=None):
    return {"Kênh": KDT, "Tiêu đề video": td or "心理 " + ma_v, "Link video": "https://www.youtube.com/watch?v=" + ma_v,
            "Ngày đăng": _ngay(cach), "Thời lượng": "15:00", "View": str(view), "Tuyến / Kênh": tuyen}


def _cay_radar(goc, *, chu_vung="B"):
    """Nhóm A, B; kênh đối thủ giả có 10 video cũ ~100 view và MỘT video 2 ngày tuổi 6.000 view (nổ)."""
    _kenh(goc, "A")
    _kenh(goc, "B")
    luc = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - 3600))
    for m in ("A", "B"):
        db.luu(goc, m, list(db.COT), [[{"Kênh": KDT, "Link kênh": L_KDT, "Trạng thái": db.THEO_DOI,
                                        "Ghi chú": "✓ AI kiểm ngách 11/10: đúng ngách", "Quét lúc": luc,
                                        "Subs": "300"}.get(c, "") for c in db.COT]])
    cu = [_video("vidRadarC{0:02d}".format(i), 100 + i, 20 + i) for i in range(10)]
    _content(goc, "A", cu + [_video(MA_NO, 8000, 2, tuyen="tep-b")])
    vung_ai = {"video": {"https://www.youtube.com/watch?v=" + MA_NO: "v-thu"}, "vung_moi": {"v-thu": "Vùng thử"}}
    d = os.path.join(goc, "workspace", "chien-truong")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "vung-ai.json"), "w", encoding="utf-8") as t:
        json.dump(vung_ai, t)
    with open(os.path.join(d, "chu-quyen-vung.json"), "w", encoding="utf-8") as t:
        json.dump({"phien_ban": 1, "vung": {"v-thu": {"chu": chu_vung, "nguon": "tu_dong"}}}, t)


def test_muc_dot_bien():
    assert [rd.muc_cua(x) for x in (None, 1.0, 3.0, 7.9, 8.0, 19.9, 20.0)] == [0, 0, 1, 1, 2, 2, 3]


def test_duong_cong_rieng_cua_kenh_khi_du_quan_sat():
    t0 = _dt.datetime(2026, 10, 1, 12, 0, tzinfo=_dt.timezone.utc).timestamp()
    qs = {"vidCurve{0:03d}".format(i): {"k": "K1", "d": "2026-10-01", "o": [[t0 + 48 * 3600, 100.0]]}
          for i in range(6)}
    duong = rd.dung_duong_cong(qs, {"K1": 200.0}, n_rieng=5)
    kv, nguon = rd.ky_vong_tai(duong, "K1", 200.0, 48.0)
    assert abs(kv - 100.0) < 1.0 and nguon.startswith("kênh")
    kv2, nguon2 = rd.ky_vong_tai(duong, "K-khac", 200.0, 48.0)
    assert nguon2 == "ngách" and abs(kv2 - 200.0 * rd.DUONG_DU_PHONG[3]) < 1.0   # ngách thiếu số → dự phòng


def test_tinh_radar_tren_cay_gia_gan_chu_vung(tmp_path):
    goc = str(tmp_path)
    _cay_radar(goc)
    kq = rd.tinh(goc, NHOM)
    assert kq["dong"], kq["thong_ke"]
    d = kq["dong"][0]
    assert d["ma"] == MA_NO and d["muc"] == 3 and d["boi"] >= 20
    assert 30 <= d["tuoi_gio"] <= 62 and d["nen"] == pytest.approx(104.5, abs=1)
    assert d["vung"] == "v-thu" and d["gan"] == "B" and "chủ vùng" in d["ly_do_gan"] and d["hop_tep"]
    assert all(x["ma"].startswith("vidRadarC") is False for x in kq["dong"])     # video cũ thường không lên radar


def test_kenh_khong_duoc_phat_khong_duoc_gan(tmp_path):
    goc = str(tmp_path)
    _cay_radar(goc)
    d = {"ma": MA_NO, "vung": "v-thu", "ten_vung": "Vùng thử", "co_o": {"A": {"tuyen": "tep-b"}}, "trang_chu": [],
         "pool": []}
    ban_do = {"vung": {"v-thu": {"chu": "B"}}}
    rd._gan(d, ban_do, {"A": (True, ""), "B": (False, "không được YouTube phát")}, {"A": ["tep-a"], "B": ["tep-b"]},
            {}, {}, {})
    assert d["gan"] != "B" and "không được YouTube phát" in d["ly_do_gan"]


def test_gan_theo_nhan_tuyen_bo_phieu(tmp_path):
    d = {"ma": MA_NO, "vung": "", "co_o": {"A": {"tuyen": "tep-b"}, "B": {"tuyen": "tep-b"}}, "trang_chu": [], "pool": []}
    rd._gan(d, {}, {"A": (True, ""), "B": (True, "")}, {"A": ["tep-a"], "B": ["tep-b"]}, {}, {}, {})
    assert d["gan"] == "B" and d["hop_tep"] and "2/2" in d["ly_do_gan"]


def _dong(ma, boi, gan="B", **kw):
    d = {"ma": ma, "link": "https://www.youtube.com/watch?v=" + ma, "tieu_de": "心理 " + ma, "kenh_nguon": KDT,
         "view": 9000.0, "ky_vong": 9000.0 / boi, "ky_vong_nguon": "ngách", "nen": 200.0, "boi": boi,
         "muc": rd.muc_cua(boi), "ten_muc": "siêu nổ", "tuoi_gio": 50.0, "dai_phut": 15.0, "dung_ngach": True,
         "kenh_ngach": "giu", "gan": gan, "ly_do_gan": "chủ vùng “x”", "hop_tep": True, "da_lam_boi": "",
         "ngay_dang": _ngay(2), "cum": "v-thu", "vung": "v-thu", "toc_do": 180.0, "toc_do_gan": None,
         "trang_chu": [], "pool": []}
    d.update(kw)
    return d


def test_quyet_ep_tran_moi_kenh_ngay_va_khong_ep_nguon_da_lam(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    kq = {"nhom": NHOM, "song": {"A": {"tu_chay": True}, "B": {"tu_chay": True}},
          "dong": [_dong("vidRadarEp1", 50.0), _dong("vidRadarEp2", 40.0),
                   _dong("vidRadarEp3", 60.0, da_lam_boi="A", ly_do_gan="đã làm bởi A"),
                   _dong("vidRadarEp4", 5.0), _dong("vidRadarEp5", 30.0, gan="A", dai_phut=55.0)]}
    thu = rd.quyet_ep(goc, kq, ghi=False)
    assert [q["quyet"] for q in thu] == ["se_ep", "bo", "bo", "bo"]
    assert not nao.doc_hanh_dong(goc)                                  # chạy thử: không tạo gì
    ra = rd.quyet_ep(goc, kq, ghi=True)
    q = {x["ma"]: x for x in ra}
    assert q["vidRadarEp1"]["quyet"] == "ep_chon" and q["vidRadarEp1"]["hanh_dong"]
    assert "hôm nay" in q["vidRadarEp2"]["vi_sao"]
    assert "đã làm" in q["vidRadarEp3"]["vi_sao"]
    assert "ngoài khuôn" in q["vidRadarEp5"]["vi_sao"]
    assert "vidRadarEp4" not in q                                       # dưới ngưỡng ép: chỉ theo dõi
    hd = nao.doc_hanh_dong(goc)
    assert len(hd) == 1 and hd[0]["tu_dong"] == "radar" and hd[0]["ngoai_han_muc"]
    assert hd[0]["tham_so"]["radar_thi_truong"] == "vidRadarEp1" and hd[0]["tham_so"]["han_san_xuat"]
    log = os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "radar", rd.TEP_QUYET)
    assert len(open(log, encoding="utf-8").read().splitlines()) == 4
    # lượt sau cùng ngày: không ép thêm cho B
    ra2 = rd.quyet_ep(goc, {"nhom": NHOM, "song": kq["song"], "dong": [_dong("vidRadarEp6", 80.0)]}, ghi=True)
    assert ra2[0]["quyet"] == "bo" and "hôm nay" in ra2[0]["vi_sao"]


def test_ep_chon_ton_trong_san_nguon_v7_cua_kenh_duoc_gan(tmp_path):
    from core import cong_thuc_v7 as v7
    goc = str(tmp_path)
    _kenh(goc, "B")
    with open(os.path.join(goc, "CHANNEL", "B", "nghien-cuu", v7.TEP_CAU_HINH), "w", encoding="utf-8") as t:
        json.dump({"phien_ban": v7.PHIEN_BAN_CAU_HINH,
                   "no": {"loai_kenh_yeu": True, "kenh_yeu_duoi": 1500, "san_view": 50000}}, t)
    kq = {"nhom": NHOM, "song": {"B": {"tu_chay": True}},
          "dong": [_dong("vidRadarV01", 50.0, nen=200.0), _dong("vidRadarV02", 30.0, nen=4000.0, view=9000.0),
                   _dong("vidRadarV03", 30.0, nen=4000.0, view=40000.0)]}
    q = {x["ma"]: x for x in rd.quyet_ep(goc, kq, ghi=False)}
    assert "kênh nguồn yếu" in q["vidRadarV01"]["vi_sao"]
    assert "sàn V7" in q["vidRadarV02"]["vi_sao"]
    assert q["vidRadarV03"]["quyet"] == "se_ep"


def test_tao_ep_chon_radar_kiem_bang_ma(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "B")
    _kenh(goc, "C")
    hd = nao.tao_ep_chon_radar(goc, "B", "https://www.youtube.com/watch?v=vidRadarM01", "vidRadarM01",
                               ly_do="RADAR: ×50 kỳ vọng", du_doan="video đạt phân vị ≥ 50")
    assert hd["tu_dong"] == "radar"
    with pytest.raises(nao.TuChoi):   # trùng link đang mở (kênh khác)
        nao.tao_ep_chon_radar(goc, "C", "https://www.youtube.com/watch?v=vidRadarM01", "vidRadarM01",
                              ly_do="RADAR: ×50 kỳ vọng", du_doan="video đạt phân vị ≥ 50")
    with pytest.raises(nao.TuChoi):   # trần 1/kênh/ngày
        nao.tao_ep_chon_radar(goc, "B", "https://www.youtube.com/watch?v=vidRadarM02", "vidRadarM02",
                              ly_do="RADAR: ×50 kỳ vọng", du_doan="video đạt phân vị ≥ 50")
    with pytest.raises(nao.TuChoi):
        nao.tao_ep_chon_radar(goc, "KHONG-CO", "https://www.youtube.com/watch?v=vidRadarM03", "vidRadarM03",
                              ly_do="RADAR: ×50 kỳ vọng", du_doan="video đạt phân vị ≥ 50")
    ds = nao.doc_hanh_dong(goc)
    ds[0]["cham"] = "sai"
    assert nao.ti_le_dung(ds) == (0, 0)                                  # đề cử máy tạo không vào tỉ lệ đúng của não


def test_ep_chon_dung_dong_radar_va_ghi_cong_h_radar(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "B")
    nao.tao_ep_chon_radar(goc, "B", "https://www.youtube.com/watch?v=vidRadarE01", "vidRadarE01",
                          ly_do="RADAR: ×50 kỳ vọng", du_doan="video đạt phân vị ≥ 50",
                          so_lieu={"boi": 50.0, "muc": 3, "tuoi_gio": 40.0, "view": 9000.0},
                          nguon_dong={"ma": "vidRadarE01", "link": "https://www.youtube.com/watch?v=vidRadarE01",
                                      "tieu_de": "心理 E01", "kenh": KDT, "view": 9000.0, "dai_giay": 900})
    ghi = []
    nc = types.SimpleNamespace(goc=goc, ma_kenh="B", ghi=ghi.append, loc=lambda x: x, loai_tru=set(),
                               _kq_v7=types.SimpleNamespace(ung_vien=[], bi_loai=[]))
    ds = nao.ep_chon(nc, [])
    assert len(ds) == 1, ghi
    u = ds[0]
    assert u["ep_chon"] and u["ma"] == "vidRadarE01" and u["gia_thuyet_radar"] == "H-RADAR"
    assert u["radar_thi_truong"]["boi"] == 50.0
    nguon = dict(u, gia_thuyet="H-V7", gia_thuyet_khe="H-V7", ptn={"pb": 1})
    chia_khe.chot_nguon(nguon)
    assert nguon["gia_thuyet"] == "H-RADAR" and nguon["gia_thuyet_bo"] == "H-V7"
    assert nguon["ptn"]["ghi_cong"] == "radar thị trường" and nguon["ptn_pb"] is None
    # nguồn bộ não ép chọn THƯỜNG vẫn không được ghi công (luật cũ)
    thuong = {"gia_thuyet": "H-V7", "gia_thuyet_khe": "H-V7", "ep_chon": True, "ptn": {"pb": 1}}
    chia_khe.chot_nguon(thuong)
    assert thuong["gia_thuyet"] == "" and thuong["gia_thuyet_bo"] == "H-V7"
    # ap_uu_tien cũng gắn ghi công cho dòng đã có trong bảng
    ra = nao.ap_uu_tien(goc, "B", [{"ma": "vidRadarE01", "link": "https://www.youtube.com/watch?v=vidRadarE01",
                                    "diem": 1.0}])
    assert ra[0]["ep_chon"] and ra[0]["gia_thuyet_radar"] == "H-RADAR"


def test_dac_trung_radar_va_gia_thuyet_h_radar():
    gt = next(g for g in gia_thuyet.HAT_GIONG if g["id"] == "H-RADAR")
    assert gt["trang_thai"] == gia_thuyet.BONG and not gia_thuyet.kiem_tham_so(gt["tham_so"])
    kho = [dac_trung.mo_rong({"ma": "vidRadarK01", "radar_boi": 40.0, "radar_muc": 3.0, "radar_cua_minh": 1.0,
                              "radar_tuoi_gio": 50.0, "dai_phut": 15.0, "view": 9000.0, "nguon": "doi_thu"}),
           dac_trung.mo_rong({"ma": "vidRadarK02", "radar_boi": 90.0, "radar_muc": 3.0, "radar_cua_minh": 0.0,
                              "radar_tuoi_gio": 50.0, "dai_phut": 15.0, "view": 9000.0, "nguon": "doi_thu"}),
           dac_trung.mo_rong({"ma": "vidRadarK03", "radar_boi": None, "radar_muc": 0.0, "radar_cua_minh": 0.0,
                              "nguon": "doi_thu"})]
    top, n = gia_thuyet.xep_hang(dict(gt, phien_ban=1), kho, 10)
    assert n == 1 and top[0][0]["ma"] == "vidRadarK01"
    assert {"radar_boi", "radar_muc", "radar_cua_minh", "radar_tuoi_gio"} <= set(dac_trung.COT_KHO)


def test_truc_quan_va_dong_cho_nao(tmp_path):
    goc = str(tmp_path)
    _cay_radar(goc)
    kq = rd.chay(goc, NHOM, ghi=True, ep=True)
    assert os.path.isfile(os.path.join(goc, "CHANNEL", "_NHOM", NHOM, "radar", rd.TEP_MOI))
    du = rd.truc_quan(goc)
    n = du["nhom"][0]
    assert n["co"] and n["dong"][0]["ma"] == MA_NO
    assert n["dong"][0]["trang_thai"] == "ep_chon" and n["ep_hom_nay"] == 1, (kq["quyet_dinh"], n["dong"][0])
    dong = rd.dong_cho_nao(goc)
    assert any(MA_NO in x for x in dong)
    assert rd.dac_trung_cho_kenh(goc, "B")[MA_NO]["radar_cua_minh"] == 1.0
    assert rd.dac_trung_cho_kenh(goc, "A")[MA_NO]["radar_cua_minh"] == 0.0


def test_nap_vao_so_content_kenh_duoc_gan(tmp_path):
    goc = str(tmp_path)
    _cay_radar(goc)
    rd.chay(goc, NHOM, ghi=True, ep=False)
    assert rd.nap_vao_so(goc, "B") == 1
    cot, hang = so.doc_bang(goc, "B")
    o = {c: i for i, c in enumerate(cot)}
    h = next(h for h in hang if so.ma_video(h[o[so.COT_LINK]]) == MA_NO)
    assert h[o["View"]] == "8000" and h[o[so.COT_TUYEN]] == ""            # nhãn tuyến của A không chép sang
    assert rd.nap_vao_so(goc, "B") == 0


def test_tang_kenh_nguon_tren_radar_va_video_no_keo_tang_3_len_tang_2(tmp_path):
    """Tầng đối thủ (13/10/2026): dòng radar mang tầng kênh nguồn; video nổ của kênh tầng 3 KHÔNG bị bỏ và kéo kênh lên
    tầng 2 ngay lần gộp sổ chung cuối lượt radar; cắt bảng `so_dong` không bỏ video nổ nào."""
    from core import so_doi_thu_chung as sdc

    goc = str(tmp_path)
    _cay_radar(goc)
    cu = [_video("vidRadarC{0:02d}".format(i), 100 + i, 20 + i) for i in range(10)]
    _content(goc, "A", cu + [_video(MA_NO, 8000, 2, tuyen="tep-b"), _video("vidRadarNo2", 6000, 2)])
    du0 = sdc.gop(goc, NHOM)
    (k, e0), = du0["kenh"].items()
    assert e0["tang"] == "3", e0.get("tang_ly_do")
    kq = rd.tinh(goc, NHOM, ch=dict(rd.cau_hinh(goc), so_dong=1), ghi_quan_sat=False)
    assert len(kq["dong"]) == 2 and all(d["muc"] >= 2 and d["kenh_tang"] == "3" for d in kq["dong"])
    rd.chay(goc, NHOM, ghi=True, ep=False)
    e = sdc.doc(goc, NHOM)["kenh"][k]
    assert e["tang"] == "2" and e["dot_bien"]["muc"] == 3 and "radar" in e["tang_ly_do"], e.get("tang_ly_do")
    assert rd.truc_quan(goc)["nhom"][0]["so_doi_thu"]["tang"]["2"] == 1


def test_chay_neu_cu_hoan_trong_luot_nhom(tmp_path):
    goc = str(tmp_path)
    _cay_radar(goc)
    with rd.hoan():
        assert "bo_qua" in rd.chay_neu_cu(goc, "A")
    assert rd.chay_neu_cu(goc, "A").get("dong") is not None
    assert "bo_qua" in rd.chay_neu_cu(goc, "A")                           # vừa chạy < 2 giờ


def test_khong_nhom_khong_radar(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "C", nhom="")
    assert rd.chay_neu_cu(goc, "C") == {} and rd.dac_trung_cho_kenh(goc, "C") == {}


def test_kenh_do_dem_ghi_chung_trong_tien_trinh(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "A")
    _kenh(goc, "B")
    from core.youtube import Channel, Video
    goi = []

    def lay(link, max_videos=0, lang="", cancel=None):
        goi.append(link)
        return Channel(input_url=link, name="Gia", channel_url=link, subscribers=10,
                       videos=[Video(video_id="vidKenhDo01", title="x", views=10, duration_s=600)])
    ncc.lay_kenh_co_dem(goc, "A", lay)("https://www.youtube.com/@giado", max_videos=40, lang="ja")
    ncc.lay_kenh_co_dem(goc, "B", lay)("https://www.youtube.com/@giado", max_videos=40, lang="ja")
    assert goi == ["https://www.youtube.com/@giado"]
    p = os.path.join(ncc.thu_muc(goc, "A"), ncc.TEP_KENH_DO)
    ncc.xa_dem_kenh_do()
    du = json.load(open(p, encoding="utf-8"))
    assert "https://www.youtube.com/@giado|40|ja" in du
