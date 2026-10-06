"""Bàn giao lượt sản xuất DONE cho máy ảo đăng — nửa TRÊN TOOL của GĐ4.

Chủ dự án, 01/09/2026: *"luồng mới nó nằm ở trên tool mà"* — đúng: máy ảo chỉ
là tay đăng; còn *sản xuất xong → xuất gói → lên kế hoạch → duyệt* phải diễn
ra ở tool. Tệp này là khâu XUẤT GÓI + LÊN KẾ HOẠCH:

    PROJECTS/AUTO/<kênh>/<lượt>/          (lượt đã DONE của tab sản xuất)
        8-video.mp4                        →  <done>/<mã gói>/8-video.mp4
        3-phu-de.srt (8-phu-de.srt nếu có) →  <done>/<mã gói>/3-phu-de.srt
        7-thumbnail/CHON-*.jpg             →  <done>/<mã gói>/<tên ảnh>
        1-tieu-de.txt  (TITLE: …)          →  cột "Tiêu đề" của kế hoạch
        1-seo.txt (DESCRIPTION:/KEYWORDS:) →  cột "Mô tả" / "Thẻ SEO"

`<done>` là thư mục mà máy ảo nhìn thấy qua ổ chia sẻ Remote Desktop
(`\\tsclient\\...\\AUTO\\done`) — đúng đường tệp mà tool đăng `D:\\upload`
đang dùng, không đổi thứ đang chạy. Mã gói = `<kênh>-<lượt>`.

Ba tệp mp4 + srt + ảnh là ĐÚNG bộ mà tool đăng kiểm (`has_required_files`);
thiếu tệp nào thì DỪNG VÀ NÓI thiếu gì, không xuất gói cụt.
"""

from __future__ import annotations

import os
import shutil
import datetime as _dt
from typing import Dict, List, Optional, Tuple

from . import ke_hoach_dang
from . import qa_truoc_dang

__all__ = ["ma_goi", "doc_gioi_thieu", "kiem_du_bo", "xuat_goi", "ban_giao",
           "ghi_nhan_dang_tay", "danh_dau_dang_tay", "TRANG_THAI_DANG_TAY",
           "TEP_VIDEO", "TEP_SRT", "TEP_BINH_LUAN", "kiem_clip_that", "TEP_NGUON_CLIP"]

#: Trạng thái ghi khi chủ kênh đăng TAY. Khác chuỗi "ĐÃ ĐĂNG" của máy một
#: chút là cố ý: nhìn sổ biết ngay video nào máy đăng, video nào người đăng —
#: và vòng dọn dẹp của tool đăng (so bằng đúng chuỗi "ĐÃ ĐĂNG") không đi xoá
#: thư mục của một gói chưa từng được xuất.
TRANG_THAI_DANG_TAY = "ĐÃ ĐĂNG (tay)"

TEP_VIDEO = "8-video.mp4"
TEP_SRT = "3-phu-de.srt"
#: Phụ đề đã làm sạch theo trục video mới (khâu dựng theo phần, Việc 2).
TEP_SRT_SACH = "8-phu-de.srt"
#: Bình luận để ghim ngay sau khi đăng. Đi kèm gói nhưng KHÔNG nằm trong bộ
#: bắt buộc: thiếu nó thì video vẫn đăng được như trước.
TEP_BINH_LUAN = "1-binh-luan.txt"
_THU_MUC_THUMB = "7-thumbnail"


def ma_goi(kenh: str, luot: str) -> str:
    """`TL4-T7` + `0004` → `TL4-T7-0004` — đọc là biết của ai, lượt nào."""
    return "{0}-{1}".format(str(kenh).strip(), str(luot).strip())


#: 05/10: trần chờ AI chọn danh sách phát. Lời gọi chat chờ VÔ HẠN khi mất mạng (su_co.goi_kien_nhan) —
#: ShopAPI treo 13:09 làm gói TL5 đã dựng xong kẹt ở bàn giao, giữ luôn khe "nang" của cả máy.
HAN_CHON_DSP_GIAY = 120


def _goi_co_han(goi_ai, de: str, han: float):
    """Gọi `goi_ai(de)` trong luồng nền; quá `han` giây → None (luồng daemon tự chết theo tiến trình)."""
    import threading  # noqa: PLC0415
    kq: dict = {}

    def chay():
        try:
            kq["tra"] = goi_ai(de)
        except Exception as loi:  # noqa: BLE001
            kq["loi"] = loi

    t = threading.Thread(target=chay, name="chon-dsp", daemon=True)
    t.start()
    t.join(han)
    if t.is_alive():
        return None
    if "loi" in kq:
        raise kq["loi"]
    return kq.get("tra")


def chon_danh_sach_phat(danh_sach: str, tieu_de: str, mo_ta: str, goi_ai,
                        han_giay: float = HAN_CHON_DSP_GIAY) -> str:
    """1 lượt LLM rẻ chọn đúng 1 tên trong `danh_sach` ("a | b | c"). Trả tên
    ĐÚNG NGUYÊN VĂN, hoặc "" khi không chọn được (lỗi/không khớp/quá `han_giay`) — không ném."""
    ten = [t.strip() for t in str(danh_sach or "").split("|") if t.strip()]
    if not ten or goi_ai is None:
        return ""
    if len(ten) == 1:
        return ten[0]
    de = ("Choose the ONE playlist that best fits this video, by meaning.\n"
          "Playlists:\n" + "\n".join("- " + t for t in ten)
          + "\n\nVideo title: " + str(tieu_de)[:300]
          + "\nVideo description: " + str(mo_ta)[:1500]
          + "\n\nReply with ONLY the exact playlist name, nothing else.")
    try:
        tra = str(_goi_co_han(goi_ai, de, han_giay) or "").strip().strip("\"'`「」- ").strip()
    except Exception:  # noqa: BLE001 — AI hỏng: bỏ, máy đăng lùi về hành vi cũ
        return ""
    for t in ten:
        if tra == t:
            return t
    for t in ten:  # AI lỡ kèm chữ thừa: nhận nếu đúng 1 tên xuất hiện
        if t in tra and sum(1 for u in ten if u in tra) == 1:
            return t
    return ""


def _doc(duong: str) -> str:
    try:
        with open(duong, "r", encoding="utf-8", errors="replace") as tep:
            return tep.read()
    except OSError:
        return ""


def doc_gioi_thieu(thu_muc_luot: str) -> Dict[str, str]:
    """Tiêu đề / mô tả / thẻ từ gói chữ của lượt — thiếu thì trả chuỗi rỗng.

    `1-seo.txt` xếp theo mục `DESCRIPTION:` … `HASHTAGS:` … `KEYWORDS:` —
    mô tả là cả khối dưới DESCRIPTION tới mục kế; thẻ là dòng sau KEYWORDS
    (đã phân cách bằng dấu phẩy, đúng dạng ô thẻ của Studio).
    """
    ra = {"tieu_de": "", "mo_ta": "", "the": "", "binh_luan": ""}
    ra["binh_luan"] = _doc(os.path.join(thu_muc_luot, TEP_BINH_LUAN)).strip()
    for dong in _doc(os.path.join(thu_muc_luot, "1-tieu-de.txt")).splitlines():
        if dong.startswith("TITLE:"):
            ra["tieu_de"] = dong[len("TITLE:"):].strip()
            break
    seo = _doc(os.path.join(thu_muc_luot, "1-seo.txt"))
    if seo:
        muc: Dict[str, List[str]] = {}
        dang: Optional[str] = None
        for dong in seo.splitlines():
            dau = dong.strip().upper()
            if dau.startswith(("DESCRIPTION:", "HASHTAGS:", "KEYWORDS:")):
                dang = dau.split(":", 1)[0]
                duoi = dong.split(":", 1)[1].strip()
                muc[dang] = [duoi] if duoi else []
                continue
            if dang:
                muc.setdefault(dang, []).append(dong)
        ra["mo_ta"] = "\n".join(muc.get("DESCRIPTION", [])).strip()
        ra["the"] = " ".join(muc.get("KEYWORDS", [])).strip()
    return ra


def _tim_thumb(thu_muc_luot: str) -> str:
    """Ảnh bìa ĐÃ CHỌN (`CHON-*`); chưa chọn thì lấy tấm đầu cho khỏi cụt bộ."""
    thu_muc = os.path.join(thu_muc_luot, _THU_MUC_THUMB)
    try:
        ten = sorted(os.listdir(thu_muc))
    except OSError:
        return ""
    anh = [t for t in ten
           if os.path.splitext(t)[1].lower() in (".jpg", ".jpeg", ".png", ".webp")]
    chon = [t for t in anh if t.startswith("CHON-")]
    return os.path.join(thu_muc, (chon or anh)[0]) if (chon or anh) else ""


def kiem_du_bo(thu_muc_luot: str) -> List[str]:
    """Danh sách thứ còn THIẾU để bàn giao — rỗng nghĩa là đủ bộ."""
    thieu = []
    if not os.path.isfile(os.path.join(thu_muc_luot, TEP_VIDEO)):
        thieu.append("video (" + TEP_VIDEO + ")")
    if not os.path.isfile(os.path.join(thu_muc_luot, TEP_SRT)):
        thieu.append("phụ đề (" + TEP_SRT + ")")
    if not _tim_thumb(thu_muc_luot):
        thieu.append("ảnh bìa (7-thumbnail/)")
    return thieu


#: Dấu NGUỒN CLIP đi kèm gói (luật 07/10/2026) — máy đăng đọc để từ chối gói
#: có cảnh không phải clip thật (`vm/may_dang_dom.kiem_clip_that_goi`).
TEP_NGUON_CLIP = "nguon-clip.json"


def kiem_clip_that(thu_muc_luot: str, *, kiem_thieu: bool = True) -> Dict[str, object]:
    """Lượt này có ĐỦ clip THẬT cho mọi cảnh không — luật 07/10/2026.

    Chủ dự án: *"thà không đăng còn hơn là sản phẩm cuối không ổn."* Trả
    `{"tong", "that", "tu_anh": [số cảnh], "thieu": [số cảnh], "loi": [câu]}`;
    `loi` rỗng = đủ clip thật. Cảnh dựng từ ảnh (`6-clip/tu-anh.json`) KHÔNG phải
    clip thật. `kiem_thieu=False` (kênh timelapse — mạch khối chủ ý không có clip
    mọi cảnh) thì chỉ kiểm clip từ ảnh. Không có `4-canh.json`/`6-clip/` (lượt
    tay, lượt cũ) thì không kiểm được số thiếu — chỉ kiểm clip từ ảnh."""
    import json  # noqa: PLC0415

    thu_muc_clip = os.path.join(thu_muc_luot, "6-clip")
    ra: Dict[str, object] = {"tong": 0, "that": 0, "tu_anh": [], "thieu": [], "loi": []}
    try:
        with open(os.path.join(thu_muc_clip, "tu-anh.json"), "r", encoding="utf-8") as tep:
            du = json.load(tep)
        tu_anh = sorted({int(x) for x in ((du or {}).get("canh") or [])})
    except (OSError, ValueError, TypeError, AttributeError):
        tu_anh = []
    canh: List[int] = []
    try:
        with open(os.path.join(thu_muc_luot, "4-canh.json"), "r", encoding="utf-8") as tep:
            canh = [int(c["scene_id"]) for c in json.load(tep) if isinstance(c, dict)]
    except (OSError, ValueError, TypeError, KeyError):
        canh = []
    thieu: List[int] = []
    if kiem_thieu and canh and os.path.isdir(thu_muc_clip):
        thieu = [n for n in canh
                 if not os.path.isfile(os.path.join(thu_muc_clip, "{0}.mp4".format(n)))]
    tong = len(canh)
    ra.update(tong=tong, tu_anh=tu_anh, thieu=thieu,
              that=max(0, tong - len(set(thieu) | set(tu_anh))) if tong else 0)
    loi: List[str] = []
    if tu_anh:
        loi.append("{0}{1} cảnh là clip DỰNG TỪ ẢNH (6-clip/tu-anh.json), không phải clip "
                   "thật".format(len(tu_anh), "/{0}".format(tong) if tong else ""))
    if thieu:
        loi.append("thiếu clip thật cho {0}/{1} cảnh ({2})".format(
            len(thieu), tong, ", ".join(str(x) for x in thieu[:12])
            + ("…" if len(thieu) > 12 else "")))
    ra["loi"] = loi
    return ra


def _ghi_nguon_clip(thu_muc_goi: str, kq: Dict[str, object]) -> None:
    """Ghi `nguon-clip.json` cạnh mp4 của gói — hỏng thì bỏ qua (máy đăng vẫn tự
    kiểm thư mục lượt)."""
    import json  # noqa: PLC0415

    du = {"tong": kq.get("tong"), "that": kq.get("that"),
          "tu_anh": list(kq.get("tu_anh") or []), "thieu": list(kq.get("thieu") or []),
          "dat": not kq.get("loi"), "cho_phep_tu_anh": bool(kq.get("cho_phep_tu_anh")),
          "luc": _dt.datetime.now().replace(microsecond=0).isoformat()}
    try:
        duong = os.path.join(thu_muc_goi, TEP_NGUON_CLIP)
        with open(duong + ".tam", "w", encoding="utf-8") as tep:
            json.dump(du, tep, ensure_ascii=False, indent=1)
        os.replace(duong + ".tam", duong)
    except OSError:
        pass


def _la_timelapse(k) -> bool:
    try:
        from .timelapse import la_timelapse  # noqa: PLC0415

        return bool(la_timelapse(k))
    except Exception:  # noqa: BLE001
        return False


def xuat_goi(thu_muc_luot: str, thu_muc_done: str, ma: str) -> str:
    """Chép bộ mp4 + srt + ảnh bìa vào `<done>/<mã>`. Trả về đường thư mục gói.

    Chép qua tên tạm rồi đổi tên từng tệp: tool đăng bên máy ảo có thể đang
    liếc thư mục này — không được để nó vớ một tệp mp4 chép nửa chừng.
    """
    thieu = kiem_du_bo(thu_muc_luot)
    if thieu:
        raise RuntimeError("lượt chưa đủ bộ để bàn giao — thiếu: "
                           + ", ".join(thieu))
    dich = os.path.join(thu_muc_done, ma)
    os.makedirs(dich, exist_ok=True)
    # (nguồn, tên đích). Phụ đề: khâu dựng theo phần (Việc 2, 28/09/2026)
    # ghi `8-phu-de.srt` — đã dời theo khoảng nghỉ bù, bỏ tiền tố `--- `,
    # không câu nào nằm trong khoảng nghỉ — thì giao BẢN ĐÓ. Tên đích giữ
    # nguyên `3-phu-de.srt`: QA và máy đăng bên máy ảo không phải đổi gì.
    # Khâu dựng tự xoá `8-phu-de.srt` khi lùi về dựng kiểu cũ, nên có tệp này
    # nghĩa là nó khớp đúng video đang nằm cạnh.
    srt_sach = os.path.join(thu_muc_luot, TEP_SRT_SACH)
    nguon = [(os.path.join(thu_muc_luot, TEP_VIDEO), TEP_VIDEO),
             (srt_sach if os.path.isfile(srt_sach)
              else os.path.join(thu_muc_luot, TEP_SRT), TEP_SRT)]
    anh = _tim_thumb(thu_muc_luot)
    nguon.append((anh, os.path.basename(anh)))
    # Bình luận để GHIM sau khi đăng — đi CÙNG gói, không đi qua bảng kế hoạch.
    # Bảng ấy có sẵn cột cố định mà cả tool đăng bên máy ảo lẫn giao diện đều
    # đọc; thêm cột là sửa lược đồ đang chạy ở hai nơi. Đặt tệp cạnh mp4 thì ai
    # đăng cũng thấy, và đăng tay cũng dùng được. Thiếu tệp KHÔNG chặn bàn giao:
    # video vẫn đăng được, chỉ là không có sẵn câu để ghim.
    bl = os.path.join(thu_muc_luot, TEP_BINH_LUAN)
    if os.path.isfile(bl):
        nguon.append((bl, TEP_BINH_LUAN))
    for duong, ten in nguon:
        ra = os.path.join(dich, ten)
        tam = ra + ".tam"
        # Video (`TEP_VIDEO`, 0,3–1,1 GB) là mục nặng nhất — nguồn
        # (`PROJECTS/AUTO/...`) và đích (`thu_muc_done`) đều nằm trong MyTool,
        # thường CÙNG một ổ đĩa NTFS. `os.link` (hardlink) trỏ một mục lục mới
        # vào CÙNG khối dữ liệu trên đĩa — tức thời, 0 byte đọc/ghi thêm — thay
        # vì `shutil.copy2` đọc rồi ghi lại toàn bộ nội dung. Chỉ áp cho VIDEO:
        # các tệp khác (srt, ảnh bìa, bình luận) nhỏ, không đáng đổi, và giữ
        # `copy2` cho chúng là không mở rộng diện rủi ro không cần thiết. Khác
        # ổ đĩa thì `os.link` ném `OSError` — lùi về `copy2` như cũ, không hỏng
        # gói. Vẫn giữ NGUYÊN cơ chế "ghi tệp tạm rồi os.replace": `os.link`
        # tạo `tam` trước, `os.replace` sau, đúng cấu trúc cũ.
        if ten == TEP_VIDEO:
            try:
                if os.path.exists(tam):
                    os.remove(tam)  # rác lượt chạy dở trước — os.link báo lỗi
                                    # "đã tồn tại" nếu còn tệp .tam cũ
                os.link(duong, tam)
            except OSError:
                shutil.copy2(duong, tam)
        else:
            shutil.copy2(duong, tam)
        os.replace(tam, ra)
    return dich


def ban_giao(goc: str, kenh: str, luot: str, thu_muc_done: str,
             ngay: str = "", gio: str = "", goi_ai=None) -> Tuple[str, bool]:
    """Xuất gói + kiểm chất lượng + ghi một dòng kế hoạch.

    Trả `(mã gói, có thêm dòng mới không)`.

    Chạy hai lần cho cùng lượt là chuyện thường (bấm nhầm, chạy lại) — gói
    được chép đè cho tươi, nhưng kế hoạch KHÔNG mọc dòng trùng: dòng cũ giữ
    nguyên ngày giờ với trạng thái người ta đã đặt.

    ═══ CỔNG QA (`core.qa_truoc_dang`), THÊM 26/09/2026 ═══

    `Sẵn sàng` (và ngày/giờ đăng) chỉ được điền khi gói xuất ra QUA ĐƯỢC bộ
    kiểm chất lượng cục bộ (đủ file, video mở được có tiếng đúng độ dài/độ
    phân giải, phụ đề khớp, tiêu đề/ảnh bìa hợp lệ) — không phải cứ đủ file là
    "x" như trước. QA fail thì: dòng MỚI để trống Sẵn sàng lẫn ngày giờ (máy
    ảo bỏ qua), ghi lý do vào `qa-loi.txt` cạnh gói, và báo ra ngoài (Telegram
    nếu có cấu hình, luôn có trong `workspace/tu-chay/tu-chay.log`). Dòng đã
    có sẵn từ trước thì KHÔNG bị đụng vào (xem đoạn "chạy hai lần" ở trên) —
    QA chỉ cập nhật `qa-loi.txt`, không tự ý xoá "Sẵn sàng" một dòng chủ dự án
    đã tự tay duyệt.

    Đây là điều kiện để sau này bật `tu_duyet: true` (tool tự điền giờ, không
    ai duyệt lại) mà không phải giao thẳng con mắt người cho máy — xem
    docstring đầu `core/qa_truoc_dang.py`.
    """
    from .auto import duong_luot  # noqa: PLC0415 — tránh vòng nhập

    from .dung_video import tim_ffmpeg  # noqa: PLC0415 — tránh nạp khi không cần
    from .kenh import doc_kenh  # noqa: PLC0415

    thu_muc_luot = duong_luot(goc, kenh, luot)
    ma = ma_goi(kenh, luot)
    k = doc_kenh(goc, kenh)
    # ═══ LUẬT 07/10/2026: KHÔNG BÀN GIAO VIDEO THIẾU CLIP THẬT ═══
    # Đêm 06/10 bảy gói bị bù cảnh bằng ảnh tĩnh rồi bàn giao 01:00, một gói
    # đã lên YouTube. Chặn ở đây (trước khi chép gói, trước khi có dòng kế
    # hoạch) — lượt còn `da_ban_giao: false`, lượt sau khâu clip làm lại.
    clip = kiem_clip_that(thu_muc_luot, kiem_thieu=not _la_timelapse(k))
    cho_phep_tu_anh = bool(getattr(k, "clip_tu_anh", False))
    loi_clip = [x for x in clip["loi"] if not (cho_phep_tu_anh and "DỰNG TỪ ẢNH" in x)]
    if loi_clip:
        raise RuntimeError("KHÔNG bàn giao {0}: {1} — luật 07/10/2026: thà không đăng còn hơn "
                           "sản phẩm kém; khâu clip làm lại bằng clip thật rồi mới bàn giao."
                           .format(ma, "; ".join(loi_clip)))
    xuat_goi(thu_muc_luot, thu_muc_done, ma)
    thu_muc_goi = os.path.join(thu_muc_done, ma)
    _ghi_nguon_clip(thu_muc_goi, dict(clip, loi=loi_clip, cho_phep_tu_anh=cho_phep_tu_anh))
    gt = doc_gioi_thieu(thu_muc_luot)
    ket_qua_qa = qa_truoc_dang.kiem_thu_muc_goi(
        thu_muc_goi, tieu_de=gt["tieu_de"], mo_ta=gt["mo_ta"],
        phut_muc_tieu=k.phut_muc_tieu, chenh_cho_phep=k.chenh_cho_phep,
        do_dai_tu_do=k.do_dai_tu_do, do_dai_theo_goc=k.do_dai_theo_goc,
        do_phan_giai_mong_muon=qa_truoc_dang.do_phan_giai_mong_muon(goc, k),
        ffmpeg=tim_ffmpeg(goc))
    qa_truoc_dang.ghi_ket_qua(thu_muc_goi, ket_qua_qa)
    if not ket_qua_qa.dat:
        qa_truoc_dang.bao_qa_hong(goc, ma, ket_qua_qa)

    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    o_ma = cot.index("Mã gói")
    da_co_dong = any(d[o_ma].strip() == ma for d in hang)
    if not da_co_dong:
        dsp = ""
        if getattr(k, "danh_sach_phat_kenh", ""):
            if goi_ai is None:
                try:
                    from .giam_doc.quan_ly import goi_chat_that  # noqa: PLC0415
                    _g = goi_chat_that(goc)
                    goi_ai = (lambda de: _g(de, mo_hinh="claude-sonnet-5",
                                            toi_da_token=64)) if _g else None
                except Exception:  # noqa: BLE001
                    goi_ai = None
            dsp = chon_danh_sach_phat(k.danh_sach_phat_kenh, gt["tieu_de"],
                                      gt["mo_ta"], goi_ai)
            if dsp and "Danh sách phát" not in cot:  # thêm cột, giữ tương thích
                cot = list(cot) + ["Danh sách phát"]
                hang = [list(h) + [""] for h in hang]
        dong = {ten: "" for ten in cot}
        dong.update({"Mã gói": ma, "Danh sách phát": dsp,
                     "Ngày đăng": ngay if ket_qua_qa.dat else "",
                     "Giờ đăng": gio if ket_qua_qa.dat else "",
                     "Tiêu đề": gt["tieu_de"], "Mô tả": gt["mo_ta"],
                     "Thẻ SEO": gt["the"], "Sẵn sàng": "x" if ket_qua_qa.dat else ""})
        hang.append([dong.get(ten, "") for ten in cot])
        ke_hoach_dang.luu_bang(goc, kenh, hang, cot)
    elif ngay and gio and ket_qua_qa.dat:
        _lam_tuoi_lich_cu(goc, kenh, ma, cot, hang, ngay, gio)

    # ═══ HỒ SƠ VIDEO (Việc 3, 28/09/2026) ═══
    #
    # Chụp lại NGAY LÚC NÀY — thư mục lượt còn đủ mọi tệp (kịch bản, hồ sơ
    # chấm điểm, ảnh bìa…) — vào `CHANNEL/<kênh>/ho-so-video/`, nơi
    # `core/don_dep*.py` không bao giờ đụng tới. Đây là NGUỒN DUY NHẤT còn lại
    # để nối số liệu Studio (về sau vài ngày) với "tool đã chọn gì cho video
    # này" một khi thư mục lượt AUTO bị dọn. Thuần đọc/ghi đĩa, 0 đồng — nhưng
    # hỏng ở đây (đĩa đầy, quyền tệp…) TUYỆT ĐỐI không được làm hỏng cả lượt
    # bàn giao đã xong xuôi phía trên.
    try:
        from . import ho_so_video  # noqa: PLC0415 — tránh vòng nhập
        ho_so_video.tao_ho_so(goc, kenh, luot, ma)
    except Exception as loi:  # noqa: BLE001
        pass

    return ma, not da_co_dong


def _lam_tuoi_lich_cu(goc: str, kenh: str, ma: str, cot: List[str], hang: List[List[str]],
                      ngay: str, gio: str, bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Dòng kế hoạch CÓ SẴN của gói mà lịch đã TRÔI QUA, chưa tải lên (Trạng thái
    đăng trống, không Video ID) → đổi sang khe mới (`ngay`, `gio`) vừa tính.

    Ca 07/10/2026: gói chờ clip thật (kho clip hết hạn mức) quá giờ đăng cũ —
    bàn giao lại phải lấy khe trống KẾ TIẾP, không giữ một giờ đã qua (máy đăng
    bỏ qua giờ đã qua → gói nằm chết). Dòng người đã duyệt mà lịch còn ở tương
    lai thì KHÔNG đụng (luật "chạy hai lần" của `ban_giao`). Trả True nếu đổi."""
    luc = bay_gio or _dt.datetime.now()
    if "Ngày đăng" not in cot or "Giờ đăng" not in cot:
        return False
    o = {t: cot.index(t) for t in ("Mã gói", "Ngày đăng", "Giờ đăng")}
    o_tt = cot.index("Trạng thái đăng") if "Trạng thái đăng" in cot else -1
    o_id = cot.index("Video ID") if "Video ID" in cot else -1
    doi = False
    for d in hang:
        if d[o["Mã gói"]].strip() != ma:
            continue
        if (o_tt >= 0 and o_tt < len(d) and d[o_tt].strip()) or \
                (o_id >= 0 and o_id < len(d) and d[o_id].strip()):
            continue
        try:
            cu = _dt.datetime.strptime("{0} {1}".format(d[o["Ngày đăng"]].strip(),
                                                         d[o["Giờ đăng"]].strip()),
                                       "%d/%m/%Y %H:%M")
        except ValueError:
            cu = None
        if cu is None or cu > luc:
            continue    # chưa có lịch (chờ duyệt/QA) hoặc lịch còn ở tương lai: để nguyên
        d[o["Ngày đăng"]], d[o["Giờ đăng"]] = ngay, gio
        doi = True
    if doi:
        ke_hoach_dang.luu_bang(goc, kenh, hang, cot)
    return doi


def danh_dau_dang_tay(goc: str, kenh: str, ma: str, *, ghi_chu: str = "",
                      bay_gio: Optional[_dt.datetime] = None) -> bool:
    """Đổi một dòng kế hoạch có sẵn thành **đã đăng thủ công**.

    Ghi cả ngày/giờ THẬT lúc người dùng bấm, không chỉ đổi trạng thái. Mốc này
    là thứ lịch hai ngày tính lượt kế tiếp và bộ dọn đĩa tính hạn ân xá. Xoá
    ``Sẵn sàng`` để máy đăng không bao giờ nhặt lại dòng người đã đăng tay.
    """
    luc = bay_gio or _dt.datetime.now()
    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    if "Mã gói" not in cot:
        return False
    o_ma = cot.index("Mã gói")
    thay = False
    for dong in hang:
        if dong[o_ma].strip() != str(ma).strip():
            continue
        cap_nhat = {
            "Ngày đăng": luc.strftime("%d/%m/%Y"),
            "Giờ đăng": luc.strftime("%H:%M"),
            "Sẵn sàng": "",
            "Trạng thái đăng": TRANG_THAI_DANG_TAY,
        }
        if ghi_chu:
            cap_nhat["Ghi chú"] = ghi_chu
        for ten, gia_tri in cap_nhat.items():
            if ten in cot:
                dong[cot.index(ten)] = gia_tri
        thay = True
    if thay:
        ke_hoach_dang.luu_bang(goc, kenh, hang, cot)
    return thay


def ghi_nhan_dang_tay(goc: str, kenh: str, luot: str,
                      ghi_chu: str = "", *,
                      bay_gio: Optional[_dt.datetime] = None) -> Tuple[str, bool]:
    """Chủ kênh vừa ĐĂNG TAY một lượt — ghi vào sổ kế hoạch cho tool biết.

    Chủ dự án, 01/09/2026: *"tool edit xong vẫn còn 1 bước nữa là tao làm thủ
    công đưa vào CapCut ghép nhạc và xem lại, sau đó mới xuất ra rồi mới đưa
    sang vm để đăng… tao sẽ edit hoàn thiện và đăng tay trước mắt — nên thiết
    kế 1 kiểu gì đó tao đăng xong tao sẽ tự cập nhật trạng thái tool"*.

    Đây là cái nút ấy. KHÔNG xuất gói, KHÔNG đòi đủ bộ (bản đăng thật đã đi
    qua CapCut, tool không giữ nó): chỉ ghi một dòng sổ — tiêu đề/mô tả/thẻ
    lấy từ lượt để sổ tự đọc được, ngày giờ là LÚC GHI NHẬN, `Sẵn sàng` để
    trống và trạng thái là :data:`TRANG_THAI_DANG_TAY` nên máy ảo không bao
    giờ đụng vào dòng này. Lượt từng được bàn giao rồi thì chỉ đổi trạng thái,
    không mọc dòng mới.

    Sổ này về sau là trí nhớ của bộ não chu kỳ (GĐ6): đề tài nào đã đăng —
    tay hay máy — đều nằm một chỗ.
    """
    from .auto import duong_luot  # noqa: PLC0415 — tránh vòng nhập

    ma = ma_goi(kenh, luot)
    cot, hang = ke_hoach_dang.doc_bang(goc, kenh)
    o_ma = cot.index("Mã gói")
    if any(d[o_ma].strip() == ma for d in hang):
        danh_dau_dang_tay(goc, kenh, ma, ghi_chu=ghi_chu, bay_gio=bay_gio)
        return ma, False
    luc = bay_gio or _dt.datetime.now()
    gt = doc_gioi_thieu(duong_luot(goc, kenh, luot))
    dong = {ten: "" for ten in cot}
    dong.update({"Mã gói": ma,
                 "Ngày đăng": luc.strftime("%d/%m/%Y"),
                 "Giờ đăng": luc.strftime("%H:%M"),
                 "Tiêu đề": gt["tieu_de"], "Mô tả": gt["mo_ta"],
                 "Thẻ SEO": gt["the"],
                 "Trạng thái đăng": TRANG_THAI_DANG_TAY,
                 "Ghi chú": ghi_chu})
    hang.append([dong.get(ten, "") for ten in cot])
    ke_hoach_dang.luu_bang(goc, kenh, hang, cot)
    return ma, True


# ═══ TỰ MỞ KHOÁ GÓI KẸT QA (30/09/2026) ═══════════════════════════════════════
#
# Cổng độ dài đã đổi thành CHỈ CẢNH BÁO, nhưng gói kẹt từ trước (còn
# `qa-loi.txt`) không tự được kiểm lại. `kiem_lai_goi_ket` = logic của
# `workspace/cong-cu-dieu-phoi/mo_khoa_qa.py`, đưa vào tool để `core.gac_tong`
# gọi định kỳ — "video đã xong thì cứ đăng", không cần người bấm.


def _loi_clip_cua_goi(goc: str, ma_kenh: str, ma: str, k=None) -> List[str]:
    """Lỗi clip thật của lượt sinh ra gói `ma` (`<kênh>-<lượt>`) — [] nếu ổn hoặc
    không tìm được thư mục lượt."""
    from .auto import duong_luot  # noqa: PLC0415

    tien_to = str(ma_kenh) + "-"
    if not str(ma).startswith(tien_to):
        return []
    thu_muc_luot = duong_luot(goc, ma_kenh, str(ma)[len(tien_to):])
    if not os.path.isdir(thu_muc_luot):
        return []
    kq = kiem_clip_that(thu_muc_luot, kiem_thieu=not _la_timelapse(k))
    cho_phep = bool(getattr(k, "clip_tu_anh", False))
    return [x for x in kq["loi"] if not (cho_phep and "DỰNG TỪ ẢNH" in x)]


def liet_ke_goi_ket(goc: str, kenh: str) -> List[str]:
    """Mã các gói trong `thu_muc_done` của kênh còn `qa-loi.txt` (chỉ đọc đĩa)."""
    from .kenh import doc_kenh  # noqa: PLC0415
    try:
        k = doc_kenh(goc, kenh)
    except Exception:  # noqa: BLE001 — kênh hỏng cấu hình: coi như không có gì
        return []
    if not k.thu_muc_done or not os.path.isdir(k.thu_muc_done):
        return []
    return sorted(m for m in os.listdir(k.thu_muc_done)
                  if os.path.isfile(os.path.join(k.thu_muc_done, m, qa_truoc_dang.TEN_TEP_KET_QUA)))


def kiem_lai_goi_ket(goc: str, ma_kenh: str, *, kiem=None, toi_da: int = 0) -> List[Dict[str, object]]:
    """Chạy lại QA cho gói kẹt của một kênh; ĐẠT thì điền Sẵn sàng + khe trống
    sớm nhất và xoá `qa-loi.txt`. Bỏ qua dòng Ghi chú bắt đầu "Bỏ", dòng đã có
    "Trạng thái đăng", dòng đã Sẵn sàng, gói không có dòng kế hoạch.

    `kiem(goc, kenh, ma) -> KetQuaQA` (mặc định `qa_truoc_dang.kiem_goi`, chạy
    FFmpeg — nơi gọi phải giữ khe "nang"). `toi_da` > 0: chỉ kiểm tối đa ngần
    ấy gói (chặn một lượt gác chạy quá lâu). Trả danh sách
    `{"ma", "ket_qua": "mo"|"chua_dat"|"bo_qua", "loi": [...], "ngay", "gio"}`.
    """
    from . import xep_lich  # noqa: PLC0415
    from .kenh import doc_kenh  # noqa: PLC0415

    kiem = kiem or qa_truoc_dang.kiem_goi
    ds = liet_ke_goi_ket(goc, ma_kenh)
    if not ds:
        return []
    k = doc_kenh(goc, ma_kenh)
    cot, hang = ke_hoach_dang.doc_bang(goc, ma_kenh)
    if "Mã gói" not in cot or "Sẵn sàng" not in cot:
        return []
    o = {t: cot.index(t) for t in ("Mã gói", "Ngày đăng", "Giờ đăng", "Sẵn sàng")}
    o_tt = cot.index("Trạng thái đăng") if "Trạng thái đăng" in cot else -1
    o_gc = cot.index("Ghi chú") if "Ghi chú" in cot else -1
    dung = xep_lich.khe_da_dung(goc, ma_kenh)
    ra: List[Dict[str, object]] = []
    doi, da_kiem = False, 0
    for ma in ds:
        dong = next((d for d in hang if d[o["Mã gói"]].strip() == ma), None)
        if dong is None or (o_tt >= 0 and dong[o_tt].strip()) \
                or (o_gc >= 0 and dong[o_gc].strip().lower().startswith("bỏ")) \
                or dong[o["Sẵn sàng"]].strip():
            ra.append({"ma": ma, "ket_qua": "bo_qua", "loi": []})
            continue
        if toi_da and da_kiem >= toi_da:
            continue
        loi_clip = _loi_clip_cua_goi(goc, ma_kenh, ma, k)
        if loi_clip:    # luật 07/10/2026: gói thiếu clip thật không bao giờ được mở khoá
            ra.append({"ma": ma, "ket_qua": "chua_dat", "loi": loi_clip})
            continue
        da_kiem += 1
        kq = kiem(goc, ma_kenh, ma)
        if not kq.dat:
            ra.append({"ma": ma, "ket_qua": "chua_dat", "loi": list(kq.loi)})
            continue
        ngay, gio = xep_lich.khe_trong_som_nhat(goc, ma_kenh, k, da_dung=dung)
        if not ngay:  # chưa có khe: chưa đổi gì, lần sau thử lại
            ra.append({"ma": ma, "ket_qua": "bo_qua", "loi": ["chưa có khe trống"]})
            continue
        dung.add((ngay, gio))
        qa_truoc_dang.ghi_ket_qua(os.path.join(k.thu_muc_done, ma), kq)
        dong[o["Ngày đăng"]], dong[o["Giờ đăng"]], dong[o["Sẵn sàng"]] = ngay, gio, "x"
        doi = True
        ra.append({"ma": ma, "ket_qua": "mo", "loi": [], "ngay": ngay, "gio": gio})
    if doi:
        ke_hoach_dang.luu_bang(goc, ma_kenh, hang, cot)
    return ra
