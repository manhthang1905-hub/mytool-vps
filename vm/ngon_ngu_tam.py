"""TẠM ĐỔI ngôn ngữ giao diện YouTube cho máy DOM — rồi TRẢ LẠI (05/10/2026).

Kênh giữ ĐÚNG ngôn ngữ hiển thị của nước nó (kênh Nhật → 日本語: trang chủ, đề xuất, nuôi trang chủ, quét đối thủ
đều chạy trên ngôn ngữ đó). Máy DOM (đăng / bình luận) thì bấm theo chữ đã KIỂM CHỨNG ở một ngôn ngữ (`vi`) — nên
lúc vào Studio làm việc nó tạm đặt cookie PREF `hl=vi`, xong phiên trả `hl` CŨ. Như vậy VPS ở nước nào cũng chạy được,
không phải dạy máy DOM đọc từng ngôn ngữ (thứ vỡ mỗi lần YouTube đổi chữ).

Bền khi chết giữa chừng: trước khi đổi, ghi `logs/hl-tam/<kênh>.json` = hl GỐC (chỉ ghi nếu CHƯA có — lần đổi đầu
tiên mới biết gốc thật). `tra()` đọc tệp ấy, đặt lại, ĐỌC LẠI, rồi xoá. Lần chạy sau vẫn trả được nếu lần trước chết.
Chỉ đụng cặp `hl` của cookie PREF (giữ `gl`, `tz`, …); không đụng ngôn ngữ tài khoản Google.
"""
from __future__ import annotations

import json
import os
import time

GOC = os.path.dirname(os.path.abspath(__file__))
THU_MUC = os.path.join(GOC, "logs", "hl-tam")
#: hl GỐC rỗng (cookie PREF chưa có hl) — trả lại bằng cách BỎ cặp hl.
KHONG_CO = "-"


def _duong(kenh: str, thu_muc: str = None) -> str:
    return os.path.join(thu_muc or THU_MUC, "{0}.json".format(kenh))


def doc_tam(kenh: str, thu_muc: str = None) -> dict:
    try:
        with open(_duong(kenh, thu_muc), "r", encoding="utf-8") as tep:
            d = json.load(tep)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def ghi_tam(kenh: str, hl_goc: str, thu_muc: str = None) -> bool:
    """Ghi hl GỐC trước khi tạm đổi — CHỈ khi chưa có tệp (giữ gốc thật của lần đổi đầu). True nếu vừa ghi."""
    if doc_tam(kenh, thu_muc):
        return False
    d = _duong(kenh, thu_muc)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    with open(d + ".tam", "w", encoding="utf-8") as tep:
        json.dump({"hl_goc": hl_goc or KHONG_CO, "luc": time.strftime("%Y-%m-%d %H:%M:%S")}, tep, ensure_ascii=False)
    os.replace(d + ".tam", d)
    return True


def xoa_tam(kenh: str, thu_muc: str = None) -> None:
    try:
        os.remove(_duong(kenh, thu_muc))
    except OSError:
        pass


def cap_pref(gia_tri: str) -> list:
    return [c for c in str(gia_tri or "").split("&") if c.strip()]


def hl_cua(gia_tri: str) -> str:
    return next((c.split("=", 1)[1] for c in cap_pref(gia_tri) if c.split("=", 1)[0] == "hl" and "=" in c), "")


def pref_voi_hl(gia_tri: str, hl: str) -> str:
    """Giá trị PREF với `hl` mới (hl rỗng/KHONG_CO → bỏ cặp hl); giữ MỌI cặp khác. Hàm thuần."""
    giu = [c for c in cap_pref(gia_tri) if c.split("=", 1)[0] != "hl"]
    if hl and hl != KHONG_CO:
        giu.append("hl=" + hl)
    return "&".join(giu)


def _pref_cookie(cdp) -> dict:
    ck = cdp.goi("Storage.getCookies", {}, han=15).get("cookies") or []
    return ([c for c in ck if c.get("name") == "PREF" and "youtube.com" in str(c.get("domain") or "")] or [{}])[0]


def _dat_pref(cdp, goc: dict, gia_tri: str) -> None:
    c = {"name": "PREF", "value": gia_tri, "domain": ".youtube.com", "path": "/", "secure": True, "sameSite": "None",
         "expires": goc["expires"] if (goc.get("expires") or -1) > 0 else time.time() + 400 * 86400}
    cdp.goi("Storage.setCookies", {"cookies": [c]}, han=15)


def tra(cdp, kenh: str, nk=None, thu_muc: str = None) -> str:
    """TRẢ hl gốc (nếu có tệp tạm của kênh). Trả "" (không có gì để trả) | "ok:<hl>" | "loi:<lý do>".
    `cdp` cấp TRÌNH DUYỆT (Storage.*), không cần tab."""
    nk = nk or (lambda _s: None)
    d = doc_tam(kenh, thu_muc)
    if not d:
        return ""
    hl_goc = str(d.get("hl_goc") or KHONG_CO)
    try:
        goc = _pref_cookie(cdp)
        _dat_pref(cdp, goc, pref_voi_hl(goc.get("value", ""), hl_goc))
        sau = hl_cua(_pref_cookie(cdp).get("value", "")) or KHONG_CO
    except Exception as loi:  # noqa: BLE001 — giữ tệp tạm: lần sau trả tiếp
        nk("ngôn ngữ giao diện {0}: TRẢ hl={1} lỗi: {2}".format(kenh, hl_goc, str(loi)[:120]))
        return "loi:" + str(loi)[:120]
    if sau != hl_goc:
        nk("ngôn ngữ giao diện {0}: trả hl={1} nhưng đọc lại {2} — giữ tệp tạm".format(kenh, hl_goc, sau))
        return "loi:đọc lại {0}".format(sau)
    xoa_tam(kenh, thu_muc)
    nk("ngôn ngữ giao diện {0}: đã TRẢ lại hl={1} (máy DOM xong việc)".format(kenh, hl_goc))
    return "ok:" + hl_goc
