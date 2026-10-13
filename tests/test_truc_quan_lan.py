# -*- coding: utf-8 -*-
"""13/10/2026 — trung tâm trực quan mở cho máy CÙNG MẠNG (chủ: session shopapi.vn kéo dữ liệu về đẩy lên web)."""
import json
import threading
import urllib.request

from core import truc_quan as tq


def test_dia_chi_nghe_theo_tep_va_co(tmp_path, monkeypatch):
    p = tmp_path / "cai-dat.json"
    monkeypatch.setattr(tq, "TEP_CAI_DAT", str(p))
    assert tq.dia_chi_nghe([]) == "127.0.0.1"                 # không có tệp → như cũ
    p.write_text(json.dumps({"mo_lan": True}), encoding="utf-8")
    assert tq.dia_chi_nghe([]) == "::"
    p.write_text("{hong", encoding="utf-8")
    assert tq.dia_chi_nghe([]) == "127.0.0.1"                 # tệp hỏng → an toàn
    assert tq.dia_chi_nghe(["--lan"]) == "::"


def test_may_chu_hai_ngan_nhan_ipv4_va_json_co_cors():
    sv = tq._MayChuHaiNgan(("::", 0), tq._Xu)  # noqa: SLF001
    cong = sv.server_address[1]
    t = threading.Thread(target=sv.serve_forever, daemon=True)
    t.start()
    try:
        ph = urllib.request.urlopen("http://127.0.0.1:{0}/vendor/khong-co".format(cong), timeout=10)
    except urllib.error.HTTPError as loi:            # 404 vẫn là trả lời qua IPv4 → hai ngăn xếp chạy
        assert loi.code == 404
    else:
        ph.close()
    finally:
        sv.shutdown()
        sv.server_close()
