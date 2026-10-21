"""MÁY BÌA A/B (DOM/CDP, G4 «tự chơi», 21/10/2026) — bước «bìa A/B» trong PHIÊN NGÀY của kênh.

Kế hoạch + sổ + học (video nào, bìa nào, kết quả, não «bia», họ kiểu chữ, giám khảo): `core/bia_ab.py`. Tệp này chỉ
thao tác Chrome kênh ĐANG MỞ của phiên (chủ: «không mở Chrome thêm — tích hợp vào cùng lúc, các kênh làm lần lượt»):

    ĐẶT  trang sửa video → «Thử nghiệm A/B» → chip «Chỉ hình thu nhỏ» → ô 1 = bìa đang chạy (Studio điền sẵn) → ô 2/3 =
         bìa nhì/ba của lô ĐÃ QUA cổng đọc được + cổng chữ (tấm chưa dấu: đọc mù 2 lượt, dấu trên bản sao) →
         «Thiết lập thử nghiệm» → Lưu nếu trang còn đổi → ĐỌC LẠI gói `videoCreatorExperiment` (STARTED, số nhánh).
         Dùng nguyên `studio_may_dom.test_mot_video` (cùng đường đã chạy thật 16–21/10).
    ĐỌC  thử nghiệm của máy đang chạy ≥ 2 ngày: trang sửa → gói Studio → `bia_ab.ghi_ket_qua` (CHỈ ĐỌC Studio).
    THĂM video HẸN LỊCH (một lần / kênh): trang sửa → trạng thái nút «Thử nghiệm A/B» (CHỈ ĐỌC) → `meta.len_lich`.

Cách chạy:
    python vm/bia_ab_dom.py --phien --kenh K --trong-phien   # agent gọi giữa phiên (Chrome kênh mở, khoá máy agent giữ)
    python vm/bia_ab_dom.py --phien --kenh K [--thu]         # tay: tự giữ khoá máy; --thu = chỉ đọc, không đặt / ghi

Luật an toàn: không việc → thoát ngay, KHÔNG nối Chrome; khung cấm + 60 phút trước giờ công khai (`bia_ab.trong_gio_cam`);
van IPv4 mở → không nối; đúng kênh (UC ghim `logs/kenh-uc.json` qua `MayDangDom.lay_uc`, giao diện `vi` tạm, cuối bước
trả); chỉ đóng tab của mình; video đang THẮNG không bao giờ bị đặt thử; không xoá gì trên YouTube, không đổi tiêu đề /
mô tả / chế độ hiển thị; trang sửa có thay đổi lạ → huỷ, không lưu. Trần thời gian bước `HAN_PHUT`.

Mã thoát: 0 xong (kể cả không có việc) · 1 có việc hỏng · 3 đường DOM không dùng được · 4 bị chặn an toàn / khoá bận.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import socket
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

GOC = os.path.dirname(os.path.abspath(__file__))                 # vm/
GOC_TOOL = os.path.dirname(GOC)
for _d in (GOC, GOC_TOOL):
    if _d not in sys.path:
        sys.path.append(_d)
import studio_may_dom as smd  # noqa: E402 — đặt / đọc thử nghiệm: dùng CHUNG đường D13

tl = smd.tl
MA_XONG, MA_HONG, MA_LUI, MA_CHAN = 0, 1, 3, 4
#: Một máy bìa A/B mỗi lúc (ngoài dải trạm 8765–8775, kéo chéo 8781, cộng sự 8782).
CONG_KHOA = 8783
#: Trần thời gian của bước trong phiên (agent cho tối đa `phien_han_bia_ab_giay`, mặc định 20 phút).
HAN_PHUT = 16.0
DUONG_BAO_CAO = os.path.join(GOC, "logs", "bia-ab-cuoi.json")


def _ba():
    from core import bia_ab  # noqa: PLC0415
    return bia_ab


def _sm():
    from core import studio_may  # noqa: PLC0415
    return studio_may


# ── chuẩn bị bìa (KHÔNG Chrome) ─────────────────────────────────────────────

def chuan_bi_video(goc: str, kenh: str, v: Dict[str, Any], ghi, dau_lai=None, tai=None, cham=None) -> Dict[str, Any]:
    """Bìa A (đang chạy) + 2 ứng viên tốt nhất ĐÃ qua cổng (đọc được + dấu cổng chữ; `dau_lai(mã, tệp)` đóng dấu bản sao
    tấm chưa dấu) → {kh (cho `test_mot_video`, chế độ «Chỉ hình thu nhỏ»), bien_the [A, B?, C?] theo thứ tự ô, bo}."""
    ba, sm = _ba(), _sm()
    vid, ma = v["video_id"], v["ma_goi"]
    bt = v.get("bien_the") or ba.bien_the_goi(goc, kenh, ma)
    hs = bt[0]["tep"] if bt else ""
    a = smd.tai_bia_a(goc, kenh, vid, ghi, tai) if v.get("cong_khai", True) else ""
    if a and hs and os.path.isfile(hs):
        try:
            from core import cong_chu  # noqa: PLC0415
            cong_chu.chuyen_dau(hs, a)
        except Exception:  # noqa: BLE001
            pass
    dl = (lambda p: dau_lai(ma, p)) if dau_lai is not None else None
    chon, bo = sm.ung_vien_bia(goc, kenh, ma, [x for x in (a, hs) if x], cham=cham, dau_lai=dl)
    ok: List[Dict[str, Any]] = []
    for u in chon:
        try:
            ok.append(dict(u, tai_len=sm.tep_tai_len(u["tep"], os.path.join(smd.thu_muc_so(), kenh, "tai-len"))))
        except Exception as e:  # noqa: BLE001
            bo.append(dict(u, ly_do="không dựng được bản tải lên: {0}".format(str(e)[:80])))
    a0 = dict(bt[0]) if bt else {"nhan": "A", "tep": hs}
    bien = [dict(a0, nhan="A", sha1=ba.sha1_tep(hs) if hs else "", nguon="dang_chay")]
    for i, u in enumerate(ok[:ba.TOI_DA_BIEN_THE - 1]):
        bien.append(dict(ba.meta_ung_vien(bt, u), nhan=ba.NHAN[i + 1], tep=u["tai_len"], sha1=ba.sha1_tep(u["tai_len"]),
                         nguon=u.get("nguon") or ""))
    ghi("   {0} ({1}): bìa A {2} · thử {3} · bỏ {4}".format(
        vid, ma, "có" if (a or hs) else "KHÔNG", ["{0}:{1} {2} gk={3}".format(b["nhan"], os.path.basename(b["tep"]),
                                                                          b.get("ho") or "?", b.get("diem_gk"))
                                                for b in bien[1:]],
        ["{0}: {1}".format(os.path.basename(str(u.get("tep"))), str(u.get("ly_do"))[:80]) for u in bo][:4]))
    return {"kh": {"ma_goi": ma, "anh_a": a, "chon": ok[:ba.TOI_DA_BIEN_THE - 1], "tieu_de": [], "doi_thu": [],
                   "bo": [{k: u.get(k) for k in ("tep", "nguon", "ly_do")} for u in bo]},
            "bien_the": bien, "bo": bo}


# ── phiên Chrome (Chrome kênh của PHIÊN — không mở thêm) ────────────────────

def phien_chrome(kenh: str, tu_giu: bool, ghi, lam: Callable[..., Any]) -> Tuple[int, Any]:
    """Nối Chrome kênh (phiên đang mở; chạy tay mà chưa mở thì `ket_noi_kenh` mở và cuối bước đóng), đúng UC ghim,
    giao diện vi tạm → `lam(S, agent)` → đóng tab của mình, trả ngôn ngữ. `tu_giu`: tự giữ khoá máy (chạy tay)."""
    import agent  # noqa: PLC0415
    import cdp as cdp_mod  # noqa: PLC0415
    import cdp_studio  # noqa: PLC0415
    import may_dang_dom as mdd  # noqa: PLC0415
    if tu_giu and not agent.giu_khoa_may_chung(viec="bia_ab", kenh=kenh, uu_tien=smd.UU_TIEN_KHOA):
        ghi("hoãn: khoá máy (.khoa-may) bận — để phiên sau")
        return MA_CHAN, "khoá máy bận"
    cdp = md = S = None
    try:
        if agent.van_ipv4_mo():
            ghi("DỪNG: van IPv4 đang mở — không nối Chrome kênh")
            return MA_CHAN, "van IPv4 mở"
        bo = smd.bo_cho_luu(cdp_studio.doc_bo_chon())
        thieu = [k for k in ("ab_nut", "ab_chip_bia", "ab_thiet_lap", "tieu_de", "sua_luu")
                 if k not in (bo.get("phan_tu") or {})]
        if thieu:
            ghi("studio-selectors.json thiếu khoá: " + ", ".join(thieu))
            return MA_LUI, "thiếu bộ chọn"
        try:
            cdp = cdp_mod.ket_noi_kenh(agent.doc_cau_hinh(), kenh, nhat_ky=ghi)
        except cdp_mod.CdpKhongDung as loi:
            ghi("hoãn: không nối được Chrome kênh: {0} (mã {1})".format(loi.ly_do, loi.ma))
            return MA_CHAN, "không nối được Chrome"
        thu_muc_anh = os.path.join(smd.thu_muc_so(), kenh)
        md = mdd.MayDangDom(kenh, bo, lambda: cdp_studio.TrangStudio.mo_tab_moi(cdp, bo, nhat_ky=ghi,
                                                                               thu_muc_dom=thu_muc_anh),
                            mdd.SoVideoId(), bao=None, thu_muc_done="", nhat_ky=ghi)
        S = tl.Studio(md.tab_b(), ghi, thu_muc_anh)
        try:
            S.uc = md.lay_uc()                       # ĐÚNG kênh (UC ghim) — sai là DỪNG, không thao tác gì
        except mdd.DungKenh as e:
            ghi("DỪNG: {0}".format(e))
            return MA_CHAN, "sai kênh"
        if smd.dang_xuat_url(S.url()):
            ghi("DỪNG: Chrome kênh {0} bị đăng xuất YouTube (việc của người)".format(kenh))
            return MA_HONG, "dang-xuat"
        ghi("── BÌA A/B {0} — Chrome cổng {1}{2} ──".format(kenh, cdp.cong, " (máy này mở)" if cdp.tu_mo else " (phiên)"))
        return MA_XONG, lam(S, agent)
    except smd.DangXuat as e:
        ghi("DỪNG — {0} (đăng nhập là việc của người)".format(e))
        return MA_HONG, "dang-xuat"
    except tl.CanNguoi as c:
        ghi("DỪNG — cần người: {0}".format(c))
        return MA_HONG, str(c)[:200]
    except tl.Hoan as h:
        ghi("hoãn: {0}".format(h))
        return MA_CHAN, str(h)[:200]
    except Exception as e:  # noqa: BLE001 — không chết im lặng
        ghi("BƯỚC BÌA A/B LỖI: {0}".format(str(e)[:300]))
        if S:
            S.chup("bia-ab-loi")
        return MA_HONG, str(e)[:300]
    finally:
        try:
            if md is not None:
                md.dong_het()
            if cdp is not None:
                try:
                    import ngon_ngu_tam  # noqa: PLC0415
                    ngon_ngu_tam.tra(cdp, kenh, ghi)
                except Exception as e:  # noqa: BLE001
                    ghi("trả ngôn ngữ giao diện lỗi: {0}".format(str(e)[:120]))
                if cdp.tu_mo and tu_giu:
                    ghi("đóng Chrome kênh {0} (máy này đã mở): {1}".format(
                        kenh, "đã đóng" if cdp_mod.dong_trinh_duyet(cdp) else "CỔNG CHƯA ĐÓNG"))
                else:
                    cdp.dong()
        finally:
            if tu_giu:
                agent.nha_khoa_may_chung()


#: Lý do bỏ ứng viên là TRƯỢT THẬT (không thử lại): trùng bìa, trượt cổng đọc được / bố cục, chữ trên ảnh sai, chữ
#: chưa qua soát. Mọi lý do khác (AI lỗi, mạng, đĩa) = tạm.
_TRUOT_THAT = ("trùng bìa a", "trùng một ứng viên", "trượt cổng đọc được", "bố cục hỏng", "≠ chữ đã soát",
               "chưa qua soát", "đủ 2 ứng viên")


def tam_thoi(ly_do: Any) -> bool:
    """Lý do bỏ ứng viên là lỗi TẠM (cổng chưa kiểm được…), không phải tấm trượt thật."""
    s = str(ly_do or "").lower()
    return bool(s) and not any(x in s for x in _TRUOT_THAT)


def _don_trang(S, ghi) -> None:
    try:
        smd.dong_hop_khong_luu(S, ghi)
        if not smd.luu_dang_tat(S):
            smd.huy_thay_doi(S, ghi)
    except Exception:  # noqa: BLE001
        pass


def doc_nut(S, vid: str) -> Dict[str, Any]:
    """CHỈ ĐỌC: trang sửa của `vid` → nút «Thử nghiệm A/B» {co, tat, chu, thu_nghiem}."""
    goi, kb = smd.doc_trang_sua(S, vid)
    pt = smd._tim_khoa(S, "ab_nut")                                   # noqa: SLF001
    nut = kb.get("nut") or []
    return {"co": bool(pt) or bool(nut), "tat": bool(pt.get("tat")) if pt else (all(n.get("tat") for n in nut) if nut
                                                                                 else None),
            "chu": " · ".join(str(n.get("chu") or "") for n in nut)[:200] + (
                " | " + str(kb.get("chu") or "")[:160] if kb.get("chu") else ""),
            "thu_nghiem": smd.phan_tich_thu_nghiem((goi or {}).get("videoCreatorExperiment")) if goi is not None else None}


# ── bước ────────────────────────────────────────────────────────────────────

def chay_buoc(kenh: str, *, thu: bool = False, tu_giu: bool = True, bay: Optional[_dt.datetime] = None, ghi=None,
              phien=None, tai=None, cham=None, dau_lai: Any = "mac_dinh", dong_ho=time.monotonic,
              khoa: Optional[Callable[[], bool]] = None) -> Tuple[int, Dict[str, Any]]:
    """MỘT bước «bìa A/B» cho kênh. `phien(kenh, tu_giu, ghi, lam)` thay `phien_chrome`, `khoa()` thay khoá một-mình
    (kiểm). Không việc → không nối Chrome (vẫn ghi sổ «bỏ» + đóng quá hạn). Trả (mã, báo cáo)."""
    ba = _ba()
    goc = GOC_TOOL
    bay = bay or _dt.datetime.now()
    ghi = ghi or smd._nhat_ky(kenh)                                   # noqa: SLF001
    bc: Dict[str, Any] = {"kenh": kenh, "luc": bay.replace(microsecond=0).isoformat(), "thu": thu, "dat": {}, "doc": {},
                          "len_lich": {}, "bo": [], "hoan": []}
    ok, ly, kh = ba.can_dom(goc, kenh, bay)
    bc.update(ly_do=ly, bo=kh.get("bo") or [], hoan=kh.get("hoan") or [])
    if not thu:
        if ba.bat(ba._kenh_yaml(goc, kenh)):                          # noqa: SLF001
            ba.danh_dau_phien(goc, kenh, bay)
        ba.dong_qua_han(goc, kenh, bay)
        ba.ghi_bo(goc, kenh, kh.get("bo") or [], bay)
    for b in (kh.get("bo") or []) + (kh.get("hoan") or []):
        ghi("   {0} ({1}): không thử bìa — {2}".format(b.get("video_id"), b.get("ma_goi"), str(b.get("ly_do"))[:160]))
    if not ok:
        ghi("bìa A/B {0}: {1} — bỏ qua bước (không nối Chrome)".format(kenh, ly))
        return MA_XONG, bc
    if dau_lai == "mac_dinh":
        dau_lai = None if thu else smd._goi_dau_lai(goc, kenh, ghi)     # noqa: SLF001 — gọi AI LƯỜI (chỉ khi cần)
    viec: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for v in kh["dat"]:
        cb = chuan_bi_video(goc, kenh, v, ghi, dau_lai, tai, cham)
        if not cb["kh"]["chon"]:
            ly_bo = "; ".join("{0}: {1}".format(os.path.basename(str(u.get("tep"))), str(u.get("ly_do"))[:60])
                              for u in cb["bo"][:3]) or "không có bìa nhì/ba"
            # cổng chưa KIỂM ĐƯỢC (AI lỗi / không nối được) = tạm → `loi` (phiên sau thử lại); trượt thật → `bo`
            ket = "loi" if any(tam_thoi(u.get("ly_do")) for u in cb["bo"]) else "khong_ung_vien"
            bc["dat"][v["video_id"]] = {"ket": ket, "ly_do": ly_bo}
            if not thu:
                ba.ghi_dat(goc, kenh, v["video_id"], v["ma_goi"], cb["bien_the"][:1], {"ket": ket, "ly_do": ly_bo}, bay)
            continue
        viec.append((v, cb))
    if not viec and not kh["doc"] and not kh["tham_do_len_lich"]:
        return MA_XONG, bc
    han = dong_ho() + HAN_PHUT * 60.0

    def lam(S, agent):
        for v, cb in viec:
            vid = v["video_id"]
            if dong_ho() > han:
                ghi("   hết giờ bước — {0} để phiên sau".format(vid))
                break
            thang = ba._dang_thang(goc, kenh, v["ma_goi"])           # noqa: SLF001 — xét lại sát lúc đặt
            if thang:
                bc["dat"][vid] = {"ket": "bo", "ly_do": "video đang THẮNG: " + thang}
                if not thu:
                    ba.ghi_bo(goc, kenh, [dict(v, trang_thai=ba.TT_BO, ly_do="video đang THẮNG: " + thang)], bay)
                continue
            try:
                kv = smd.test_mot_video(S, vid, cb["kh"], ghi, thu=thu)
            except (smd.DangXuat, tl.Hoan, tl.CanNguoi):
                raise
            except Exception as e:  # noqa: BLE001 — một video hỏng: video kế vẫn làm
                kv = {"ket": "loi", "ly_do": str(e)[:200]}
                S.chup("bia-ab-loi-" + vid)
            if kv.get("ket") != "da_dat":
                _don_trang(S, ghi)                                  # không để thay đổi dở trên trang sửa
            n = int(kv.get("so_bia") or 0) or (1 + len(cb["kh"]["chon"]))
            bc["dat"][vid] = {k: kv.get(k) for k in ("ket", "ly_do", "che_do", "so_bien_the", "so_bia", "trang_thai")}
            ghi("   {0}: bìa A/B → {1}{2}".format(vid, kv.get("ket"), " — " + str(kv.get("ly_do"))[:160]
                                                 if kv.get("ly_do") else ""))
            if not thu:
                ba.ghi_dat(goc, kenh, vid, v["ma_goi"], cb["bien_the"][:n], kv, bay)
            if kv.get("ket") == "khong_quyen":
                break
        for vid in kh["doc"]:
            if dong_ho() > han:
                break
            goi = None
            try:
                goi, _kb = smd.doc_trang_sua(S, vid)
            except (smd.DangXuat, tl.Hoan, tl.CanNguoi):
                raise
            except Exception as e:  # noqa: BLE001
                ghi("   {0}: đọc thử nghiệm bìa hỏng: {1}".format(vid, str(e)[:160]))
            exp = (goi or {}).get("videoCreatorExperiment") if goi is not None else None
            kt = ba.doc_thu_nghiem(exp) if goi is not None else {}
            kq = None if thu else ba.ghi_ket_qua(goc, kenh, vid, exp, bay, doc_duoc=goi is not None)
            bc["doc"][vid] = {"tho": kt.get("trang_thai_tho"), "ti_phan": kt.get("ti_phan"),
                              "ket": (kq or {}).get("ket_luan") or ("loi" if goi is None else "dang_chay"),
                              "thang": (kq or {}).get("thang"), "chon": (kq or {}).get("chon")}
            ghi("   {0}: thử nghiệm bìa — {1}".format(vid, bc["doc"][vid]))
        vid = kh["tham_do_len_lich"]
        if vid and dong_ho() <= han:
            try:
                nut = doc_nut(S, vid)
                S.st.ghi_bang_chung("bia-ab-len-lich-" + vid)
            except (smd.DangXuat, tl.Hoan, tl.CanNguoi):
                raise
            except Exception as e:  # noqa: BLE001
                nut = {"loi": str(e)[:200]}
            bc["len_lich"] = dict(nut, video_id=vid, thu_nghiem=None)
            tt = "thu" if thu else ba.ghi_tham_do_len_lich(goc, kenh, vid, nut, bay)
            ghi("   {0} (HẸN LỊCH): nút Thử nghiệm A/B {1} → {2}".format(vid, {k: nut.get(k) for k in ("co", "tat", "loi")},
                                                                       tt))
        return bc

    if not (khoa or _khoa_mot_minh)():
        ghi("đã có một máy bìa A/B khác đang chạy (cổng {0}) — thoát".format(CONG_KHOA))
        return MA_CHAN, dict(bc, loi_phien="máy bìa A/B khác đang chạy")
    ma, r = (phien or phien_chrome)(kenh, tu_giu, ghi, lam)
    if ma != MA_XONG:
        bc["loi_phien"] = r
        return ma, bc
    hong = any(str((x or {}).get("ket")) == "loi" for x in bc["dat"].values())
    return (MA_HONG if hong else MA_XONG), bc


# ── CLI ─────────────────────────────────────────────────────────────────────

_O_KHOA = None


def _khoa_mot_minh(cong: int = CONG_KHOA) -> bool:
    global _O_KHOA
    try:
        _O_KHOA = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _O_KHOA.bind(("127.0.0.1", cong))
        _O_KHOA.listen(1)
        return True
    except OSError:
        return False


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(prog="bia_ab_dom.py", description="Bước «bìa A/B» (Thử nghiệm A/B 3 bìa) của phiên kênh.")
    ap.add_argument("--kenh", required=True)
    ap.add_argument("--phien", action="store_true", help="bước bìa A/B của MỘT kênh (đặt thử + đọc kết quả)")
    ap.add_argument("--thu", action="store_true", help="CHỈ ĐỌC: dò nút / thử nghiệm, không đặt, không ghi sổ")
    ap.add_argument("--trong-phien", action="store_true", help="agent gọi giữa phiên — không tự giữ khoá máy")
    a = ap.parse_args(argv)
    if not a.phien:
        ap.error("cần --phien")
    ghi = smd._nhat_ky(a.kenh)                                       # noqa: SLF001
    ma, bc = chay_buoc(a.kenh, thu=a.thu, tu_giu=not a.trong_phien, ghi=ghi)
    try:
        smd._ghi_json(DUONG_BAO_CAO, dict(bc, ma_thoat=ma))           # noqa: SLF001
    except Exception:  # noqa: BLE001
        pass
    try:
        import agent  # noqa: PLC0415
        agent.ghi("bìa A/B DOM {0}{1}: {2} đặt · {3} đọc · mã {4} ({5})".format(
            a.kenh, " [thử]" if a.thu else "", len(bc.get("dat") or {}), len(bc.get("doc") or {}), ma,
            str(bc.get("ly_do") or "")[:80]))
    except Exception:  # noqa: BLE001
        pass
    return ma


if __name__ == "__main__":
    raise SystemExit(main())
