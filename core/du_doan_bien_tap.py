"""SỔ DỰ ĐOÁN của biên tập viên AI + chấm BRIER (12/10/2026).

`workspace/chan-doan/v7-chon-content-2026-10-12.md` mục 0.5 / `nao-vong-hoc-2026-10-12.md` #5: biên tập AI đoán
"thắng" 49 lần, đúng 5 (10%) — mà không ai chấm lại, nên nó không bao giờ biết mình sai. Từ bản này biên tập CHỈ PHỦ
QUYẾT (`tu_chay._ap_cham_bien_tap`); dự đoán của nó vẫn được giữ, có XÁC SUẤT, để đo hiệu chuẩn trước khi ai đó tính
tới chuyện trao lại quyền xếp hạng:

    ghi(goc, kenh, ung_vien, ket)   — mỗi dòng đã chấm: p = điểm biên tập / 100 (đề bài: "điểm = xác suất thắng × 100"),
                                      hạng TỐT/TẠM/TỆ, kết cục đoán, hạng công thức. Chỉ ghi khi dự đoán ĐỔI (bộ nhớ
                                      phán quyết 18h trả lại cùng số mỗi lượt) — tệp không phình.
    cham(goc, kenh)                 — nối với video ĐÃ LÀM từ đúng nguồn ấy (sổ lượt → hồ sơ video → nhãn thước chung
                                      `core.thuoc_thang`, y = 1 khi THẮNG): Brier, Brier nền (tỉ lệ thắng của chính
                                      mẫu), kỹ năng = 1 − Brier/Brier nền (> 0 mới là có tài), độ chính xác của "thắng".

Giới hạn ghi rõ trong kết quả: chỉ nguồn ĐÃ sản xuất mới có kết cục (thiên lệch chọn mẫu), n nhỏ.
Tệp: `CHANNEL/<k>/nghien-cuu/bien-tap/du-doan-xac-suat.jsonl` (+ `.chi-muc.json`), `brier.json`.
Chỉ đọc/ghi đĩa, không mạng, không tiền. Lỗi không bao giờ ném ra nơi gọi chọn nguồn (nơi gọi bọc try).

    python -m core.du_doan_bien_tap [--kenh K]        # in Brier từng kênh (chỉ đọc)
"""

from __future__ import annotations

import datetime as _dt
import io
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

TEP = "du-doan-xac-suat.jsonl"
TEP_CHI_MUC = "du-doan-xac-suat.chi-muc.json"
TEP_BRIER = "brier.json"
NGAY_GIU_CHI_MUC = 30


def _thu_muc(goc: str, kenh: str) -> str:
    from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415

    return os.path.join(thu_muc_nghien_cuu(goc, kenh), "bien-tap")


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ma(x: Any) -> str:
    from .doi_thu_kenh import ma_video  # noqa: PLC0415

    s = str(x or "")
    return str(ma_video(s) or s)


def ghi(goc: str, kenh: str, ung_vien: Sequence[Dict[str, Any]], ket: Dict[str, Any],
        bay_gio: Optional[_dt.datetime] = None) -> int:
    """Ghi dự đoán của các dòng `ung_vien` đã được chấm trong `ket` (hợp đồng `bien_tap_content.chon_cua_so`:
    `hang`/`diem_bt`/`du_doan`, khoá = link). Trả số dòng mới ghi."""
    luc = (bay_gio or _dt.datetime.now()).replace(microsecond=0)
    hang = ket.get("hang") or {}
    diem = ket.get("diem_bt") or {}
    dd = ket.get("du_doan") or {}
    tm = _thu_muc(goc, kenh)
    duong_cm = os.path.join(tm, TEP_CHI_MUC)
    cm = _doc_json(duong_cm)
    cm = cm if isinstance(cm, dict) else {}
    moi: List[Dict[str, Any]] = []
    for i, d in enumerate(ung_vien):
        link = str(d.get("link") or "")
        h = hang.get(link)
        if not h:
            continue
        try:
            p = None if diem.get(link) is None else max(0.0, min(1.0, float(diem[link]) / 100.0))
        except (TypeError, ValueError):
            p = None
        ma = str(d.get("ma") or _ma(link))
        ket_cuc = str((dd.get(link) or {}).get("ket_cuc") or "")
        dau = [h, p, ket_cuc]
        if (cm.get(ma) or {}).get("dau") == dau:
            continue
        cm[ma] = {"dau": dau, "luc": luc.isoformat()}
        moi.append({"luc": luc.isoformat(), "kenh": kenh, "ma": ma, "link": link,
                    "tieu_de": str(d.get("tieu_de") or "")[:80], "hang": h, "p": p, "ket_cuc": ket_cuc,
                    "hang_cong_thuc": d.get("hang_cong_thuc") or (i + 1),
                    "cong_thuc": str(d.get("cong_thuc") or d.get("nguon") or "")})
    if not moi:
        return 0
    os.makedirs(tm, exist_ok=True)
    with io.open(os.path.join(tm, TEP), "a", encoding="utf-8", newline="\n") as tep:
        for r in moi:
            tep.write(json.dumps(r, ensure_ascii=False) + "\n")
    han = (luc - _dt.timedelta(days=NGAY_GIU_CHI_MUC)).isoformat()
    cm = {k: v for k, v in cm.items() if str((v or {}).get("luc") or "") >= han}
    tam = duong_cm + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(cm, tep, ensure_ascii=False)
    os.replace(tam, duong_cm)
    return len(moi)


def doc(goc: str, kenh: str) -> List[Dict[str, Any]]:
    ra: List[Dict[str, Any]] = []
    try:
        with io.open(os.path.join(_thu_muc(goc, kenh), TEP), encoding="utf-8") as tep:
            for dong in tep:
                try:
                    r = json.loads(dong)
                except ValueError:
                    continue
                if isinstance(r, dict) and r.get("ma"):
                    ra.append(r)
    except OSError:
        pass
    return ra


def brier(cap: Sequence[Sequence[float]]) -> Dict[str, Any]:
    """`[(p, y)]` → `{n, brier, brier_nen, ky_nang, ti_le_thang}` — hàm thuần. `brier_nen` = Brier của dự đoán hằng
    bằng tỉ lệ thắng của chính mẫu; `ky_nang` = 1 − brier/brier_nen (None khi mẫu toàn thắng hoặc toàn trượt)."""
    cap = [(float(p), float(y)) for p, y in cap]
    n = len(cap)
    if not n:
        return {"n": 0, "brier": None, "brier_nen": None, "ky_nang": None, "ti_le_thang": None}
    b = sum((p - y) ** 2 for p, y in cap) / n
    nen = sum(y for _p, y in cap) / n
    bn = sum((nen - y) ** 2 for _p, y in cap) / n
    return {"n": n, "brier": round(b, 4), "brier_nen": round(bn, 4),
            "ky_nang": round(1.0 - b / bn, 3) if bn > 0 else None, "ti_le_thang": round(nen, 3)}


def cham(goc: str, kenh: str) -> Dict[str, Any]:
    """Chấm dự đoán đã ghi với kết cục thật (xem đầu tệp). Không ném lỗi: hỏng → kết quả rỗng + `loi`."""
    ra: Dict[str, Any] = {"kenh": kenh, "n": 0, "chi_tiet": [],
                          "gioi_han": "chỉ nguồn đã sản xuất mới có kết cục (thiên lệch chọn mẫu); n nhỏ"}
    try:
        from . import ho_so_video  # noqa: PLC0415
        from .chien_luoc import ket_qua  # noqa: PLC0415

        du_doan = doc(goc, kenh)
        if not du_doan:
            return dict(ra, **brier([]))
        theo_ma: Dict[str, List[Dict[str, Any]]] = {}
        for r in du_doan:
            theo_ma.setdefault(str(r["ma"]), []).append(r)
        so_luot = ho_so_video.nguon_cua_goi(goc, kenh)
        ho_so = ket_qua.ho_so_theo_goi(goc, kenh)
        vm, _ng = ket_qua.video_kenh(goc, kenh)
        cap: List[List[float]] = []
        doan_thang = dung_thang = 0
        for ma_goi, g in sorted(so_luot.items()):
            ma = str(g.get("ma") or _ma(g.get("link")))
            if g.get("bo") or ma not in theo_ma:
                continue
            ngay = str(g.get("ngay") or "9999")
            truoc = [r for r in theo_ma[ma] if str(r.get("luc") or "")[:10] <= ngay and r.get("p") is not None]
            if not truoc:
                continue
            r = truoc[-1]
            vid = str((ho_so.get(ma_goi) or {}).get("video_id") or "")
            nhan = ket_qua.ket_luan_3(vm.get(vid) if vid else None, ho_so.get(ma_goi) or {}, vm)
            if not nhan:
                continue
            y = 1.0 if nhan == "thang" else 0.0
            cap.append([float(r["p"]), y])
            if str(r.get("ket_cuc") or "").lower() in ("thắng", "thang"):
                doan_thang += 1
                dung_thang += int(y)
            ra["chi_tiet"].append({"ma_goi": ma_goi, "nguon": ma, "p": r["p"], "hang": r.get("hang"),
                                   "ket_cuc_doan": r.get("ket_cuc"), "ket_that": nhan})
        ra.update(brier(cap))
        ra["doan_thang"], ra["dung_thang"] = doan_thang, dung_thang
    except Exception as loi:  # noqa: BLE001
        ra["loi"] = "{0}: {1}".format(type(loi).__name__, str(loi)[:160])
    return ra


def ghi_tom_tat(goc: str, kenh: str) -> str:
    """Ghi `bien-tap/brier.json` (gọi từ vòng học hằng ngày). Trả đường tệp."""
    kq = cham(goc, kenh)
    kq["cap_nhat_luc"] = _dt.datetime.now().replace(microsecond=0).isoformat()
    tm = _thu_muc(goc, kenh)
    os.makedirs(tm, exist_ok=True)
    duong = os.path.join(tm, TEP_BRIER)
    tam = duong + ".tmp"
    with io.open(tam, "w", encoding="utf-8") as tep:
        json.dump(kq, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)
    return duong


def main(argv: Optional[List[str]] = None) -> int:
    import argparse  # noqa: PLC0415

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    p = argparse.ArgumentParser(prog="python -m core.du_doan_bien_tap")
    p.add_argument("--goc", default=os.environ.get("MYTOOL_GOC") or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    p.add_argument("--kenh", action="append", default=[])
    a = p.parse_args(argv)
    ds = a.kenh
    if not ds:
        from .kenh import liet_ke_kenh  # noqa: PLC0415

        ds = list(liet_ke_kenh(a.goc))
    for k in ds:
        kq = cham(a.goc, k)
        print("{0}: n={1} · Brier {2} (nền {3}, kỹ năng {4}) · đoán THẮNG {5} lần, đúng {6}{7}".format(
            k, kq.get("n"), kq.get("brier"), kq.get("brier_nen"), kq.get("ky_nang"), kq.get("doan_thang", 0),
            kq.get("dung_thang", 0), " · LỖI " + kq["loi"] if kq.get("loi") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
