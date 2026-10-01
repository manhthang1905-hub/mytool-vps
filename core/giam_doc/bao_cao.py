"""Chữ của giám đốc kênh: bảng số cho lời nhắc, bản in `--thu`, báo cáo tuần, một câu cho bảng điều khiển.

    bang_so_chu(bs) -> str            BẢNG SỐ gọn (≤ ~6k token) — vào lời nhắc và bản in thử
    in_ket_qua(kq) -> str             bản in `python -m core.giam_doc --thu/--llm`
    ghi_tuan(goc, ma, kq) -> str      `giam-doc/BAO-CAO-TUAN.md` + `bao-cao.json`
    cau_the(goc, ma) -> str           một dòng cho bảng điều khiển
"""

from __future__ import annotations

import io
import json
import os
from typing import Any, Dict, List

from .du_lieu import BangSo, chu_so, ctr_trang_chu, moi_nhat, thu_muc_giam_doc, trong_khoang

TOI_DA_KY_TU_BANG = 14000
TEP_BAO_CAO_MD = "BAO-CAO-TUAN.md"
TEP_BAO_CAO_JSON = "bao-cao.json"


_s = chu_so


def _dong_video(v: Dict[str, Any]) -> str:
    b = moi_nhat(v) or {}
    tc = ctr_trang_chu(v) or {}
    kl = {"thang": "THẮNG", "truot": "trượt", "": "chờ"}.get(v.get("ket_luan") or "", v.get("ket_luan"))
    return ("- {id} {ngay} · {phut} phút · cụm {cum} · công thức {ct} → {kl} · 48h: {h48} hiển thị\n"
            "  @{tuoi}h: {imp} hiển thị, CTR {ctr} (CTR trang chủ {ctrb}), trang chủ {pb} / đề xuất {pd} view, "
            "AVD {avd}, {gx} giờ xem/1k hiển thị, sub/1k view {s1k} — “{td}”").format(
        id=v["id"], ngay=v.get("ngay_dang") or "?", phut=_s((v.get("dai_giay") or 0) / 60.0, 1) if v.get("dai_giay") else "?",
        cum="/".join(v.get("cum") or []) or "—", ct=v.get("cong_thuc") or "—", kl=kl,
        h48=_s(v.get("hien_thi_48h")), tuoi=_s(b.get("tuoi")), imp=_s(b.get("hien_thi")),
        ctr=_s(b.get("ctr"), 1, "%"), ctrb=_s(tc.get("ctr_browse"), 1, "%") + ("@{0:.0f}h".format(tc["tuoi"]) if tc else ""), pb=_s(b.get("pct_browse"), 0, "%"),
        pd=_s(b.get("pct_de_xuat"), 0, "%"), avd=_s(b.get("avd_pct"), 0, "%"), gx=_s(b.get("gx_1k"), 2),
        s1k=_s(v.get("sub_1k"), 1), td=(v.get("tieu_de") or "")[:60])


def bang_so_chu(bs: BangSo, toi_da: int = TOI_DA_KY_TU_BANG) -> str:
    """Bảng số gọn của kênh, cắt ở `toi_da` ký tự (video cũ nhất rơi trước)."""
    import datetime as _dt  # noqa: PLC0415

    y = bs.ypp or {}
    dau = [
        "Kênh {0} · giai đoạn {1} · chien_luoc: {2} · cong_thuc_chon: {3} · phut_muc_tieu: {4} · tự học: {5}".format(
            bs.ma_kenh, bs.giai_doan or "?", bs.cai.get("chien_luoc") or "(không khai)",
            bs.cai.get("cong_thuc_chon") or "tu_dong", _s(bs.phut_muc_tieu), bs.cai.get("chien_luoc_tu_hoc", False)),
        "YPP (trọn đời): {0} sub · {1} giờ xem — ràng buộc: {2}".format(
            _s(y.get("sub")), _s(y.get("gio_xem")), y.get("rang_buoc") or "?"),
        "Ngưỡng thắng 48h của kênh: {0} hiển thị (tính từ {1} video có số 48h) · mục tiêu CTR trang chủ {2} ({3})".format(
            _s(bs.nguong_thang_48h), bs.n_48h,
            _s(bs.ctr_muc_tieu, 1, "%"), bs.nhan_ctr_muc_tieu)
        + (" — kênh < 5 video có số 48h: ngưỡng = ngưỡng NGÁCH trộn dần sang trung vị kênh "
           "(cong_thuc_v7.nguong_thang_48h), nhãn thắng/trượt còn non" if bs.n_48h < 5 else ""),
    ]
    cuoi_k = [d for d in bs.kenh_ngay if d.get("hien_thi") is not None]
    if cuoi_k:
        d = cuoi_k[-1]
        dau.append("Kênh trọn đời (chụp {0:%d/%m %H:%M}): {1} hiển thị · CTR {2} · {3} view · {4} giờ xem · {5} sub".format(
            d["luc"], _s(d["hien_thi"]), _s(d.get("ctr"), 2, "%"), _s(d.get("xem")), _s(d.get("gio_xem"), 1),
            _s(d.get("sub"))))
    mot = _dt.timedelta(days=7)
    for ten, tu, den in (("7 ngày qua", bs.bay_gio - mot, bs.bay_gio), ("7 ngày trước đó", bs.bay_gio - 2 * mot, bs.bay_gio - mot)):
        h = trong_khoang(bs, "hien_thi", tu, den)
        if h is not None:
            dau.append("Kênh {0}: {1} hiển thị · {2} giờ xem · {3} sub · {4} view".format(
                ten, _s(h), _s(trong_khoang(bs, "gio_xem", tu, den), 1), _s(trong_khoang(bs, "sub", tu, den)),
                _s(trong_khoang(bs, "xem", tu, den))))
    bh = ["- " + b["cau"] for b in bs.bai_hoc if b.get("pham_vi") == "kenh" and int(b.get("n") or 0) >= 3][:10]
    cuoi = []
    if bh:
        cuoi.append("BÀI HỌC KÊNH (n ≥ 3):\n" + "\n".join(bh))
    if bs.luat_chon:
        cuoi.append("LUẬT CHỌN ĐANG DÙNG: " + " | ".join(bs.luat_chon[:4])[:600])
    if bs.bien_tap_cuoi.get("nhan_dinh"):
        cuoi.append("BIÊN TẬP VIÊN (lần cuối {0}): {1}".format(str(bs.bien_tap_cuoi.get("luc"))[:16],
                                                          bs.bien_tap_cuoi["nhan_dinh"][:400]))
    if bs.ghi_chu:
        cuoi.append("THIẾU SỐ: " + "; ".join(bs.ghi_chu))
    video = [_dong_video(v) for v in bs.video]
    while True:
        chu = "\n".join(dau + ["VIDEO (mới → cũ, {0}/{1}):".format(len(video), len(bs.video))] + video + cuoi)
        if len(chu) <= toi_da or not video:
            return chu[:toi_da]
        video.pop()


def _dong_de_xuat(d: Dict[str, Any]) -> str:
    dau = "✔" if d.get("duoc") else "✘"
    if d["loai"] == "tham_so":
        than = "{0}: {1} → {2}".format(d.get("khoa"), d.get("gia_tri_cu"), d.get("gia_tri"))
    elif d["loai"] == "chi_dao":
        than = "chỉ đạo: “{0}”".format(d.get("noi_dung"))
    else:
        than = "Studio {0} {1}: “{2}”".format(d.get("viec"), d.get("video_id"), d.get("tieu_de_cu") or "")
    ly = "" if d.get("duoc") else " — chặn: " + str(d.get("ly_do_kiem"))
    return "  {0} {1} [{2}] {3}{4}".format(dau, d["id"], d["loai"], than, ly)


def in_ket_qua(kq: Any, *, ca_loi_nhac: bool = False) -> str:
    """Bản in đầy đủ của một lượt chạy (bảng số → quan sát → đề xuất → quyết định)."""
    bs = kq.bs
    ra: List[str] = ["=== GIÁM ĐỐC KÊNH {0} · {1:%d/%m/%Y %H:%M} · chế độ {2}{3} ===".format(
        bs.ma_kenh, bs.bay_gio, kq.che_do, " · lượt tuần" if kq.tuan else ""), "", "MỤC TIÊU", bs.muc_tieu, "",
        "BẢNG SỐ", bang_so_chu(bs), ""]
    for v in kq.viec:
        ra.append("── {0} ({1}) · áp dụng {2:.1f}{3}".format(v["ten"], v["nhip"], v["ap_dung"],
                                                          " · LỖI: " + v["loi"] if v.get("loi") else ""))
        if v["ap_dung"] <= 0 and not v.get("loi"):
            ra.append("  (không chạy: thiếu dữ liệu)")
        ra += ["  · {0} (n={1}, {2})".format(q["cau"], q.get("n", 0), q.get("tin_cay", "?")) for q in v["quan_sat"]]
        ra += [_dong_de_xuat(d) for d in kq.thuc_don if d.get("plugin") == v["ten"]]
    ra += ["", "THÍ NGHIỆM ĐANG MỞ: " + (", ".join(t["id"] for t in kq.thi_nghiem) or "không")]
    if kq.bao_dong:
        ra.append("SỨC KHOẺ BÁO ĐỘNG — đóng băng mọi thay đổi.")
    qd = kq.quyet_dinh
    if qd is not None:
        ra += ["", "QUYẾT ĐỊNH ({0})".format(qd.mo_hinh or "—")]
        if qd.loi:
            ra.append("  không quyết được: " + qd.loi)
        else:
            ra.append("  Chẩn đoán: " + qd.chan_doan)
            ra += ["  Chọn {0}: {1} — {2}".format(d["id"], d.get("noi_dung") or d.get("gia_tri") or d.get("viec"),
                                                d.get("ly_do_llm")) for d in qd.chon] or ["  Chọn: (không chọn gì)"]
            ra += ["  Kết luận {0}: {1} — {2}".format(k["id"], k["ket"], k["ly_do"]) for k in qd.ket_luan]
            ra += ["  Tuần tới: " + qd.tuan_toi] if qd.tuan_toi else []
    vcb = list(kq.viec_cua_ban) + (list(qd.viec_cua_ban) if qd is not None else [])
    if vcb:
        ra += ["", "VIỆC CỦA BẠN"] + ["  - " + x for x in dict.fromkeys(vcb)]
    if kq.da_lam:
        ra += ["", "ĐÃ LÀM"] + ["  - " + json.dumps(x, ensure_ascii=False, default=str) for x in kq.da_lam]
    if ca_loi_nhac and qd is not None:
        ra += ["", "──────── LỜI NHẮC ({0} ký tự) ────────".format(len(qd.loi_nhac)), qd.loi_nhac,
               "", "──────── TRẢ LỜI THÔ ────────", (qd.tho or "")[:6000]]
    return "\n".join(ra) + "\n"


def ghi_tuan(goc: str, ma: str, kq: Any) -> str:
    """Báo cáo tuần bằng câu người thường hiểu: đã thử gì, kết quả, tuần tới làm gì. Trả đường tệp .md."""
    from . import so_thi_nghiem as stn  # noqa: PLC0415

    qd = kq.quyet_dinh
    ds = stn.doc(goc, ma)
    dong = ["# Báo cáo tuần — giám đốc kênh {0}".format(ma), "",
            "_{0:%d/%m/%Y %H:%M} · chế độ {1}_".format(kq.bs.bay_gio, kq.che_do), "",
            "## Kênh đang thế nào", (qd.chan_doan if qd and not qd.loi else "(không có chẩn đoán)"), "",
            "## Đã thử"]
    dong += ["- {0}: {1} — **{2}**{3}".format(t.get("viec"), t.get("gia_thuyet"), t.get("trang_thai"),
                                             " ({0})".format((t.get("ket_luan") or {}).get("ly_do"))
                                             if (t.get("ket_luan") or {}).get("ly_do") else "")
             for t in ds[-8:]] or ["- (chưa có thí nghiệm nào)"]
    se_lam = list(getattr(kq, "se_lam", []) or [])
    if kq.che_do == "goi_y":
        dong += ["", "## Sẽ làm (chế độ gợi ý — CHƯA áp gì)"]
        dong += ["- {0}{1} — {2}".format(
            "{0}: {1} → {2}".format(x.get("khoa"), x.get("cu"), x.get("moi")) if x.get("loai") == "tham_so"
            else "chỉ đạo: “{0}”".format(x.get("moi")), "", x.get("ly_do_llm") or x.get("gia_thuyet") or "")
            for x in se_lam] or ["- (không chọn gì)"]
    tc = dict(getattr(kq, "tu_cham", {}) or {})
    if tc.get("tong") or tc.get("cho") or tc.get("moi_doan"):
        dong += ["", "## Tự chấm dự đoán thắng/trượt",
                 "- Đã chấm {0}: đúng {1}{2}; đang chờ 48h: {3} (lượt này đoán thêm {4}).".format(
                     tc.get("tong", 0), tc.get("dung", 0),
                     " ({0:.0%})".format(tc["dung"] / tc["tong"]) if tc.get("tong") else "",
                     tc.get("cho", 0) + int(tc.get("moi_doan") or 0), int(tc.get("moi_doan") or 0))]
    dong += ["", "## Tuần tới", (qd.tuan_toi if qd and qd.tuan_toi else "(chưa có)")]
    vcb = list(kq.viec_cua_ban) + (list(qd.viec_cua_ban) if qd else [])
    if vcb:
        dong += ["", "## Việc của bạn"] + ["- " + x for x in dict.fromkeys(vcb)]
    tm = thu_muc_giam_doc(goc, ma)
    os.makedirs(tm, exist_ok=True)
    duong = os.path.join(tm, TEP_BAO_CAO_MD)
    with io.open(duong, "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")
    stn._ghi_json(os.path.join(tm, TEP_BAO_CAO_JSON), {  # noqa: SLF001
        "kenh": ma, "luc": kq.bs.bay_gio.isoformat(timespec="seconds"), "che_do": kq.che_do,
        "chan_doan": qd.chan_doan if qd else "", "tuan_toi": qd.tuan_toi if qd else "",
        "viec_cua_ban": list(dict.fromkeys(vcb)), "da_lam": kq.da_lam, "se_lam": se_lam, "tu_cham": tc,
        "loi_llm": qd.loi if qd is not None else "", "mo_hinh": qd.mo_hinh if qd is not None else ""})
    return duong


def cau_the(goc: str, ma: str) -> str:
    """Một dòng cho bảng điều khiển: lần chạy cuối + chẩn đoán + số thí nghiệm mở."""
    from . import so_thi_nghiem as stn  # noqa: PLC0415

    try:
        with io.open(os.path.join(thu_muc_giam_doc(goc, ma), TEP_BAO_CAO_JSON), encoding="utf-8") as tep:
            bc = json.load(tep)
    except (OSError, ValueError):
        bc = {}
    mo = len(stn.dang_mo(stn.doc(goc, ma)))
    tt = stn.doc_trang_thai(goc, ma)
    if tt.get("loi_cuoi") and str(tt.get("loi_luc")) > str(bc.get("luc") or ""):
        return "Giám đốc kênh: lượt {0} hỏng — {1}; mai tự thử lại.".format(
            str(tt["loi_luc"])[:16].replace("T", " "), str(tt["loi_cuoi"])[:120])
    if not bc:
        return "Giám đốc kênh: chưa chạy lần nào."
    tc = bc.get("tu_cham") or {}
    doan = " · đoán đúng {0}/{1}".format(tc.get("dung", 0), tc["tong"]) if tc.get("tong") else ""
    chan = bc.get("chan_doan") or ("(không quyết được: {0})".format(str(bc.get("loi_llm"))[:80])
                                   if bc.get("loi_llm") else "—")
    return "Giám đốc kênh ({0}, {1}): {2} · {3} thí nghiệm đang mở{4}.".format(
        str(bc.get("luc"))[:16].replace("T", " "), bc.get("che_do"), chan[:140], mo, doan)
