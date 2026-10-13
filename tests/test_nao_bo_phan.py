"""Tests `core/nao_bo_phan` — lõi: `ghi`, chữ ký lỗi, trạng thái nơ-ron, sổ tay, `nho`, dựng lại chỉ mục, mục trong
`core.nao xem`. Mọi thứ trong `tmp_path`; mã giả (`AAAAAAAAAAA`, `UCfake…`), kênh giả `KA`/`KB`."""

import contextlib
import os
import random
import sqlite3
import time

import core.nao_bo_phan.kho as kho
import core.nao_bo_phan.no_ron as no_ron
from core import nao_bo_phan as nbp
from core.nao_bo_phan import _chung as C

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


def test_ghi_khong_bao_gio_nem_va_chong_trung(tmp_path, monkeypatch):
    goc = _goc(tmp_path)
    assert nbp.ghi(goc, "giong-doc", "loi", kenh="KA", noi_dung="tải kết quả hỏng (400)", khoa="k1")
    assert not nbp.ghi(goc, "giong-doc", "loi", kenh="KA", noi_dung="khác", khoa="k1")        # trùng khoá
    assert not nbp.ghi(goc, "khong-co", "loi", noi_dung="x")                                     # bộ phận lạ
    assert not nbp.ghi(goc, "giong-doc", "la", noi_dung="x")                                     # loại lạ
    assert nbp.ghi(goc, "dieu-phoi", "do", so={"vat": object()})                                  # số lạ → chuỗi
    tep = tmp_path / "la-tep"
    tep.write_text("x", encoding="utf-8")
    assert not nbp.ghi(str(tep), "giong-doc", "loi", noi_dung="x")                              # gốc hỏng

    def hong(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(kho, "mo", hong)
    assert nbp.ghi(goc, "giong-doc", "loi", noi_dung="y") is False
    monkeypatch.undo()
    with _db(goc) as con:
        assert con.execute("SELECT COUNT(*) FROM su_kien").fetchone()[0] == 2
        ck = con.execute("SELECT chu_ky FROM su_kien WHERE khoa='k1'").fetchone()[0]
    assert ck == nbp.chu_ky("tải kết quả hỏng (400)")


def test_chuan_hoa_chu_ky():
    ks = ["KA", "KA-K2"]
    a = nbp.chuan_hoa("lần 3 hỏng (đợi 12 phút) job_abc123def456ghi789xyz — https://example.com/x?v=1 tại "
                      r"C:\Users\x\a.json, video AAAAAAAAAAa, kênh UCfakefakefakefakefake12", ks)
    assert a == "lần # hỏng (đợi # phút) <ma> — <duong> tại <duong> video <id>, kênh <uc>"
    assert nbp.chuan_hoa("KHÔNG bàn giao KA-K2-0023: 24 cảnh (19, 20, 21)", ks) == \
        "KHÔNG bàn giao <goi>: # cảnh (#)"
    assert nbp.chuan_hoa("Kênh KA-K2 và KA", ks) == "Kênh <kenh> và <kenh>"
    assert nbp.chuan_hoa("Video 「【心理】「いい人」をやめる」 của kênh KA", ks) == "Video 「…」 của kênh <kenh>"
    assert nbp.chuan_hoa("không ra số: AAAAAAAAAAa, BBBBBBBBBBb, CCCCCCCCCCc.") == "không ra số: <id>."
    assert nbp.chuan_hoa("mã 9f3e2a7b1c thử lại") == "mã <ma> thử lại"
    assert nbp.chuan_hoa("x" * 300) == "x" * 160
    # chữ thường / mã viết hoa không bị coi là id video; cùng mẫu → cùng chữ ký
    assert nbp.chuan_hoa("hien_thi_tr VIDEO_STATU") == "hien_thi_tr VIDEO_STATU"
    assert nbp.chu_ky("đợi 12 phút mà máy chủ chưa trả", ks) == nbp.chu_ky("đợi 25 phút mà máy chủ chưa trả", ks)
    assert nbp.chu_ky("lỗi A") != nbp.chu_ky("lỗi B")


def test_trang_thai_loi():
    bg = 1_800_000_000.0
    tt = no_ron.trang_thai_loi
    assert tt(bg - 3600, None, bg) == C.DANG
    assert tt(bg - 3 * NGAY, None, bg) == C.TAM_LANG
    assert tt(bg - 8 * NGAY, None, bg) == C.DA_HET
    assert tt(bg - 3600, bg - 2 * NGAY, bg) == C.TAI_PHAT            # quay lại sau quãng im, gần đây
    assert tt(bg - 3600, bg - 20 * NGAY, bg) == C.DANG               # quay lại đã lâu → lại là "đang"


def test_chuyen_trang_thai_qua_su_kien(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    cau = "máy chủ ảnh treo 12 phút"
    for i, tuoi in enumerate((20 * NGAY, 19 * NGAY, 3600)):        # 2 lần cũ, im 19 ngày, quay lại 1 giờ trước
        assert nbp.ghi(goc, "anh-clip", "loi", kenh="KA", noi_dung=cau, khoa="a%d" % i, luc=bg - tuoi)
    nbp.ghi(goc, "anh-clip", "loi", kenh="KB", noi_dung="lỗi khác", khoa="b", luc=bg - 10 * NGAY)
    nbp.ghi(goc, "anh-clip", "sua", noi_dung="đổi engine", chu_ky=nbp.chu_ky("lỗi khác"), khoa="s",
            luc=bg - 9 * NGAY)
    with _db(goc) as con:
        nr = no_ron.gom_no_ron_loi(con, ["KA", "KB"], bg)
    a = nr[("anh-clip", nbp.chu_ky(cau))]
    assert (a["trang_thai"], a["so_lan"], a["so_7"], a["so_48"]) == (C.TAI_PHAT, 3, 1, 1)
    b = nr[("anh-clip", nbp.chu_ky("lỗi khác"))]
    assert b["trang_thai"] == C.DA_HET and no_ron.sua_da_kiem(b, bg)
    van = no_ron.ve_loi(b, bg)
    assert "ĐÃ KIỂM" in van and "trang_thai: da-het" in van and "[[bo-phan/thuc-the/kenh/KB|KB]]" in van
    # nơ-ron dựng lại tất định: không đổi gì → không ghi lại tệp
    nbp.gom(goc, bay_gio=bg)
    assert nbp.gom(goc, bay_gio=bg)["ghi_tep"] == 0


def test_so_tay_tran_dong():
    bg = time.time()
    loi = [{"id": "anh-clip/loi/%03d" % i, "bo_phan": "anh-clip", "trang_thai": C.DANG, "so_7": 100 - i,
            "lan_cuoi": bg, "cau_chinh": "lỗi số %d" % i, "kenh": {"KA": 1}, "sua": [], "so_lan": 5}
           for i in range(80)]
    bai = [{"id": "BH-%04d" % i, "bo_phan": "anh-clip", "trang_thai": C.DANG_DUNG, "n": 5, "alpha": 4, "beta": 2,
            "cau": "bài %d" % i, "kenh": "KA"} for i in range(30)]
    van = no_ron.ve_so_tay("anh-clip", loi, bai, bg)
    dau, than = C.doc_ghi_chu(van)
    assert dau == {"loai": "so-tay", "bo_phan": "anh-clip"}
    dong = than.rstrip("\n").split("\n")
    assert len(dong) <= C.SO_TAY_TOI_DA_DONG and "… còn" in dong[-1]
    assert "**100×/7 ngày**" in than                                 # lỗi dày nhất đứng đầu


def _vault_mau(tmp_path):
    goc = _goc(tmp_path)
    bg = time.time()
    for i in range(6):
        nbp.ghi(goc, "giong-doc", "loi", kenh="KA", noi_dung="cổng ShopAPI ngừng nhận việc đoạn đọc",
                khoa="g%d" % i, luc=bg - i * 3600)
    nbp.ghi(goc, "giong-doc", "loi", kenh="KB", noi_dung="tải kết quả hỏng (400) cho job", khoa="t", luc=bg - 7200)
    nbp.ghi(goc, "giong-doc", "loi", kenh="KB", noi_dung="音声の生成に失敗しました", khoa="j", luc=bg - 7200)
    nbp.gom(goc, bay_gio=bg)
    return goc


def test_nho_xep_hang_va_dung(tmp_path):
    goc = _vault_mau(tmp_path)
    ds = nbp.nho(goc, "giong-doc", "tải kết quả bị hỏng 400", k=3, rng=random.Random(1))
    assert ds and ds[0]["cau"].startswith("tải kết quả hỏng") and set(ds[0]) == {
        "id", "loai", "bo_phan", "cau", "trang_thai", "diem", "duong"}
    assert ds[0]["duong"].startswith("nao/bo-phan/giong-doc/loi/")
    assert os.path.isfile(os.path.join(goc, ds[0]["duong"]))
    assert nbp.nho(goc, "giong-doc", "音声の生成", rng=random.Random(1))[0]["cau"] == "音声の生成に失敗しました"
    assert nbp.nho(goc, "giong-doc", "cong shopapi ngung nhan", rng=random.Random(1))[0]["cau"].startswith("cổng")
    # không khớp chữ nào vẫn trả nơ-ron (lỗi dày nhất trước); bộ phận khác / chưa có kho → []
    assert nbp.nho(goc, "giong-doc", "zzz", rng=random.Random(1))[0]["cau"].startswith("cổng")
    assert nbp.nho(goc, "bia", "tải kết quả") == [] and nbp.nho(str(tmp_path / "trong"), "bia", "x") == []
    t0 = time.perf_counter()
    nbp.nho(goc, "giong-doc", "cổng ShopAPI ngừng nhận việc đoạn đọc giữa chừng", rng=random.Random(2))
    assert time.perf_counter() - t0 < 0.5                            # mục tiêu < 50 ms; nới cho máy CI bận
    with _db(goc) as con:
        assert con.execute("SELECT COUNT(*) FROM dung").fetchone()[0] == 0   # không có mã quyết định → không ghi


def test_nho_doi_chung(tmp_path):
    goc = _vault_mau(tmp_path)
    rng = random.Random(7)
    rong = sum(not nbp.nho(goc, "giong-doc", "cổng ShopAPI", k=2, quyet_dinh="qd-%d" % i, rng=rng)
               for i in range(400))
    assert 40 <= rong <= 80                                          # ≈ 15% của 400
    with _db(goc) as con:
        n, dc = con.execute("SELECT COUNT(*), SUM(doi_chung) FROM dung").fetchone()
        mau = con.execute("SELECT bai_hoc FROM dung WHERE doi_chung = 0 LIMIT 1").fetchone()[0]
    assert (n, dc) == (400, rong) and mau.startswith('["giong-doc/loi/')


def test_dung_lai_chi_muc_tu_vault(tmp_path):
    goc = _vault_mau(tmp_path)
    truoc = [x["id"] for x in nbp.nho(goc, "giong-doc", "tải kết quả", rng=random.Random(3))]
    with _db(goc) as con:
        lk = con.execute("SELECT COUNT(*) FROM lien_ket").fetchone()[0]
        for bang in ("no_ron", "chi_muc_tri", "chi_muc_viet", "lien_ket"):
            con.execute("DELETE FROM " + bang)
    assert nbp.nho(goc, "giong-doc", "tải kết quả") == []
    assert nbp.dung_lai_chi_muc(goc) == {"loi": 3}
    assert [x["id"] for x in nbp.nho(goc, "giong-doc", "tải kết quả", rng=random.Random(3))] == truoc
    with _db(goc) as con:
        assert con.execute("SELECT COUNT(*) FROM lien_ket").fetchone()[0] == lk
        assert con.execute("SELECT COUNT(*) FROM lien_ket WHERE toi = 'thuc-the/kenh/KB'").fetchone()[0] == 2


def test_loi_dang_tang_va_nao_xem(tmp_path):
    import datetime as dt

    from core import nao

    goc = _vault_mau(tmp_path)
    dong = nbp.dong_loi_dang_tang(goc, 5)
    assert dong[0].startswith("  - [giong-doc] 6×/7 ngày, 1 kênh, ") and "sự cố/48h" in dong[0]
    assert ": cổng ShopAPI" in dong[0] and len(dong) == 4
    bc = nao.bao_cao(goc, dt.datetime.now())
    assert "NÃO BỘ PHẬN — lỗi đang tăng" in bc and "cổng ShopAPI" in bc
    # kho hỏng → `xem` không in mục này, không vỡ
    with open(C.duong_db(goc), "wb") as tep:
        tep.write(b"khong phai sqlite")
    bc = nao.bao_cao(goc, dt.datetime.now())
    assert "NÃO BỘ PHẬN" not in bc and "ĐỌC SÂU" in bc
