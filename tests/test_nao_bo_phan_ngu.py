"""Tests `core/nao_bo_phan` ĐỢT 2 — cảnh báo tách lỗi, lỗi đang tăng theo sự cố, nốt thực thể, nhật ký bộ phận,
việc Max không tên, `ky_lai`, giấc ngủ (bảng số, cặp, kiểm lệnh, áp lệnh, trần, soát), khối lời nhắc, panel 8790.
Cây giả trong `tmp_path`, LLM giả (không gọi Claude thật), kênh giả `KA`/`KB`, mã giả."""

import contextlib
import datetime as _dt
import json
import os
import random
import re
import sqlite3
import time
import types

import pytest

import core.nao_bo_phan.ngu as ngu_mod
from core import nao_bo_phan as nbp
from core.nao_bo_phan import _chung as C
from core.nao_bo_phan import bo_gom, kho, no_ron, truy_xuat

NGAY = 86400.0


def _goc(tmp_path, kenh=("KA", "KB")):
    for k in kenh:
        d = tmp_path / "CHANNEL" / k
        d.mkdir(parents=True, exist_ok=True)
        (d / "kenh.yaml").write_text("nhom: n1\n", encoding="utf-8")
    C._KENH.clear()
    return str(tmp_path)


@contextlib.contextmanager
def _db(goc):
    con = sqlite3.connect(C.duong_db(goc))
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _ids(goc, bp, loai=None):
    with _db(goc) as con:
        q = "SELECT id FROM su_kien WHERE bo_phan = ?" + (" AND loai = ?" if loai else "") + " ORDER BY id"
        return [r[0] for r in con.execute(q, (bp, loai) if loai else (bp,))]


def _anh_clip(goc, bg, n_ok=12, n_hong=4):
    """Khâu ảnh: lượt xong / hỏng (đo) + dòng lỗi "đợi 12 phút" cùng lượt hỏng."""
    for i in range(n_ok):
        k = "KA" if i % 2 else "KB"
        nbp.ghi(goc, "anh-clip", "do", kenh=k, ma_goi="{0}-{1:04d}".format(k, i), luc=bg - (i + 1) * 3 * 3600,
                noi_dung="khâu anh: xong", so={"khau": "anh", "trang_thai": "xong", "so_lan": 1, "giay": 2000 + i},
                nguon="trang-thai", khoa="ok%d" % i)
    for i in range(n_hong):
        k = "KA" if i % 2 else "KB"
        goi, luc = "{0}-{1:04d}".format(k, 100 + i), bg - (i + 1) * 3 * 3600 - 600
        nbp.ghi(goc, "anh-clip", "do", kenh=k, ma_goi=goi, luc=luc, noi_dung="khâu anh: hong",
                so={"khau": "anh", "trang_thai": "hong", "so_lan": 3, "giay": 20000}, nguon="trang-thai",
                khoa="hong%d" % i)
        nbp.ghi(goc, "anh-clip", "loi", kenh=k, ma_goi=goi, luc=luc, so={"khau": "anh"}, nguon="so-ngay",
                noi_dung="đợi 12 phút mà máy chủ veo3 vẫn chưa trả kết quả", khoa="loi%d" % i)


# ── A1 · A2: cảnh báo tách khỏi lỗi; lỗi đang tăng theo sự cố khác nhau ───────────────────────────────────────

def test_canh_bao_va_xep_lo_dang_tang_theo_su_co(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    for i in range(10):                                   # X: 10 dòng, MỘT sự cố 48h + 5 sự cố 5 ngày trước
        nbp.ghi(goc, "giong-doc", "loi", kenh="KA", ma_goi="KA-0001", noi_dung="lỗi X đọc hỏng", khoa="x%d" % i,
                luc=bg - 3600 - i * 60)
    for i in range(5):
        nbp.ghi(goc, "giong-doc", "loi", kenh="KA", ma_goi="KA-00%d" % (10 + i), noi_dung="lỗi X đọc hỏng",
                khoa="x5%d" % i, luc=bg - (3 + i) * NGAY)
    for i in range(3):                                    # Y: 3 sự cố khác gói, mới toanh
        nbp.ghi(goc, "giong-doc", "loi", kenh="KB", ma_goi="KB-00%d" % i, noi_dung="lỗi Y tải giọng", khoa="y%d" % i,
                luc=bg - 7200)
    for i in range(30):                                   # mục kiểm mức canh_bao: cảnh báo, không vào "đang tăng"
        nbp.ghi(goc, "kiem-chat-luong", "loi", kenh="KA", ma_goi="KA-%04d" % i, nguon="chat-luong",
                noi_dung="kb_mo_dau (canh_bao): mở đầu 160s", chu_ky=C.bam("qa:kb_mo_dau"),
                so={"ma": "kb_mo_dau", "muc": "canh_bao"}, khoa="qa%d" % i, luc=bg - 600)
    for kieu, k in (("DU PHONG", "nut_a"), ("TU CHUA", "nut_b")):   # cùng độ dày: dự phòng nhẹ hơn tự chữa
        for i in range(4):
            so = {"khoa_dom": k, "kieu": kieu}
            nbp.ghi(goc, "dang-video", "loi", kenh="KA", nguon="dang-dom.log", so=so, khoa=k + str(i), luc=bg - 900,
                    noi_dung="bộ chọn {0}: {1}".format(k, kieu), chu_ky=C.chu_ky_su_kien("dang-dom.log", "loi", "", so, ()))
    nbp.gom(goc, bay_gio=bg)
    ds = nbp.loi_dang_tang(goc, 10)
    cau = [x["cau"] for x in ds]
    assert cau.index("lỗi Y tải giọng") < cau.index("lỗi X đọc hỏng")             # nhịp sự cố, không phải số dòng
    y = ds[cau.index("lỗi Y tải giọng")]
    x = ds[cau.index("lỗi X đọc hỏng")]
    assert (y["su_co_48"], y["ti_le_tang"]) == (3, 10.0) and (x["su_co_48"], x["ti_le_tang"]) == (1, round(1 / 1.2, 2))
    assert not any("kb_mo_dau" in c or "nut_a" in c for c in cau) and any("nut_b" in c for c in cau)
    v = C.duong_vault(goc)
    st = C.doc_chu(os.path.join(v, "kiem-chat-luong", "so-tay.md"))
    assert "## Cảnh báo đang có" in st and "## Lỗi đang xảy ra (0)" not in st and "Lỗi đang xảy ra" not in st
    qa = C.doc_ghi_chu(C.doc_chu(os.path.join(v, "kiem-chat-luong", "loi", C.bam("qa:kb_mo_dau") + ".md")))[0]
    assert qa["muc"] == C.CANH_BAO and qa["su_co_48h"] == 30
    xep = [r["id"] for r in nbp.nho(goc, "dang-video", "bộ chọn", k=2, rng=random.Random(5))]
    assert xep[0].endswith(C.bam("dom:nut_b")) and xep[1].endswith(C.bam("dom-du-phong:nut_a"))
    tom = {r["ma"]: r for r in nbp.tom_tat(goc, bg)}
    assert tom["kiem-chat-luong"]["canh_bao"] == 1 and tom["giong-doc"]["loi"][C.DANG] == 2


# ── A3 · A4: nốt thực thể + nhật ký bộ phận ───────────────────────────────────────────────────────────────────

def test_thuc_the_va_nhat_ky(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.gom(goc, bay_gio=bg)
    v = C.duong_vault(goc)
    for t in ("khau/anh", "engine/veo3", "kenh/KA"):
        assert os.path.isfile(os.path.join(v, "thuc-the", t + ".md")), t
    ck = nbp.chu_ky("đợi 12 phút mà máy chủ veo3 vẫn chưa trả kết quả", ["KA", "KB"])
    dau, than = C.doc_ghi_chu(C.doc_chu(os.path.join(v, "anh-clip", "loi", ck + ".md")))
    assert dau["thuc_the"] == ["engine/veo3", "khau/anh"] and "[[bo-phan/thuc-the/khau/anh|khâu anh]]" in than
    with _db(goc) as con:
        assert con.execute("SELECT COUNT(*) FROM lien_ket WHERE toi = 'thuc-the/engine/veo3'").fetchone()[0] == 1
    nk = os.path.join(v, "anh-clip", "nhat-ky.md")
    assert not os.path.isfile(nk)                          # lượt gom ĐẦU (chưa có chỉ mục cũ): không đổ cả não vào
    nbp.ghi(goc, "anh-clip", "loi", kenh="KA", noi_dung="máy chủ ảnh trả 500", khoa="moi", luc=bg - 60)
    nbp.gom(goc, bay_gio=bg)
    van = C.doc_chu(nk)
    assert van.startswith("---\nloai: nhat-ky") and van.count("— gom") == 1 and "- mới: [[bo-phan/anh-clip/loi/" in van
    nbp.gom(goc, bay_gio=bg)
    assert C.doc_chu(nk) == van                            # không đổi gì → không nối thêm
    nbp.gom(goc, bay_gio=bg + 3 * NGAY)
    sau = C.doc_chu(nk)
    assert sau.startswith(van) and "đang xảy ra → tạm lặng" in sau
    with _db(goc) as con:                                  # nhật ký không tính là liên kết của nơ-ron
        assert not con.execute("SELECT COUNT(*) FROM lien_ket WHERE tu LIKE '%nhat-ky'").fetchone()[0]


# ── A5: việc Max không tên → mô-đun gọi ──────────────────────────────────────────────────────────────────────

def test_viec_khong_ten_ghi_mo_dun_goi_va_nao_doc_duoc(tmp_path):
    from core import viet_max

    nhan = {}

    def gia(loi_nhac, **kw):
        nhan.update(kw)
        return "ok"

    goi = viet_max.dung_goi_chat_max(str(tmp_path), viet=gia, ngu=lambda s: None)
    assert goi("x") == "ok" and nhan["viec"].startswith("@") and "test_nao_bo_phan_ngu" in nhan["viec"]
    assert "core.viet_max" not in nhan["viec"]
    goi("x", khoa="KA:0001:chat:thumb")
    assert nhan["viec"] == "KA:0001:chat:thumb"
    ngu = bo_gom.Ngu("viet-max", [])
    bp = lambda v: next(iter(bo_gom.dong_viet_max(json.dumps(  # noqa: E731
        {"viec": v, "ok": True, "giay": 3, "luc": "2026-10-13T01:00:00"}), ngu)))[1]
    assert bp("@core.tu_chay<core.bien_tap_content") == "chon-content" and bp("@core.chon_bia") == "bia"
    assert bp("nao-bo-phan-ngu:tieu-de") == "dieu-phoi" and bp("") == "kich-ban"


# ── A6: ký lại ───────────────────────────────────────────────────────────────────────────────────────────────

def test_ky_lai_doi_chu_ky_va_khoa_khong_trung(tmp_path):
    goc = _goc(tmp_path)
    con = kho.mo(goc)
    bg = time.time()
    du_phong = kho.dong_su_kien("dang-video", "loi", luc=bg, kenh="KA", chu_ky_=C.bam("dom:nut_x"), nguon="dang-dom.log",
                                noi_dung="bộ chọn nut_x: DU PHONG", so={"khoa_dom": "nut_x", "kieu": "DU PHONG"},
                                khoa="dang-dom.log|t|1")
    cu1 = kho.dong_su_kien("giong-doc", "loi", luc=bg, kenh="KA", chu_ky_="aaaaaaaaaa", nguon="so-ngay",
                           noi_dung="tải hỏng (400)", khoa="khau|KA|0001|giong-doc|aaaaaaaaaa")
    cu2 = kho.dong_su_kien("giong-doc", "loi", luc=bg, kenh="KA", chu_ky_="bbbbbbbbbb", nguon="trang-thai",
                           noi_dung="tải hỏng (401)", khoa="khau|KA|0001|giong-doc|bbbbbbbbbb")
    tay = kho.dong_su_kien("giong-doc", "loi", luc=bg, chu_ky_="tu-dat", nguon="bo-phan-tu-ghi", noi_dung="x", khoa="t")
    kho.ghi_nhieu(con, [du_phong, cu1, cu2, tay])
    con.commit()
    kq = bo_gom.ky_lai(con, ["KA", "KB"])
    assert kq == {"xet": 3, "doi": 3, "giu_khoa": 1}
    r = dict(con.execute("SELECT khoa, chu_ky FROM su_kien"))
    moi = nbp.chu_ky("tải hỏng (400)", ["KA", "KB"])
    assert r["dang-dom.log|t|1"] == C.bam("dom-du-phong:nut_x") and r["t"] == "tu-dat"      # nguồn lạ: không đụng
    assert r["khau|KA|0001|giong-doc|" + moi] == moi and r["khau|KA|0001|giong-doc|bbbbbbbbbb"] == moi
    assert bo_gom.ky_lai(con, ["KA", "KB"])["xet"] == 3 and kho.doc_meta(con, "phien_ky") == str(C.PHIEN_KY)
    kho.dat_meta(con, "phien_ky", "1")
    con.commit()
    con.close()
    assert "ky_lai" not in nbp.gom(goc, bay_gio=bg)           # phiên cũ → gom tự ký lại (lần này không gì đổi)
    with _db(goc) as c2:
        assert kho.doc_meta(c2, "phien_ky") == str(C.PHIEN_KY)


# ── B1: bảng số + cặp ────────────────────────────────────────────────────────────────────────────────────────

def test_bang_so_co_cap_va_ma_that(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    ck = nbp.chu_ky("đợi 12 phút mà máy chủ veo3 vẫn chưa trả kết quả", ["KA", "KB"])
    nbp.ghi(goc, "anh-clip", "sua", chu_ky=ck, noi_dung="tăng chờ máy chủ lên 15 phút", khoa="s", luc=bg - 4 * 3600)
    nbp.gom(goc, bay_gio=bg)
    con = kho.mo(goc)
    try:
        so = ngu_mod.to_so(con, "anh-clip", bg, moi=33)
        that = set(_ids(goc, "anh-clip"))
    finally:
        con.close()
    for muc in ("== TỔNG ==", "== LỖI LẶP", "== CẶP HỎNG ⇄ ĐƯỢC", "== KHÂU ==", "== THEO KÊNH ==", "== THEO ENGINE =="):
        assert muc in so, muc
    assert "mới từ lần ngủ trước: 33" in so and "- khâu anh: 16 lượt kết thúc · hỏng 4 (25%)" in so
    assert re.search(r"- HỎNG #\d+ .*\[K[AB]\].*\n  ĐƯỢC #\d+ .*\[K[AB]\]", so)
    assert "· sửa #" in so and "engine veo3" in so
    assert {int(x) for x in re.findall(r"#(\d+)", so)} <= that                # mọi mã trích đều có thật, đúng bộ phận
    con = kho.mo(goc)
    try:                                                                      # nhiều sự kiện → vẫn ≤ trần
        kho.ghi_nhieu(con, [kho.dong_su_kien("anh-clip", "loi", kenh="KA", ma_goi="KA-%05d" % i, so={"khau": "anh"},
                                             noi_dung="lỗi lạ số %d kiểu %s" % (i, "abcdefghij"[i % 10] * (i % 7 + 1)),
                                             khoa="n%d" % i, luc=bg - i * 60) for i in range(3000)])
        con.commit()
        assert len(ngu_mod.to_so(con, "anh-clip", bg)) <= C.TRAN_TO_SO
    finally:
        con.close()


# ── B3: kiểm lệnh ────────────────────────────────────────────────────────────────────────────────────────────

def test_kiem_lenh_bang_chung_trung_va_luat_chu(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.ghi(goc, "giong-doc", "loi", noi_dung="khác bộ phận", khoa="la", luc=bg)
    nbp.gom(goc, bay_gio=bg)
    a = _ids(goc, "anh-clip")
    la = _ids(goc, "giong-doc")[0]
    cau = "Khâu ảnh: lượt hỏng chờ 12 phút × 3 lần (4/16 = 25%) — nên chờ máy chủ veo3 thay vì thử lại ngay"
    lenh = [{"lenh": "them", "cau": cau, "huong": "nen", "pham_vi": ["khau/anh", "engine/veo3", "xau/zz"],
             "vao_loi_nhac": False, "bang_chung": [a[0], "#%d" % a[1]]},
            {"lenh": "them", "cau": "bài có số 1", "bang_chung": [a[0], 999999]},
            {"lenh": "them", "cau": "bài có số 2", "bang_chung": [a[0], la]},
            {"lenh": "them", "cau": "bài có số 3"},
            {"lenh": "them", "cau": "không có số nào", "bang_chung": [a[0], a[1]]},
            {"lenh": "them", "cau": "Veo chậm quá 12 phút thì chuyển sang clip từ ảnh", "bang_chung": [a[0], a[1]]}]
    con = kho.mo(goc)
    try:
        ap, bo = ngu_mod.kiem_lenh(con, "anh-clip", lenh, [])
        assert [x["lenh"] for x in ap] == ["them"] and ap[0]["pham_vi"] == ["khau/anh", "engine/veo3"]
        ly = [y for _, y in bo]
        assert ly[0].startswith("mã sự kiện không có thật") and "#999999" in ly[0]
        assert ly[1].startswith("mã sự kiện không có thật") and "#%d" % la in ly[1]      # của bộ phận khác
        assert ly[2:] == ["thiếu bằng chứng", "câu không có số", "quá 5 lệnh"]
        ap2, bo2 = ngu_mod.kiem_lenh(con, "anh-clip", [lenh[5]], [])
        assert not ap2 and "hạ chất lượng" in bo2[0][1]
        ap3, _ = ngu_mod.kiem_lenh(con, "anh-clip", [{"lenh": "them", "cau": "Nạp thêm tiền ví khi chờ quá 30 phút",
                                                       "vao_loi_nhac": True, "bang_chung": [a[0], a[2]]}], [])
        assert ap3[0]["chi_goi_y"] and not ap3[0]["vao_loi_nhac"]                   # chuyện tiền: chỉ gợi ý
        bai: list = []
        ngu_mod.ap_lenh(con, C.duong_vault(goc), "anh-clip", ap, bai, bg)
        b = bai[0]
        assert b["id"].startswith("BH-N") and (b["alpha"], b["beta"], b["trang_thai"]) == (3, 1, C.UNG_VIEN)
        gan = cau.replace("25%", "26%").replace("ngay", "liền")                     # na ná → thành ủng hộ bài cũ
        ap4, bo4 = ngu_mod.kiem_lenh(con, "anh-clip", [
            {"lenh": "them", "cau": gan, "bang_chung": [a[3], a[4]]},
            {"lenh": "ung_ho", "id": b["id"], "bang_chung": [a[0]]},
            {"lenh": "phan_doi", "id": "BH-khong-co", "bang_chung": [a[0]]},
            {"lenh": "nghi", "id": b["id"], "bang_chung": [a[0]]},
            {"lenh": "noi", "tu": b["id"], "toi": "anh-clip/loi/khong-co", "bang_chung": [a[0]]}], bai)
        assert [(x["lenh"], x["id"]) for x in ap4] == [("ung_ho", b["id"])] and ap4[0]["tu_them"] == gan
        assert [y for _, y in bo4] == ["bằng chứng đã tính rồi", "không phải bài học tự rút của bộ phận: BH-khong-co",
                                       "nghỉ cần lý do", "nơ-ron đích không có: anh-clip/loi/khong-co"]
        ngu_mod.ap_lenh(con, C.duong_vault(goc), "anh-clip", ap4, bai, bg)
        assert (b["alpha"], b["trang_thai"], b["ung_ho"][-2:]) == (5, C.DANG_DUNG, [a[3], a[4]])
    finally:
        con.close()


def test_bang_so_bo_ket_qua_video_khong_duoc_phat(tmp_path):
    """13/10/2026: video < 50 hiển thị (YouTube không phát — lỗi mail) không phải content thua → bảng số bỏ."""
    goc = _goc(tmp_path)
    bg = time.time()
    for i, (k, gt, kq) in enumerate((("KA", 26, "truot"), ("KA", 2, "truot"), ("KB", 5170, "thang"),
                                     ("KB", 138, "truot"))):
        goi = "{0}-{1:04d}".format(k, i)
        nbp.ghi(goc, "chon-content", "chon", kenh=k, ma_goi=goi, so={"tuyen": "tuyen-x"}, khoa="c%d" % i,
                luc=bg - 3600)
        nbp.ghi(goc, "chon-content", "ket_qua", kenh=k, ma_goi=goi, so={"ket": kq, "ket_gia_tri": gt},
                khoa="k%d" % i, luc=bg - 600)
    con = kho.mo(goc)
    try:
        so = ngu_mod.to_so(con, "chon-content", bg)
    finally:
        con.close()
    assert "đã BỎ 2 kết quả video < 50 hiển thị" in so
    assert "tuyen=tuyen-x → thang 1, truot 1 (n 2)" in so or "tuyen=tuyen-x → truot 1, thang 1 (n 2)" in so


def test_bang_chung_mot_kenh_thi_tu_gan_kenh(tmp_path):
    """13/10/2026: bằng chứng chỉ của MỘT kênh mà LLM quên `kenh/…` → mã tự gắn; nhiều kênh → để trống (bài gộp)."""
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.gom(goc, bay_gio=bg)
    with _db(goc) as con:
        theo_kenh = {}
        for id_, k in con.execute("SELECT id, kenh FROM su_kien WHERE bo_phan = 'anh-clip' ORDER BY id"):
            theo_kenh.setdefault(k, []).append(id_)
    con = kho.mo(goc)
    try:
        cau = "Khâu ảnh chờ 12 phút × 3 lần (2/6 lượt hỏng) — nên chờ máy chủ"
        ap, _ = ngu_mod.kiem_lenh(con, "anh-clip", [{"lenh": "them", "cau": cau, "pham_vi": ["khau/anh"],
                                                     "bang_chung": theo_kenh["KA"][:2]}], [])
        assert ap[0]["pham_vi"] == ["khau/anh", "kenh/KA"]
        ap2, _ = ngu_mod.kiem_lenh(con, "anh-clip", [{"lenh": "them", "cau": "Khâu ảnh 4/16 lượt hỏng ở cả hai kênh",
                                                      "bang_chung": [theo_kenh["KA"][0], theo_kenh["KB"][0]]}], [])
        assert not any(t.startswith("kenh/") for t in ap2[0]["pham_vi"])
    finally:
        con.close()


def test_tran_bai_hoc_nghi_bai_yeu_nhat(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    a = _ids(goc, "anh-clip")
    monkeypatch.setattr(ngu_mod, "BAI_HOC_TOI_DA", 2)
    con = kho.mo(goc)
    try:
        bai: list = []
        v = C.duong_vault(goc)
        for i, n in enumerate((3, 2, 1)):                 # α = 1 + số bằng chứng → bài thứ ba (1 bằng chứng) yếu nhất
            ngu_mod.ap_lenh(con, v, "anh-clip", [{"lenh": "them", "cau": "bài %d có số %d" % (i, i), "huong": "nen",
                                                   "pham_vi": [], "vao_loi_nhac": False, "chi_goi_y": False,
                                                   "bang_chung": a[i * 3:i * 3 + n]}], bai, bg + i)
        assert [b["trang_thai"] for b in bai] == [C.UNG_VIEN, C.UNG_VIEN, C.NGHI]
        assert "vượt trần 2 bài" in C.doc_chu(bai[2]["duong"])
    finally:
        con.close()


# ── B2–B5: cả đêm ngủ ────────────────────────────────────────────────────────────────────────────────────────

def _gia_llm(goc, hong=()):
    goi = []

    def gia(loi_nhac, bp):
        goi.append((bp, loi_nhac))
        if bp in hong:
            raise RuntimeError("Claude giả hỏng")
        a = _ids(goc, bp)
        assert "═══ (1) BẢNG SỐ ═══" in loi_nhac and "#%d" % a[-1] in loi_nhac and "thà không đăng" in loi_nhac
        return "```json\n" + json.dumps({"lenh": [
            {"lenh": "them", "cau": "Khâu ảnh hỏng 4/16 lượt (25%) khi chờ 12 phút — chờ máy chủ veo3 rồi mới thử lại",
             "huong": "nen", "pham_vi": ["khau/anh", "kenh/KA"], "vao_loi_nhac": True, "bang_chung": a[:3]},
            {"lenh": "them", "cau": "bịa 1 lần", "bang_chung": [123456789, a[0]]}]}) + "\n```"
    return gia, goi


def test_ngu_ca_dem_ap_lenh_ghi_tep_va_so_tay(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)                                     # 20 sự kiện anh-clip
    for i in range(25):
        nbp.ghi(goc, "dieu-phoi", "do", noi_dung="đo %d" % i, khoa="dp%d" % i, luc=bg - i * 60)
    for i in range(5):
        nbp.ghi(goc, "bia", "do", noi_dung="ít %d" % i, khoa="b%d" % i, luc=bg)   # < 20 sự kiện mới: không ngủ
    nbp.gom(goc, bay_gio=bg)
    gia, goi = _gia_llm(goc, hong=("dieu-phoi",))
    kq = ngu_mod.ngu(goc, bay_gio=bg, goi=gia, soat_tuan=False)
    assert [x for x, _ in goi] == ["dieu-phoi", "anh-clip"]                # bận nhất trước; bìa chưa đủ
    hong, ok = kq["bo_phan"]
    assert hong["bo_phan"] == "dieu-phoi" and "Claude giả hỏng" in hong["loi"]     # hỏng một bộ phận không chặn
    assert ok["de_xuat"] == 2 and len(ok["ap"]) == 1 and "123456789" in ok["bo"][0][1]
    v = C.duong_vault(goc)
    tep = [t for t in os.listdir(os.path.join(v, "anh-clip", "bai-hoc")) if t.startswith("BH-N")]
    dau, than = C.doc_ghi_chu(C.doc_chu(os.path.join(v, "anh-clip", "bai-hoc", tep[0])))
    assert (dau["nguon"], dau["trang_thai"], dau["alpha"], dau["beta"], dau["kenh"]) == ("ngu", C.UNG_VIEN, 4, 1, ["KA"])
    assert "## Bằng chứng" in than and "## Lịch sử" in than and "[[bo-phan/thuc-the/khau/anh|khâu anh]]" in than
    assert "## Bài học tự rút — giấc ngủ (1)" in C.doc_chu(os.path.join(v, "anh-clip", "so-tay.md"))
    nk = C.doc_chu(os.path.join(v, "anh-clip", "nhat-ky.md"))
    assert "— ngủ (20 sự kiện mới · 2 lệnh: áp 1, bỏ 1" in nk and "- bỏ them: mã sự kiện không có thật" in nk
    with _db(goc) as con:
        rows = con.execute("SELECT bo_phan, de_xuat, ap, bo, loi FROM giac_ngu ORDER BY id").fetchall()
        assert rows[0][0] == "dieu-phoi" and rows[0][4] and rows[1] == ("anh-clip", 2, 1, 1, "")
        assert con.execute("SELECT nguon, vao_loi_nhac FROM no_ron WHERE id LIKE 'anh-clip/bai-hoc/BH-N%'").fetchone() \
            == ("ngu", 1)
    nbp.gom(goc, bay_gio=bg)                                # gom KHÔNG coi bài tự rút là bản chiếu biến mất
    assert C.doc_ghi_chu(C.doc_chu(os.path.join(v, "anh-clip", "bai-hoc", tep[0])))[0]["trang_thai"] == C.UNG_VIEN
    goi.clear()
    ngu_mod.ngu(goc, bay_gio=bg, goi=gia, soat_tuan=False)
    assert [x for x, _ in goi] == ["dieu-phoi"]            # anh-clip đã ngủ (mốc dời); điều phối hỏng → ngủ lại
    assert ngu_mod.ngu(goc, bay_gio=bg, goi=gia, chi=["anh-clip"], soat_tuan=False)["bo_phan"] == []


def test_ngu_khong_co_claude_thi_bo_qua_khong_di_vi(tmp_path, monkeypatch):
    from core import viet_max

    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.gom(goc, bay_gio=bg)
    monkeypatch.setattr(viet_max, "co_claude_code", lambda: "")
    kq = ngu_mod.ngu(goc, bay_gio=bg, soat_tuan=False)
    assert kq["bo_phan"] == [] and "KHÔNG đi ví" in kq["bo_qua"]


def test_ngu_chu_chon_vi_thi_ngu_bang_vi(tmp_path, monkeypatch):
    """17/10/2026: Cài đặt `viet_chu_bang: "vi"` → giấc ngủ đi ví, không gọi Claude Max dù máy có CLI."""
    from core import cai_dat, viet_max
    from core.giam_doc import quan_ly

    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.gom(goc, bay_gio=bg)
    monkeypatch.setattr(cai_dat, "doc", lambda _g: {"viet_chu_bang": "vi"})
    monkeypatch.setattr(viet_max, "co_claude_code", lambda: "claude")
    monkeypatch.setattr(ngu_mod, "goi_max", lambda *a, **k: (_ for _ in ()).throw(AssertionError("không được gọi Max")))
    da_goi = []
    monkeypatch.setattr(quan_ly, "goi_chat_that", lambda _g, *a, **k: (lambda de_bai, **kw: (da_goi.append(kw), "")[1]))
    ngu_mod.ngu(goc, bay_gio=bg, soat_tuan=False)
    assert da_goi and da_goi[0]["khoa"].startswith("nao-bo-phan-ngu:")


# ── B4: soát tuần ────────────────────────────────────────────────────────────────────────────────────────────

def test_soat_tuan(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.ghi(goc, "anh-clip", "loi", noi_dung="lỗi mồ côi không kênh", khoa="mc", luc=bg)
    nbp.gom(goc, bay_gio=bg)
    a = _ids(goc, "anh-clip")
    v = C.duong_vault(goc)
    con = kho.mo(goc)
    try:
        bai: list = []
        mau = lambda cau, h, pv, ids: {"lenh": "them", "cau": cau, "huong": h, "pham_vi": pv,  # noqa: E731
                                       "vao_loi_nhac": False, "chi_goi_y": False, "bang_chung": ids}
        ngu_mod.ap_lenh(con, v, "anh-clip", [
            mau("Chờ máy chủ ảnh 15 phút giảm hỏng 25% xuống 5%", "nen", ["khau/anh"], a[:2]),
            mau("Chờ máy chủ ảnh 15 phút không giảm hỏng 25%", "tranh", ["khau/anh"], a[2:4]),
            mau("Kênh KB làm lại 3 lần mỗi lượt", "nen", ["kenh/KB"], a[4:6]),
            mau("Bằng chứng đã mất 2 lần", "nen", [], [888888, 999999]),
            # cùng phạm vi, ngược hướng nhưng KHÁC đề (đo thật 13/10: 0,36) → không phải mâu thuẫn
            mau("Ở khâu chọn content, tránh tuyến A: 9/13 lần chọn bị trượt, chỉ 2/13 thắng", "tranh", ["khau/chon"],
                a[6:8]),
            mau("Ở khâu chọn content, nên ưu tiên tuyến B: 11/15 lần không trượt (5 thắng, 6 trung bình)", "nen",
                ["khau/chon"], a[8:10])], bai, bg - 40 * NGAY)
        bai[2]["trang_thai"] = C.DANG_DUNG                 # đang dùng, xác nhận cuối 40 ngày trước
        ngu_mod.ghi_bai(con, v, bai[2])
        no_ron.dung_lai_chi_muc(goc, con)
        kq = ngu_mod.soat(con, v, bg)
        tt = {b["id"]: b["trang_thai"] for b in no_ron.doc_bai_ngu(v, "anh-clip")}
        assert [tt[b["id"]] for b in bai] == [C.THU_THACH, C.THU_THACH, C.THU_THACH, C.NGHI, C.UNG_VIEN, C.UNG_VIEN]
        assert kq["anh-clip"] == {"cu": 1, "khong_bang_chung": 1, "mau_thuan": 1, "mo_coi": 1}
        nk = C.doc_chu(os.path.join(v, "anh-clip", "nhat-ky.md"))
        assert "— soát tuần" in nk and "mâu thuẫn với" in nk and "mồ côi (không nối nốt thực thể nào): 1" in nk
        assert kho.doc_meta(con, "soat_cuoi") == time.strftime("%Y-%m-%d", time.localtime(bg))
    finally:
        con.close()


# ── C1: khối não trong lời nhắc ──────────────────────────────────────────────────────────────────────────────

def _nao_co_bai(tmp_path, bp="tieu-de"):
    goc = _goc(tmp_path)
    bg = time.time()
    for i in range(3):
        nbp.ghi(goc, bp, "loi", kenh="KA", ma_goi="KA-000%d" % i, noi_dung="tiêu đề dài 120 ký tự bị cắt",
                khoa="l%d" % i, luc=bg - 600)
    nbp.ghi(goc, "kiem-chat-luong", "loi", kenh="KA", nguon="chat-luong", chu_ky=C.bam("qa:meta_khong_chuong"),
            noi_dung="meta_khong_chuong (canh_bao): mô tả không có chương 0:00", so={"ma": "meta_khong_chuong",
                                                                                   "muc": "canh_bao"}, khoa="qa", luc=bg)
    nbp.ghi(goc, "kiem-chat-luong", "loi", kenh="KA", nguon="chat-luong", chu_ky=C.bam("qa:pd_lech"),
            noi_dung="pd_lech: phụ đề lệch 2s", so={"ma": "pd_lech"}, khoa="qa2", luc=bg)
    nbp.gom(goc, bay_gio=bg)
    a = _ids(goc, bp)
    con = kho.mo(goc)
    try:
        bai: list = []
        mau = lambda cau, vao, ids, k="KA": {"lenh": "them", "cau": cau, "huong": "nen",  # noqa: E731
                                             "pham_vi": ["kenh/" + k], "vao_loi_nhac": vao, "chi_goi_y": False,
                                             "bang_chung": ids}
        ngu_mod.ap_lenh(con, C.duong_vault(goc), bp, [mau("Tiêu đề ≤ 60 ký tự không bị cắt (3/3 lượt)", True, a[:2]),
                                                       mau("Bài vận hành 2 lần thử", False, a[1:3]),
                                                       mau("Riêng kênh KB: 2 lần tiêu đề hỏi thắng", True, a[:2], "KB")],
                        bai, bg)
        ngu_mod.ap_lenh(con, C.duong_vault(goc), bp, [dict(mau("Bài gộp nhiều kênh 3/3 lượt", True, a[:2]),
                                                           pham_vi=[])], bai, bg)
        no_ron.dung_lai_chi_muc(goc, con)
    finally:
        con.close()
    return goc


def test_khoi_loi_nhac_doi_chung_va_dung(tmp_path):
    goc = _nao_co_bai(tmp_path)
    ka = nbp.khoi_loi_nhac(goc, "tieu_de", "tiêu đề", kenh="KA")
    dong = ka.splitlines()
    assert dong[0] == truy_xuat.DAU_KHOI and 2 <= len(dong) <= 7
    assert any("Tiêu đề ≤ 60 ký tự" in d and "(ứng viên · kênh KA)" in d for d in dong)
    assert not any("Bài vận hành" in d for d in dong)                      # vao_loi_nhac = false: không vào
    assert any(d.startswith("- Đang gặp: tiêu đề dài 120 ký tự") and "sự cố/48h" in d for d in dong)
    assert not any("meta_khong_chuong" in d for d in dong)                 # 13/10: cảnh báo không vào lời nhắc
    assert not any("pd_lech" in d for d in dong)                           # mục kiểm của khâu khác: không
    assert "Riêng kênh KB" not in ka                                       # mỗi kênh một tệp khán giả
    assert "Bài gộp nhiều kênh" not in ka                                  # 13/10: bài không gắn kênh không vào
    van = nbp.khoi_loi_nhac(goc, "tieu_de", "tiêu đề")                      # không biết kênh → không bài học nào
    assert "Tiêu đề ≤ 60" not in van and "Riêng kênh KB" not in van and "tiêu đề dài 120" in van
    assert "Riêng kênh KB" in nbp.khoi_loi_nhac(goc, "tieu_de", "tiêu đề", kenh="KB")
    assert "Tiêu đề ≤ 60" in nbp.khoi_loi_nhac(goc, "tieu_de", "tiêu đề", kenh="KA-v2")   # bản thử = kênh gốc
    assert nbp.khoi_loi_nhac(goc, "khau_la", "x") == "" and nbp.khoi_loi_nhac(str(tmp_path / "trong"), "bia") == ""
    doi = next(q for q in ("qd-%d" % i for i in range(200)) if random.Random(q).random() < C.TI_LE_DOI_CHUNG)
    thuong = next(q for q in ("qd-%d" % i for i in range(200)) if random.Random(q).random() >= C.TI_LE_DOI_CHUNG)
    assert nbp.khoi_loi_nhac(goc, "tieu_de", "x", doi, kenh="KA") == ""
    a = nbp.khoi_loi_nhac(goc, "tieu_de", "x", thuong, kenh="KA")
    assert a and nbp.khoi_loi_nhac(goc, "tieu_de", "x", thuong, kenh="KA") == a   # cùng quyết định → cùng kết quả
    with _db(goc) as con:
        rows = con.execute("SELECT quyet_dinh, bo_phan, doi_chung, bai_hoc FROM dung ORDER BY id").fetchall()
    assert [(r[0], r[1], r[2]) for r in rows] == [(doi, "tieu-de", 1), (thuong, "tieu-de", 0)]   # một dòng mỗi lần
    assert "tieu-de/bai-hoc/BH-N" in rows[1][3]
    with open(C.duong_db(goc), "wb") as tep:                               # kho hỏng → "" (lời nhắc như cũ)
        tep.write(b"khong phai sqlite")
    assert nbp.khoi_loi_nhac(goc, "tieu_de", "x") == ""


def test_khoi_nao_vao_loi_nhac_kich_ban_va_bien_tap(tmp_path):
    from core import auto_khau, bien_tap_content

    goc = _nao_co_bai(tmp_path, "kich-ban")
    d = os.path.join(goc, "PROJECTS", "AUTO", "KA", "0007")
    os.makedirs(d)
    with open(os.path.join(d, auto_khau.TEP_BINH_LUAN_GOC), "w", encoding="utf-8") as tep:
        tep.write("(không lấy được)\n")
    bc = types.SimpleNamespace(goc=goc, ghi=lambda *_a: None, cancel=None)
    k = types.SimpleNamespace(ma="KA", duong=os.path.join(goc, "CHANNEL", "KA"), ngon_ngu="ja")
    st = auto_khau._khoi_khan_gia(bc, k, d)["SU_THAT_KENH"]  # noqa: SLF001
    (qd, doi_chung), = _dung(goc)
    assert qd == "KA-0007:kich_ban:" + time.strftime("%Y-%m-%d")             # mã quyết định = gói : khâu : ngày
    assert st == "(chưa có)" if doi_chung else st.startswith("(chưa có)\n\n" + truy_xuat.DAU_KHOI + "\n- ")
    assert auto_khau._khoi_nao("", "KA", "kich_ban") == "" and auto_khau._khoi_nao(goc, "", "kich_ban") == ""  # noqa
    goc2 = _nao_co_bai(tmp_path / "b", "chon-content")
    ngay = next(_dt.datetime(2026, 10, 1) + _dt.timedelta(days=i) for i in range(60) if random.Random(
        "KA:bien_tap:" + (_dt.date(2026, 10, 1) + _dt.timedelta(days=i)).isoformat()).random() >= C.TI_LE_DOI_CHUNG)
    ra = bien_tap_content._khoi_nao(goc2, "KA", ngay)  # noqa: SLF001
    assert _dung(goc2) == [("KA:bien_tap:" + ngay.strftime("%Y-%m-%d"), 0)] and ra.startswith(truy_xuat.DAU_KHOI)
    assert "Tiêu đề ≤ 60 ký tự" in ra


def _dung(goc):
    with _db(goc) as con:
        return [tuple(r) for r in con.execute("SELECT quyet_dinh, doi_chung FROM dung ORDER BY id")]


# ── C2 · C3: não trung tâm + panel 8790 ──────────────────────────────────────────────────────────────────────

def test_nao_xem_giu_duoi_va_dong_bo_phan(tmp_path):
    from core import nao

    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.gom(goc, bay_gio=bg)
    bc = nao.bao_cao(goc, _dt.datetime.now(), toi_da_dong=25)
    dong = bc.splitlines()
    assert len(dong) <= 25 and "… (cắt bớt cho gọn" in bc                  # cắt khúc giữa, giữ đuôi
    assert "== NÃO BỘ PHẬN — từng bộ phận" in bc and "== ĐỌC SÂU (chỉ đọc) ==" in bc
    assert any(d.startswith("  - anh-clip: 20 sự kiện/7n") for d in dong) and "nao/bo-phan/_ban-do.md" in bc


def test_panel_nao_bo_phan_8790(tmp_path, monkeypatch):
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from core import truc_quan
    from core.nao_bo_phan import truc_quan as nbp_tq

    goc = _goc(tmp_path)
    bg = time.time()
    _anh_clip(goc, bg)
    nbp.gom(goc, bay_gio=bg)
    monkeypatch.setattr(truc_quan, "GOC", goc)
    monkeypatch.setattr(nbp_tq, "_NHO", {"luc": 0.0, "du": None, "goc": ""})
    sv = ThreadingHTTPServer(("127.0.0.1", 0), truc_quan._Xu)
    threading.Thread(target=sv.serve_forever, daemon=True).start()
    try:
        url = "http://127.0.0.1:{0}".format(sv.server_address[1])
        du = json.loads(urllib.request.urlopen(url + "/nao-bo-phan.json?bo_phan=anh-clip", timeout=20).read())
        assert du["co_kho"] and len(du["bo_phan"]) == 15 and du["loi_dang_tang"][0]["bo_phan"] == "anh-clip"
        ac = next(x for x in du["bo_phan"] if x["ma"] == "anh-clip")
        assert ac["su_kien_7"] == 20 and ac["loi"] == {C.DANG: 1}
        assert du["chi_tiet"]["so_tay"].startswith("---\nloai: so-tay") and "# Sổ tay — Ảnh / clip" in \
            du["chi_tiet"]["so_tay"]
        assert json.loads(urllib.request.urlopen(url + "/nao-bo-phan.json?bo_phan=la", timeout=20).read())[
            "chi_tiet"] == {"loi": "bộ phận lạ"}
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(truc_quan.__file__))), "ui_web",
                               "nao.html"), encoding="utf-8") as tep:
            assert "/nao-bo-phan.json" in tep.read()
    finally:
        sv.shutdown()
        sv.server_close()


@pytest.mark.parametrize("a, b, cu, ra", [(3, 1, C.UNG_VIEN, C.UNG_VIEN), (4, 1, C.UNG_VIEN, C.DANG_DUNG),
                                          (4, 3, C.DANG_DUNG, C.THU_THACH), (2, 4, C.DANG_DUNG, C.THU_THACH),
                                          (2, 4, C.UNG_VIEN, C.NGHI), (9, 1, C.NGHI, C.NGHI)])
def test_xep_trang_thai(a, b, cu, ra):
    assert ngu_mod.xep_trang_thai(a, b, cu) == ra
