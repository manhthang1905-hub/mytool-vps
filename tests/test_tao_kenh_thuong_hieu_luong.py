"""19/10: skill tạo kênh thương hiệu — làm sạch tên (NFKC, «：» toàn khổ), DÙNG LẠI kênh đã có (không tạo trùng),
chọn kênh mới trong Studio bằng signinUrl + đọc lại ở lần tải KẾ, ghim UC. Đồ giả, không Chrome."""
import json

from vm import tao_kenh_thuong_hieu as tk

EMAIL = "kenh" + "@gmail.com"
UC_CU, UC_MOI, UC_KHAC = "UC" + "a" * 22, "UC" + "b" * 22, "UC" + "c" * 22


class TDGia:
    """Chrome giả: danh sách kênh của tài khoản, hộp Tạo kênh, Studio đổi kênh ở lần tải SAU signinUrl."""

    def __init__(self, ds, tao_ra=None, bam_duoc=True, email=EMAIL):
        self.ds = [dict(k) for k in ds]
        self.tao_ra, self.bam_duoc, self.email = tao_ra, bam_duoc, email
        self.da_tao, self.da_mo, self.studio, self.cho_doi = [], [], (ds[0]["uc"] if ds else ""), ""
        self._url = ""

    def mo(self, url):
        self.da_mo.append(url)
        self._url = url
        for k in self.ds:
            if k.get("url") and url.endswith(k["url"]):
                self.cho_doi = k["uc"]                     # chỉ lần tải Studio KẾ mới đổi

    def url(self):
        return self._url

    def chu(self):
        return "Tài khoản " + self.email

    def ds_kenh(self):
        return [dict(k) for k in self.ds]

    def tao_kenh(self, ten, handle):
        self.da_tao.append(ten)
        if self.bam_duoc and self.tao_ra:
            self.ds.append(dict(self.tao_ra, ten=ten))
        return self.bam_duoc

    def uc_studio(self):
        uc = self.studio
        if self.cho_doi:
            self.studio, self.cho_doi = self.cho_doi, ""
        return uc

    def ngu(self, s):
        pass


def _muc(uc, ten, sid="1"):
    return {"ten": ten, "uc": uc, "url": "/signin?action_handle_signin=true&pageid=" + sid + "&next=%2F", "chon": False}


def _chay(td, tmp_path, so_cu=None, ten="脳の部屋：老後の心理", thu=False, dau=None):
    return tk.chay_luong(td, "K1", ten, "nou-heya", EMAIL, so_cu or {}, thu=thu, goc=str(tmp_path),
                         ghi=lambda s: None, ngu=lambda s: None, ghi_dau=(dau.append if dau is not None else None))


def _ghim(tmp_path):
    try:
        return json.loads((tmp_path / "vm" / "logs" / "kenh-uc.json").read_text(encoding="utf-8"))
    except OSError:
        return {}


# ── tên ──────────────────────────────────────────────────────────────────────
def test_lam_sach_ten_toan_kho_va_ky_tu_cam():
    assert tk.lam_sach_ten("脳の部屋：老後の心理") == "脳の部屋・老後の心理"
    assert tk.lam_sach_ten("脳の部屋 ： 老後") == "脳の部屋・老後"
    assert tk.lam_sach_ten("Ｂｒａｉｎ　Ｌａｂ: Night") == "Brain Lab Night"
    assert tk.lam_sach_ten("A <b> \"c\" @d #e") == "A b c d e"
    assert tk.lam_sach_ten("x​y") == "xy"
    assert tk.lam_sach_ten("：：") == "" and tk.lam_sach_ten(None) == ""
    assert len(tk.lam_sach_ten("あ" * 80)) == tk.DAI_TOI_DA_TEN


def test_khoa_ten_so_nfkc():
    assert tk.khoa_ten("脳の部屋：老後") == tk.khoa_ten("脳の部屋・老後")
    assert tk.khoa_ten("Ｂｒａｉｎ Lab") == tk.khoa_ten("brain  lab")
    assert tk.khoa_ten("脳の部屋") != tk.khoa_ten("脳の部屋2")
    assert tk.uc_cua_khoa("b" * 22) == UC_MOI and tk.uc_cua_khoa(UC_MOI) == UC_MOI and tk.uc_cua_khoa("") == ""


# ── dùng lại, không tạo trùng ───────────────────────────────────────────────
def test_da_co_kenh_trung_ten_thi_dung_lai_chon_va_ghim(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0"), _muc(UC_MOI, "脳の部屋・老後の心理", "7")])
    ket = _chay(td, tmp_path)
    assert td.da_tao == []                                              # KHÔNG tạo thêm
    assert ket["ket_qua"] == "da_co" and ket["uc"] == UC_MOI and ket["ten"] == "脳の部屋・老後の心理"
    assert ket["chon_kenh"] and ket["ghim_uc"] and _ghim(tmp_path) == {"K1": UC_MOI}
    assert any("pageid=7" in u for u in td.da_mo)                        # đúng mục channel_switcher


def test_uc_trong_so_duoc_dung_lai_du_ten_da_doi(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0"), _muc(UC_MOI, "Tên đã đổi", "7")])
    ket = _chay(td, tmp_path, so_cu={"ket_qua": "ok", "uc": UC_MOI})
    assert td.da_tao == [] and ket["uc"] == UC_MOI and ket["ket_qua"] == "da_co"


def test_so_co_uc_ma_tai_khoan_khong_co_thi_khong_tao(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0")], tao_ra=_muc(UC_KHAC, "", "9"))
    ket = _chay(td, tmp_path, so_cu={"ket_qua": "ok", "uc": UC_MOI})
    assert td.da_tao == [] and ket["ket_qua"] == "can_nguoi"


def test_da_bam_tao_truoc_do_ma_chua_thay_thi_khong_bam_lai(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0")], tao_ra=_muc(UC_KHAC, "", "9"))
    dau = {"luc": "2026-10-19 10:00", "ten": "x", "truoc": [UC_CU]}
    ket = _chay(td, tmp_path, so_cu={"ket_qua": "chua_xac_minh", "da_bam_tao": dau})
    assert td.da_tao == [] and ket["ket_qua"] == "can_nguoi" and ket["da_bam_tao"] == dau


def test_da_bam_tao_truoc_do_kenh_moi_hien_ten_khac_van_dung_lai(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0"), _muc(UC_MOI, "YouTube tự đặt", "7")])
    dau = {"luc": "2026-10-19 10:00", "ten": "x", "truoc": [UC_CU]}
    ket = _chay(td, tmp_path, so_cu={"ket_qua": "chua_xac_minh", "da_bam_tao": dau})
    assert td.da_tao == [] and ket["ket_qua"] == "da_co" and ket["uc"] == UC_MOI


def test_khong_doc_duoc_danh_sach_thi_khong_tao(tmp_path):
    td = TDGia([], tao_ra=_muc(UC_MOI, "", "7"))
    ket = _chay(td, tmp_path)
    assert td.da_tao == [] and ket["ket_qua"] == "chua_xac_minh"


def test_sai_tai_khoan_thi_dung(tmp_path):
    td = TDGia([_muc(UC_CU, "x", "0")], email="khac" + "@gmail.com")
    assert _chay(td, tmp_path)["ket_qua"] == "sai_danh_tinh" and td.da_tao == []


# ── tạo mới → chọn → ghim ───────────────────────────────────────────────────
def test_tao_moi_ten_sach_chon_doc_lai_va_ghim(tmp_path):
    (tmp_path / "vm" / "logs").mkdir(parents=True)
    (tmp_path / "vm" / "logs" / "kenh-uc.json").write_text(json.dumps({"K1": UC_CU, "K9": UC_KHAC}), encoding="utf-8")
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0")], tao_ra=_muc(UC_MOI, "", "7"))
    dau = []
    ket = _chay(td, tmp_path, dau=dau)
    assert td.da_tao == ["脳の部屋・老後の心理"]                           # tên đã làm sạch được gõ
    assert dau and dau[0]["da_bam_tao"]["truoc"] == [UC_CU]              # dấu ghi TRƯỚC khi bấm
    assert ket["ket_qua"] == "ok" and ket["uc"] == UC_MOI and ket["ten_goc"] == "脳の部屋：老後の心理"
    assert ket["chon_kenh"] and td.studio == UC_MOI
    assert _ghim(tmp_path) == {"K1": UC_MOI, "K9": UC_KHAC} and ket["uc_ghim_cu"] == UC_CU


def test_tao_moi_chi_mot_lan_khi_chua_thay_kenh(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0")], tao_ra=None)            # bấm được nhưng kênh chưa hiện
    ket = _chay(td, tmp_path, dau=[])
    assert td.da_tao == ["脳の部屋・老後の心理"] and ket["ket_qua"] == "chua_xac_minh" and ket["da_bam_tao"]
    ket2 = _chay(td, tmp_path, so_cu=ket)                                # lượt sau: KHÔNG bấm lại
    assert td.da_tao == ["脳の部屋・老後の心理"] and ket2["ket_qua"] == "can_nguoi"


def test_khong_bam_duoc_thi_go_dau(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0")], bam_duoc=False)
    dau = []
    ket = _chay(td, tmp_path, dau=dau)
    assert ket["ket_qua"] == "hong" and "da_bam_tao" not in ket and "da_bam_tao" not in dau[-1]


def test_chi_doc_khong_tao_khong_chon_khong_ghim(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0"), _muc(UC_MOI, "脳の部屋・老後の心理", "7")])
    ket = _chay(td, tmp_path, thu=True)
    assert ket["ket_qua"] == "chi_doc" and ket["uc"] == UC_MOI and td.studio == UC_CU and _ghim(tmp_path) == {}
    td2 = TDGia([_muc(UC_CU, "Tên cá nhân", "0")], tao_ra=_muc(UC_MOI, "", "7"))
    assert _chay(td2, tmp_path, thu=True)["ket_qua"] == "chi_doc" and td2.da_tao == []


def test_studio_khong_doi_kenh_thi_chua_xac_minh_khong_ghim(tmp_path):
    td = TDGia([_muc(UC_CU, "Tên cá nhân", "0"), dict(_muc(UC_MOI, "脳の部屋・老後の心理"), url="")])
    ket = _chay(td, tmp_path)
    assert ket["ket_qua"] == "chua_xac_minh" and not ket["chon_kenh"] and _ghim(tmp_path) == {}


# ── ghim UC ─────────────────────────────────────────────────────────────────
def test_ghim_uc_khong_de_uc_cua_tai_khoan_khac(tmp_path):
    (tmp_path / "vm" / "logs").mkdir(parents=True)
    p = tmp_path / "vm" / "logs" / "kenh-uc.json"
    p.write_text(json.dumps({"K1": UC_KHAC}), encoding="utf-8")
    ok, ly, cu = tk.ghim_uc("K1", UC_MOI, [UC_CU, UC_MOI], str(tmp_path))
    assert not ok and cu == UC_KHAC and json.loads(p.read_text(encoding="utf-8")) == {"K1": UC_KHAC}
    assert tk.ghim_uc("K1", UC_KHAC, [], str(tmp_path))[:2] == (True, "đã ghim sẵn")
    assert tk.ghim_uc("K2", UC_MOI, [], str(tmp_path))[0] and json.loads(p.read_text(encoding="utf-8"))["K2"] == UC_MOI


def test_chon_kenh_doc_lai_o_lan_tai_ke():
    td = TDGia([_muc(UC_CU, "a", "0"), _muc(UC_MOI, "b", "7")])
    ok, uc = tk.chon_kenh(td, td.ds[1], ngu=lambda s: None)
    assert ok and uc == UC_MOI
