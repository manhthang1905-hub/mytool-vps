"""05/10: danh mục skill + kiểm token bình luận (token hỏng → quay về DOM)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vm"))
from core import ky_nang as kn  # noqa: E402


def test_ma_duy_nhat_va_can_tro_dung():
    ma = [k.ma for k in kn.DANH_MUC]
    assert len(ma) == len(set(ma))
    for k in kn.DANH_MUC:
        for c in k.can:
            assert c.startswith("nguoi:") or kn.theo_ma(c) is not None, (k.ma, c)
        assert k.loai in ("khoi_tao", "dinh_ky", "sua_chua", "mo_rong")


def _goc(tmp_path, kenh="K", yaml='nhom: "a"\ntep: "b"\nvoice_id: "x"\n'):
    d = tmp_path / "CHANNEL" / kenh
    (d / "nv").mkdir(parents=True)
    (d / "kenh.yaml").write_text(yaml, encoding="utf-8")
    (tmp_path / "vm" / "logs").mkdir(parents=True)
    return str(tmp_path)


def test_kiem_kenh_khong_vo_khi_thieu_moi_thu(tmp_path):
    goc = _goc(tmp_path)
    ra = kn.kiem_kenh(goc, "K")
    assert len(ra) == len(kn.DANH_MUC)
    tt = {k.ma: t for k, t, _ in ra}
    assert tt["K04"] == kn.DAT and tt["K05"] == kn.THIEU
    assert tt["K07"] == kn.KHONG               # kênh không bật thiet_lap_kenh → thiết lập tay


def test_token_hong_thi_agent_quay_ve_dom(tmp_path, monkeypatch):
    import agent
    monkeypatch.setattr(agent, "GOC", str(tmp_path))
    (tmp_path / "tokens").mkdir()
    (tmp_path / "logs" / "oauth").mkdir(parents=True)
    assert agent.co_token_oauth("K") is False                       # không tệp
    (tmp_path / "tokens" / "K.json").write_text(json.dumps({"token": "x"}), encoding="utf-8")
    assert agent.co_token_oauth("K") is False                       # không refresh_token
    (tmp_path / "tokens" / "K.json").write_text(json.dumps({"refresh_token": "r"}), encoding="utf-8")
    assert agent.co_token_oauth("K") is True
    (tmp_path / "logs" / "oauth" / "K.json").write_text(json.dumps({"tt": "hong"}), encoding="utf-8")
    assert agent.co_token_oauth("K") is False                       # làm mới hỏng → DOM
    assert agent.chon_may_cmt(None, True, agent.co_token_oauth("K")) == "dom"
