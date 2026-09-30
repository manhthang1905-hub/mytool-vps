"""Vá `vm/may_dang.py` để "sẵn sàng chạy lại" (26/09/2026, xem workspace/
ban-va/2026-09-26-va-may-dang/GHI-CHU.md).

Log `vm/logs/dang.log` dừng từ 02/09 vì `tu_dang` đang TẮT cả 4 kênh — KHÔNG
phải lỗi. Nhưng rà lại `may_dang.py` cho VPS nhiều-kênh (kênh cạnh MyTool\\,
không phải cạnh vm\\ — xem CLAUDE.local.md + NHAT-KY-PHAT-TRIEN.md mục "Gộp
toàn bộ VPS vào một thư mục MyTool") lộ ra `discover_channels()` đang quét
SAI một cấp thư mục: nó chỉ thấy kênh nếu chúng nằm NGAY CẠNH `vm/`, trong
khi VPS thật (agent.py đã vá đúng, `_cac_goc_trinh_duyet`) có kênh nằm cạnh
CHÍNH `MyTool\\` (thư mục cha của `MyTool`). Bật `tu_dang` mà chưa vá thì
máy đăng sẽ "chết im lặng" giống hệt agent.py từng gặp trước khi được vá.

Các bài dưới test từng hàm THUẦN bằng cách cắt mã nguồn + exec (không nạp cả
module `vm/may_dang.py` — nó đụng pyautogui/DPI-awareness/di chuyển cửa sổ
console lúc import, đúng lý do `tests/test_vm_phien.py::_tai_ham_thuan` đã
né từ trước)."""

from __future__ import annotations

import json
import os
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
_SRC = (GOC / "vm" / "may_dang.py").read_text(encoding="utf-8")


def _khoi(ten_ham, ten_ham_ke_tiep):
    """Cắt NGUYÊN VĂN từ `def ten_ham` tới ngay trước `def ten_ham_ke_tiep`."""
    return "def " + ten_ham + _SRC.split("def " + ten_ham)[1].split("\ndef " + ten_ham_ke_tiep)[0]


def _tai_ham_thuan(ten_ham, ten_ham_ke_tiep, ns_them=None):
    ns: dict = {"os": os}
    ns.update(ns_them or {})
    exec(_khoi(ten_ham, ten_ham_ke_tiep), ns)  # noqa: S102 — cắt mã của chính kho
    return ns[ten_ham]


class TestCoKiem:
    """Cờ dòng lệnh `--kiem` (chạy thử, không đăng gì) — RIÊNG với
    `--mot-lan`/`--kenh` để không đụng bài test đã khoá `_doc_co_dong_lenh`."""

    def test_co_co(self):
        ham = _tai_ham_thuan("_co_kiem", "_loc_kenh")
        assert ham(["--kiem"]) is True
        assert ham(["--kenh", "TL1-T7", "--mot-lan"]) is False
        assert ham([]) is False


class TestDiscoverChannelsVPSLongNhau:
    """`discover_channels()` — kênh cạnh `MyTool\\` (VPS nhiều-kênh, có
    `vps.json`/`CHANNEL` cạnh `vm/`) phải được thấy, KHÔNG chỉ kênh cạnh
    thẳng `vm/` (nếp cũ D:\\{GROUP}\\upload\\dang.py)."""

    def _ham(self):
        return _tai_ham_thuan("_thu_muc_do_tim_kenh", "discover_channels",
                              ns_them={"logging": __import__("logging")})

    def _nap_ca_hai(self, upload_dir):
        khoi = (_khoi("_thu_muc_do_tim_kenh", "discover_channels")
               + "def discover_channels():"
               + _SRC.split("def discover_channels():")[1].split("\nIDX_TAG_AL")[0])
        ns = {"os": os, "logging": __import__("logging"), "_UPLOAD_DIR": str(upload_dir)}
        exec(khoi, ns)  # noqa: S102
        return ns["discover_channels"], ns["_thu_muc_do_tim_kenh"]

    def test_nep_cu_mot_cap_khong_doi(self, tmp_path):
        """Máy MỘT kênh nếp cũ (không vps.json/CHANNEL cạnh vm/) — y hệt
        hành vi trước khi vá: chỉ quét cạnh `upload/`(=vm/)."""
        goc = tmp_path / "D_GROUP"
        upload = goc / "upload"
        upload.mkdir(parents=True)
        kenh = goc / "TL9-X"
        kenh.mkdir()
        (kenh / "TL9-X.exe").write_bytes(b"")
        discover, thu_muc = self._nap_ca_hai(upload)
        assert thu_muc(str(upload)) == [str(goc)]
        ds = discover()
        assert [c["code"] for c in ds] == ["TL9-X"]

    def test_vps_long_nhau_thay_ca_hai_cap(self, tmp_path):
        """VPS đóng gói: `vm/` nằm TRONG `MyTool/`, kênh nằm cạnh MyTool
        (thư mục CHA của MyTool) — đúng bố cục thật trên VPS 26/09/2026."""
        cha_mytool = tmp_path / "TL"
        mytool = cha_mytool / "MyTool"
        vm = mytool / "vm"
        vm.mkdir(parents=True)
        (mytool / "vps.json").write_text("{}", encoding="utf-8")
        for ma in ("TL1-T7", "TL2-T7"):
            k = cha_mytool / ma
            k.mkdir()
            (k / (ma + ".exe")).write_bytes(b"")
        discover, thu_muc = self._nap_ca_hai(vm)
        goc_tim = thu_muc(str(vm))
        assert str(mytool) in goc_tim and str(cha_mytool) in goc_tim
        ds = discover()
        assert sorted(c["code"] for c in ds) == ["TL1-T7", "TL2-T7"]

    def test_vps_khong_trung_khi_kenh_o_ca_hai_cap(self, tmp_path):
        """Kênh trùng tên xuất hiện ở CẢ HAI cấp (hiếm, nhưng không được
        báo hai lần) — cấp gần `vm/` hơn thắng."""
        cha_mytool = tmp_path / "TL"
        mytool = cha_mytool / "MyTool"
        vm = mytool / "vm"
        vm.mkdir(parents=True)
        (mytool / "CHANNEL").mkdir()
        for goc, ma in ((mytool, "TL1-T7"), (cha_mytool, "TL1-T7")):
            k = goc / ma
            k.mkdir()
            (k / (ma + ".exe")).write_bytes(b"")
        discover, _ = self._nap_ca_hai(vm)
        ds = discover()
        assert [c["code"] for c in ds] == ["TL1-T7"], "không được liệt kê trùng"
        assert ds[0]["dir"] == str(mytool / "TL1-T7"), "cấp gần vm/ hơn thắng"

    def test_khong_thay_kenh_nao_thi_rong(self, tmp_path):
        goc = tmp_path / "trong"
        upload = goc / "upload"
        upload.mkdir(parents=True)
        discover, _ = self._nap_ca_hai(upload)
        assert discover() == []


class TestKiemTraIcon:
    def _ham(self):
        return _tai_ham_thuan("_danh_gia_icon", "_duong_chrome_profile")

    def test_du_ca(self, tmp_path):
        a = tmp_path / "a.png"; a.write_bytes(b"")
        b = tmp_path / "b.png"; b.write_bytes(b"")
        kq = self._ham()([str(a), str(b)])
        assert kq == {"tong": 2, "thieu": [], "ok": True}

    def test_thieu_mot_thi_bao_ten(self, tmp_path):
        a = tmp_path / "a.png"; a.write_bytes(b"")
        b = tmp_path / "thieu.png"  # không tạo
        kq = self._ham()([str(a), str(b)])
        assert kq["ok"] is False
        assert kq["thieu"] == ["thieu.png"]


class TestChromeProfile:
    def _ham(self):
        src = (_khoi("_duong_chrome_profile", "_danh_gia_chrome_profile")
              + _khoi("_danh_gia_chrome_profile", "_danh_gia_man_hinh"))
        ns = {"os": os}
        exec(src, ns)  # noqa: S102
        return ns["_duong_chrome_profile"], ns["_danh_gia_chrome_profile"]

    def test_duong_dung_quy_uoc(self):
        duong_ham, _ = self._ham()
        assert duong_ham(r"C:\Users\x\Documents\TL", "TL1-T7") == \
            os.path.join(r"C:\Users\x\Documents\TL", "TL1-T7", "Data", "profile")

    def test_co_va_khong_co(self, tmp_path):
        _, danh_gia = self._ham()
        co = tmp_path / "TL1-T7" / "Data" / "profile"
        co.mkdir(parents=True)
        kq = danh_gia(str(tmp_path), ["TL1-T7", "TL2-T7"])
        assert kq["TL1-T7"]["ok"] is True
        assert kq["TL2-T7"]["ok"] is False


class TestDanhGiaManHinh:
    def _ham(self):
        return _tai_ham_thuan("_danh_gia_man_hinh", "_dong_bao_cao_kiem")

    def test_man_hinh_du_lon(self):
        kq = self._ham()((1920, 1080), [(534, 86, "henlich.png"), (806, 49, "doitai.png")])
        assert kq["ok"] is True

    def test_man_hinh_qua_nho(self):
        kq = self._ham()((640, 480), [(806, 49, "doitai.png")])
        assert kq["ok"] is False

    def test_khong_co_kich_thuoc_man_hinh(self):
        kq = self._ham()(None, [(806, 49, "doitai.png")])
        assert kq["ok"] is False


class TestDoDang:
    """Dấu vết "đang đăng dở" (`vm/logs/dang-dodang.json`) — luật riêng VPS
    "đang đăng thì không giết" (CLAUDE.local.md) cần thấy MÃ nào đang dở,
    không chỉ biết tiến trình còn sống hay không."""

    def _ham(self, duong_json):
        src = _khoi("_ghi_dodang", "wait_and_click_image")
        ns = {"os": os, "json": __import__("json"), "time": __import__("time"),
             "DUONG_DODANG": str(duong_json)}
        exec(src, ns)  # noqa: S102
        return ns["_ghi_dodang"], ns["_xoa_dodang"]

    def test_ghi_roi_xoa(self, tmp_path):
        duong = tmp_path / "logs" / "dang-dodang.json"
        ghi, xoa = self._ham(duong)
        ghi("TL1-T7", "TL1-0007")
        assert duong.is_file()
        noi_dung = duong.read_text(encoding="utf-8")
        assert "TL1-T7" in noi_dung and "TL1-0007" in noi_dung
        xoa()
        assert not duong.exists()

    def test_xoa_khi_chua_ghi_khong_loi(self, tmp_path):
        _, xoa = self._ham(tmp_path / "logs" / "khong-ton-tai.json")
        xoa()  # không được ném lỗi


class TestDoAnhDaTyLe:
    """S9.5 (vá 28/09/2026, xem workspace/ban-va/2026-09-28-may-dang-da-ti-le/
    GHI-CHU.md) — sự cố TL1-T7-0005: Chrome kênh tự cập nhật 143->151 và/hoặc
    zoom trang khác 100% làm nút "Tiếp" hiển thị chỉ ~73% kích thước ảnh mẫu
    tiep.png (59x34 -> ~43x25 thật), dò 1 tỉ lệ duy nhất tụt dưới sàn 0.50 dù
    CÙNG một nút -> "Het thoi gian cho: tiep.png", 0/1 mã. Dò đa tỉ lệ là
    đường lùi thay cho hạ ngưỡng (không được hạ, kiểm toán trước đã cảnh báo
    0.55 dễ bấm nhầm)."""

    def _nap(self):
        import pyscreeze
        src = _khoi("_ghi_dodang", "wait_and_click_image")
        ns = {"os": os, "json": __import__("json"), "time": __import__("time"),
             "logging": __import__("logging"), "DUONG_DODANG": "unused",
             "pyscreeze": pyscreeze}
        exec(src, ns)  # noqa: S102 — cắt mã của chính kho
        return ns

    def _fake_pyautogui(self, haystack_path):
        import pyscreeze
        from PIL import Image

        class _Fake:
            @staticmethod
            def locateOnScreen(needle, confidence=0.85, grayscale=True, region=None):
                haystack = Image.open(haystack_path)
                return pyscreeze.locate(needle, haystack, confidence=confidence,
                                        grayscale=grayscale)
        return _Fake()

    def _dan_nut_thu_nho(self, tmp_path, ty_le, vi_tri=(1258, 966)):
        """Tạo ảnh 'màn hình' giả 1920x1080, dán tiep.png đã co theo `ty_le`
        vào `vi_tri` — mô phỏng đúng sự cố thật (nút nhỏ hơn ảnh mẫu)."""
        from PIL import Image
        goc = GOC / "vm" / "icon" / "tiep.png"
        mau = Image.open(goc).convert("RGB")
        w, h = mau.size
        nut = mau.resize((max(1, round(w * ty_le)), max(1, round(h * ty_le))), Image.LANCZOS)
        canvas = Image.new("RGB", (1920, 1080), (32, 33, 36))
        canvas.paste(nut, vi_tri)
        duong = tmp_path / "haystack.png"
        canvas.save(duong)
        return duong, nut.size

    def test_khong_thay_o_1_ti_le_khi_nut_nho_hon(self, tmp_path):
        """Trước vá: dò ĐÚNG 1 tỉ lệ (ảnh mẫu gốc) không thấy nút đã co 0.73
        — tái hiện đúng "Het thoi gian cho: tiep.png" của sự cố thật."""
        goc = GOC / "vm" / "icon" / "tiep.png"
        if not goc.is_file():
            import pytest
            pytest.skip("khong co vm/icon/tiep.png tren may nay")
        from PIL import Image
        import pyscreeze
        duong, _ = self._dan_nut_thu_nho(tmp_path, 0.73)
        haystack = Image.open(duong)
        mau = Image.open(goc)
        try:
            box = pyscreeze.locate(mau, haystack, confidence=0.50, grayscale=True)
        except pyscreeze.ImageNotFoundException:
            box = None
        assert box is None, "dò 1 tỉ lệ đáng lẽ KHÔNG thấy — nếu thấy thì bài test không mô phỏng đúng sự cố"

    def test_da_ti_le_thay_nut_nho_hon_anh_mau(self, tmp_path):
        """SAU vá: `_do_anh_da_ty_le` phải thấy nút đã co 0.73 (đúng tỉ lệ đo
        được từ ảnh bằng chứng 28/09/2026), ở SÀN cũ 0.50 (không hạ ngưỡng)."""
        goc = GOC / "vm" / "icon" / "tiep.png"
        if not goc.is_file():
            import pytest
            pytest.skip("khong co vm/icon/tiep.png tren may nay")
        vi_tri = (1258, 966)
        duong, (nw, nh) = self._dan_nut_thu_nho(tmp_path, 0.73, vi_tri)
        ns = self._nap()
        ns["pyautogui"] = self._fake_pyautogui(duong)
        do_da_ty_le = ns["_do_anh_da_ty_le"]

        box = do_da_ty_le(str(goc), confidence=0.50, grayscale=True)
        assert box is not None, "da ti le van khong thay nut da co 0.73"
        cx, cy = box.left + box.width // 2, box.top + box.height // 2
        # Tam nut that ~ (1258+43/2, 966+25/2) = (~1279, ~978) - dung nhu
        # bao cao "HIỆN RÕ ở góc dưới phải hộp thoại (~x1258-1301, y967-990)".
        tam_that_x, tam_that_y = vi_tri[0] + nw / 2, vi_tri[1] + nh / 2
        assert abs(cx - tam_that_x) <= 6, f"lech tam X qua nhieu: {cx} vs {tam_that_x}"
        assert abs(cy - tam_that_y) <= 6, f"lech tam Y qua nhieu: {cy} vs {tam_that_y}"

    def test_nho_ti_le_khop_de_thu_truoc_lan_sau(self, tmp_path):
        """Yêu cầu bản vá: nhớ tỉ lệ đã khớp trong PHIÊN này, thử tỉ lệ đó
        TRƯỚC ở lần dò kế tiếp (đỡ quét lại toàn bộ danh sách tỉ lệ)."""
        goc = GOC / "vm" / "icon" / "tiep.png"
        if not goc.is_file():
            import pytest
            pytest.skip("khong co vm/icon/tiep.png tren may nay")
        duong, _ = self._dan_nut_thu_nho(tmp_path, 0.73)
        ns = self._nap()
        ns["pyautogui"] = self._fake_pyautogui(duong)
        do_da_ty_le = ns["_do_anh_da_ty_le"]

        assert do_da_ty_le(str(goc), confidence=0.50, grayscale=True) is not None
        nho = ns["_TY_LE_KHOP_GAN_NHAT"]
        assert str(goc) in nho
        ty_le_nho = nho[str(goc)]
        assert abs(ty_le_nho - 1.0) > 1e-9, "phai nho mot ti le KHAC 1.0 (0.73 gan nhat trong danh sach)"

    def test_anh_bang_chung_that_28_09(self):
        """Kiểm trên ẢNH BẰNG CHỨNG THẬT của sự cố (nếu còn trên máy này —
        `_don_bot_anh_loi` có thể đã dọn bớt ảnh cũ, nên bỏ qua nếu không còn)
        — tiep.png phải khớp gần đúng vị trí nút thật (~1279,978), độ tin cao."""
        import pytest
        anh_that = GOC / "vm" / "logs" / "anh-loi" / "20260928-143716-het-han-tiep.png"
        goc_mau = GOC / "vm" / "icon" / "tiep.png"
        if not anh_that.is_file() or not goc_mau.is_file():
            pytest.skip("khong con anh bang chung that tren may nay")
        ns = self._nap()
        ns["pyautogui"] = self._fake_pyautogui(anh_that)
        do_da_ty_le = ns["_do_anh_da_ty_le"]

        box = do_da_ty_le(str(goc_mau), confidence=0.80, grayscale=True)
        assert box is not None, "khong thay tiep.png tren anh bang chung that o nguong >= 0.80"
        cx, cy = box.left + box.width // 2, box.top + box.height // 2
        assert abs(cx - 1279) <= 15 and abs(cy - 978) <= 15, (
            f"vi tri khop ({cx},{cy}) lech qua xa nut that (~1279,978)")


class TestDonTempAnToan:
    """`_don_temp_an_toan` (vá 28/09/2026, xem workspace/ban-va/
    2026-09-28-may-dang-da-ti-le/GHI-CHU.md) — bản trước gọi
    `cmd /c del /q /f /s "%temp%\\*.*"`, xoá ĐỆ QUY SẠCH toàn bộ %TEMP% của
    tài khoản, kể cả thư mục con của MỌI tiến trình khác đang dùng chung
    %TEMP% (nghi giết tiến trình nền của các phiên Claude Code khác chiều
    28/09/2026). Bản vá CHỈ xoá file rác CŨ nằm THẲNG ở gốc %TEMP%, không
    bao giờ đụng vào thư mục con."""

    def _ham(self):
        return _tai_ham_thuan(
            "_don_temp_an_toan", "close_browsers_gently_in_rdp",
            ns_them={"time": __import__("time"), "tempfile": __import__("tempfile")})

    def test_khong_dung_vao_thu_muc_con(self, tmp_path, monkeypatch):
        """Thư mục con (dù tên gì, dù file bên trong cũ tới đâu) KHÔNG BAO
        GIỜ bị đụng tới — đây là chỗ tiến trình KHÁC (vd Claude Code) giữ
        trạng thái riêng của nó trong %TEMP% dùng chung."""
        monkeypatch.setenv("TEMP", str(tmp_path))
        thu_muc_con = tmp_path / "claude" / "mot-phien"
        thu_muc_con.mkdir(parents=True)
        tep_trong_con = thu_muc_con / "trang-thai.json"
        tep_trong_con.write_text("{}", encoding="utf-8")
        # Lam file "cu" (mtime lui ve 10 gio truoc) de neu ham co loi dung
        # vao thu muc con thi se lo ngay o day.
        cu = __import__("time").time() - 10 * 3600
        os.utime(tep_trong_con, (cu, cu))

        ham = self._ham()
        so_xoa = ham(gio_cu_toi_thieu=2.0)

        assert thu_muc_con.is_dir(), "KHONG duoc xoa thu muc con"
        assert tep_trong_con.is_file(), "KHONG duoc dung vao file trong thu muc con"
        assert so_xoa == 0

    def test_xoa_file_cu_o_goc_giu_file_moi(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TEMP", str(tmp_path))
        cu = tmp_path / "rac-cu.tmp"
        moi = tmp_path / "vua-tao.tmp"
        cu.write_text("x", encoding="utf-8")
        moi.write_text("x", encoding="utf-8")
        gio_cu = __import__("time").time() - 10 * 3600
        os.utime(cu, (gio_cu, gio_cu))
        # 'moi' giu nguyen mtime = vua tao

        ham = self._ham()
        so_xoa = ham(gio_cu_toi_thieu=2.0)

        assert not cu.exists(), "file rac cu o GOC phai duoc xoa"
        assert moi.exists(), "file VUA TAO o goc KHONG duoc xoa (co the dang duoc dung)"
        assert so_xoa == 1

    def test_khong_co_temp_khong_loi(self, monkeypatch):
        monkeypatch.delenv("TEMP", raising=False)
        monkeypatch.delenv("TMP", raising=False)
        ham = self._ham()
        ham()  # khong duoc nem loi du moi truong thieu bien TEMP/TMP


class TestVatCanBatThuong:
    """S9.6 (vá 28/09/2026) — hộp thoại Chrome xin quyền xem tab
    ("Allow studio.youtube.com to see this tab?") + nút "Thử lại" của Man
    hinh ket thuc bị lỗi, cắt từ ảnh bằng chứng sự cố đăng lại TL1-T7-0005
    16:25 28/09/2026 (`vm/logs/anh-loi/20260928-162553-khong-thay-henlich.png`)."""

    def test_khong_con_lenh_xoa_dem_qui_temp(self):
        """Bảo vệ hồi quy: KHÔNG được gọi lại lệnh xoá đệ quy sạch %TEMP%
        (chỉ kiểm mã THỰC THI qua open_run_and_execute — không tính dòng
        docstring/chú thích kể lại lịch sử sự cố)."""
        goi_thuc_thi = 'open_run_and_execute(\'cmd /c del /q /f /s "%temp%'
        assert goi_thuc_thi not in _SRC, (
            "lenh xoa dem qui %TEMP% da quay lai trong ma THUC THI - day chinh la "
            "thu pham nghi giet tien trinh nen cua tien trinh khac dung chung %TEMP%")

    def test_icon_mau_ton_tai(self):
        import pytest
        for ten in ("huyxemtab.png", "thulai.png"):
            duong = GOC / "vm" / "icon" / ten
            if not duong.is_file():
                pytest.skip(f"khong co vm/icon/{ten} tren may nay")
            assert duong.stat().st_size > 0

    def test_do_duoc_hop_thoai_xin_quyen_tren_anh_bang_chung(self, tmp_path):
        """Kiểm trên ẢNH BẰNG CHỨNG THẬT của sự cố 16:25 — nút Cancel của
        hộp thoại xin quyền xem tab phải dò được ở vị trí đã cắt icon."""
        import pytest
        anh_that = GOC / "vm" / "logs" / "anh-loi" / "20260928-162553-khong-thay-henlich.png"
        goc_mau = GOC / "vm" / "icon" / "huyxemtab.png"
        if not anh_that.is_file() or not goc_mau.is_file():
            pytest.skip("khong con anh bang chung that / icon tren may nay")
        import pyscreeze
        from PIL import Image
        box = pyscreeze.locate(Image.open(goc_mau), Image.open(anh_that),
                               confidence=0.80, grayscale=True)
        assert box is not None, "khong dò được nut Cancel tren chinh anh da cat no ra"


class TestGocDoneKenh:
    """`_goc_done_kenh` — 26/09/2026, đối chiếu dữ liệu THẬT phát hiện
    `LOCAL_DONE_ROOT`/`SERVER_DONE_ROOT` mặc định (`Desktop\\done`, không tồn
    tại trên VPS) LỆCH với `thu_muc_done` thật của kenh.yaml
    (`MyTool\\DONE\\<kênh>`, có file thật) — và `GET /ke-hoach` không mang
    đường này. Trạm mới có thêm `GET /thu-muc-dang?kenh=X`; hàm này dùng nó
    qua `nguon_tool.thu_muc_dang`, có `_cung_may` sẵn có để quyết định."""

    def _ham(self, thu_muc_dang_gia):
        src = (_khoi("_cung_may", "_goc_done_kenh")
              + "def _goc_done_kenh" + _SRC.split("def _goc_done_kenh")[1].split("\nVAN_IPV4")[0])
        ns = {
            "os": os, "logging": __import__("logging"),
            "SERVER_DONE_ROOT_GOC": None, "LOCAL_DONE_ROOT": "",
            "NGUON": "tool", "CFG": {},
            "nguon_tool": type("_NT", (), {"thu_muc_dang": staticmethod(thu_muc_dang_gia)})(),
        }
        exec(src, ns)  # noqa: S102
        return ns["_goc_done_kenh"]

    def test_tram_bao_duong_co_that_tren_dia_thi_dung(self, tmp_path):
        goc = tmp_path / "DONE" / "TL1-T7"
        goc.mkdir(parents=True)
        ham = self._ham(lambda cfg, kenh: str(goc))
        local, server, cung_may = ham("TL1-T7", r"C:\Desktop\done", r"\\tsclient\D\AUTO\done")
        assert local == server == str(goc)
        assert cung_may is True, "cùng một thư mục cho cả hai vai -> chắc chắn cùng máy"

    def test_tram_bao_duong_khong_ton_tai_thi_lui_ve_mac_dinh(self, tmp_path):
        """Trạm trả một đường nhưng thư mục đó KHÔNG có thật trên đĩa (vd
        kenh.yaml khai sai, hoặc gói chưa bàn giao) -> đừng tin mù, lùi về
        mặc định thay vì post_channel() đi tìm ở một chỗ chắc chắn rỗng."""
        ham = self._ham(lambda cfg, kenh: str(tmp_path / "khong-ton-tai"))
        local, server, _ = ham("TL1-T7", r"C:\Desktop\done", r"\\tsclient\D\AUTO\done")
        assert local == r"C:\Desktop\done" and server == r"\\tsclient\D\AUTO\done"

    def test_tram_khong_tra_gi_thi_lui_ve_mac_dinh(self):
        """Trạm tắt / bản cũ chưa có route / kênh chưa khai thu_muc_done."""
        ham = self._ham(lambda cfg, kenh: "")
        local, server, cung_may = ham("TL9-X", r"C:\Desktop\done", r"\\tsclient\D\AUTO\done")
        assert (local, server) == (r"C:\Desktop\done", r"\\tsclient\D\AUTO\done")
        assert cung_may is False, "mặc định cũ là đường UNC -> không phải cùng máy"

    def test_nguon_khong_phai_tool_thi_khong_hoi_tram(self, tmp_path):
        """Máy một-kênh nếp cũ (Google Sheets, `NGUON != 'tool'`) không được
        đụng vào `nguon_tool` — không đổi hành vi một chút nào."""
        def _khong_duoc_goi(cfg, kenh):
            raise AssertionError("khong duoc hoi tram khi NGUON != 'tool'")

        src = (_khoi("_cung_may", "_goc_done_kenh")
              + "def _goc_done_kenh" + _SRC.split("def _goc_done_kenh")[1].split("\nVAN_IPV4")[0])
        ns = {"os": os, "logging": __import__("logging"),
             "SERVER_DONE_ROOT_GOC": None, "LOCAL_DONE_ROOT": "",
             "NGUON": "sheets", "CFG": {},
             "nguon_tool": type("_NT", (), {"thu_muc_dang": staticmethod(_khong_duoc_goi)})()}
        exec(src, ns)  # noqa: S102
        local, server, _ = ns["_goc_done_kenh"]("K1", r"D:\a", r"D:\b")
        assert (local, server) == (r"D:\a", r"D:\b")


class TestKiemTraFileVideo:
    """`_kiem_tra_file_video` — dò file THẬT của từng mã "Sẵn sàng", đúng
    lớp lỗi mà `--kiem` giờ bắt được: kế hoạch báo sẵn sàng nhưng file nằm
    sai thư mục DONE."""

    def _ham(self):
        src = _khoi("_kiem_tra_file_video", "_dong_bao_cao_kiem")
        ns = {"os": os,
             "has_required_files": lambda d: os.path.isfile(os.path.join(d, "co-video.txt"))}
        exec(src, ns)  # noqa: S102
        return ns["_kiem_tra_file_video"]

    def _goi(self, thu_muc, ma):
        d = thu_muc / ma
        d.mkdir(parents=True)
        (d / "co-video.txt").write_text("x", encoding="utf-8")

    def test_tim_thay_het_o_local(self, tmp_path):
        local = tmp_path / "local"
        self._goi(local, "TL1-0001")
        self._goi(local, "TL1-0002")
        kq = self._ham()(["TL1-0001", "TL1-0002"], str(local), str(local))
        assert kq == {"tim_thay": ["TL1-0001", "TL1-0002"], "thieu": [], "ok": True}

    def test_thieu_mot_ma(self, tmp_path):
        local = tmp_path / "local"
        self._goi(local, "TL1-0001")
        kq = self._ham()(["TL1-0001", "TL1-0002"], str(local), str(local))
        assert kq["ok"] is False
        assert kq["thieu"] == ["TL1-0002"]
        assert kq["tim_thay"] == ["TL1-0001"]

    def test_tim_thay_o_server_khi_khong_co_o_local(self, tmp_path):
        local = tmp_path / "local"
        server = tmp_path / "server"
        os.makedirs(local, exist_ok=True)
        self._goi(server, "TL1-0003")
        kq = self._ham()(["TL1-0003"], str(local), str(server))
        assert kq == {"tim_thay": ["TL1-0003"], "thieu": [], "ok": True}


class TestThuMucDangQuaTramThat:
    """`nguon_tool.thu_muc_dang` <-> `core/chi_so_ytb/tram.py` route mới
    `GET /thu-muc-dang` — dựng một `Tram` thật (cổng 0, cùng nếp
    `tests/test_vm_nhieu_kenh.py`), KHÔNG phải gọi mạng thật (loopback nội
    bộ trong chính tiến trình test)."""

    def _nap_nguon_tool(self, tmp_path):
        """Nạp `vm/nguon_tool.py` nhưng đặt `__file__` giả trong `tmp_path`
        — hàm `thu_muc_dang`/`_tai_csv` tự suy thư mục đệm từ `__file__`,
        KHÔNG làm vậy thì bài test ghi thẳng `thu-muc-dang-*.json` vào
        NGUYÊN `vm/` thật của kho (đã dính một lần lúc soạn bài test này)."""
        import importlib.util

        spec = importlib.util.spec_from_file_location("nt_thu_muc_dang", GOC / "vm" / "nguon_tool.py")
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(tmp_path / "_gia_lap_vm" / "nguon_tool.py")
        os.makedirs(os.path.dirname(mod.__file__), exist_ok=True)
        spec.loader.exec_module(mod)
        return mod

    def test_tram_bao_dung_duong_kenh_yaml(self, tmp_path):
        from core.chi_so_ytb.tram import Tram
        from core.trung_tam import ghi_cai_kenh

        os.makedirs(tmp_path / "CHANNEL" / "K1", exist_ok=True)
        ghi_cai_kenh(str(tmp_path), "K1", thu_muc_done=r"D:\ban-giao\K1")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            nt = self._nap_nguon_tool(tmp_path)
            duong = nt.thu_muc_dang({"TRAM": dia_chi}, "K1")
        finally:
            tram.tat()
        assert duong == r"D:\ban-giao\K1"

    def test_kenh_chua_khai_thu_muc_done_thi_rong(self, tmp_path):
        from core.chi_so_ytb.tram import Tram

        os.makedirs(tmp_path / "CHANNEL" / "K2", exist_ok=True)
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            nt = self._nap_nguon_tool(tmp_path)
            duong = nt.thu_muc_dang({"TRAM": dia_chi}, "K2")
        finally:
            tram.tat()
        assert duong == ""

    def test_tram_tat_thi_lui_ve_cache_da_tai_lan_truoc(self, tmp_path):
        from core.chi_so_ytb.tram import Tram
        from core.trung_tam import ghi_cai_kenh

        os.makedirs(tmp_path / "CHANNEL" / "K3", exist_ok=True)
        ghi_cai_kenh(str(tmp_path), "K3", thu_muc_done=r"D:\ban-giao\K3")
        tram = Tram(cong=0, goc=str(tmp_path))
        tram.bat()
        nt = self._nap_nguon_tool(tmp_path)
        tep_cache = Path(nt.__file__).parent / "thu-muc-dang-K3.json"
        try:
            dia_chi = "http://127.0.0.1:{0}".format(tram._may.server_address[1])
            duong1 = nt.thu_muc_dang({"TRAM": dia_chi}, "K3")
            assert duong1 == r"D:\ban-giao\K3"
            assert tep_cache.is_file(), "phải lưu cache sau lượt tải thành công"
        finally:
            tram.tat()
        # Trạm đã tắt -> phải đọc lại đúng bản cache vừa lưu, không rỗng.
        duong2 = nt.thu_muc_dang({"TRAM": dia_chi}, "K3")
        assert duong2 == r"D:\ban-giao\K3"


class TestAnhBangChung:
    """`_luu_anh_bang_chung` — chụp bằng chứng lúc timeout/lỗi, và tự dọn
    bớt khi quá `SO_ANH_LOI_GIU_LAI` ảnh (máy chạy 24/7 nhiều tháng)."""

    def _ham(self, thu_muc, giu_lai=3):
        import logging as _logging

        class _PyAutoGuiGia:
            def screenshot(self, duong):
                with open(duong, "wb") as f:
                    f.write(b"\x89PNG")

        src = (_khoi("_luu_anh_bang_chung", "_ghi_dodang")
              + _khoi("_ghi_dodang", "wait_and_click_image"))
        ns = {"os": os, "time": __import__("time"), "logging": _logging,
             "pyautogui": _PyAutoGuiGia(), "THU_MUC_ANH_LOI": str(thu_muc),
             "SO_ANH_LOI_GIU_LAI": giu_lai, "_THU_MUC_LOG_SOM": str(thu_muc.parent)}
        exec(src, ns)  # noqa: S102
        return ns["_luu_anh_bang_chung"]

    def test_luu_thanh_cong(self, tmp_path):
        luu = self._ham(tmp_path / "anh-loi")
        duong = luu("khong-thay-henlich")
        assert duong and os.path.isfile(duong)
        assert "khong-thay-henlich" in os.path.basename(duong)

    def test_ten_la_gi_cung_khong_vo(self, tmp_path):
        """Ký tự lạ trong nhãn (vd mã gói có dấu, khoảng trắng) không được
        làm hỏng đường dẫn tệp."""
        luu = self._ham(tmp_path / "anh-loi")
        duong = luu("mã/lạ: có dấu và khoảng trắng!!")
        assert duong and os.path.isfile(duong)

    def test_tu_don_bot_giu_dung_so_luong(self, tmp_path):
        luu = self._ham(tmp_path / "anh-loi", giu_lai=3)
        import time as _time
        for i in range(6):
            luu("anh-{0}".format(i))
            _time.sleep(0.01)
        con_lai = os.listdir(tmp_path / "anh-loi")
        assert len(con_lai) == 3, "phải dọn bớt, chỉ giữ 3 ảnh mới nhất"


class TestBoMaCoVideoId:
    """Việc C, 29/09/2026: đường ảnh (`get_all_ready_codes`) phải bỏ qua mã
    đã có `video_id` trong sổ của máy đăng DOM (`vm/logs/so-video-id.json`)
    — máy DOM đang giữ bản nháp/đã đăng, tải lại bằng đường ảnh là đăng đôi."""

    IDX_CHANNEL_AI = 34
    IDX_STATUS_AV = 47
    IDX_DATE_BI = 60
    IDX_TIME_BJ = 61
    STATUS_OK = "EDIT XONG"

    def _ham(self, duong_so):
        import json as _json
        from datetime import datetime as _datetime

        ns = {
            "os": os, "json": _json, "datetime": _datetime,
            "norm": lambda s: s.strip() if isinstance(s, str) else None,
            "_parse_date": lambda s: _datetime.strptime(s.strip(), "%d/%m/%Y").date()
            if s else None,
            "_parse_time": lambda s: _datetime.strptime(s.strip(), "%H:%M").time()
            if s else None,
            "IDX_CHANNEL_AI": self.IDX_CHANNEL_AI, "IDX_STATUS_AV": self.IDX_STATUS_AV,
            "IDX_DATE_BI": self.IDX_DATE_BI, "IDX_TIME_BJ": self.IDX_TIME_BJ,
            "STATUS_OK": self.STATUS_OK, "CHANNEL_CODE": "",
            "DUONG_SO_VIDEO_ID": str(duong_so),
        }
        exec(_khoi("_ma_co_video_id", "get_tomorrow_codes"), ns)  # noqa: S102
        return ns["get_all_ready_codes"]

    def _hang(self, ma, gio):
        """Một dòng 62 cột hợp lệ cho `get_all_ready_codes`: kênh TL1-T7,
        trạng thái OK, hôm nay, giờ `gio` (HH:MM, phải SAU giờ hiện tại)."""
        from datetime import datetime
        row = [""] * 62
        row[0] = ma
        row[self.IDX_CHANNEL_AI] = "TL1-T7"
        row[self.IDX_STATUS_AV] = self.STATUS_OK
        row[self.IDX_DATE_BI] = datetime.now().strftime("%d/%m/%Y")
        row[self.IDX_TIME_BJ] = gio
        return row

    def _gio_xa_tuong_lai(self):
        from datetime import datetime, timedelta
        return (datetime.now() + timedelta(hours=1)).strftime("%H:%M")

    def test_ma_da_co_video_id_thi_bi_bo_qua(self, tmp_path):
        so = tmp_path / "so-video-id.json"
        so.write_text(json.dumps({"TL1-T7/TL1-T7-0007": {"video_id": "abc123"}}),
                     encoding="utf-8")
        ham = self._ham(so)
        rows = [[""] * 62, self._hang("TL1-T7-0007", self._gio_xa_tuong_lai()),
                self._hang("TL1-T7-0009", self._gio_xa_tuong_lai())]
        assert ham(rows, "TL1-T7") == ["TL1-T7-0009"], \
            "0007 đã có videoId trong sổ DOM — đường ảnh phải bỏ qua"

    def test_khong_co_so_thi_khong_bo_gi_ca(self, tmp_path):
        """Sổ chưa tồn tại (máy DOM chưa từng chạy) — hành vi y hệt trước
        khi tính năng này có, không mất mã nào oan."""
        ham = self._ham(tmp_path / "khong-ton-tai.json")
        rows = [[""] * 62, self._hang("TL1-T7-0007", self._gio_xa_tuong_lai())]
        assert ham(rows, "TL1-T7") == ["TL1-T7-0007"]

    def test_muc_khong_co_video_id_thi_van_cho_qua(self, tmp_path):
        so = tmp_path / "so-video-id.json"
        so.write_text(json.dumps({"TL1-T7/TL1-T7-0007": {"trang_thai": "nhap"}}),
                     encoding="utf-8")
        ham = self._ham(so)
        rows = [[""] * 62, self._hang("TL1-T7-0007", self._gio_xa_tuong_lai())]
        assert ham(rows, "TL1-T7") == ["TL1-T7-0007"], \
            "mục có trong sổ nhưng chưa có video_id (chưa chạm Studio) — vẫn cho đường ảnh thử"
