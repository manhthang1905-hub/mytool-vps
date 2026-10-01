"""Bộ não của giám đốc kênh — MỘT lượt LLM mạnh chọn trong thực đơn các việc đã có số.

    nghi(bs, quan_sat, thuc_don, thi_nghiem, ngan_sach, goi_chat, *, tuan) -> QuyetDinh
    doc_ket_qua(tho, thuc_don, thi_nghiem, toi_da_tham_so) -> dict | None
    goi_chat_that(goc) -> hàm gọi AI qua ví (hỏi van ví trước) | None

Luật: LLM CHỈ chọn id trong thực đơn (và viết chữ cho chỉ đạo / tiêu đề mới); giá trị tham số là của
thực đơn, không phải của LLM. `gioi_han.kiem` còn soát lại lần nữa trước khi áp. LLM hỏng / trả lời
không đọc được → hôm đó không áp gì (không có đường lùi "luật cứng tự áp").
Thang mô hình: `bien_tap_content.thang_mo_hinh` (Fable → Opus → Sonnet).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

TOI_DA_TOKEN = 3000
SO_LUOT_TOI_DA = 3
KET_HOP_LE = ("giu", "bo", "mo_rong", "chua_du")
TOI_DA_KY_TU_CHU = 200

TIEU_CHI = """\
- View = Hiển thị × CTR × Giữ chân: chẩn đoán cổng nào hỏng rồi mới sửa đúng cổng đó.
- Tự đọc BẢNG SỐ của CHÍNH kênh; ý biên tập viên / nhóm chỉ là tham khảo. n < 3 là tín hiệu yếu — chưa đủ
  số thì chọn ít hoặc không chọn gì, và nói rõ số nào chưa tin được.
- Mỗi thay đổi là một thí nghiệm đo được; không đổi hai thứ lên cùng một chỉ số; đừng lặp một khuôn.
- Việc chỉ chủ làm được (Studio, tiền, đăng nhập) → "viec_cua_ban", câu người thường hiểu. CHỈ việc người phải TỰ
  TAY làm — "đợi số / chờ video qua 48h" không phải việc của ai (máy tự đợi), không ghi vào đó.
- Với MỖI video đang "chờ" (chưa đủ 48h) trong bảng số: đoán "thang" | "truot" theo ngưỡng của kênh — máy tự
  chấm khi video qua 48h (tỉ lệ đoán đúng là thước đo giám đốc có đọc đúng kênh không)."""

DANG_TRA_LOI = """\
Chỉ trả MỘT khối JSON:
{"chan_doan": "≤ 3 câu, có số, theo 3 cổng của chính kênh — Hiển thị · CTR trang chủ · Giữ chân: cổng nào mạnh, cổng nào hỏng",
 "chon": [{"id": "d1", "ly_do": "1 câu có số", "noi_dung": "chỉ cho chi_dao (sửa câu được) / viec_studio (tiêu đề mới)"}],
 "ket_luan": [{"id": "<id thí nghiệm>", "ket": "giu|bo|mo_rong|chua_du", "ly_do": "1 câu"}],
 "viec_cua_ban": ["…"],
 "du_doan": [{"video_id": "<mã video đang chờ>", "ket": "thang|truot", "ly_do": "1 câu có số"}],
 "tuan_toi": "1 câu: tuần tới giám đốc định thử gì"}"""


@dataclass
class QuyetDinh:
    """Kết quả một lượt nghĩ. `loi` khác rỗng = không quyết được (không áp gì)."""
    chan_doan: str = ""
    chon: List[Dict[str, Any]] = field(default_factory=list)
    ket_luan: List[Dict[str, Any]] = field(default_factory=list)
    viec_cua_ban: List[str] = field(default_factory=list)
    du_doan: List[Dict[str, Any]] = field(default_factory=list)
    tuan_toi: str = ""
    mo_hinh: str = ""
    loi: str = ""
    loi_nhac: str = ""
    tho: str = ""


def _gon(x: Any, n: int) -> str:
    s = " ".join(str(x or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _dong_thuc_don(d: Dict[str, Any]) -> str:
    """Một dòng thực đơn cho lời nhắc."""
    dau = "{0} [{1}/{2}]".format(d["id"], d.get("plugin", "?"), d["loai"])
    if d["loai"] == "tham_so":
        than = "{0}: {1} → {2}".format(d["khoa"], d.get("gia_tri_cu"), d["gia_tri"])
    elif d["loai"] == "chi_dao":
        than = "chỉ đạo (hạn {0} ngày, sửa câu được): “{1}”".format(d.get("han_ngay"), d.get("noi_dung"))
    else:
        g = d.get("goi_y") or {}
        than = ("đổi tiêu đề {0} “{1}” — CẦN viết noi_dung = tiêu đề mới (giữ nhãn đầu, cùng ý). Bản đã chấm: {2}. "
                "Tiêu đề thắng của kênh: {3}. Pool cạnh video: {4}.").format(
            d.get("video_id"), d.get("tieu_de_cu"), " / ".join(g.get("tieu_de_da_cham") or []) or "—",
            " / ".join(g.get("tieu_de_thang_kenh") or []) or "—", " / ".join(g.get("pool") or []) or "—")
    duoi = " — giả thuyết: {0}".format(d.get("gia_thuyet")) if d.get("gia_thuyet") else ""
    if d.get("co_mau") and d["loai"] == "tham_so":
        duoi += " (đo {0}, cỡ mẫu {1}, hạn {2} ngày)".format(d.get("chi_so"), d.get("co_mau"), d.get("han_ngay"))
    return dau + " " + than + duoi


def loi_nhac(bs: Any, quan_sat: Dict[str, List[Dict[str, Any]]], thuc_don: List[Dict[str, Any]],
             thi_nghiem: List[Dict[str, Any]], ngan_sach: Dict[str, Any], *, tuan: bool = False) -> str:
    """MỤC TIÊU + TIÊU CHÍ + DỮ LIỆU (bảng số, quan sát, thí nghiệm, ngân sách, thực đơn) + DẠNG TRẢ LỜI."""
    from .bao_cao import bang_so_chu  # noqa: PLC0415

    qs = ["- [{0}] {1} (n={2}, tin cậy {3})".format(t, q["cau"], q.get("n", 0), q.get("tin_cay", "?"))
          for t, ds in quan_sat.items() for q in ds] or ["(không có)"]
    tn = ["- {0} [{1}]: {2}; biến {3} {4} → {5}; nền {6}; hạn {7}; số hiện tại: {8}{9}".format(
        t["id"], t.get("viec"), t.get("gia_thuyet"), (t.get("bien") or {}).get("khoa"), (t.get("bien") or {}).get("cu"),
        (t.get("bien") or {}).get("moi"), (t.get("nen") or {}).get("gia_tri"), str(t.get("han"))[:10],
        (t.get("_ket_luan_so") or {}).get("so"), " — CÒ QUAY LUI: " + t["_quay_lui"] if t.get("_quay_lui") else "")
        for t in thi_nghiem] or ["(không có)"]
    ns = "Còn {0}/2 thay đổi tham số tuần này; {1}/2 việc Studio. Khoá đang nghỉ: {2}. Chủ giữ: {3}.".format(
        ngan_sach.get("tham_so_con"), ngan_sach.get("studio_con"),
        ", ".join(ngan_sach.get("khoa_nghi") or {}) or "không", ", ".join(ngan_sach.get("chu_giu") or {}) or "không")
    luot = ("LƯỢT TUẦN: kết luận thí nghiệm đủ mẫu, tối đa 2 thay đổi tham số, làm mới chỉ đạo (≤ 5 dòng)."
            if tuan else "LƯỢT NGÀY: chỉ việc gấp (cứu video, thí nghiệm tới hạn); tối đa 1 thay đổi tham số.")
    td = [_dong_thuc_don(d) for d in thuc_don] or ["(trống — không có việc nào qua giới hạn an toàn)"]
    return "\n\n".join([
        "Bạn là GIÁM ĐỐC KÊNH YouTube {0}: người làm nội dung giỏi — đọc số, chọn ÍT việc nhưng đúng cổng hỏng, "
        "rồi đo lại.\nMỤC TIÊU\n{1}".format(bs.ma_kenh, bs.muc_tieu),
        "TIÊU CHÍ\n" + TIEU_CHI,
        "BẢNG SỐ\n" + bang_so_chu(bs),
        "QUAN SÁT\n" + "\n".join(qs),
        "THÍ NGHIỆM ĐANG MỞ\n" + "\n".join(tn),
        "NGÂN SÁCH\n" + ns + "\n" + luot,
        "THỰC ĐƠN (chỉ được chọn id trong đây; không có gì đáng làm thì \"chon\": [])\n" + "\n".join(td),
        DANG_TRA_LOI,
    ])


def doc_ket_qua(tho: str, thuc_don: List[Dict[str, Any]], thi_nghiem: List[Dict[str, Any]],
                toi_da_tham_so: int = 2, video_cho: Optional[set] = None) -> Optional[Dict[str, Any]]:
    """Câu trả lời thô → quyết định đã soát. Không đọc được / sai dạng → None. Bỏ mọi id lạ, việc Studio
    thiếu tiêu đề mới, tham số vượt ngân sách; chữ dài quá thì cắt. `du_doan` chỉ giữ video trong
    `video_cho` (video đang chờ kết luận của kênh)."""
    from ..goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du = loc_json(tho)
    except (ValueError, TypeError):
        return None
    if not isinstance(du, dict) or not ("chon" in du or "chan_doan" in du):
        return None
    theo_id = {d["id"]: d for d in thuc_don}
    chon: List[Dict[str, Any]] = []
    so_tham_so = 0
    for m in du.get("chon") or []:
        if not isinstance(m, dict) or m.get("id") not in theo_id or any(c["id"] == m["id"] for c in chon):
            continue
        d = dict(theo_id[m["id"]], ly_do_llm=_gon(m.get("ly_do"), 300))
        nd = _gon(m.get("noi_dung"), TOI_DA_KY_TU_CHU)
        if d["loai"] == "viec_studio":
            if not nd:
                continue
            d["noi_dung"] = nd
        elif d["loai"] == "chi_dao" and nd:
            d["noi_dung"] = nd
        elif d["loai"] == "tham_so":
            if so_tham_so >= toi_da_tham_so:
                continue
            so_tham_so += 1
        chon.append(d)
    id_tn = {t["id"] for t in thi_nghiem}
    ket_luan = [{"id": k["id"], "ket": k["ket"], "ly_do": _gon(k.get("ly_do"), 300)}
                for k in du.get("ket_luan") or []
                if isinstance(k, dict) and k.get("id") in id_tn and k.get("ket") in KET_HOP_LE]
    vcb = du.get("viec_cua_ban") or []
    dd: List[Dict[str, Any]] = []
    for x in du.get("du_doan") or []:
        if (isinstance(x, dict) and str(x.get("video_id")) in (video_cho or set()) and x.get("ket") in ("thang", "truot")
                and all(d["video_id"] != str(x["video_id"]) for d in dd)):
            dd.append({"video_id": str(x["video_id"]), "ket": x["ket"], "ly_do": _gon(x.get("ly_do"), 200)})
    return {"chan_doan": _gon(du.get("chan_doan"), 600), "chon": chon, "ket_luan": ket_luan, "du_doan": dd,
            "viec_cua_ban": [_gon(x, 300) for x in (vcb if isinstance(vcb, list) else [vcb]) if str(x).strip()][:5],
            "tuan_toi": _gon(du.get("tuan_toi"), 300)}


def nghi(bs: Any, quan_sat: Dict[str, List[Dict[str, Any]]], thuc_don: List[Dict[str, Any]],
         thi_nghiem: List[Dict[str, Any]], ngan_sach: Dict[str, Any], goi_chat: Optional[Callable[..., str]], *,
         tuan: bool = False, ghi: Optional[Callable[[str], None]] = None) -> QuyetDinh:
    """Một lượt LLM theo thang mô hình; mô hình hỏng / trả lời không đọc được thì thử bậc dưới."""
    ln = loi_nhac(bs, quan_sat, thuc_don, thi_nghiem, ngan_sach, tuan=tuan)
    if goi_chat is None:
        return QuyetDinh(loi="không có hàm gọi AI (chế độ thử)", loi_nhac=ln)
    from ..bien_tap_content import thang_mo_hinh  # noqa: PLC0415

    toi_da = min(int(ngan_sach.get("tham_so_con") or 0), 2 if tuan else 1)
    khoa = "giam-doc-{0}-{1}-{2}".format(bs.ma_kenh, bs.bay_gio.strftime("%Y%m%d%H"),
                                        hashlib.sha1(ln.encode("utf-8")).hexdigest()[:10])
    loi = ""
    for lan, mo_hinh in enumerate(thang_mo_hinh(bs.goc, bs.ma_kenh)[:SO_LUOT_TOI_DA], 1):
        try:
            tho = goi_chat(ln, mo_hinh=mo_hinh, khoa="{0}-{1}".format(khoa, lan), toi_da_token=TOI_DA_TOKEN)
        except Exception as e:  # noqa: BLE001 — mô hình hỏng thì thử bậc dưới
            loi = "{0}: {1}".format(mo_hinh, str(e)[:160])
            if ghi:
                ghi("  [giám đốc] {0} hỏng — thử bậc dưới.".format(loi))
            continue
        kq = doc_ket_qua(tho, thuc_don, thi_nghiem, toi_da,
                         {v["id"] for v in getattr(bs, "video", []) or [] if not v.get("ket_luan")})
        if kq is not None:
            return QuyetDinh(mo_hinh=mo_hinh, loi_nhac=ln, tho=tho, **kq)
        loi = "{0}: trả lời không đọc được — {1}".format(mo_hinh, _gon(tho, 120))
        if ghi:
            ghi("  [giám đốc] " + loi)
    return QuyetDinh(loi=loi or "không mô hình nào trả lời", loi_nhac=ln)


def vi_cho_phep(goc: str) -> str:
    """Rỗng nếu van ví không chặn; không thì lý do (chỉ ĐỌC trạng thái van, không ghi)."""
    try:
        from ..van_vi import doc_trang_thai  # noqa: PLC0415

        tt = doc_trang_thai(goc) or {}
    except Exception:  # noqa: BLE001 — không đọc được van thì không chặn (cùng luật van_vi)
        return ""
    return str(tt.get("ly_do_chan") or "ví đang bị chặn") if tt.get("chan") else ""


def goi_chat_that(goc: str, ghi: Optional[Callable[[str], None]] = None) -> Optional[Callable[..., str]]:
    """Hàm gọi AI qua ví ShopAPI (client như `tram_nen._bo_viet_ho`); None khi van ví đang chặn."""
    ly = vi_cho_phep(goc)
    if ly:
        if ghi:
            ghi("  [giám đốc] không gọi AI: " + ly)
        return None
    hop: Dict[str, Any] = {}

    def goi(de_bai: str, mo_hinh: str = "claude-sonnet-5", khoa: str = "", toi_da_token: int = TOI_DA_TOKEN) -> str:
        import os  # noqa: PLC0415

        from ..goi_van_ban import goi_van_ban, tin_nhan_viet  # noqa: PLC0415

        if "client" not in hop:
            from ..api import build_client  # noqa: PLC0415
            from ..config import CONFIG_FILENAME, load_config  # noqa: PLC0415

            ch = load_config(os.path.join(goc, CONFIG_FILENAME))
            if ch.problem:
                raise RuntimeError("tool chưa đăng nhập được: " + ch.problem)
            hop["client"] = build_client(ch)
        return goi_van_ban(hop["client"], tin_nhan_viet(de_bai), mo_hinh=mo_hinh, toi_da_token=int(toi_da_token),
                           khoa=khoa, on_log=ghi)

    return goi
