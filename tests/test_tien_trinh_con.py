"""Tắt tool là con chết theo; mở tool là dọn xác lần trước (`core/tien_trinh_con`).

Chủ dự án, 24/08/2026: *"khi tắt tool là mọi thứ tắt hoặc khi bật tool nó
cũng có logic tắt để không có gì kiểu rác zombie"*.

Bài kiểm sinh tiến trình `python` ngủ thật rồi giết thật — chạy trên máy,
không mạng, mỗi bài dưới hai giây.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest

from core import tien_trinh_con as ttc

NGU = [sys.executable, "-c", "import time; time.sleep(60)"]
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ngu():
    co = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    return subprocess.Popen(NGU, creationflags=co)


def _doi_chet(pid: int, giay: float = 3.0) -> bool:
    het = time.time() + giay
    while time.time() < het:
        if not ttc.con_song(pid):
            return True
        time.sleep(0.1)
    return False


class TestSoGhiVaDonXac:
    def test_ghi_nhan_roi_dung_tat_ca(self, tmp_path):
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            assert os.path.isfile(os.path.join(str(tmp_path), "workspace",
                                               ttc.TEN_SO))
            assert ttc.dung_tat_ca() >= 1
            assert _doi_chet(tt.pid)
        finally:
            if tt.poll() is None:
                tt.kill()

    def test_mo_tool_don_xac_lan_truoc(self, tmp_path, monkeypatch):
        """Giả lập: lần chạy trước ghi sổ rồi chết mà không kịp giết con.

        Đây là đường GIẾT THẬT — chỉ xảy ra khi tool mở lên ngoài đời, không
        phải dưới pytest (xem `test_don_xac_cu_khong_giet_gi_duoi_pytest`).
        Bài này phải tự gỡ `PYTEST_CURRENT_TEST` để soi đúng đường đó, kẻo
        cờ chặn (đang bật sẵn vì chính bài này CŨNG chạy dưới pytest) khiến
        bài kiểm "giết thật" không còn kiểm gì cả."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            # "Lần chạy trước" biến mất: quên hết trong bộ nhớ, chỉ còn sổ.
            ttc._DANG_SONG.clear()  # noqa: SLF001
            assert ttc.con_song(tt.pid)
            assert ttc.don_xac_cu(str(tmp_path)) == 1
            assert _doi_chet(tt.pid)
            # Sổ được dọn sạch sau khi xử lý.
            assert ttc._doc_so(str(tmp_path)) == []  # noqa: SLF001
        finally:
            if tt.poll() is None:
                tt.kill()

    def test_khong_giet_nham_khi_ma_tien_trinh_bi_tai_dung(self, tmp_path, monkeypatch):
        """Cùng pid nhưng giờ tạo khác = chương trình khác của khách. Không đụng.

        Gỡ cờ pytest như bài trên: soi đúng logic so vân tay, không phải
        cờ chặn (cờ chặn cũng trả 0 nhưng vì lý do khác hẳn)."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            ttc._DANG_SONG.clear()  # noqa: SLF001
            so = ttc._doc_so(str(tmp_path))  # noqa: SLF001
            so[0]["tao_luc"] = 12345  # dấu vân tay lệch
            ttc._ghi_so(str(tmp_path), so)  # noqa: SLF001
            assert ttc.don_xac_cu(str(tmp_path)) == 0
            assert ttc.con_song(tt.pid), "giết nhầm tiến trình không phải của mình"
        finally:
            tt.kill()

    def test_bo_ghi_nhan_rut_khoi_so(self, tmp_path):
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path))
            ttc.bo_ghi_nhan(tt, str(tmp_path))
            assert ttc._doc_so(str(tmp_path)) == []  # noqa: SLF001
        finally:
            tt.kill()

    def test_chu_mac_dinh_doan_qua_argv0(self, monkeypatch):
        """`_chu_mac_dinh` — đúng `tu_chay.py` thì "tu_chay", còn lại "gui"."""
        monkeypatch.setattr(sys, "argv", [r"D:\MyTool\tu_chay.py", "--tat-ca"])
        assert ttc._chu_mac_dinh() == ttc.CHU_TU_CHAY  # noqa: SLF001
        monkeypatch.setattr(sys, "argv", [r"D:\MyTool\shopapi_studio_qt.py"])
        assert ttc._chu_mac_dinh() == ttc.CHU_GUI  # noqa: SLF001
        monkeypatch.setattr(sys, "argv", [r"D:\MyTool\Tu_Chay.PY", "--dieu-phoi"])
        assert ttc._chu_mac_dinh() == ttc.CHU_TU_CHAY  # noqa: SLF001 — không phân biệt hoa/thường

    def test_ghi_nhan_ghi_chu_gui_mac_dinh_duoi_pytest(self, tmp_path):
        """Dưới pytest, `sys.argv[0]` không phải `tu_chay.py` → mặc định "gui"."""
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            so = ttc._doc_so(str(tmp_path))  # noqa: SLF001
            assert so and so[0]["chu"] == ttc.CHU_GUI
        finally:
            tt.kill()

    def test_don_xac_cu_khong_dung_muc_chu_tu_chay(self, tmp_path, monkeypatch):
        """Mục `chu == "tu_chay"` — một lượt sản xuất tách rời — KHÔNG bị giết
        và vẫn còn trong sổ sau `don_xac_cu` (đúng phần "CHỦ SỞ HỮU")."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu", chu=ttc.CHU_TU_CHAY)
            ttc._DANG_SONG.clear()  # noqa: SLF001
            assert ttc.don_xac_cu(str(tmp_path)) == 0
            assert ttc.con_song(tt.pid), "giết nhầm tiến trình tu_chay tách rời"
            so = ttc._doc_so(str(tmp_path))  # noqa: SLF001
            assert len(so) == 1 and so[0]["chu"] == ttc.CHU_TU_CHAY
        finally:
            if tt.poll() is None:
                tt.kill()

    def test_don_xac_cu_muc_so_cu_khong_chu_cha_da_chet_thi_giet(self, tmp_path, monkeypatch):
        """Mục sổ CŨ (di trú, không có trường `chu`) — chỉ giết khi tiến trình
        CHA của nó đã chết (mô phỏng: cha là PID không tồn tại)."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            ttc._DANG_SONG.clear()  # noqa: SLF001
            so = ttc._doc_so(str(tmp_path))  # noqa: SLF001
            del so[0]["chu"]
            ttc._ghi_so(str(tmp_path), so)  # noqa: SLF001
            monkeypatch.setattr(ttc, "_ppid", lambda pid: 999_999_999)  # cha "chết"
            assert ttc.don_xac_cu(str(tmp_path)) == 1
            assert _doi_chet(tt.pid)
        finally:
            if tt.poll() is None:
                tt.kill()

    def test_don_xac_cu_muc_so_cu_khong_chu_cha_con_song_thi_khong_dung(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            ttc._DANG_SONG.clear()  # noqa: SLF001
            so = ttc._doc_so(str(tmp_path))  # noqa: SLF001
            del so[0]["chu"]
            ttc._ghi_so(str(tmp_path), so)  # noqa: SLF001
            monkeypatch.setattr(ttc, "_ppid", lambda pid: os.getpid())  # cha "còn sống"
            assert ttc.don_xac_cu(str(tmp_path)) == 0
            assert ttc.con_song(tt.pid)
        finally:
            tt.kill()

    def test_don_xac_cu_khong_giet_gi_duoi_pytest(self, tmp_path):
        """Sổ dùng chung với `claude` của lượt sản xuất thật (`core/viet_max.py`).

        `PYTEST_CURRENT_TEST` LUÔN có khi chạy dưới pytest — bài này chỉ xác
        nhận `don_xac_cu` tôn trọng đúng cờ đó (không cần xoá cờ, vì xoá rồi
        đặt lại giữa một bài test đang chạy là tự nói dối chính pytest)."""
        assert "PYTEST_CURRENT_TEST" in os.environ
        tt = _ngu()
        try:
            ttc.ghi_nhan(tt, str(tmp_path), "ngu")
            ttc._DANG_SONG.clear()  # noqa: SLF001 — giả lập "lần chạy trước"
            assert ttc.con_song(tt.pid)
            duong_log = os.path.join(str(tmp_path), "workspace",
                                      "tien-trinh-con.log")
            assert ttc.don_xac_cu(str(tmp_path)) == 0, \
                "don_xac_cu phải KHÔNG giết gì dưới pytest"
            assert ttc.con_song(tt.pid), "tiến trình bị giết dù đang chạy dưới pytest"
            # Sổ giữ nguyên (không bị dọn rỗng như đường giết thật).
            assert len(ttc._doc_so(str(tmp_path))) == 1  # noqa: SLF001
            # Có ghi log để biết là đã bị chặn, không im lặng bỏ qua.
            assert os.path.isfile(duong_log)
            with open(duong_log, encoding="utf-8") as tep:
                noi_dung = tep.read()
            assert "pytest" in noi_dung.lower()
        finally:
            if tt.poll() is None:
                tt.kill()


@pytest.mark.skipif(os.name != "nt", reason="Job Object là của Windows")
class TestJobObject:
    def test_vao_job_duoc(self):
        assert ttc.vao_job_ket_thuc_cung_tool() is True
        # Gọi lại là vô hại.
        assert ttc.vao_job_ket_thuc_cung_tool() is True

    def test_cha_chet_bat_ngo_thi_chau_chet_theo(self):
        """Lưới chính: cha vào job, sinh cháu, rồi cha `os._exit` không dọn gì.

        Cháu phải chết dù không ai gọi `kill()` — đó là toàn bộ lý do dùng Job
        Object thay vì tin vào mã dọn dẹp.
        """
        ma_cha = (
            "import os, subprocess, sys\n"
            "sys.path.insert(0, {goc!r})\n"
            "from core import tien_trinh_con as t\n"
            "assert t.vao_job_ket_thuc_cung_tool()\n"
            "c = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(60)'])\n"
            "print(c.pid, flush=True)\n"
            "os._exit(0)\n").format(goc=GOC)
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cha = subprocess.run([sys.executable, "-c", ma_cha], capture_output=True,
                             text=True, timeout=30, creationflags=co)
        assert cha.returncode == 0, cha.stderr
        chau = int(cha.stdout.strip().splitlines()[-1])
        assert _doi_chet(chau, 5.0), "cháu vẫn sống sau khi cha chết — job không ăn"

    def test_con_tach_job_thi_song_lau_hon_cha(self, tmp_path):
        """Ngoại lệ có chủ đích: tiến trình cập nhật / VS Code phải sống tiếp.

        Pid đi qua TỆP chứ không qua ống: con sống tiếp thì ống stdout nó thừa
        hưởng cũng sống tiếp, và `subprocess.run` sẽ ngồi đợi ống đóng — tức
        bài kiểm treo đúng vì điều nó muốn chứng minh là đúng.
        """
        tep_pid = os.path.join(str(tmp_path), "pid.txt")
        ma_cha = (
            "import os, subprocess, sys\n"
            "sys.path.insert(0, {goc!r})\n"
            "from core import tien_trinh_con as t\n"
            "assert t.vao_job_ket_thuc_cung_tool()\n"
            "c = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(60)'], creationflags=t.CO_TACH_KHOI_JOB, "
            "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, "
            "stderr=subprocess.DEVNULL, close_fds=True)\n"
            "open({tep!r}, 'w').write(str(c.pid))\n"
            "os._exit(0)\n").format(goc=GOC, tep=tep_pid)
        co = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        cha = subprocess.run([sys.executable, "-c", ma_cha], timeout=30,
                             creationflags=co, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert cha.returncode == 0
        with open(tep_pid, encoding="utf-8") as t:
            con = int(t.read().strip())
        time.sleep(1.0)
        try:
            assert ttc.con_song(con), "con đã tách job mà vẫn bị giết"
        finally:
            ttc._giet(con)  # noqa: SLF001


class TestDauNoiVaoTool:
    """Ba chỗ phải nối đúng, kiểm bằng mã nguồn để không ai rút ra cho gọn."""

    def _doc(self, *phan):
        with open(os.path.join(GOC, *phan), encoding="utf-8") as t:
            return t.read()

    def test_cua_so_chinh_vao_job_va_don_xac_luc_mo(self):
        chu = self._doc("ui_qt", "app.py")
        assert "vao_job_ket_thuc_cung_tool()" in chu
        assert "don_xac_cu(base_dir)" in chu
        assert "dung_tat_ca()" in chu[chu.index("def closeEvent"):]

    def test_tien_trinh_cap_nhat_tach_job(self):
        chu = self._doc("ui_qt", "cap_nhat.py")
        assert "CO_TACH_KHOI_JOB" in chu[chu.index("def _tai_xong"):]

    def test_vs_code_va_dong_lenh_tach_job(self):
        chu = self._doc("core", "claude_code.py")
        khuc = chu[chu.index("def _mo_kem_moi_truong"):]
        khuc = khuc[:khuc.index("def lenh_cua_so_cmd")]
        assert khuc.count("CO_TACH_KHOI_JOB") >= 3  # import + 2 nhánh

    def test_claude_va_whisper_duoc_ghi_nhan(self):
        for tep in (("core", "viet_max.py"), ("core", "nghe_ngoai.py")):
            chu = self._doc(*tep)
            assert "ghi_nhan(tien_trinh" in chu and "bo_ghi_nhan(tien_trinh" in chu, tep
