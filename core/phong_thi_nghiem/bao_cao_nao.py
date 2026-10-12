"""Mục PHÒNG THÍ NGHIỆM trong báo cáo `python -m core.nao xem` (gọn, có số): bảng xếp hạng theo kênh + độ thay đổi so
lần tính ngày trước, quyết định gần đây, việc SẮP TỚI NGƯỠNG (máy tính sẵn), giả thuyết mới đang chạy bóng, lệnh đề xuất.

Mã tính số, não suy nghĩ: não đọc mục này để đề xuất giả thuyết mới (`gia-thuyet-moi`) hoặc ghi lý do giữ nguyên.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import _chung as c

TOP_MOI_KENH = 4
NGAY_QUYET_DINH_GAN = 3


def _pt(x: Any) -> str:
    return "—" if x is None else "{0:.0f}%".format(100.0 * float(x))


def _ci(ci: Any) -> str:
    return "[{0:.0f}–{1:.0f}]".format(100 * ci[0], 100 * ci[1]) if ci else ""


def _delta(p: Any, p0: Any) -> str:
    if p is None or p0 is None:
        return ""
    d = 100.0 * (float(p) - float(p0))
    return " ({0}{1:.0f})".format("▲" if d > 0 else "▼", abs(d)) if abs(d) >= 1 else ""


def sap_toi_nguong(bang: Dict[str, Any], vai: Dict[str, Dict[str, str]]) -> List[str]:
    """Dòng "sắp tới ngưỡng" — dẫn đầu / loại / mất dẫn đầu sắp xảy ra, giả thuyết mới kẹt sàn."""
    from . import luat  # noqa: PLC0415

    t2 = bang.get("tang2") or {}
    gts = bang.get("gia_thuyet") or {}
    ra: List[str] = []
    for kenh, m in sorted((t2.get("theo_kenh") or {}).items()):
        for gt, o in sorted(m.items()):
            if (gts.get(gt) or {}).get("trang_thai") == "loai" or o.get("p_tot_nhat") is None:
                continue
            n, p = int(o.get("n") or 0), float(o.get("p_tot_nhat") or 0)
            v = (vai.get(kenh) or {}).get(gt, "")
            if v != luat.DAN_DAU and p >= 0.6 and luat.N_QUYET - 3 <= n < luat.N_QUYET:
                ra.append("{0} @{1}: P {2} với n {3}/{4} — thêm {5} video đã phán là xét DẪN ĐẦU".format(
                    gt, kenh, _pt(p), n, luat.N_QUYET, luat.N_QUYET - n))
            elif v == luat.DAN_DAU and p < luat.P_DAN_DAU + 0.05:
                ra.append("{0} @{1}: đang dẫn đầu nhưng P chỉ {2} (ngưỡng {3}) — mong manh".format(
                    gt, kenh, _pt(p), _pt(luat.P_DAN_DAU)))
            elif v != luat.LOAI and p < 0.1 and n >= max(3, luat.N_QUYET - 3):
                g2, o2 = luat.doi_thu_dan(m, gt)
                ra.append("{0} @{1}: P {2} với n {3} — ứng viên LOẠI (đối thủ {4} n {5}/{6})".format(
                    gt, kenh, _pt(p), n, g2 or "—", o2.get("n", 0), luat.N_QUYET))
    for gt, o in sorted(gts.items()):
        if (o or {}).get("trang_thai") != "bong":
            continue
        ngay_b = max([int(((bang.get("ngay_bong") or {}).get(k) or {}).get(gt) or 0)
                      for k in (bang.get("ngay_bong") or {})] or [0])
        if ngay_b < luat.NGAY_BONG:
            ra.append("{0} ({1}, tạo {2}): chạy bóng {3}/{4} ngày — chưa được khe".format(
                gt, o.get("tao_boi") or "?", o.get("tao_luc") or "?", ngay_b, luat.NGAY_BONG))
        elif not any(v.get(gt) in (luat.THU, luat.DAN_DAU) for v in vai.values()):
            _ok, ly = luat.qua_san_tang1(bang, "", gt)
            ra.append("{0}: đủ {1} ngày bóng nhưng KẸT SÀN tầng 1 ở mọi kênh — {2}".format(gt, ngay_b, ly[:140]))
    return ra


def dong_nao(goc: str, *, kenh_ds: Optional[List[str]] = None) -> List[str]:
    from . import chia_khe, danh_gia, luat  # noqa: PLC0415

    bang = danh_gia.doc_bang(goc)
    if not bang:
        return ["  (chưa có bảng xếp hạng — `python -m core.phong_thi_nghiem --danh-gia`)"]
    t2 = bang.get("tang2") or {}
    ts = bang.get("tham_so") or {}
    lich = danh_gia.doc_lich_su(goc)
    truoc = next((x for x in reversed(lich) if x.get("ngay") and x["ngay"] < (bang.get("ngay") or c.hom_nay())), None)
    hom = c.hom_nay()
    d = ["  Bảng lúc {0} · nền danh mục {1} trên {2} video đã phán{3}. Luật: dẫn đầu P ≥ {4} & n ≥ {5}; loại P < {6} "
         "& n ≥ {5} (chỉ khi thua giả thuyết cũng đã đo n ≥ {5}); mới: ≥ {7} ngày bóng + qua sàn tầng 1 → {8} khe/kênh/tuần."
         .format(str(bang.get("luc") or "")[:16].replace("T", " "), _pt(t2.get("g")), t2.get("n_nen", 0),
                 " · Δ so {0}".format(truoc["ngay"]) if truoc else "", _pt(ts.get("p_dan_dau", 0.8)),
                 ts.get("n_quyet", 8), _pt(ts.get("p_loai", 0.05)), luat.NGAY_BONG, chia_khe.KHE_THU_TUAN)]
    vai_all: Dict[str, Dict[str, str]] = {}
    for kenh in kenh_ds or list(bang.get("kenh") or []):
        m = (t2.get("theo_kenh") or {}).get(kenh) or {}
        if not m:
            continue
        vai_all[kenh] = {g: v[0] for g, v in luat.vai_kenh(bang, kenh).items()}
        on, _vi_sao = chia_khe.bat(goc, kenh)
        tr = ((truoc or {}).get("kenh") or {}).get(kenh) or {}
        top = sorted(m.items(), key=lambda kv: -float(kv[1].get("p_tot_nhat") or -1))[:TOP_MOI_KENH]
        phan = []
        for gt, o in top:
            v = vai_all[kenh].get(gt, "")
            phan.append("{0}{1} n{2} TB {3} {4} P {5}{6}".format(
                gt, {"dan_dau": "(DẪN ĐẦU)", "thu": "(thử)", "loai": "(loại)"}.get(v, ""), o.get("n", 0), _pt(o.get("tb")),
                _ci(o.get("ci90")), _pt(o.get("p_tot_nhat")), _delta(o.get("p_tot_nhat"), (tr.get(gt) or [0, 0, 0, None])[3])))
        dong = "  - {0} [chia khe {1}]: {2}".format(kenh, "BẬT" if on else "tắt", " · ".join(phan))
        if on:
            try:
                tt = chia_khe.tom_tat_kenh(goc, kenh, ngay=hom, bang=bang)
                tl = tt.get("ti_le_khe") or {}
                dong += " | khe dự kiến: " + ", ".join("{0} {1}".format(g, _pt(x)) for g, x in
                                                     sorted(tl.items(), key=lambda kv: -kv[1])[:4])
            except Exception:  # noqa: BLE001
                pass
        d.append(dong)
    gan = c.cong_ngay(hom, -NGAY_QUYET_DINH_GAN)
    qd = [x for x in luat.doc_quyet_dinh(goc, 60) if str(x.get("ngay") or "") >= gan]
    d.append("  Quyết định {0} ngày qua ({1}):".format(NGAY_QUYET_DINH_GAN, len(qd)))
    for x in qd[-8:]:
        d.append("    · {0} {1}{2}: {3}".format(x.get("ten") or x.get("loai"), x.get("gt"),
                                               " @" + x["kenh"] if x.get("kenh") else "", str(x.get("ly_do") or "")[:150]))
    if not qd:
        d.append("    (không có)")
    sap = sap_toi_nguong(bang, vai_all)
    d.append("  SẮP TỚI NGƯỠNG / CẦN NÃO XEM ({0}):".format(len(sap)))
    d += ["    · " + x for x in sap[:10]] or ["    (không có)"]
    d.append("  Đề xuất giả thuyết mới (chạy bóng trước, mã tự đo): `python -m core.nao gia-thuyet-moi --id H-TEN "
             "--mo-ta \"...\" --trong-so \"log_vuot:1,dai_tot:0.5\" [--cong \"vuot>=3; trong_pool co\"] [--tran "
             "\"log_vuot:3.9\"] --ly-do \"lý lẽ + số\"` · xem đặc trưng: `python -m core.nao gia-thuyet-moi --dac-trung`")
    return d


__all__ = ["dong_nao", "sap_toi_nguong"]
