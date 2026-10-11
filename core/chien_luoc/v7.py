"""Công thức V7 — cụm đang thắng + bảng đề xuất của CHÍNH kênh + nguồn nổ thật + khuôn.

Thân nhánh V7 cũ của `tu_chay.ung_vien_xep_hang`, dời nguyên văn; lọc chung (`nc.loc`); rồi cộng điểm anh em trong
nhóm (`tu_chay._cong_diem_anh_em_an_toan`, chạy SAU lọc vì trần "tự thắng" tính trên bảng đã lọc).

═══ CHỌN THEO HẠNG (12/10/2026, `workspace/chan-doan/v7-chon-content-2026-10-12.md` P2) ═══

Trước: chỉ nhận dòng "Làm ngay"/"Nên làm" (≥ 60 điểm) — 6/7 kênh hầu như ngày nào cũng 0 dòng (trần thực tế ~50 khi
kênh chưa có video thắng), nên `v7:0.5, vph:0.5` chạy VPH 100%. Trong khi THỨ TỰ của V7 dự báo đúng: nguồn top-10 V7
hôm trước 5/7 thành hit, hạng > 10 0/14. Giờ: `cong_thuc_v7.chon_theo_hang` — top `chon.top_n` (10) dòng của bảng ngày
(sau cổng + lọc đã làm/trùng), giữ thứ tự điểm, qua sàn chất lượng tối thiểu (`chon.diem_san`, `chon.vuot_san`). Cấu
hình cũ không được nâng (`cong_thuc_v7._cho_nang_cap`) giữ luật cũ (`chon.theo_hang: false`).

Kênh CHƯA có video thắng (`co_v7` sai) vẫn dùng được V7 khi chọn theo hạng: cột Nổ + Khuôn (hai cột có tín hiệu trên
số của ta) không cần video thắng. `ap_dung` chỉ trả 0 khi cấu hình vẫn ở luật cũ.

Hỏng hay rỗng thì trả `[]` và KHÔNG lùi (`LUI_KHI_RONG = ""`): trộn với VPH là việc của bộ điều phối.
Kết quả chấm đầy đủ gắn vào `nc._kq_v7` (để bộ điều phối tra nguồn bộ não đề cử ngoài top, xem `ep_chon`).
"""

from __future__ import annotations

from typing import Any, Dict, List

TEN = "v7"
MO_TA = "Công thức V7 — top hạng của bảng V7 (nguồn nổ thật, khuôn, cụm đang thắng, bảng đề xuất)"
LUI_KHI_RONG = ""


def _theo_hang(nc: Any) -> bool:
    try:
        from .. import cong_thuc_v7 as v7  # noqa: PLC0415

        ch = getattr(nc, "_ch_v7", None) or {}
        return bool(dict(v7.CAU_HINH_MAC_DINH["chon"], **(ch.get("chon") or {})).get("theo_hang"))
    except Exception:  # noqa: BLE001
        return False


def ap_dung(nc: Any) -> float:
    if not nc.co_v7:
        # 12/10/2026: kênh chưa có video thắng vẫn có bảng V7 có tín hiệu (Nổ + Khuôn) khi chọn theo hạng.
        return 0.8 if _theo_hang(nc) else 0.0
    return {"dang_len": 1.0, "kiem_tien": 0.8}.get(nc.giai_doan, 1.0)


def _dong(d: Any, v7: Any, so: Any, hang: int = 0) -> Dict[str, Any]:
    """Dòng chuẩn của một `DongV7`. `hang` > 0 (chọn theo hạng) thêm `vuot`/`dai_giay`/`hang_v7`; = 0 thì đúng dòng
    cũ từng khoá (golden `tests/test_chien_luoc_golden.py` canh kênh giữ luật cũ)."""
    ma = str(getattr(d, "ma", "") or so.ma_video(str(getattr(d, "link", "") or "")))
    ra = {"nguon": "v7", "ma": ma, "link": str(getattr(d, "link", "") or ""),
            "tieu_de": str(getattr(d, "tieu_de", "") or ""),
            "kenh": str(getattr(d, "kenh", "") or ""),
            "diem": getattr(d, "diem", 0), "loai": str(getattr(d, "loai", "") or ""),
            # Điểm cụm CỦA CHÍNH KÊNH MÌNH — để `cong_diem_anh_em` biết ứng viên nào TỰ THẮNG.
            "diem_cum": float(getattr(d, "diem_cum", 0) or 0),
            # Kênh anh em đã cho điểm cụm THỪA HƯỞNG — `cong_diem_anh_em` bỏ qua dòng này.
            "thua_huong": str(getattr(d, "thua_huong", "") or ""),
            "cum": list(getattr(d, "cum", None) or []),
            "view": float(getattr(d, "view", 0) or 0),
            "ly_do": list(getattr(d, "ly_do", None) or [])}
    if hang:
        ra.update(vuot=getattr(d, "vuot", None), dai_giay=getattr(d, "dai_giay", None), hang_v7=hang)
    return ra


def cham(nc: Any) -> List[Dict[str, Any]]:
    from .. import cong_thuc_v7 as v7  # noqa: PLC0415
    from .. import doi_thu_kenh as so  # noqa: PLC0415
    from .. import tu_chay  # noqa: PLC0415 — nhập muộn: tu_chay nhập gói này lúc nạp

    try:
        kq = (nc.cham_v7 or v7.cham)(nc.goc, nc.ma_kenh)
    except Exception as loi:  # noqa: BLE001
        nc.ghi("  Công thức V7 hỏng ({0}) — không có nguồn hôm nay (kênh đã có cấu hình V7, "
               "không rơi về bảng Một nút vì bảng đó không mang phán đoán của V7).".format(
                   str(loi)[:120]))
        return []
    try:
        nc._kq_v7 = kq  # noqa: SLF001 — bộ điều phối tra nguồn đề cử của bộ não (ep_chon)
    except Exception:  # noqa: BLE001
        pass
    ch = getattr(kq, "cau_hinh", None) or getattr(nc, "_ch_v7", None) or {}
    tat_ca = [d for d in (getattr(kq, "ung_vien", None) or []) if not getattr(d, "bi_loai", "")]
    theo_hang = bool(dict(v7.CAU_HINH_MAC_DINH["chon"], **(ch.get("chon") or {})).get("theo_hang"))
    if theo_hang:
        ra = nc.loc([_dong(d, v7, so, i + 1) for i, d in enumerate(tat_ca)])
        for i, d in enumerate(ra):
            d["hang_v7_sau_loc"] = i + 1
        nhan, bo = v7.chon_theo_hang(ra, ch)
        if not nhan:
            nc.ghi("  Công thức V7 (theo hạng): không dòng nào qua sàn chất lượng ({0} dòng sau cổng{1}).".format(
                len(ra), "; dòng đầu: " + bo[0][1] if bo else ""))
        else:
            nc.ghi("  Công thức V7 (theo hạng): {0} ứng viên đủ điều kiện — top {1} sau cổng, đầu bảng “{2}” "
                   "({3} điểm, {4}).".format(len(nhan), dict(v7.CAU_HINH_MAC_DINH["chon"], **(ch.get("chon") or {}))
                                             .get("top_n"), str(nhan[0].get("tieu_de") or "")[:50],
                                             nhan[0].get("diem"), nhan[0].get("loai")))
        for d in nhan:
            d["ly_do"] = list(d.get("ly_do") or []) + ["V7 hạng {0} của ngày (chọn theo hạng)".format(
                d.get("hang_v7_sau_loc"))]
        ra = nhan
    else:
        ra = nc.loc([_dong(d, v7, so) for d in tat_ca if str(getattr(d, "loai", "")) in (v7.LAM_NGAY, v7.NEN_LAM)])
        if not ra:
            nc.ghi("  Công thức V7: không có ứng viên nào đạt “{0}” trở lên — không có nguồn hôm nay "
                   "(kênh đã có cấu hình V7, không rơi về bảng Một nút).".format(v7.NEN_LAM))
    return tu_chay._cong_diem_anh_em_an_toan(nc.goc, nc.ma_kenh, ra, True, nc.ghi)
