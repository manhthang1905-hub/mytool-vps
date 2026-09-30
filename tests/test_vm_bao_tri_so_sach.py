"""Dọn sổ sách phình vô hạn trên máy ảo: xoay vòng `agent.log`, cắt khoá cũ
trong `trang-thai.json`, và giới hạn `replied/<kênh>.txt`.

Nạp thẳng `vm/agent.py`/`vm/may_cmt.py` bằng đường dẫn TUYỆT ĐỐI thật của
repo (không đi qua `MyTool/vm/...` như `tests/test_vm_agent.py` — bố cục thật
là `vm/` NẰM CẠNH `MyTool/`, không nằm trong nó; đó cũng là lý do khoảng 141+
test khác trong bộ này fail sẵn, không liên quan tới thay đổi ở đây).

KHÔNG BAO GIỜ đụng `vm/agent.log`/`vm/trang-thai.json`/`vm/replied/` THẬT —
mọi test dưới đây trỏ về `tmp_path`.
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

_DAY_TEST = Path(__file__).resolve()
_UNG_VIEN_GOC_VM = [
    _DAY_TEST.parents[2] / "vm",   # bố cục THẬT: <gốc repo>/vm cạnh <gốc repo>/MyTool
    _DAY_TEST.parents[1] / "vm",   # phòng khi bố cục đổi: MyTool/vm
]


def _duong_vm(ten_tep: str) -> Path:
    for goc in _UNG_VIEN_GOC_VM:
        duong = goc / ten_tep
        if duong.exists():
            return duong
    pytest.skip(f"không tìm thấy vm/{ten_tep} ở bất kỳ vị trí ứng viên nào")


def _nap_module(duong: Path, ten: str):
    spec = importlib.util.spec_from_file_location(ten, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def agent_mod():
    return _nap_module(_duong_vm("agent.py"), "vm_agent_bao_tri")


@pytest.fixture(scope="module")
def cmt_mod():
    return _nap_module(_duong_vm("may_cmt.py"), "vm_may_cmt_bao_tri")


# ============================== agent.log xoay vòng ==========================


class TestXoayVongNhatKy:
    def test_chua_vuot_nguong_thi_khong_xoay(self, agent_mod, tmp_path, monkeypatch):
        duong_log = tmp_path / "agent.log"
        monkeypatch.setattr(agent_mod, "_duong_nhat_ky", lambda: str(duong_log))
        # Ngưỡng mặc định 5MB -> vài dòng ngắn không bao giờ chạm.
        for i in range(5):
            agent_mod.ghi(f"dòng {i}")
        assert duong_log.exists()
        assert not (tmp_path / "agent.log.1").exists()
        noi_dung = duong_log.read_text(encoding="utf-8")
        for i in range(5):
            assert f"dòng {i}" in noi_dung

    def test_vuot_nguong_thi_doi_ten_thanh_ban_1(self, agent_mod, tmp_path, monkeypatch):
        duong_log = tmp_path / "agent.log"
        monkeypatch.setattr(agent_mod, "_duong_nhat_ky", lambda: str(duong_log))
        monkeypatch.setattr(agent_mod, "NHAT_KY_TOI_DA_BYTE", 1)
        monkeypatch.setattr(agent_mod, "NHAT_KY_SO_BAN_CU", 3)

        agent_mod.ghi("MOC-0")   # file chưa có -> ghi thẳng, giờ đã vượt 1 byte
        agent_mod.ghi("MOC-1")   # vượt ngưỡng -> xoay: log -> log.1 (chứa MOC-0)

        assert (tmp_path / "agent.log.1").exists()
        assert "MOC-0" in (tmp_path / "agent.log.1").read_text(encoding="utf-8")
        assert "MOC-1" in duong_log.read_text(encoding="utf-8")

    def test_giu_toi_da_so_ban_cu_khong_phinh_vo_han(self, agent_mod, tmp_path, monkeypatch):
        duong_log = tmp_path / "agent.log"
        monkeypatch.setattr(agent_mod, "_duong_nhat_ky", lambda: str(duong_log))
        monkeypatch.setattr(agent_mod, "NHAT_KY_TOI_DA_BYTE", 1)
        monkeypatch.setattr(agent_mod, "NHAT_KY_SO_BAN_CU", 3)

        for i in range(10):
            agent_mod.ghi(f"MOC-{i}")

        assert "MOC-9" in duong_log.read_text(encoding="utf-8")
        assert "MOC-8" in (tmp_path / "agent.log.1").read_text(encoding="utf-8")
        assert "MOC-7" in (tmp_path / "agent.log.2").read_text(encoding="utf-8")
        assert "MOC-6" in (tmp_path / "agent.log.3").read_text(encoding="utf-8")
        # Không tích luỹ vô hạn: không có bản thứ 4.
        assert not (tmp_path / "agent.log.4").exists()

    def test_loi_xoay_khong_lam_mat_dong_log_moi(self, agent_mod, tmp_path, monkeypatch):
        """Giả lập `os.replace` luôn lỗi (vd tệp đang bị khoá bởi tiến trình
        khác) — `ghi()` không được crash, và dòng log MỚI vẫn phải được ghi
        (rơi về nối tiếp vào file cũ, thà phình tạm còn hơn mất log)."""
        duong_log = tmp_path / "agent.log"
        monkeypatch.setattr(agent_mod, "_duong_nhat_ky", lambda: str(duong_log))
        monkeypatch.setattr(agent_mod, "NHAT_KY_TOI_DA_BYTE", 1)

        agent_mod.ghi("MOC-0")

        def _loi(*a, **k):
            raise OSError("giả lập tệp đang bị mở")

        monkeypatch.setattr(agent_mod.os, "replace", _loi)
        agent_mod.ghi("MOC-1")  # không được raise

        noi_dung = duong_log.read_text(encoding="utf-8")
        assert "MOC-0" in noi_dung and "MOC-1" in noi_dung
        assert not (tmp_path / "agent.log.1").exists()


# ============================ trang-thai.json cắt bớt ========================


class TestDonTrangThaiTheoNgay:
    def test_khoa_qua_han_bi_bo_khoa_con_han_duoc_giu(self, agent_mod):
        bay_gio = time.mktime(time.strptime("2026-09-21", "%Y-%m-%d"))
        tt = {
            "phien_muc_tieu@TL1-T7@2026-07-01": "07:00",   # > 60 ngày trước -> bỏ
            "phien_muc_tieu@TL1-T7@2026-09-20": "07:00",   # hôm qua -> giữ
            "phien_cuoi@TL1-T7": "2026-09-20",              # không mang @ngày -> luôn giữ
            "quet_cuoi@TL1-T7@07:30": "2026-09-20",         # hậu tố là GIỜ, không phải ngày -> giữ
        }
        ket_qua = agent_mod._don_trang_thai_theo_ngay(tt, bay_gio=bay_gio)
        assert "phien_muc_tieu@TL1-T7@2026-07-01" not in ket_qua
        assert ket_qua["phien_muc_tieu@TL1-T7@2026-09-20"] == "07:00"
        assert ket_qua["phien_cuoi@TL1-T7"] == "2026-09-20"
        assert ket_qua["quet_cuoi@TL1-T7@07:30"] == "2026-09-20"

    def test_khong_dung_cham_key_khong_lien_quan(self, agent_mod):
        tt = {"linh_tinh": 123, "kenh": "TL1-T7"}
        assert agent_mod._don_trang_thai_theo_ngay(tt) == tt

    def test_luu_trang_thai_tu_dong_don_khi_ghi(self, agent_mod, tmp_path):
        cau_hinh = {"thu_muc_du_lieu": str(tmp_path)}
        duong = tmp_path / "trang-thai.json"
        duong.write_text(
            json.dumps({"phien_muc_tieu@KENH@2000-01-01": "07:00"}, ensure_ascii=False),
            encoding="utf-8",
        )
        agent_mod._luu_trang_thai(cau_hinh, khoa_moi="gia_tri_moi")
        tt = json.loads(duong.read_text(encoding="utf-8"))
        assert "phien_muc_tieu@KENH@2000-01-01" not in tt
        assert tt["khoa_moi"] == "gia_tri_moi"


# ============================ replied/<kênh>.txt giới hạn =====================


class TestGioiHanReplied:
    def test_load_state_khong_co_file_tra_ve_rong(self, cmt_mod, tmp_path, monkeypatch):
        monkeypatch.setattr(cmt_mod, "REPLIED_DIR", str(tmp_path))
        assert cmt_mod.load_state("KENH-X") == set()

    def test_save_roi_load_lai_dung_noi_dung(self, cmt_mod, tmp_path, monkeypatch):
        monkeypatch.setattr(cmt_mod, "REPLIED_DIR", str(tmp_path))
        cmt_mod.save_state("KENH-X", {"id1", "id2"})
        assert cmt_mod.load_state("KENH-X") == {"id1", "id2"}

    def test_khong_sap_xep_lai_theo_chu_cai_id_moi_noi_cuoi(self, cmt_mod, tmp_path, monkeypatch):
        """Chốt đúng yêu cầu an toàn: thứ tự TRÊN ĐĨA phải là thứ tự THỜI
        GIAN (id cũ trước, id mới nối sau) — KHÔNG phải alphabet. Cố tình
        đặt "b" trước "a" trong file gốc để lộ ngay nếu code lỡ `sorted()`."""
        (tmp_path / "KENH-X.txt").write_text("b\na\n", encoding="utf-8")
        monkeypatch.setattr(cmt_mod, "REPLIED_DIR", str(tmp_path))

        cmt_mod.save_state("KENH-X", {"b", "a", "c"})  # "c" là id MỚI duy nhất

        dong = (tmp_path / "KENH-X.txt").read_text(encoding="utf-8").splitlines()
        assert dong == ["b", "a", "c"], "id cũ phải giữ nguyên thứ tự, id mới nối vào CUỐI"

    def test_vuot_tran_thi_cat_id_cu_nhat_giu_id_moi_nhat(self, cmt_mod, tmp_path, monkeypatch):
        monkeypatch.setattr(cmt_mod, "REPLIED_DIR", str(tmp_path))
        monkeypatch.setattr(cmt_mod, "REPLIED_MAX_IDS", 5)

        # Mô phỏng process_channel: mỗi bình luận mới -> seen.add(cid) rồi save_state NGAY.
        seen = set()
        for i in range(10):
            seen.add(f"id{i}")
            cmt_mod.save_state("KENH-X", seen)

        dong = (tmp_path / "KENH-X.txt").read_text(encoding="utf-8").splitlines()
        assert dong == ["id5", "id6", "id7", "id8", "id9"], (
            "phải giữ đúng 5 id GẦN NHẤT theo thời gian thêm vào, "
            "không phải 5 id nhỏ nhất theo chữ cái"
        )

    def test_id_da_bi_cat_van_o_trong_seen_khong_lam_phinh_lai_vo_han(self, cmt_mod, tmp_path, monkeypatch):
        """`seen` (bộ nhớ trong tiến trình, KHÔNG bao giờ tự rút gọn trong một
        lần chạy) vẫn còn giữ id đã bị cắt khỏi đĩa ở lượt lưu trước — lượt
        lưu sau không được coi nó là "mới" rồi đẩy lùi id thật sự mới hơn."""
        monkeypatch.setattr(cmt_mod, "REPLIED_DIR", str(tmp_path))
        monkeypatch.setattr(cmt_mod, "REPLIED_MAX_IDS", 3)

        seen = set()
        for i in range(3):
            seen.add(f"id{i}")
            cmt_mod.save_state("KENH-X", seen)  # id0,id1,id2 (chưa vượt trần)

        seen.add("id3")
        cmt_mod.save_state("KENH-X", seen)  # vượt trần -> cắt id0, còn id1,id2,id3

        # id0 đã rớt khỏi đĩa nhưng vẫn còn trong "seen" (process vẫn nhớ) —
        # lưu lại lần nữa KHÔNG được coi id0 là "mới" rồi đẩy id2/id3 ra.
        cmt_mod.save_state("KENH-X", seen)

        dong = (tmp_path / "KENH-X.txt").read_text(encoding="utf-8").splitlines()
        assert dong == ["id1", "id2", "id3"]
