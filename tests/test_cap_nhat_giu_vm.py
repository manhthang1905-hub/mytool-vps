"""Đợt 5.2 — `vm/` không còn bị cập nhật đè trắng.

═══ BUG ĐÃ SỬA ═══

`vm` không nằm trong `PRESERVE` cũng không trong `HOA_NHAP`, nên trước Đợt
5.2 nó rơi thẳng vào nhánh "bản mới đè hoàn toàn" của `apply_tai_cho`: mỗi
lần cập nhật là mất `vm/config.json`, token OAuth (`tokens/`), client bí mật
(`clients/`), đã trả lời cmt nào (`replied/`), video đã đăng
(`logs/so-video-id.json`) — mất cái cuối là ĐĂNG TRÙNG một video thật lên
kênh thật. Và `.rollback` cũ bị xoá ở lần cập nhật SAU, nên không lùi lại
được nữa.

Bài dưới đây khoá: (1) trạng thái máy thật trong `vm/` (và các tệp/thư mục
riêng máy khác thêm vào `PRESERVE` cùng đợt) không đổi một byte qua một lượt
`apply_tai_cho`; (2) mã trong `vm/` (kể cả trong `tien-ich/<kênh>/`) vẫn nhận
bản mới; (3) một lượt bị huỷ giữa chừng (healthcheck hỏng) trả nguyên trạng
CẢ mã lẫn trạng thái, không riêng gì top-level; (4) đường tải qua manifest
(`core/nguon_cap_nhat.py`) không hạ bản, từ chối toàn bộ khi sai SHA-256, và
giữ đúng 2 bản `.rollback-<version>`.

Không bài nào gọi mạng — `tai` luôn là hàm giả.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from core import nguon_cap_nhat as ncn
from core.safe_update import UpdateError, apply_tai_cho


# ── Dựng cây thư mục giả (cùng khuôn với tests/test_cap_nhat_tai_cho.py) ────


def _dung_ban(thu_muc: Path, ban: str, dau_vet: str = "") -> Path:
    """Dựng một thư mục trông đủ giống bản cài để qua được `_healthcheck_tree`."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    (thu_muc / "shopapi_studio_qt.py").write_text("# tool", encoding="utf-8")
    (thu_muc / "VERSION").write_text(ban + "\n", encoding="utf-8")
    for ten in ("core", "ui_qt", "tool-catalog"):
        (thu_muc / ten).mkdir(exist_ok=True)
        (thu_muc / ten / "__init__.py").write_text("", encoding="utf-8")
    (thu_muc / "tool-catalog" / "mau").mkdir(exist_ok=True)
    (thu_muc / "tool-catalog" / "mau" / "tool.json").write_text(
        "{}", encoding="utf-8")
    if dau_vet:
        (thu_muc / "dau-vet.txt").write_text(dau_vet, encoding="utf-8")
    return thu_muc


def _dung_vm_cu(cai: Path) -> None:
    """`vm/` + phần riêng máy khác của một máy ĐANG CHẠY THẬT — mã và trạng
    thái trộn lẫn, đúng như máy thật (xem docstring đầu tệp)."""
    vm = cai / "vm"
    vm.mkdir(parents=True, exist_ok=True)

    (vm / "config.json").write_text('{"tram":"http://cu:8765"}', encoding="utf-8")
    (vm / "cai-dat-tool.json").write_text('{"dang_video":true}', encoding="utf-8")
    (vm / "trang-thai.json").write_text('{"phien_cuoi@K1":"2026-09-28"}', encoding="utf-8")
    (vm / "agent.py").write_text("# ma CU cua agent", encoding="utf-8")
    (vm / "may_dang.py").write_text("# ma CU cua may_dang", encoding="utf-8")

    (vm / "tokens").mkdir()
    (vm / "tokens" / "K1.json").write_text('{"access_token":"AAA-that"}', encoding="utf-8")
    (vm / "clients").mkdir()
    (vm / "clients" / "client.json").write_text('{"client_id":"bi-mat"}', encoding="utf-8")
    (vm / "replied").mkdir()
    (vm / "replied" / "K1.txt").write_text("cmt-1\ncmt-2\n", encoding="utf-8")
    (vm / "logs").mkdir()
    (vm / "logs" / "so-video-id.json").write_text('{"vid-that-1":"da dang"}', encoding="utf-8")
    (vm / "logs" / "kenh-uc.json").write_text('{"K1":"UCthat"}', encoding="utf-8")

    ti = vm / "tien-ich" / "K1"
    ti.mkdir(parents=True)
    (ti / "manifest.json").write_text('{"version":"cu"}', encoding="utf-8")
    (ti / "cau-hinh.json").write_text('{"bat":"K1-that"}', encoding="utf-8")
    (ti / "content.js").write_text("// ma CU cua content.js", encoding="utf-8")

    # Trạng thái riêng máy NGOÀI vm/ — thêm vào PRESERVE cùng Đợt 5.2.
    (cai / "vps.json").write_text('{"vm_dir":"vm"}', encoding="utf-8")
    (cai / "bao-dong.json").write_text('{"da_gui":["canh-bao-1"]}', encoding="utf-8")
    (cai / "mang-youtube.json").write_text('{"UCthat":"K1"}', encoding="utf-8")
    (cai / "CLAUDE.local.md").write_text("# luat rieng may nay", encoding="utf-8")
    done = cai / "DONE" / "mot-video"
    done.mkdir(parents=True)
    (done / "xong.txt").write_text("video that da san xuat xong", encoding="utf-8")

    # `CHANNEL/K1` — kênh RIÊNG của khách, chỉ có trong `cai`, không có trong
    # bản mới (tránh nhánh hoà `CHANNEL` xen vào bài kiểm rollback bên dưới —
    # luật hoà `CHANNEL` đã có bài kiểm riêng ở test_cap_nhat_tai_cho.py).
    ch = cai / "CHANNEL" / "K1"
    ch.mkdir(parents=True)
    (ch / "kenh.yaml").write_text("ma: K1\nkenh_rieng: true\n", encoding="utf-8")


def _dung_vm_moi(moi: Path) -> None:
    """`vm/` của BẢN MỚI: chỉ mang mã, đúng như một gói phát hành thật (trạng
    thái máy thật bị `.gitignore` chặn khỏi mọi gói phát đi)."""
    vm = moi / "vm"
    vm.mkdir(parents=True, exist_ok=True)
    (vm / "agent.py").write_text("# ma MOI cua agent", encoding="utf-8")
    (vm / "may_dang.py").write_text("# ma MOI cua may_dang", encoding="utf-8")

    # Cố tình VẪN đưa vài tên "trạng thái" vào bản mới — đúng cảnh thật nhất:
    # phải chứng minh `_la_trang_thai_may` tự chặn được, không phải vì bản
    # mới "quên mang theo".
    (vm / "config.json").write_text('{"tram":"khong duoc dung cai nay"}', encoding="utf-8")

    ti = vm / "tien-ich" / "K1"
    ti.mkdir(parents=True)
    (ti / "manifest.json").write_text('{"version":"moi"}', encoding="utf-8")
    (ti / "cau-hinh.json").write_text('{"bat":"khong duoc dung cai nay"}', encoding="utf-8")
    (ti / "content.js").write_text("// ma MOI cua content.js", encoding="utf-8")


@pytest.fixture
def san(tmp_path):
    cai = _dung_ban(tmp_path / "MyTool", "2.132.0", "ban cu")
    _dung_vm_cu(cai)
    moi = _dung_ban(tmp_path / "cho-dung" / "2.133.0", "2.133.0", "ban moi")
    _dung_vm_moi(moi)
    return tmp_path, cai, moi


def _sha(duong: Path) -> str:
    return hashlib.sha256(duong.read_bytes()).hexdigest()


def _hash_cay(goc: Path) -> dict:
    return {str(p.relative_to(goc).as_posix()): _sha(p)
           for p in sorted(goc.rglob("*")) if p.is_file()}


#: Mọi tệp TRẠNG THÁI MÁY THẬT phải sống sót qua một lượt `apply_tai_cho`,
#: nguyên byte — đây là danh sách dùng để soi TRƯỚC/SAU trong bài kiểm chính.
_DUONG_TRANG_THAI = (
    "vm/config.json", "vm/cai-dat-tool.json", "vm/trang-thai.json",
    "vm/tokens/K1.json", "vm/clients/client.json", "vm/replied/K1.txt",
    "vm/logs/so-video-id.json", "vm/logs/kenh-uc.json",
    "vm/tien-ich/K1/cau-hinh.json",
    "vps.json", "bao-dong.json", "mang-youtube.json", "CLAUDE.local.md",
    "DONE/mot-video/xong.txt",
)
#: Mã trong `vm/` phải nhận bản MỚI — đối lập với danh sách trên.
_DUONG_MA_VM = (
    "vm/agent.py", "vm/may_dang.py", "vm/tien-ich/K1/manifest.json",
    "vm/tien-ich/K1/content.js",
)


class TestVmGiuTrangThaiMayThat:
    """Kịch bản 1–3 của Phần 3: trạng thái giữ nguyên, mã lên bản mới."""

    def test_trang_thai_khong_doi_mot_byte(self, san):
        _goc, cai, moi = san
        truoc = {p: _sha(cai / p) for p in _DUONG_TRANG_THAI}

        apply_tai_cho(moi, cai)

        for p in _DUONG_TRANG_THAI:
            assert _sha(cai / p) == truoc[p], "trạng thái bị đổi: " + p

    def test_ma_trong_vm_da_len_ban_moi(self, san):
        _goc, cai, moi = san
        apply_tai_cho(moi, cai)

        assert (cai / "vm" / "agent.py").read_text(encoding="utf-8") == \
            "# ma MOI cua agent"
        assert (cai / "vm" / "may_dang.py").read_text(encoding="utf-8") == \
            "# ma MOI cua may_dang"
        assert (cai / "vm" / "tien-ich" / "K1" / "manifest.json").read_text(
            encoding="utf-8") == '{"version":"moi"}'
        assert (cai / "vm" / "tien-ich" / "K1" / "content.js").read_text(
            encoding="utf-8") == "// ma MOI cua content.js"

    def test_ma_top_level_ngoai_vm_cung_len_ban_moi(self, san):
        """Bug cũ chỉ ở `vm/` — không được vá kiểu làm hỏng lại luật cũ."""
        _goc, cai, moi = san
        apply_tai_cho(moi, cai)
        assert (cai / "dau-vet.txt").read_text(encoding="utf-8") == "ban moi"
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.133.0"

    def test_kenh_rieng_cua_khach_khong_dung_toi(self, san):
        _goc, cai, moi = san
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "K1" / "kenh.yaml").read_text(
            encoding="utf-8") == "ma: K1\nkenh_rieng: true\n"


class TestRollbackKhiHongGiuaChung:
    """Kịch bản 4: healthcheck hỏng NGAY SAU khi đã hoà `vm/` — phải trả lại
    nguyên trạng CẢ mã lẫn trạng thái, không riêng top-level."""

    def test_hong_thi_current_giong_het_ban_dau(self, san):
        _goc, cai, moi = san
        truoc = _hash_cay(cai)

        so_dem = {"n": 0}

        def hong_o_lan_thu_hai(_duong):
            # Lần 1: soi `staged` trước khi động vào `cai` — phải qua được để
            # vòng dọn + hoà `vm/` thật sự chạy. Lần 2: soi `cai` SAU khi đã
            # chép/hoà xong — đây mới là chỗ ta cố tình cho hỏng.
            so_dem["n"] += 1
            if so_dem["n"] >= 2:
                raise RuntimeError("healthcheck hỏng có chủ đích")

        with pytest.raises(UpdateError):
            apply_tai_cho(moi, cai, healthcheck=hong_o_lan_thu_hai)

        sau = _hash_cay(cai)
        thieu = set(truoc) - set(sau)
        thua = set(sau) - set(truoc)
        khac = {p for p in set(truoc) & set(sau) if truoc[p] != sau[p]}
        assert not thieu, "mất tệp sau khi lùi: " + repr(thieu)
        assert not thua, "thừa tệp sau khi lùi: " + repr(thua)
        assert not khac, "tệp đổi nội dung sau khi lùi: " + repr(khac)
        assert sau == truoc


# ── Phần 2: core/nguon_cap_nhat.py (manifest qua raw.githubusercontent.com) ─


def _tai_gia(bang: dict):
    """`tai` giả: `bang` ánh xạ URL (hay đuôi URL) → bytes trả về."""
    def tai(url: str) -> bytes:
        for khoa, gia_tri in bang.items():
            if url == khoa or url.endswith(khoa):
                return gia_tri
        raise AssertionError("URL không có trong bảng giả: " + url)
    return tai


class TestKhongHaBan:
    def test_manifest_cu_hon_khong_ap_dung(self):
        cfg = {"kho": "acme/tool", "nhanh": "main", "kenh": "on-dinh"}
        manifest = json.dumps({
            "version": "2.100.0",
            "files": [{"path": "a.py", "sha256": "0" * 64}],
        }).encode("utf-8")
        assert ncn.kiem_ban_moi(cfg, "2.132.0", lambda _u: manifest) is None

    def test_manifest_bang_ban_dang_dung_khong_ap_dung(self):
        cfg = {"kho": "acme/tool"}
        manifest = json.dumps({
            "version": "2.132.0",
            "files": [{"path": "a.py", "sha256": "0" * 64}],
        }).encode("utf-8")
        assert ncn.kiem_ban_moi(cfg, "2.132.0", lambda _u: manifest) is None

    def test_chua_cau_hinh_kho_thi_khong_hoi_mang(self):
        cfg = {"kho": ""}

        def no_bung(_url):
            raise AssertionError("không được gọi tai() khi kho rỗng")

        assert ncn.kiem_ban_moi(cfg, "2.132.0", no_bung) is None

    def test_ban_moi_hon_thi_tra_manifest(self):
        cfg = {"kho": "acme/tool"}
        manifest = json.dumps({
            "version": "2.140.0",
            "files": [{"path": "a.py", "sha256": "0" * 64, "size": 3}],
        }).encode("utf-8")
        ra = ncn.kiem_ban_moi(cfg, "2.132.0", lambda _u: manifest)
        assert ra is not None
        assert ra["version"] == "2.140.0"


class TestManifestSaiShaBiTuChoiToanBo:
    def test_mot_tep_sai_sha_thi_khong_ghi_gi_ca(self, tmp_path):
        noi_dung_dung = b"print('shopapi')\n"
        sha_dung = hashlib.sha256(noi_dung_dung).hexdigest()
        manifest = {
            "version": "2.140.0",
            "files": [
                {"path": "a.py", "sha256": sha_dung},
                # Khai SHA của "noi dung dung", nhưng `tai` giả bên dưới trả
                # về một nội dung KHÁC cho tệp này — mô phỏng tải hỏng/bị đổi.
                {"path": "b.py", "sha256": sha_dung},
            ],
        }

        def tai(url: str) -> bytes:
            if url.endswith("a.py"):
                return noi_dung_dung
            if url.endswith("b.py"):
                return b"noi dung khac hoan toan"
            raise AssertionError(url)

        cfg = {"kho": "acme/tool", "nhanh": "main"}
        thu_muc_dung = tmp_path / "cho-dung"

        with pytest.raises(UpdateError):
            ncn.tai_va_dung_san(cfg, manifest, thu_muc_dung, tai)

        # Từ chối TOÀN BỘ: không một tệp nào được ghi ra đĩa.
        assert not list(thu_muc_dung.iterdir())

    def test_duong_dan_thoat_khoi_thu_muc_bi_chan(self, tmp_path):
        manifest = {
            "version": "2.140.0",
            "files": [{"path": "../../thoat-ra-ngoai.py", "sha256": "0" * 64}],
        }
        cfg = {"kho": "acme/tool"}
        with pytest.raises(UpdateError):
            ncn.tai_va_dung_san(cfg, manifest, tmp_path / "cho-dung",
                                lambda _u: b"noi dung")


class TestGiuToiDa2BanRollback:
    def test_giu_dung_2_ban_gan_nhat(self, tmp_path):
        cai = _dung_ban(tmp_path / "MyTool", "2.130.0")

        # Lượt 1: 2.130.0 -> 2.131.0. Chưa có `.rollback` nào từ trước.
        ncn.giu_toi_da_2_ban_rollback(cai, "2.130.0")
        moi1 = _dung_ban(tmp_path / "cho-dung" / "2.131.0", "2.131.0")
        apply_tai_cho(moi1, cai)

        # Lượt 2: 2.131.0 -> 2.132.0. `.rollback` hiện có (VERSION=2.130.0)
        # phải được đặt tên lại trước khi `apply_tai_cho` xoá sạch nó.
        ncn.giu_toi_da_2_ban_rollback(cai, "2.131.0")
        moi2 = _dung_ban(tmp_path / "cho-dung" / "2.132.0", "2.132.0")
        apply_tai_cho(moi2, cai)

        # Lượt 3: 2.132.0 -> 2.133.0.
        ncn.giu_toi_da_2_ban_rollback(cai, "2.132.0")
        moi3 = _dung_ban(tmp_path / "cho-dung" / "2.133.0", "2.133.0")
        apply_tai_cho(moi3, cai)

        dat_ten = sorted(
            p.name for p in cai.parent.iterdir()
            if p.name.startswith(cai.name + ".rollback-"))
        assert dat_ten == ["MyTool.rollback-2.130.0", "MyTool.rollback-2.131.0"], dat_ten

        # Lượt 4: phải có ĐÚNG 2 bản, bản 2.130.0 (cũ nhất) bị dọn.
        ncn.giu_toi_da_2_ban_rollback(cai, "2.133.0")
        moi4 = _dung_ban(tmp_path / "cho-dung" / "2.134.0", "2.134.0")
        apply_tai_cho(moi4, cai)

        dat_ten = sorted(
            p.name for p in cai.parent.iterdir()
            if p.name.startswith(cai.name + ".rollback-"))
        assert dat_ten == ["MyTool.rollback-2.131.0", "MyTool.rollback-2.132.0"], dat_ten

    def test_chua_co_rollback_thi_khong_lam_gi(self, tmp_path):
        cai = _dung_ban(tmp_path / "MyTool", "2.130.0")
        ncn.giu_toi_da_2_ban_rollback(cai, "2.130.0")  # không được ném lỗi
        assert not any(
            p.name.startswith(cai.name + ".rollback")
            for p in cai.parent.iterdir())


class TestDocCauHinh:
    def test_thieu_tep_thi_an_toan_khong_cap_nhat(self, tmp_path):
        cfg = ncn.doc_cau_hinh(str(tmp_path))
        assert cfg["kho"] == ""
        assert cfg["chinh_sach"] in ("hoi", "khung_an_toan")

    def test_tep_hong_json_thi_an_toan_khong_cap_nhat(self, tmp_path):
        (tmp_path / "cap-nhat.json").write_text("{khong phai json", encoding="utf-8")
        cfg = ncn.doc_cau_hinh(str(tmp_path))
        assert cfg["kho"] == ""

    def test_may_nha_mac_dinh_hoi(self, tmp_path):
        (tmp_path / "cap-nhat.json").write_text(
            json.dumps({"kho": "acme/tool"}), encoding="utf-8")
        cfg = ncn.doc_cau_hinh(str(tmp_path))
        assert cfg["chinh_sach"] == "hoi"

    def test_vps_mac_dinh_khung_an_toan(self, tmp_path):
        (tmp_path / "vps.json").write_text('{"vm_dir":"vm"}', encoding="utf-8")
        (tmp_path / "cap-nhat.json").write_text(
            json.dumps({"kho": "acme/tool"}), encoding="utf-8")
        cfg = ncn.doc_cau_hinh(str(tmp_path))
        assert cfg["chinh_sach"] == "khung_an_toan"

    def test_khoa_da_khai_thi_ton_trong_nguyen_van(self, tmp_path):
        (tmp_path / "vps.json").write_text('{"vm_dir":"vm"}', encoding="utf-8")
        (tmp_path / "cap-nhat.json").write_text(
            json.dumps({"kho": "acme/tool", "chinh_sach": "tat"}), encoding="utf-8")
        cfg = ncn.doc_cau_hinh(str(tmp_path))
        assert cfg["chinh_sach"] == "tat"

    def test_duoc_phep_hien_nut_can_ca_kho_lan_chinh_sach(self, tmp_path):
        assert ncn.duoc_phep_hien_nut(str(tmp_path)) is False
        (tmp_path / "cap-nhat.json").write_text(
            json.dumps({"kho": "", "chinh_sach": "khung_an_toan"}), encoding="utf-8")
        assert ncn.duoc_phep_hien_nut(str(tmp_path)) is False, \
            "kho rỗng thì dù chính sách gì cũng không được hiện nút"
        (tmp_path / "cap-nhat.json").write_text(
            json.dumps({"kho": "acme/tool", "chinh_sach": "tat"}), encoding="utf-8")
        assert ncn.duoc_phep_hien_nut(str(tmp_path)) is False
        (tmp_path / "cap-nhat.json").write_text(
            json.dumps({"kho": "acme/tool", "chinh_sach": "hoi"}), encoding="utf-8")
        assert ncn.duoc_phep_hien_nut(str(tmp_path)) is True


class TestApDung:
    def test_chinh_sach_hoi_khong_tu_ap(self, san):
        _goc, cai, moi = san
        cfg = {"kho": "acme/tool", "nhanh": "main", "kenh": "on-dinh", "chinh_sach": "hoi"}
        ra = ncn.ap_dung(str(cai), cfg, {"version": "2.133.0"}, moi)
        assert ra["da_ap_dung"] is False
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.132.0", \
            "chinh_sach=hoi không được tự áp gì cả"

    def test_chinh_sach_tat_khong_tu_ap(self, san):
        _goc, cai, moi = san
        cfg = {"kho": "acme/tool", "chinh_sach": "tat"}
        ra = ncn.ap_dung(str(cai), cfg, {"version": "2.133.0"}, moi)
        assert ra["da_ap_dung"] is False

    def test_khung_an_toan_ap_khi_an_toan(self, san, monkeypatch):
        _goc, cai, moi = san
        import core.an_toan_khoi_dong as atkd

        monkeypatch.setattr(atkd, "kiem_tra",
                            lambda *_a, **_k: {"duoc": True, "ly_do": []})
        cfg = {"kho": "acme/tool", "chinh_sach": "khung_an_toan"}
        ra = ncn.ap_dung(str(cai), cfg, {"version": "2.133.0"}, moi,
                         healthcheck_sau=lambda _g: None)
        assert ra["da_ap_dung"] is True
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.133.0"
        # Trạng thái vẫn phải nguyên — `ap_dung` chỉ là lớp điều phối trên
        # `apply_tai_cho`, không đổi luật giữ trạng thái.
        assert (cai / "vm" / "config.json").read_text(encoding="utf-8") == \
            '{"tram":"http://cu:8765"}'

    def test_khung_an_toan_khong_ap_khi_chua_an_toan(self, san, monkeypatch):
        _goc, cai, moi = san
        import core.an_toan_khoi_dong as atkd

        monkeypatch.setattr(
            atkd, "kiem_tra",
            lambda *_a, **_k: {"duoc": False, "ly_do": ["đang đăng dở"]})
        cfg = {"kho": "acme/tool", "chinh_sach": "khung_an_toan"}
        ra = ncn.ap_dung(str(cai), cfg, {"version": "2.133.0"}, moi)
        assert ra["da_ap_dung"] is False
        assert (cai / "VERSION").read_text(encoding="utf-8").strip() == "2.132.0"

    def test_healthcheck_sau_hong_thi_khoi_phuc(self, san, monkeypatch):
        """`ap_dung` phải tự lùi khi healthcheck SAU (import module thật)
        phát hiện hỏng — đúng cảnh `apply_tai_cho` không tự biết được vì nó
        chỉ soi cây tệp, không import thật."""
        _goc, cai, moi = san
        import core.an_toan_khoi_dong as atkd

        monkeypatch.setattr(atkd, "kiem_tra",
                            lambda *_a, **_k: {"duoc": True, "ly_do": []})
        truoc = _hash_cay(cai)

        def hong(_goc):
            raise ImportError("mo-phong mot module chinh khong nap duoc")

        cfg = {"kho": "acme/tool", "chinh_sach": "khung_an_toan"}
        with pytest.raises(UpdateError):
            ncn.ap_dung(str(cai), cfg, {"version": "2.133.0"}, moi,
                       healthcheck_sau=hong)

        sau = _hash_cay(cai)
        assert sau == truoc, "phải khôi phục nguyên trạng khi healthcheck sau hỏng"
