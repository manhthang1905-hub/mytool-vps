"""04/10/2026: kênh mới chưa có video → kiểm DOM không báo hỏng hàng video oan."""

import json
import sys
from pathlib import Path

VM = Path(__file__).resolve().parent.parent / "vm"
if str(VM) not in sys.path:
    sys.path.insert(0, str(VM))

import may_dang_dom as m  # noqa: E402


def test_kenh_co_video_trong_so(tmp_path):
    so = tmp_path / "so.json"
    so.write_text(json.dumps({"KA/KA-0001": {"video_id": "abc", "trang_thai": "xac-nhan"},
                              "KB/KB-0001": {"video_id": None, "trang_thai": "dang-tai"}}), encoding="utf-8")
    assert m._kenh_co_video_trong_so("KA", str(so)) is True
    assert m._kenh_co_video_trong_so("KB", str(so)) is False      # chưa có video_id
    assert m._kenh_co_video_trong_so("KC", str(so)) is False
    assert m._kenh_co_video_trong_so("KA", str(tmp_path / "khong-co.json")) is True   # đọc hỏng → kiểm chặt như cũ
