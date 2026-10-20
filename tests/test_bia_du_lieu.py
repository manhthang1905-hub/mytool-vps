"""BÌA THEO DỮ LIỆU (20/10/2026, `core/bia_du_lieu.py` + kỹ năng D21): bộ bìa thắng tự dựng từ bảng Studio (không lọc
kiểu), nhãn họ kiểu chữ (AI giả), họ của lô chọn theo CTR (Thompson, ghim, ép khám phá), vòng phản hồi CTR + báo
động, `bia_lo.ho_so_kieu` dùng họ dữ liệu (ảnh tham chiếu cùng họ, dải sau mọi dòng cho họ "dai"). Ảnh PIL tổng hợp,
mã video giả."""

from __future__ import annotations

import datetime as _dt
import io
import json
import os

from PIL import Image

from core import bia_du_lieu as bd
from core import bia_lo
from core.kenh import TEP_KENH, duong_kenh

BAY = _dt.datetime(2026, 10, 20, 12, 0)
#: (mã giả, ngày, tuổi giờ, hiển thị, CTR %, màu ảnh, họ AI trả)
VIDEO = [("AAAAAAAAAA1", "2026-10-01", 400, 170000, 7.4, (230, 220, 200), "dai"),
         ("AAAAAAAAAA2", "2026-10-02", 380, 160000, 6.9, (30, 60, 40), "dai"),
         ("AAAAAAAAAA3", "2026-10-03", 360, 70000, 5.1, (200, 180, 160), "tran"),
         ("AAAAAAAAAA4", "2026-10-04", 340, 30000, 8.3, (210, 190, 170), "tran"),
         ("AAAAAAAAAA5", "2026-10-05", 320, 20000, 3.0, (190, 170, 150), "tran"),
         ("AAAAAAAAAA6", "2026-10-06", 300, 2500, 9.0, (180, 160, 140), "tran"),   # < 3.000 hiển thị: không thắng
         ("AAAAAAAAAA7", "2026-10-19", 30, 9000, 9.0, (170, 150, 130), "tran"),    # < 48 giờ
         ("AAAAAAAAAA8", "2026-10-07", 280, 5000, 2.0, (160, 140, 120), "hop")]
NHAN = {v[0]: v[6] for v in VIDEO}


def _goc(tmp_path, video=VIDEO, yaml='ma: "KH"\nbia_lo: true\nbia_lo_kieu: "tran"\nbia_lo_bo_cuc: "trai"\n') -> str:
    goc = str(tmp_path / "goc")
    dk = duong_kenh(goc, "KH")
    os.makedirs(os.path.join(dk, "chi-so"), exist_ok=True)
    with io.open(os.path.join(dk, TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write(yaml)
    with io.open(os.path.join(dk, "chi-so", "bang-tom-tat.csv"), "w", encoding="utf-8-sig") as tep:
        tep.write("Tiêu đề,Mã video,Ngày đăng,Mốc mới nhất,Lượt hiển thị,Tỷ lệ bấm\n")
        for v in video:
            tep.write("T{0},{0},{1},{2}h,{3},{4}%\n".format(v[0], v[1], v[2], v[3], v[4]))
    return goc


def _tai(video=VIDEO):
    mau = {v[0]: v[5] for v in video}

    def tai(url: str):
        vid = url.split("/vi/")[1].split("/")[0]
        b = io.BytesIO()
        Image.new("RGB", (640, 360), mau.get(vid, (100, 100, 100))).save(b, "JPEG")
        return b.getvalue()
    return tai


class Goi:
    """AI phân loại GIẢ: nhận diện ảnh theo màu điểm giữa → họ của video ấy."""

    def __init__(self, video=VIDEO):
        self.lan = 0
        self.mau = {tuple(v[5]): v[6] for v in video}

    def __call__(self, loi_nhac, **kw):
        import base64
        self.lan += 1
        ra = []
        for i, a in enumerate(kw["anh"], 1):
            im = Image.open(io.BytesIO(base64.b64decode(a.split(",", 1)[1]))).convert("RGB")
            px = im.getpixel((im.width // 2, im.height // 2))
            k = min(self.mau, key=lambda m: sum(abs(x - y) for x, y in zip(m, px)))
            ra.append({"so": i, "kieu": self.mau[k], "nen": "toi" if sum(px) < 300 else "sang",
                       "mau_dai": "green" if self.mau[k] == "dai" else "none", "ta_nen": "NEN-" + self.mau[k]})
        return json.dumps({"bia": ra})


def test_chon_thang_theo_luot_bam_khong_loc_kieu():
    rows = [{"video_id": v[0], "ngay": v[1], "tuoi": v[2], "imp": v[3], "ctr": v[4]} for v in VIDEO]
    chon, tv = bd.chon_thang(rows)
    # đủ chín (≥48h, ≥1k): 1,2,3,4,5,6,8 → trung vị CTR 6.9; thắng: ≥3k và CTR ≥ 6.9 → 1, 2, 4 (đủ tối thiểu 3)
    assert tv == 6.9 and [r["video_id"] for r in chon] == ["AAAAAAAAAA1", "AAAAAAAAAA2", "AAAAAAAAAA4"]
    # thiếu bìa trên trung vị → bù theo lượt bấm
    chon2, _tv = bd.chon_thang(rows[:1] + rows[2:5])
    assert len(chon2) == 3 and chon2[0]["video_id"] == "AAAAAAAAAA1"


def test_chay_that_dung_bo_thang_sao_luu_va_thong_ke(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    os.makedirs(tm)
    Image.new("RGB", (1280, 720), (1, 2, 3)).save(os.path.join(tm, "1.jpg"))
    for t in bd.TEP_DEM_BO:
        bd._ghi_json(os.path.join(tm, t), {"cu": 1})  # noqa: SLF001
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), {"bia": [{"tep": "1.jpg", "video_id": "AAAAAAAAAA9"}]})  # noqa: SLF001
    bd._ghi_json(os.path.join(tm, bd.TEP_BO_CUC_THANG), {"khoa": "k", "bia": [{"tep": "1.jpg", "so_dong": 3}]})  # noqa: SLF001
    goi = Goi()
    # thử: không ghi gì ngoài thư mục tạm
    tam = str(tmp_path / "tam")
    bc = bd.chay_kenh(goc, "KH", thu=True, goi=goi, tai_anh=_tai(), tam=tam, log=lambda s: None, bay=BAY)
    assert [b["kieu"] for b in bc["thang"]] == ["dai", "dai", "tran"] and bc["nguon_thang"] == "rieng"
    assert not bd.doc_thong_ke(goc, "KH") and not os.path.exists(os.path.join(goc, bd.TEP_PHAN_LOAI))
    assert bia_lo._doc_json(os.path.join(tm, bd.TEP_DS_THANG))["bia"][0]["video_id"] == "AAAAAAAAAA9", \
        "chạy thử: thư mục sống không đổi"  # noqa: SLF001
    # thật
    bc = bd.chay_kenh(goc, "KH", goi=goi, tai_anh=_tai(), log=lambda s: None, bay=BAY)
    assert bc["ghi_thu_muc"] == "doi"
    du = bia_lo._doc_json(os.path.join(tm, bd.TEP_DS_THANG))  # noqa: SLF001
    assert [b["video_id"] for b in du["bia"]] == ["AAAAAAAAAA1", "AAAAAAAAAA2", "AAAAAAAAAA4"]
    assert [b["kieu"] for b in du["bia"]] == ["dai", "dai", "tran"] and du["bia"][0]["ta_nen"] == "NEN-dai"
    assert all(os.path.isfile(os.path.join(tm, b["tep"])) for b in du["bia"]) and not os.path.exists(
        os.path.join(tm, "1.jpg"))
    assert not any(os.path.exists(os.path.join(tm, t)) for t in bd.TEP_DEM_BO), "tệp đệm của bộ cũ bỏ đi"
    sl = os.path.join(os.path.dirname(tm), "thang-sao-luu")
    assert os.path.isfile(os.path.join(sl, os.listdir(sl)[0], "1.jpg")), "bộ cũ sao lưu, không xoá lịch sử"
    bcu = bia_lo._doc_json(os.path.join(tm, bd.TEP_BO_CUC_THANG))  # noqa: SLF001
    assert bcu["bia"][0]["sha1"] and bcu["khoa"].startswith("cu:"), "số đo cũ giữ theo sha1, khoá cũ hết hạn"
    tk = bd.doc_thong_ke(goc, "KH")
    assert tk["ho"]["dai"]["n"] == 2 and tk["ho"]["tran"]["n"] == 4 and tk["ho"]["hop"]["n"] == 1, \
        "video ≥ 48h, ≥ 1k hiển thị (kể cả không thắng) vào thống kê họ"
    assert tk["ho"]["dai"]["ctr"] > tk["ho"]["tran"]["ctr"]
    # lần hai cùng dữ liệu: bộ y nguyên, không gọi AI (cache sha1)
    n = goi.lan
    bc2 = bd.chay_kenh(goc, "KH", goi=goi, tai_anh=_tai(), log=lambda s: None, bay=BAY)
    assert bc2["ghi_thu_muc"] in ("giu", "cap-nhat") and goi.lan == n
    assert bd.can_chay(goc, "KH")[0] is False, "đã dựng theo bảng hiện tại → kỹ năng xong"


def test_kenh_chua_du_du_lieu_giu_bo_muon(tmp_path):
    goc = _goc(tmp_path, video=VIDEO[5:7])
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    os.makedirs(tm)
    Image.new("RGB", (1280, 720), (230, 220, 200)).save(os.path.join(tm, "1.jpg"))
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), {"bia": [{"tep": "1.jpg", "video_id": "AAAAAAAAAA1"}]})  # noqa: SLF001
    bc = bd.chay_kenh(goc, "KH", goi=Goi(), tai_anh=_tai(), log=lambda s: None, bay=BAY)
    assert bc["nguon_thang"] == "giu-bo-dang-co" and "giữ bộ đang có" in bc["ghi_thu_muc"]
    du = bia_lo._doc_json(os.path.join(tm, bd.TEP_DS_THANG))  # noqa: SLF001
    assert du["bia"][0]["tep"] == "1.jpg" and du["bia"][0]["kieu"] == "dai", "ảnh giữ nguyên, chỉ gắn nhãn họ"


def _tk(goc, **ho):
    bd._ghi_json(bd.duong_thong_ke(goc, "KH"), {"trung_vi_ctr": 5.0, "do_lech_ctr": 1.0, "ho": {  # noqa: SLF001
        h: {"n": n, "ctr": c} for h, (n, c) in ho.items()}})


def test_chon_ho_thompson_ghim_so_cai_va_ep_kham_pha(tmp_path):
    goc = _goc(tmp_path)
    assert bd.chon_ho(goc, "KH", co=["tran", "dai"]) == {}, "chưa có thống kê → đường lùi cấu hình"
    _tk(goc, dai=(10, 8.0), tran=(10, 4.0))
    assert bd.chon_ho(goc, "KH", co=["tran", "dai"])["ho"] == "dai", "không lượt → họ tốt nhất"
    assert bd.chon_ho(goc, "KH", co=["tran"])["ho"] == "tran", "chỉ họ có ảnh tham chiếu"
    ds = [bd.chon_ho(goc, "KH", co=["tran", "dai"], luot="{0:04d}".format(i))["ho"] for i in range(200)]
    assert 0.8 < ds.count("dai") / 200.0 < 1.0, "phần lớn họ tốt nhất, vẫn thử họ khác"
    assert ds == [bd.chon_ho(goc, "KH", co=["tran", "dai"], luot="{0:04d}".format(i))["ho"] for i in range(200)], \
        "tất định theo lượt"
    # sổ: lượt đã chọn giữ đúng họ (hai lần gọi của một lượt)
    k = bd.chon_ho(goc, "KH", co=["tran", "dai"], luot="/x/PROJECTS/AUTO/KH/0042", ghi=True)
    _tk(goc, dai=(10, 1.0), tran=(10, 9.0))
    assert bd.chon_ho(goc, "KH", co=["tran", "dai"], luot="0042")["ho"] == k["ho"]
    # ép khám phá: một lượt, rồi về Thompson
    tk = bd.doc_thong_ke(goc, "KH")
    tk["ep_doi_kieu"] = {"tranh": "tran", "khoa": "x"}
    bd._ghi_json(bd.duong_thong_ke(goc, "KH"), tk)  # noqa: SLF001
    e = bd.chon_ho(goc, "KH", co=["tran", "dai"], luot="0050", ghi=True)
    assert e["ho"] == "dai" and e["cach"] == "kham-pha-ep"
    assert bd.chon_ho(goc, "KH", co=["tran", "dai"], luot="0051")["cach"] != "kham-pha-ep"
    # vài video ÍT hiển thị không lật kiểu chữ: số video tính theo hiển thị
    tk2 = {"trung_vi_ctr": 5.0, "do_lech_ctr": 1.0, "trung_vi_imp": 10000.0,
           "ho": {"hop": {"n": 4, "ctr": 8.0, "imp": 10000}, "tran": {"n": 4, "ctr": 8.0, "imp": 400000}}}
    hn = bd.hau_nghiem(tk2, ["hop", "tran"])
    assert hn["hop"][0] < hn["tran"][0] and hn["hop"][1] > hn["tran"][1]
    # chủ ghim
    assert bd.chon_ho(goc, "KH", co=["tran", "dai"], cai={"bia_lo_kieu": "hop", "bia_lo_kieu_ghim": True}) == {
        "ho": "hop", "cach": "ghim", "ly_do": "kenh.yaml ghim bia_lo_kieu"}


def test_phan_hoi_ctr_tuong_quan_va_bao_dong_mot_lan(tmp_path, monkeypatch):
    video = [("AAAAAAAAAA1", "2026-10-01", 400, 170000, 7.4, (230, 220, 200), "dai"),
             ("AAAAAAAAAA2", "2026-10-02", 380, 160000, 6.9, (30, 60, 40), "dai"),
             ("AAAAAAAAAA3", "2026-10-03", 360, 70000, 7.1, (200, 180, 160), "tran"),
             ("AAAAAAAAAB1", "2026-10-15", 120, 4000, 2.0, (150, 130, 110), "tran"),
             ("AAAAAAAAAB2", "2026-10-16", 100, 3000, 2.2, (140, 120, 100), "tran"),
             ("AAAAAAAAAB3", "2026-10-17", 60, 2500, 1.9, (130, 110, 90), "tran"),
             ("AAAAAAAAAB4", "2026-10-09", 260, 3000, 4.0, (120, 100, 80), "tran")]
    goc = _goc(tmp_path, video=video)
    hs = os.path.join(duong_kenh(goc, "KH"), "ho-so-video")
    os.makedirs(hs)
    for i, v in enumerate(("AAAAAAAAAB1", "AAAAAAAAAB2", "AAAAAAAAAB3", "AAAAAAAAAB4"), 1):
        bd._ghi_json(os.path.join(hs, "KH-{0:04d}.json".format(i)), {  # noqa: SLF001
            "luot": "{0:04d}".format(i), "video_id": v, "thumbnail": {"diem_giam_khao": 60 + i}})
        bd.ghi_so_cai(goc, "KH", "{0:04d}".format(i), {"ho": "tran", "cach": "thompson", "top": [
            {"ma": "y1", "tong": 70 + i, "diem": {"bam_nhu_thang": 6 + (i % 2)}}]})
    bao = []
    from core import bao_dong, nao_bo_phan
    monkeypatch.setattr(bao_dong, "bao_dong", lambda loai, tieu_de, chi_tiet="", **kw: bao.append((loai, tieu_de)))
    monkeypatch.setattr(nao_bo_phan, "ghi", lambda *a, **k: True)
    bc = bd.chay_kenh(goc, "KH", goi=Goi(video), tai_anh=_tai(video), log=lambda s: None, bay=BAY)
    kq = bd.doc_ket_qua(goc, "KH")
    assert {(x["video_id"], x["moc"]) for x in kq} == {("AAAAAAAAAB1", "48h"), ("AAAAAAAAAB2", "48h"),
                                                       ("AAAAAAAAAB3", "48h"), ("AAAAAAAAAB4", "7d")}
    assert all(x["kieu"] == "tran" and x["kieu_chon"] == "tran" and x["diem"] for x in kq)
    assert bc["tuong_quan"]["tong"]["n"] == 3
    assert bc["tut"] and bc["tut"]["tranh"] == "tran" and len(bao) == 1 and bao[0][0] == "bia_ctr_thap"
    tk = bd.doc_thong_ke(goc, "KH")
    assert tk["ep_doi_kieu"]["tranh"] == "tran"
    # chạy lại: không ghi trùng, không báo lại cùng bộ ba
    bd.chay_kenh(goc, "KH", goi=Goi(video), tai_anh=_tai(video), log=lambda s: None, bay=BAY)
    assert len(bd.doc_ket_qua(goc, "KH")) == 4 and len(bao) == 1
    assert bd.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0 and bd.spearman([1, 2, 3], [1, 2, 3]) is None


def test_ho_so_kieu_theo_du_lieu_anh_cung_ho_va_dai_moi_dong(tmp_path):
    goc = _goc(tmp_path)
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    os.makedirs(tm)
    bia = []
    for i, (k, m) in enumerate((("dai", (30, 60, 40)), ("tran", (230, 220, 200)), ("dai", (40, 40, 40)),
                                ("tran", (220, 200, 180))), 1):
        Image.new("RGB", (1280, 720), m).save(os.path.join(tm, "{0}.jpg".format(i)))
        bia.append({"tep": "{0}.jpg".format(i), "video_id": "AAAAAAAAA{0:02d}".format(i), "imp": 50000, "ctr": 6.0,
                    "kieu": k, "mau_dai": "green" if k == "dai" else "", "ta_nen": "NEN-" + k})
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), {"bia": bia})  # noqa: SLF001
    # chưa có dữ liệu → cấu hình "tran", bộ mẫu như cũ (không lọc)
    hs0 = bia_lo.ho_so_kieu(goc, "KH", log=lambda s: None)
    assert hs0["kieu"] == "tran" and hs0["ho_cach"] == "cau-hinh" and hs0["bia_mau"] == [
        os.path.join(tm, "1.jpg"), os.path.join(tm, "2.jpg")]
    _tk(goc, dai=(5, 8.0), tran=(10, 4.0))
    hs = bia_lo.ho_so_kieu(goc, "KH", log=lambda s: None)
    assert hs["ho"] == "dai" and hs["kieu"] == "tran" and hs["ho_cach"] == "tot-nhat"
    assert hs["bia_mau"] == [os.path.join(tm, "1.jpg"), os.path.join(tm, "3.jpg")], "ảnh tham chiếu CÙNG họ"
    assert hs["bia_so"][:2] == hs["bia_mau"] and len(hs["bia_so"]) == 3, "hàng so: cùng họ trước"
    assert hs["dai_moi_dong"] == bd.MAU_DAI["green"] and "NEN-dai" in hs["nen"]
    assert "band" in bia_lo.loi_theo_kieu(hs)["hinh"]
    tang = bia_lo.doc_chu_bia_tran("年金だけで悠々自適に暮らす人", hs, cach_ai=["年金だけで|[<悠々自適に>]|暮らす人"])
    assert tang and all(t.get("dai") == bd.MAU_DAI["green"] for t in tang), "họ dải: dải sau MỌI dòng"
    # kênh kiểu hộp: họ "dai" đi bộ vẽ hộp
    with io.open(os.path.join(duong_kenh(goc, "KH"), TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "KH"\nbia_lo: true\nbia_lo_kieu: "hop"\n')
    hs2 = bia_lo.ho_so_kieu(goc, "KH", log=lambda s: None)
    assert hs2["kieu"] == "hop" and hs2["ho"] == "dai"
    # chủ ghim kiểu → dữ liệu không đổi được
    with io.open(os.path.join(duong_kenh(goc, "KH"), TEP_KENH), "w", encoding="utf-8") as tep:
        tep.write('ma: "KH"\nbia_lo: true\nbia_lo_kieu: "tran"\nbia_lo_kieu_ghim: true\n')
    hs3 = bia_lo.ho_so_kieu(goc, "KH", log=lambda s: None)
    assert hs3["ho"] == "tran" and hs3["ho_cach"] == "ghim" and not hs3.get("dai_moi_dong")
    assert hs3["bia_mau"] == [os.path.join(tm, "2.jpg"), os.path.join(tm, "4.jpg")]


def test_van_tay_vang_khong_doi_khi_chi_so_lieu_doi(tmp_path):
    goc = _goc(tmp_path)
    tm = os.path.join(goc, bia_lo.ten_thu_muc_thang("KH"))
    os.makedirs(tm)
    Image.new("RGB", (1280, 720), (1, 2, 3)).save(os.path.join(tm, "1-A.jpg"))
    du = {"bia": [{"tep": "1-A.jpg", "video_id": "AAAAAAAAAA1", "imp": 1000, "ctr": 5.0, "kieu": "tran"}]}
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), du)  # noqa: SLF001
    vt = bia_lo.van_tay_vang(goc, "KH")
    du["bia"][0].update(imp=2000, ctr=4.0)
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), du)  # noqa: SLF001
    assert bia_lo.van_tay_vang(goc, "KH") == vt, "số liệu cập nhật hằng ngày không bắt kiểm vàng chạy lại"
    du["bia"][0]["kieu"] = "dai"
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), du)  # noqa: SLF001
    assert bia_lo.van_tay_vang(goc, "KH") != vt, "nhãn họ đổi = bộ mẫu đổi"


def test_bo_cuc_thang_theo_ho_va_dung_lai_so_do_theo_sha1(tmp_path):
    tm = str(tmp_path / "thang")
    os.makedirs(tm)
    for i, m in ((1, (200, 140, 80)), (2, (30, 60, 40))):
        Image.new("RGB", (1280, 720), m).save(os.path.join(tm, "{0}.jpg".format(i)))
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), {"bia": [  # noqa: SLF001
        {"tep": "1.jpg", "imp": 100000, "ctr": 7.0, "kieu": "tran"}, {"tep": "2.jpg", "imp": 90000, "ctr": 7.0,
                                                                      "kieu": "dai"}]})
    lan = []

    def goi(loi_nhac, **kw):
        lan.append(1)
        y1 = 0.3 if len(lan) == 1 else 0.5
        return json.dumps({"dong": [{"chu": "あいう", "x0": 0.02, "x1": 0.5, "y0": 0.1, "y1": y1, "mau": "white"},
                                    {"chu": "かき", "x0": 0.02, "x1": 0.4, "y0": 0.55, "y1": 0.8, "mau": "red"}],
                           "nhan_vat": {"x0": 0.6, "x1": 0.95, "y0": 0.1, "y1": 0.9}, "vien": "thick"})
    a = bia_lo.bo_cuc_thang("G", "KH", tm, goi=goi, log=lambda s: None, kieu="tran")
    b = bia_lo.bo_cuc_thang("G", "KH", tm, goi=goi, log=lambda s: None, kieu="dai")
    assert len(lan) == 2 and a["theo_ho"] == "tran" and b["theo_ho"] == "dai" and a["cao_chinh_pct"] != b["cao_chinh_pct"]
    # bộ đổi (tên tệp mới, cùng ảnh) → số đo dùng lại theo sha1, không gọi AI
    os.rename(os.path.join(tm, "2.jpg"), os.path.join(tm, "1-X.jpg"))
    os.rename(os.path.join(tm, "1.jpg"), os.path.join(tm, "2-Y.jpg"))
    bd._ghi_json(os.path.join(tm, bd.TEP_DS_THANG), {"bia": [  # noqa: SLF001
        {"tep": "1-X.jpg", "imp": 90000, "ctr": 7.0, "kieu": "dai"}, {"tep": "2-Y.jpg", "imp": 100000, "ctr": 7.0,
                                                                       "kieu": "tran"}]})
    c = bia_lo.bo_cuc_thang("G", "KH", tm, goi=goi, log=lambda s: None, kieu="dai")
    assert len(lan) == 2 and c["cao_chinh_pct"] == b["cao_chinh_pct"]


def test_ky_nang_d21_khai_du(tmp_path):
    from core import ky_nang as kn
    from core import ky_nang_tu as knt
    k = kn.theo_ma("D21")
    assert k and k.tu_ap and not k.nang and k.mot_kenh and knt.BO_PHAN["D21"] == "bia"
    goc = _goc(tmp_path)
    assert k.dieu_kien(goc, "KH")[0] is True and k.kiem(goc, "KH")[0] == kn.THIEU
    assert k.chay(goc, "KH")[-3:] == ["chay", "--kenh", "KH"]


def test_ho_it_bang_chung_chi_vao_nhanh_kham_pha(tmp_path, monkeypatch):
    """Họ chỉ có vài video ít hiển thị: không vào Thompson — chỉ ε (~10%) số lượt."""
    from core import bia_du_lieu as bd
    tk = {"trung_vi_ctr": 4.6, "do_lech_ctr": 2.0, "trung_vi_imp": 10000.0,
          "ho": {"tran": {"n": 20, "imp": 300000, "ctr": 4.6}, "hop": {"n": 4, "imp": 8000, "ctr": 5.3}}}
    monkeypatch.setattr(bd, "doc_thong_ke", lambda g, k: tk)
    monkeypatch.setattr(bd, "doc_so_cai", lambda g, k: {})
    dem = sum(bd.chon_ho(str(tmp_path), "TLx-T7", co=["tran", "hop"], luot="%04d" % i, cai={})["ho"] == "hop"
              for i in range(400))
    assert dem < 400 * 0.2
