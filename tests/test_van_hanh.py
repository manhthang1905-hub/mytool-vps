"""Vận hành: sổ đăng ký thành phần + lượt canh + dọn khoá sau khởi động + báo cáo khởi động (`core/van_hanh.py`).

Không sinh tiến trình thật, không dò cổng thật, không gọi schtasks thật: mọi thành phần là đồ giả (`kiem`/`bat`),
báo động và não là seam, đĩa là tmp_path (CLAUDE.md luật 4).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import time

from core import lich_tu_chay, van_hanh as vh

GIO = 3600.0


class _Gia:
    """Thành phần giả: `trang` là danh sách trạng thái trả lần lượt cho mỗi lần kiểm (hết thì giữ cái cuối)."""

    def __init__(self, *trang, bat_ok=True):
        self.trang = list(trang)
        self.so_kiem = 0
        self.so_bat = 0
        self.bat_ok = bat_ok

    def kiem(self, goc):
        tt = self.trang[min(self.so_kiem, len(self.trang) - 1)]
        self.so_kiem += 1
        return tt, "giả: " + tt

    def bat(self, goc):
        self.so_bat += 1
        return self.bat_ok, "đã bật giả"


def _tp(gia, ma="truc_quan_8790", **kw):
    kw.setdefault("cho_len_giay", 0.0)
    return vh.ThanhPhan(ma, "Thành phần " + ma, gia.kiem, gia.bat, cach_bat="giả", **kw)


def _chay(goc, ds, *, luc, boot=None, ban="", thu=False, bao=None, nao=None, song=None):
    return vh.mot_luot(str(goc), thu=thu, thanh_phan=ds, bay_gio=luc, luc_boot=(luc - 10 * GIO) if boot is None else boot,
                       ly_do_ban_fn=lambda *_a, **_k: ban, pid_con_song=song or (lambda _p: False),
                       ngu=lambda _s: None, gui_bao=bao if bao is not None else (lambda *a, **k: None),
                       ghi_nao=nao if nao is not None else (lambda *a, **k: None))


# ── sổ đăng ký: kiểm + bật ─────────────────────────────────────────────────────────────────────────────────────


def test_cong_chet_thi_bat_va_cho_len(tmp_path):
    g = _Gia(vh.CHET, vh.SONG)
    kq = _chay(tmp_path, [_tp(g)], luc=time.time())
    v = kq["thanh_phan"]["truc_quan_8790"]
    assert g.so_bat == 1 and v["hanh_dong"] == "da_bat" and v["trang_thai"] == vh.SONG
    so = json.load(open(vh.duong_trang_thai(str(tmp_path)), encoding="utf-8"))
    assert so["thanh_phan"]["truc_quan_8790"]["lan_hong"] == 0
    assert so["tom_tat"]["song"] == 1 and so["tom_tat"]["tong"] == 1


def test_thanh_phan_khoe_khong_bi_dong_toi(tmp_path):
    g = _Gia(vh.SONG)
    kq = _chay(tmp_path, [_tp(g)], luc=time.time())
    assert g.so_bat == 0 and kq["thanh_phan"]["truc_quan_8790"]["hanh_dong"] == "khoe"


def test_dang_tai_len_thi_khong_bat_thanh_phan_ne_ban(tmp_path):
    agent, tq = _Gia(vh.CHET), _Gia(vh.CHET, vh.SONG)
    ds = [_tp(agent, "agent_vm", ne_ban=True), _tp(tq)]
    kq = _chay(tmp_path, ds, luc=time.time(), ban="máy đăng đang tải dở TL1 X (dang-dodang.json)")
    assert agent.so_bat == 0 and kq["thanh_phan"]["agent_vm"]["hanh_dong"] == "hoan_ban"
    assert "dang-dodang" in kq["thanh_phan"]["agent_vm"]["hoan"]
    assert tq.so_bat == 1      # thành phần không né bận (dịch vụ chỉ đọc) vẫn được bật


def test_ket_cong_thi_khong_bat_ban_thu_hai(tmp_path):
    g = _Gia(vh.KET)
    kq = _chay(tmp_path, [_tp(g)], luc=time.time())
    assert g.so_bat == 0 and kq["thanh_phan"]["truc_quan_8790"]["hanh_dong"] == "ket"


def test_an_han_sau_khoi_dong_de_co_che_san_co_tu_bat(tmp_path):
    luc = time.time()
    g = _Gia(vh.CHET)
    kq = _chay(tmp_path, [_tp(g, "giao_dien", an_han_khoi_dong_giay=600.0)], luc=luc, boot=luc - 60)
    assert g.so_bat == 0 and kq["thanh_phan"]["giao_dien"]["hanh_dong"] == "cho_khoi_dong"


def test_agent_cho_giao_dien_vua_mo(tmp_path):
    gd, ag = _Gia(vh.CHET, vh.SONG), _Gia(vh.CHET)
    ds = [_tp(gd, "giao_dien"), _tp(ag, "agent_vm", dieu_kien=vh._dk_agent)]  # noqa: SLF001
    kq = _chay(tmp_path, ds, luc=time.time())
    assert gd.so_bat == 1 and ag.so_bat == 0
    assert kq["thanh_phan"]["agent_vm"]["hanh_dong"] == "cho_phu_thuoc"


def test_lui_dan_sau_lan_hong(tmp_path):
    luc = time.time()
    g = _Gia(vh.CHET)                      # bật "được" nhưng không bao giờ lên tiếng
    _chay(tmp_path, [_tp(g)], luc=luc)
    assert g.so_bat == 1
    kq = _chay(tmp_path, [_tp(g)], luc=luc + 30)      # lùi 60 giây sau lần hỏng 1
    assert g.so_bat == 1 and kq["thanh_phan"]["truc_quan_8790"]["hanh_dong"] == "lui"
    _chay(tmp_path, [_tp(g)], luc=luc + 61)
    assert g.so_bat == 2


def test_cham_tran_bao_mot_lan_khong_bat_vong(tmp_path):
    luc = _dt.datetime(2026, 10, 16, 1, 0).timestamp()      # cố định: cả chuỗi lượt nằm trọn trong một ngày
    g = _Gia(vh.CHET)
    bao, nao = [], []
    gui = lambda *a, **k: bao.append(a)              # noqa: E731
    ghi = lambda *a, **k: nao.append((a, k))         # noqa: E731
    for _ in range(vh.TRAN_LAN_HONG):
        _chay(tmp_path, [_tp(g)], luc=luc, bao=gui, nao=ghi)
        luc += vh.LUI_TRAN_GIAY + 1                  # qua mọi quãng lùi
    assert g.so_bat == vh.TRAN_LAN_HONG and len(bao) == 1 and bao[0][0] == "van_hanh:truc_quan_8790"
    for _ in range(10):                              # cùng ngày: không bật nữa, không báo lại
        kq = _chay(tmp_path, [_tp(g)], luc=luc, bao=gui, nao=ghi)
        luc += 300
    assert g.so_bat == vh.TRAN_LAN_HONG and len(bao) == 1
    assert kq["thanh_phan"]["truc_quan_8790"]["hanh_dong"] == "da_tran"
    assert os.path.isfile(os.path.join(str(tmp_path), "workspace", "loi-chay-max.md"))
    assert any(a[2] == "loi" and a[1] == "suc-khoe-may" for a, _k in nao)
    _chay(tmp_path, [_tp(g)], luc=luc + vh.THU_LAI_SAU_TRAN_GIAY, bao=gui, nao=ghi)   # hôm sau: thử đúng 1 lần
    assert g.so_bat == vh.TRAN_LAN_HONG + 1 and len(bao) == 2


def test_song_lai_thi_dat_lai_bo_dem(tmp_path):
    luc = time.time()
    g = _Gia(vh.CHET)
    _chay(tmp_path, [_tp(g)], luc=luc)
    g.trang = [vh.SONG]
    g.so_kiem = 0
    kq = _chay(tmp_path, [_tp(g)], luc=luc + 600)
    assert kq["thanh_phan"]["truc_quan_8790"].get("hoi_phuc") is True
    so = json.load(open(vh.duong_trang_thai(str(tmp_path)), encoding="utf-8"))
    assert so["thanh_phan"]["truc_quan_8790"]["lan_hong"] == 0


def test_thu_chi_doc(tmp_path):
    g = _Gia(vh.CHET)
    kq = _chay(tmp_path, [_tp(g)], luc=time.time(), thu=True)
    assert g.so_bat == 0 and kq["thanh_phan"]["truc_quan_8790"]["hanh_dong"] == "se_bat"
    assert not os.path.exists(vh.duong_trang_thai(str(tmp_path)))
    assert not os.path.exists(vh.duong_khoi_dong(str(tmp_path)))


def test_tat_trong_cai_dat(tmp_path):
    os.makedirs(vh.duong_thu_muc(str(tmp_path)))
    with open(os.path.join(vh.duong_thu_muc(str(tmp_path)), "cai-dat.json"), "w", encoding="utf-8") as tep:
        json.dump({"tat": ["truc_quan_8790"]}, tep)
    g = _Gia(vh.CHET)
    kq = _chay(tmp_path, [_tp(g)], luc=time.time())
    assert g.so_bat == 0 and kq["thanh_phan"]["truc_quan_8790"]["trang_thai"] == vh.TAT and kq["tong"] == 0


# ── dọn khoá sau khởi động ─────────────────────────────────────────────────────────────────────────────────────


def _khoa(goc, rel, du, moc):
    d = os.path.join(str(goc), *rel.split("/"))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    with open(d, "w", encoding="utf-8") as tep:
        tep.write(du if isinstance(du, str) else json.dumps(du))
    os.utime(d, (moc, moc))
    return d


def test_don_khoa_theo_luat_khoi_dong(tmp_path):
    bay = time.time()
    boot = bay - 2 * GIO
    truoc = _khoa(tmp_path, "workspace/tu-chay/.khoa-may", {"pid": 4242, "bat_dau": boot - GIO}, boot - GIO)
    kenh = _khoa(tmp_path, "CHANNEL/K1/tu-chay/.khoa", {"pid": 4243, "bat_dau": boot - 60}, boot - 60)
    chet = _khoa(tmp_path, "workspace/khe/api-0.json", {"pid": 777, "bat_dau": bay - GIO}, bay - GIO)
    song = _khoa(tmp_path, "workspace/khe/api-1.json", {"pid": 888, "bat_dau": bay - GIO}, bay - GIO)
    moi = _khoa(tmp_path, "workspace/khe/api-2.json", {"pid": 999, "bat_dau": bay - 60}, bay - 60)
    dodang = _khoa(tmp_path, "vm/logs/dang-dodang.json",
                   {"pid": 4244, "kenh": "K1", "luc_bat_dau": "2000-01-01 00:00:00"}, boot - 30)
    rac = _khoa(tmp_path, "workspace/khe/dieu-phoi.lock", "khong phai json", boot - GIO)
    # PID 4242/4243/4244 "còn sống" = đã bị tiến trình khác dùng lại sau khởi động — vẫn phải dọn.
    ds = vh.don_khoa_khoi_dong(str(tmp_path), boot, bay_gio=bay, pid_con_song=lambda p: p in (4242, 4243, 4244, 888))
    xoa = {m["duong"] for m in ds if m["xoa"]}
    assert not os.path.exists(truoc) and not os.path.exists(kenh) and not os.path.exists(dodang)
    assert not os.path.exists(chet)                          # PID chết, khoá 1 giờ
    assert os.path.exists(song) and os.path.exists(moi) and os.path.exists(rac)
    assert xoa == {"workspace/tu-chay/.khoa-may", "CHANNEL/K1/tu-chay/.khoa", "workspace/khe/api-0.json",
                   "vm/logs/dang-dodang.json"}


def test_khoa_lam_tuoi_sau_khoi_dong_khong_bi_coi_la_cu(tmp_path):
    bay = time.time()
    boot = bay - 2 * GIO
    d = _khoa(tmp_path, "vm/logs/nuoi-trang-chu/K1.khoa", {"pid": 31, "luc": boot - GIO}, bay - 30)   # tệp sửa sau boot
    ds = vh.don_khoa_khoi_dong(str(tmp_path), boot, bay_gio=bay, pid_con_song=lambda p: True)
    assert os.path.exists(d) and ds[0]["xoa"] is False


def test_don_khoa_thu_khong_xoa(tmp_path):
    bay = time.time()
    boot = bay - GIO
    d = _khoa(tmp_path, "workspace/tu-chay/.khoa-may", {"pid": 5, "bat_dau": boot - GIO}, boot - GIO)
    ds = vh.don_khoa_khoi_dong(str(tmp_path), boot, bay_gio=bay, thu=True, pid_con_song=lambda p: True)
    assert os.path.exists(d) and ds[0]["xoa"] is None


def test_ly_do_ban(tmp_path):
    bay = time.time()
    boot = bay - GIO
    g = str(tmp_path)
    assert vh.ly_do_ban(g, luc_boot=boot, pid_con_song=lambda p: True) == ""
    d = _khoa(tmp_path, "vm/logs/dang-dodang.json", {"pid": 9, "kenh": "K1", "ma": "M1"}, boot - 60)
    assert vh.ly_do_ban(g, luc_boot=boot, pid_con_song=lambda p: True) == ""        # dấu từ trước khởi động
    os.utime(d, (bay, bay))
    assert "dang-dodang" in vh.ly_do_ban(g, luc_boot=boot, pid_con_song=lambda p: True)
    os.remove(d)
    k = _khoa(tmp_path, "workspace/tu-chay/.khoa-may", {"pid": 9, "bat_dau": bay, "viec": "kich_ban"}, bay)
    assert vh.ly_do_ban(g, luc_boot=boot, pid_con_song=lambda p: True) == ""        # việc nhẹ: không chặn
    _khoa(tmp_path, "workspace/tu-chay/.khoa-may", {"pid": 9, "bat_dau": bay, "viec": "dung"}, bay)
    assert "dựng" in vh.ly_do_ban(g, luc_boot=boot, pid_con_song=lambda p: True)
    assert vh.ly_do_ban(g, luc_boot=boot, pid_con_song=lambda p: False) == ""       # chủ khoá đã chết
    assert os.path.exists(k)


# ── báo cáo khởi động ─────────────────────────────────────────────────────────────────────────────────────────


def test_bao_cao_khoi_dong_mot_lan_moi_lan_khoi_dong(tmp_path):
    bay = time.time()
    boot = bay - 300
    _khoa(tmp_path, "workspace/tu-chay/.khoa-may", {"pid": 1, "bat_dau": boot - GIO}, boot - GIO)
    nao = []
    ghi = lambda *a, **k: nao.append((a, k))         # noqa: E731
    ds = lambda: [_tp(_Gia(vh.SONG), "giao_dien"), _tp(_Gia(vh.SONG))]   # noqa: E731
    kq = _chay(tmp_path, ds(), luc=bay, boot=boot, nao=ghi)
    assert kq["moi_boot"] is True
    cau = kq["bao_khoi_dong"]
    assert cau.startswith("khởi động {0} — 2/2 thành phần chạy, đã dọn 1 khoá cũ".format(
        time.strftime("%H:%M", time.localtime(boot))))
    kd = json.load(open(vh.duong_khoi_dong(str(tmp_path)), encoding="utf-8"))
    assert kd["cau"] == cau and kd["song"] == 2 and kd["tong"] == 2
    assert len([1 for a, k in nao if k.get("khoa", "").startswith("van-hanh|khoi-dong|")]) == 1
    assert "dọn khoá cũ workspace/tu-chay/.khoa-may" in open(vh.duong_log(str(tmp_path)), encoding="utf-8").read()
    kq2 = _chay(tmp_path, ds(), luc=bay + 300, boot=boot + 3, nao=ghi)      # cùng lần khởi động (lệch vài giây)
    assert kq2["moi_boot"] is False
    assert len([1 for a, k in nao if k.get("khoa", "").startswith("van-hanh|khoi-dong|")]) == 1
    kq3 = _chay(tmp_path, ds(), luc=bay + 9000, boot=bay + 8800, nao=ghi)   # khởi động lại
    assert kq3["moi_boot"] is True
    assert len([1 for a, k in nao if k.get("khoa", "").startswith("van-hanh|khoi-dong|")]) == 2


def test_bao_cao_khoi_dong_neu_ten_thanh_phan_hong_sau_han(tmp_path):
    bay = time.time()
    boot = bay - vh.BAO_SAU_GIAY - 60
    kq = _chay(tmp_path, [_tp(_Gia(vh.SONG), "giao_dien"), _tp(_Gia(vh.KET))], luc=bay, boot=boot)
    assert "1/2 thành phần chạy" in kq["bao_khoi_dong"] and "chưa chạy: Thành phần truc_quan_8790" in kq["bao_khoi_dong"]


def test_bao_cao_cho_khi_chua_du_va_chua_qua_han(tmp_path):
    bay = time.time()
    kq = _chay(tmp_path, [_tp(_Gia(vh.CHET), "giao_dien", an_han_khoi_dong_giay=600.0)], luc=bay, boot=bay - 60)
    assert kq["bao_khoi_dong"] == "" and not os.path.exists(vh.duong_khoi_dong(str(tmp_path)))


def test_so_dang_ky_du_bon_thanh_phan(tmp_path):
    ma = [c.ma for c in vh.so_dang_ky(str(tmp_path))]
    assert ma == ["giao_dien", "tram_8765", "agent_vm", "truc_quan_8790"]
    lenh = vh.lenh_truc_quan(str(tmp_path))
    assert lenh[1:] == ["-X", "utf8", "-m", "core.truc_quan"] and "--lan" not in lenh


# ── đăng ký lịch ──────────────────────────────────────────────────────────────────────────────────────────────


def test_dang_ky_van_hanh_hai_viec_khong_mat_khau(tmp_path):
    goc = str(tmp_path / "MyTool")
    os.makedirs(goc)
    open(os.path.join(goc, "van_hanh.py"), "w").close()
    goi = []
    ok, cau = lich_tu_chay.dang_ky_van_hanh(goc, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok, cau
    assert [l[l.index("/TN") + 1] for l in goi] == ["ShopAPI-VanHanh", "ShopAPI-VanHanhLucDangNhap"]
    assert goi[0][goi[0].index("/SC") + 1] == "MINUTE" and goi[0][goi[0].index("/MO") + 1] == "5"
    assert goi[1][goi[1].index("/SC") + 1] == "ONLOGON" and "/DELAY" in goi[1]
    for l in goi:
        assert "/F" in l and "/RU" not in l and "/RP" not in l
        assert l[l.index("/TR") + 1].endswith('van_hanh.py" mot-luot')


def test_dang_ky_van_hanh_tu_choi_worktree(tmp_path):
    goc = str(tmp_path / "MyTool" / ".claude" / "worktrees" / "agent-x")
    os.makedirs(goc)
    open(os.path.join(goc, "van_hanh.py"), "w").close()
    goi = []
    ok, cau = lich_tu_chay.dang_ky_van_hanh(goc, chay_lenh=lambda l: goi.append(l) or (0, ""))
    assert ok is False and "worktree" in cau and goi == []


def test_ket_lau_thi_bao_mot_lan_khong_bat(tmp_path):
    luc = _dt.datetime(2026, 10, 16, 1, 0).timestamp()
    g, bao = _Gia(vh.KET), []
    for _ in range(vh.TRAN_LAN_HONG + 3):
        _chay(tmp_path, [_tp(g)], luc=luc, bao=lambda *a, **k: bao.append(a[1]))
        luc += 300
    assert g.so_bat == 0 and len(bao) == 1 and "kẹt" in bao[0]
