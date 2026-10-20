"""HIỆU CHUẨN BỘ CHẤM (20/10/2026, `core/hieu_chuan.py` + kỹ năng D22): sổ cái điểm giám khảo LLM × kết quả thật →
trọng số; bộ chấm «không dự báo» chỉ còn phủ quyết ở nơi chọn (bìa lô, tiêu đề, hook); lần thử hook của bộ não được
VIẾT thật; bài học không giúp sau đủ mẫu thì nghỉ. Dữ liệu giả, không mạng, không LLM."""
from __future__ import annotations

import io
import json
import os

from core import hieu_chuan as hc


def _ghi(p, du):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as tep:
        if isinstance(du, str):
            tep.write(du)
        else:
            json.dump(du, tep, ensure_ascii=False)


def _kenh(goc, k):
    _ghi(os.path.join(goc, "CHANNEL", k, "kenh.yaml"), "ma: {0}\n".format(k))


def _bang(goc, k, dong):
    """dong: [(vid, imp, ctr, avd_pct)] — mọi video 100 giờ tuổi."""
    d = ["Tiêu đề,Mã video,Ngày đăng,Dài,Mốc mới nhất,Lượt hiển thị,Tỷ lệ bấm,Lượt xem,% độ dài"]
    d += ['"t{0}",{0},2026-10-01,10:00,100h,{1},{2}%,10,{3}%'.format(v, i, c, a) for v, i, c, a in dong]
    _ghi(os.path.join(goc, "CHANNEL", k, "chi-so", "bang-tom-tat.csv"), "\n".join(d) + "\n")


def _ho_so(goc, k, so, vid, *, diem_bia=None, diem_td=None, chon_td=0, ten_td=("đối chứng", "bản 2"), sua=None):
    ma = "{0}-{1:04d}".format(k, so)
    hs = {"ma_goi": ma, "kenh": k, "luot": "{0:04d}".format(so), "video_id": vid, "tao_luc": "2026-10-01T05:00:00"}
    if diem_bia is not None:
        hs["thumbnail"] = {"tep": "CHON-thumb_001.jpg", "kieu": "portrait_main", "diem_giam_khao": diem_bia}
    if diem_td is not None:
        hs["tieu_de_cham"] = {"chon": chon_td, "diem": diem_td, "ung_vien": [{"ten": t} for t in ten_td]}
    if sua:
        hs["lich_su_sua"] = sua
    _ghi(os.path.join(goc, "CHANNEL", k, "ho-so-video", ma + ".json"), hs)
    return ma


def _goc_12(tmp_path, nguoc=True, k="KA", n=12):
    """n video: điểm bìa tăng dần, CTR giảm dần (nguoc) hoặc tăng dần."""
    goc = str(tmp_path)
    _kenh(goc, k)
    dong = []
    for i in range(n):
        vid = "v{0}{1:02d}".format(k, i)
        ctr = (10 - 0.5 * i) if nguoc else (2 + 0.5 * i)
        dong.append((vid, 5000 + 100 * i, round(ctr, 2), 30))
        _ho_so(goc, k, i + 1, vid, diem_bia=50 + i)
    _bang(goc, k, dong)
    return goc


# ── thống kê + luật ─────────────────────────────────────────────────────────


def test_spearman_va_trong_so():
    assert hc.spearman([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) == 1.0
    assert hc.spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == -1.0
    assert hc.spearman([1, 2, 3], [1, 2, 3]) is None
    assert hc.spearman([1, 1, 1, 1], [1, 2, 3, 4]) is None
    # trọng số: cặp nặng kéo hạng về phía nó
    a, b = [1, 2, 3, 4, 5], [1, 2, 3, 5, 4]
    assert hc.spearman(a, b, [1, 1, 1, 100, 100]) < hc.spearman(a, b)


def test_luat_muc():
    assert hc._muc(0.1, 9) == ("chua_du", 1.0)  # noqa: SLF001
    assert hc._muc(0.1, 10) == ("khong_du_bao", hc.W_PHU_QUYET)  # noqa: SLF001
    assert hc._muc(0.45, 10) == ("du_bao", 1.0)  # noqa: SLF001
    muc, w = hc._muc(0.3, 12)  # noqa: SLF001
    assert muc == "yeu" and hc.W_PHU_QUYET < w < 1.0


# ── sổ cái + bù ─────────────────────────────────────────────────────────────


def test_gom_bu_tu_ho_so_khong_trung(tmp_path):
    goc = _goc_12(tmp_path, n=4)
    ma = _ho_so(goc, "KA", 9, "vKAx", diem_td={"A": 5, "B": 9}, chon_td=1)
    dong, n = hc.gom(goc, ["KA"])
    td = [d for d in dong if d["bo_cham"] == "tieu_de" and d["ma_goi"] == ma]
    assert {(d["ung_vien"], d["chon"]) for d in td} == {("A", False), ("B", True)}
    assert [d for d in td if d["chon"]][0]["phu"]["ten"] == "bản 2"
    assert n == 6 and len(hc.doc_so_cai(goc)) == 6
    assert hc.gom(goc, ["KA"])[1] == 0  # chạy lại: không phình


def test_ghi_thang_roi_bu_sua_duoc_chon(tmp_path):
    """Lô ghi tấm 1 là được chọn; cổng chữ đổi sang tấm 2 → hồ sơ video (thumb_002) sửa lại sổ."""
    goc = str(tmp_path)
    _kenh(goc, "KA")
    hc.ghi(goc, "bia_lo", "KA", "KA-0001", [{"id": "y1", "diem": 80, "chon": True}, {"id": "y2", "diem": 70, "chon": False}])
    _ghi(os.path.join(goc, "PROJECTS", "AUTO", "KA", "0001", "7-thumbnail", "_lo", "xep-hang.json"),
         {"top": [{"ma": "y1", "tong": 80, "diem": {"bam_nhu_thang": 8}}, {"ma": "y2", "tong": 70, "diem": {}}]})
    _ghi(os.path.join(goc, "CHANNEL", "KA", "ho-so-video", "KA-0001.json"),
         {"ma_goi": "KA-0001", "luot": "0001", "video_id": "v1", "thumbnail": {"tep": "CHON-thumb_002.jpg"}})
    hc.gom(goc, ["KA"])
    chon = {d["ung_vien"]: d["chon"] for d in hc.doc_so_cai(goc) if d["bo_cham"] == "bia_lo"}
    assert chon == {"y1": False, "y2": True}


# ── kết quả thật ────────────────────────────────────────────────────────────


def test_ket_qua_ctr_truoc_khi_sua(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "KA")
    _bang(goc, "KA", [("v1", 9000, 7.5, 30), ("v2", 500, 9.0, 30)])
    _ho_so(goc, "KA", 1, "v1", sua=[{"loai": "bia", "luc": "2026-10-05T10:00:00",
                                    "moc_truoc": {"impressions": 3000, "ctr": 3.1}}])
    _ho_so(goc, "KA", 2, "v2")
    kq = hc.ket_qua_kenh(goc, "KA", giu=False)
    assert kq["KA-0001"]["ctr"] == 3.1 and kq["KA-0001"]["ctr_nguon"] == "truoc-sua"
    assert "ctr" not in kq["KA-0002"]          # < 1.000 hiển thị
    assert kq["KA-0002"]["avd_pct"] == 30.0


# ── hiệu chuẩn + trọng số ───────────────────────────────────────────────────


def test_khong_du_bao_thi_chi_phu_quyet_va_kenh_it_mau_dung_so_gop(tmp_path):
    goc = _goc_12(tmp_path, nguoc=True)
    for i in range(4):  # kênh KB chỉ 4 video → dùng số gộp
        _kenh(goc, "KB")
        _ho_so(goc, "KB", i + 1, "vKB{0}".format(i), diem_bia=50 + i)
    _bang(goc, "KB", [("vKB{0}".format(i), 4000, 6 - i, 30) for i in range(4)])
    bc = hc.chay(goc, kenh_ds=["KA", "KB"])
    ka = bc["trong_so"]["kenh"]["KA"]["bia"]
    assert ka["muc"] == "khong_du_bao" and ka["w"] == hc.W_PHU_QUYET and ka["nguon"] == "kenh" and ka["rho"] < 0
    kb = bc["trong_so"]["kenh"]["KB"]["bia"]
    assert kb["nguon"] == "chung" and kb["muc"] == "khong_du_bao" and kb["n_kenh"] == 4
    assert hc.trong_so(goc, "KA", "bia")["w"] == hc.W_PHU_QUYET
    assert hc.trong_so(goc, "KA", "tieu_de")["muc"] == "mac_dinh"       # không có dữ liệu → hành vi cũ
    assert os.path.isfile(os.path.join(goc, "workspace", "hieu-chuan", bc["ngay"] + ".json"))
    assert "không dự báo" in bc["tom_tat"] and "bia KA-" not in bc["tom_tat"]
    assert any("Hiệu chuẩn bộ chấm" in d for d in hc.dong_bao_cao(goc))


def test_du_bao_thi_giu_quyen(tmp_path):
    goc = _goc_12(tmp_path, nguoc=False)
    bc = hc.chay(goc, kenh_ds=["KA"])
    assert bc["trong_so"]["kenh"]["KA"]["bia"]["muc"] == "du_bao"
    assert hc.trong_so(goc, "KA", "bia")["w"] == 1.0


def test_chay_thu_khong_ghi(tmp_path):
    goc = _goc_12(tmp_path)
    hc.chay(goc, thu=True, kenh_ds=["KA"])
    assert not os.path.exists(os.path.join(goc, "workspace", "hieu-chuan"))


def test_can_chay_moi_tuan(tmp_path):
    goc = _goc_12(tmp_path, n=2)
    assert hc.can_chay(goc)[0] is True
    _ghi(os.path.join(goc, "workspace", "hieu-chuan", "2026-10-18.json"), {})
    import datetime as _dt
    assert hc.can_chay(goc, _dt.datetime(2026, 10, 20))[0] is False
    assert hc.can_chay(goc, _dt.datetime(2026, 10, 25))[0] is True


# ── áp vào nơi chọn ─────────────────────────────────────────────────────────


def test_chon_tieu_de_phu_quyet_va_tien_nghiem():
    ten = ["đối chứng", "nắn khuôn", "bản 2"]
    diem = {"A": 6, "B": 9, "C": 2}
    assert hc.chon_tieu_de(ten, diem, 1, 1.0) == (1, {})               # đủ tin: giữ giám khảo
    tn = {"đối chứng": {"he": 1.0}, "nắn khuôn": {"he": 0.7}, "bản N": {"he": 0.9}}
    moi, ghi = hc.chon_tieu_de(ten, diem, 1, hc.W_PHU_QUYET, tien_nghiem=tn)
    assert moi == 0 and ghi["phu_quyet"] == ["C"] and ghi["chon_giam_khao"] == 1
    # không có tiên nghiệm: chỉ phủ quyết, thứ hạng giám khảo giữ
    assert hc.chon_tieu_de(ten, diem, 1, hc.W_PHU_QUYET)[0] == 1


def test_tien_nghiem_tieu_de_theo_ctr_that():
    dong = [{"bo_cham": "tieu_de", "chon": True, "kenh": "K", "ma_goi": "g{0}".format(i),
             "phu": {"ten": "nắn khuôn" if i < 12 else "đối chứng"}} for i in range(24)]
    kq = {"K": {"g{0}".format(i): {"ctr": 2.0 if i < 12 else 6.0} for i in range(24)}}
    tn = hc.tien_nghiem_tieu_de(dong, kq, {"K": {"ctr": 4.0}})
    assert tn["đối chứng"]["he"] == 1.0 and tn["nắn khuôn"]["he"] < tn["bản N"]["he"] < 1.0
    # ít mẫu (< 10 lần chọn một loại): trung tính — không đẩy tiêu đề nguồn nguyên văn lên vì vài video
    tn = hc.tien_nghiem_tieu_de(dong[8:16], kq, {"K": {"ctr": 4.0}})
    assert {x["he"] for x in tn.values()} == {1.0}


def test_xep_bia_nghieng_ve_tien_nghiem():
    ds = [{"ma": "a"}, {"ma": "b"}, {"ma": "c"}]
    tn = {"a": 0.1, "b": 0.5, "c": 0.9}
    assert [u["ma"] for u in hc.xep_bia(ds, 1.0, lambda u: tn[u["ma"]])] == ["a", "b", "c"]
    ra = hc.xep_bia(ds, hc.W_PHU_QUYET, lambda u: tn[u["ma"]])
    assert [u["ma"] for u in ra] == ["c", "b", "a"] and ra[0]["hieu_chuan"]["hang_giam_khao"] == 3


def test_tien_nghiem_mau():
    thang = [{"bao_hoa": 0.5, "tuong_phan": 0.2, "dai_sang": 0.6}, {"bao_hoa": 0.7, "tuong_phan": 0.3, "dai_sang": 0.8}]
    assert hc.tien_nghiem_mau({"bao_hoa": 0.9, "tuong_phan": 0.9, "dai_sang": 0.9}, thang) == 1.0
    assert hc.tien_nghiem_mau({"bao_hoa": 0.1, "tuong_phan": 0.1, "dai_sang": 0.1}, thang) == 0.0
    assert hc.tien_nghiem_mau(None, thang) is None


def test_kiem_san_phu_quyet():
    from core import bia_lo
    u = {"diem": {"bam_nhu_thang": 6}}
    assert bia_lo.kiem_san(u, {"bam": 7.0})                                    # sàn thường: dưới sàn
    assert bia_lo.kiem_san(u, {"bam": 7.0, "phu_quyet_bam": hc.SAN_BAM_PHU_QUYET}) == []
    assert bia_lo.kiem_san({"diem": {"bam_nhu_thang": 3}}, {"bam": 7.0, "phu_quyet_bam": hc.SAN_BAM_PHU_QUYET})
    assert bia_lo.kiem_san(dict(u, mau_duoi="màu nhạt"), {"bam": 7.0, "phu_quyet_bam": 4.0}) == ["màu nhạt"]


def test_bo_chon_mu_trong_so(monkeypatch):
    from core import tu_hoc
    monkeypatch.setattr(tu_hoc, "he_so_chon", lambda *a, **k: {"cau_hoi": 1.05, "ke_chuyen": 0.95})
    monkeypatch.setattr(tu_hoc, "gan_nhan", lambda truc, ban, kl=None: (["ke_chuyen", "cau_hoi"], [False, False]))
    sau, _g = tu_hoc.bo_chon("", "K", "hook", ["a", "b"], "h")
    assert sau(0, {"A": 9, "B": 8}, None) == 0                       # w = 1: điểm LLM thắng
    sau, ghi = tu_hoc.bo_chon("", "K", "hook", ["a", "b"], "h", trong_so_giam_khao=0.25)
    assert sau(0, {"A": 9, "B": 8}, None) == 1 and ghi["he_so"]["trong_so_giam_khao"] == 0.25


# ── hook: lần thử của bộ não được VIẾT thật ─────────────────────────────────

HOOK = "一人が楽だと感じていませんか。" + "周りは強い人だと言います。" * 5
HOOK_KE = "ある女性の話です。" + "彼女は毎晩、一人で静かにお茶を飲みました。" * 4
THAN = "一つ目は、予測できない愛情です。" + "子供のあなたは、テレビの音を小さくした。そして、足音を聞いた。" * 120
BAN = "夜の部屋に、小さな明かり。窓の外では、静かな雨の音。" * 4 + THAN


def test_thay_hook_viet_va_chon_ban_thu(monkeypatch, tmp_path):
    from core import nao, viet_nhieu_ban as vnb
    monkeypatch.setattr(nao, "thu_dang_mo", lambda g, k, t: {"id": "n039", "gia_tri": "ke_chuyen", "da_dung": 0,
                                                             "so_video": 2})
    goi, luu = [], {}

    def viet(loi_nhac, khoa_phu=""):
        goi.append(khoa_phu)
        return HOOK_KE if khoa_phu else HOOK

    def cham(_p):
        return json.dumps({"chon": "A", "diem": {"A": 9, "B": 6}, "ly_do": "A tốt hơn"})

    hoc = {"goc": str(tmp_path), "kenh": "TL1", "hat": "h"}
    moi, da_thay, _ = vnb.thay_hook(viet, cham, BAN, "goc", so_ban=1, khuon_viet="viết hook <<THAN_BAI>>",
                                    khuon_cham="chấm <<CAC_BAN>>", luu_ban=lambda i, c: luu.__setitem__(i, c), hoc=hoc)
    assert goi == ["", "thu-ke_chuyen"] and set(luu) == {0, 1}
    assert da_thay and moi.startswith("ある女性の話です。")
    assert hoc["ket"]["hook"] == "ke_chuyen" and hoc["ket"]["nhan_doan"] is False
    assert hoc["ket"]["thu_nghiem"]["id"] == "n039" and hoc["ket"]["thu_nghiem"]["ep"] is True
    assert hoc["ket"]["thu_nghiem"]["chon_cham"] == "A"


def test_thay_hook_khong_thu_thi_y_cu(monkeypatch, tmp_path):
    from core import nao, viet_nhieu_ban as vnb
    monkeypatch.setattr(nao, "thu_dang_mo", lambda g, k, t: None)
    goi = []

    def viet(loi_nhac, khoa_phu=""):
        goi.append(khoa_phu)
        return HOOK

    hoc = {"goc": str(tmp_path), "kenh": "TL1", "hat": "h"}
    vnb.thay_hook(viet, None, BAN, "goc", so_ban=1, khuon_viet="viết hook", hoc=hoc)
    assert goi == [""] and "thu_nghiem" not in (hoc.get("ket") or {})


# ── bài học có giúp không ───────────────────────────────────────────────────


def test_bai_hoc_uplift_va_nghi(tmp_path):
    from core.nao_bo_phan import _chung as C, kho, ngu as ngu_mod, no_ron
    from core import nao_bo_phan as nbp
    goc = str(tmp_path)
    _kenh(goc, "KA")
    nbp.ghi(goc, "kich-ban", "loi", kenh="KA", noi_dung="mở đầu dài quá 60 giây", khoa="e1")
    con = kho.mo(goc)
    try:
        sid = [r[0] for r in con.execute("SELECT id FROM su_kien")]
        bai: list = []
        ngu_mod.ap_lenh(con, C.duong_vault(goc), "kich-ban", [
            {"lenh": "them", "cau": "Mở đầu ngắn dưới 40 giây giữ người xem tốt hơn", "huong": "nen",
             "pham_vi": ["khau/kich-ban"], "vao_loi_nhac": True, "chi_goi_y": False, "bang_chung": sid}], bai, 0.0)
        ma_bai = "kich-ban/bai-hoc/" + bai[0]["id"]
        for i in range(16):  # 8 có bài (thắng 1), 8 đối chứng (thắng 4)
            ma = _ho_so(goc, "KA", i + 1, "v{0}".format(i))
            dc = int(i >= 8)
            con.execute("INSERT INTO dung(quyet_dinh, bo_phan, bai_hoc, doi_chung, luc) VALUES (?,?,?,?,?)",
                        (ma + ":kich_ban:2026-10-01", "kich-ban", "[]" if dc else json.dumps([ma_bai]), dc, 0.0))
        con.commit()
    finally:
        con.close()
    kq = {"KA": {"KA-{0:04d}".format(i + 1): {"thang": 1.0 if i in (0, 8, 9, 10, 11) else 0.0} for i in range(16)}}
    ub = hc.bai_hoc_uplift(goc, kq, ["KA"])
    o = ub["bo_phan"]["kich-ban"]
    assert (o["co_bai"]["n"], o["doi_chung"]["n"], o["uplift"]) == (8, 8, -0.375)
    assert ub["bai"][ma_bai]["ket_luan"] == "khong_giup" and ub["bai"][ma_bai]["tu_rut"]
    assert hc.nghi_bai_khong_giup(goc, ub) == [ma_bai]
    tt = {b["id"]: b["trang_thai"] for b in no_ron.doc_bai_ngu(C.duong_vault(goc), "kich-ban")}
    assert tt[bai[0]["id"]] == C.NGHI
    assert "hiệu chuẩn" in C.doc_chu(os.path.join(C.duong_vault(goc), "kich-ban", "nhat-ky.md"))
    assert hc.nghi_bai_khong_giup(goc, ub) == []                       # đã nghỉ: không làm lại


def test_ky_nang_d22():
    from core import ky_nang as kn, ky_nang_tu as knt
    k = kn.theo_ma("D22")
    assert k and k.tu_ap and k.toan_may and not k.nang and knt.BO_PHAN["D22"] == "dieu-phoi"


def test_quyet_dinh_bien_tap_noi_qua_so_luot(tmp_path):
    goc = str(tmp_path)
    _kenh(goc, "KA")
    _ho_so(goc, "KA", 7, "v7")
    _ghi(os.path.join(goc, "CHANNEL", "KA", "tu-chay", "2026-10-02.json"),
         {"runs": [{"ban_giao": {"ma_goi": "KA-0007"}}]})
    hs = {"KA": hc.ho_so_kenh(goc, "KA")}
    assert hc._goi_cua_quyet_dinh(goc, "KA:bien_tap:2026-10-02", hs) == [("KA", "KA-0007")]  # noqa: SLF001
    assert hc._goi_cua_quyet_dinh(goc, "KA-0007:kich_ban:2026-10-02", hs) == [("KA", "KA-0007")]  # noqa: SLF001
