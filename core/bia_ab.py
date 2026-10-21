"""BÌA A/B «TỰ CHƠI» (G4, 21/10/2026) — mỗi video mới một «Thử nghiệm A/B» chỉ-hình-thu-nhỏ với 3 bìa tốt nhất của lô.

═══ VÌ SAO ═══ (`docs/KE-HOACH-TU-HOC-KIEU-CO-VUA.md`, G4) Giám khảo LLM bìa gần như không dự báo CTR (đo 20/10). Nhãn
sạch nhất có thể có: YouTube chiếu 3 bìa của CÙNG một video, CÙNG lúc, rồi đo phần thời gian xem của từng bìa. Mỗi video
thành một ván A/B/C — học họ kiểu chữ (`core/bia_du_lieu`), hiệu chuẩn giám khảo (`core/hieu_chuan`), não «bia».

═══ ĐO THẬT (Studio vi, 16–21/10/2026, bằng chứng `vm/logs/studio-may/<K>/*test-hop*`, sổ `giam-doc/ab-tieu-de.json`) ═══
  · Nút «Thử nghiệm A/B» (`ytcp-button#ab-test-button`, khoá `phan_tu.ab_nut`) nằm DƯỚI ô Tiêu đề của TRANG SỬA video —
    gộp cả tiêu đề lẫn bìa. Hộp: chip «Chỉ tiêu đề» · «Chỉ hình thu nhỏ» · «Tiêu đề và hình thu nhỏ»; 3 ô bìa
    (`ytcp-thumbnail-uploader`: ô 1 = bìa đang chạy, Studio điền sẵn; ô 2 bắt buộc; ô 3 tuỳ chọn) → «Thiết lập thử nghiệm».
  · MỘT thử nghiệm mỗi video: đã có thử nghiệm thì nút biến mất (chỉ còn «Xem báo cáo thử nghiệm»), gói Studio
    `videoCreatorExperiment` là MỘT đối tượng (`experimentId` 1). ⇒ thử bìa và thử tiêu đề loại trừ nhau.
  · Khuôn gói: `state` STARTED|FINISHED, `finishedReason`, `selectedArm` (bìa YouTube đang cho chạy), `armCount`,
    `experimentArmData[]` (thumbnail/title theo thứ tự ô), `result.resultState` NOT_CONCLUSIVE_YET | NOT_ENOUGH_DATA |
    NO_WINNER | …, `result.winnerArm`, `result.armResults[] {arm, watchtimeFraction}`, `experimentStartTime`,
    `experimentFinishTime`, `experimentConfiguration {hasThumbnails, hasTitles}`. Một thử nghiệm 2 nhánh kết thúc sau
    3,2 ngày (NO_WINNER, 50,1/49,9 %); YouTube nói tối đa ~2 tuần → máy đóng «không kết luận» sau `NGAY_DONG` ngày.
  · Cần «tính năng nâng cao» (xác minh điện thoại): kênh bị chặn ghim (`studio_may.thieu_tinh_nang`) → việc người.

═══ LUẬT CHỌN (thử bìa vs thử tiêu đề `core/ab_tieu_de`) ═══ Một video chỉ có một thử nghiệm, nên: BÌA ƯU TIÊN trên mọi
video có ≥ 2 bìa qua cổng (A/B tiêu đề kèm bìa trộn hai biến → không ra nhãn sạch cho cái nào); A/B tiêu đề chỉ chạy ở
video KHÔNG thử bìa được (bìa nhì/ba trượt cổng, kênh tắt `bia_ab`, mục bìa `bo`/`khong_quyen`) — `uu_tien_bia`.

═══ LÀM Ở ĐÂU ═══ KHÔNG mở Chrome thêm: bước «bìa A/B» trong PHIÊN NGÀY của kênh (`vm/agent.chay_mot_phien`, sau «cộng
sự», Chrome kênh đang mở, khoá máy phiên đang giữ) — `vm/bia_ab_dom.py --phien --trong-phien`. Phiên 07:30 đăng video
ngày mai (hẹn lịch) — video công khai sáng nay (05:00) là đích: thử nghiệm bắt đầu từ vài giờ tuổi. Video HẸN LỊCH chỉ
được đọc trạng thái nút (thăm dò một lần, `meta.len_lich`); đặt thử trên video chưa công khai chỉ khi chủ bật
`workspace/cai-dat.json: bia_ab.len_lich: true`.

═══ CỔNG ═══ Bìa A = bìa đang chạy (hồ sơ `anh/<mã>.jpg`, có dấu `chu_khop`); B/C = 2 ứng viên tốt nhất còn lại
(`studio_may.ung_vien_bia`: hồ sơ `-bia-2/-bia-3`, cổng đọc được `do_bia.cham_tep`, DẤU cổng chữ — tấm chưa dấu đọc mù
lại 2 lượt và đóng dấu trên bản sao qua `studio_may.dau_ung_vien`). Chỉ 1 ứng viên qua → thử 2 bìa; 0 → không thử. Video
đang THẮNG (`do_bia.video_dang_thang`) → không bao giờ đặt thử nghiệm. Cửa ra YouTube (`studio_may_dom.test_mot_video`)
kiểm dấu lần cuối.

═══ KẾT QUẢ ═══ Thử nghiệm ≥ `NGAY_DOC_KQ_TU` ngày → phiên đọc lại (≤ 1 lần/`GIO_DOC_KQ_LAI` giờ/video) → `ket_qua`
{ket_luan thang|khong_ket_luan, thang A/B/C, ti_phan (phần thời gian xem), chon (bìa YouTube đang chạy)}. YouTube tự áp
bìa thắng → bìa đang chạy ≠ A thì hồ sơ đổi theo (`ap_ban_thang`: `anh/<mã>.jpg` = tấm thắng có dấu, bản cũ vào
`_truoc-do-bia/`, `lich_su_sua` loại bia, `thumbnail.chu_khop`). Học: não «bia», cặp thắng/thua theo họ kiểu chữ
(`thong_ke_ho_ab` → `bia_du_lieu.hau_nghiem`), giám khảo ↔ người xem thật (`do_giam_khao` → `hieu_chuan`). Đo 21/10:
3 bìa của MỘT lô hầu như cùng họ (lô vẽ theo một họ đã chọn) → cặp họ hiếm khi có; nhãn ván vẫn dạy giám khảo + ghi ý /
biến (`ma`) của từng bìa cho hàm giá trị bìa (G2). Muốn học họ thì lô phải trộn họ (đề xuất, chưa làm).

Sổ: `CHANNEL/<k>/nghien-cuu/bia-ab.json` {kenh, meta, muc: [...]}. Không mạng, không Chrome, không LLM trong tệp này.
"""

from __future__ import annotations

import datetime as _dt
import glob
import hashlib
import io
import json
import os
import re
import shutil
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

TEP = "bia-ab.json"
KHOA_CAI = "bia_ab"
#: Khung cấm (như cộng sự): lượt quét đêm 02:10–06:00, 60 phút trước giờ công khai 05:00 / 20:00.
CAI_DAT_MAC_DINH: Dict[str, Any] = {
    "bat": True,
    "gio_cam": [["02:10", "06:00"], ["04:00", "05:00"], ["19:00", "20:00"]],
    "phut_truoc_lich": 60,          # có video nào (mọi kênh) hẹn công khai trong ngần này phút → không mở thử nghiệm
    "toi_da_dat_phien": 2,
    "toi_da_doc_phien": 3,
    "len_lich": False,              # đặt thử trên video HẸN LỊCH (chưa công khai) — chủ bật sau khi thăm dò thấy được
}
#: Video công khai tối đa ngần này giờ mới được đặt thử (nhãn sạch cần thử từ sớm; khớp cò (a) của A/B tiêu đề).
TUOI_MOI_GIO = 72.0
#: Video hẹn lịch trong ngần này giờ tới được thăm dò nút (đọc).
GIO_LEN_LICH_TOI = 36.0
NGAY_DOC_KQ_TU = 2.0
GIO_DOC_KQ_LAI = 24.0
#: Thử nghiệm đặt quá ngần này ngày mà chưa kết thúc / chưa đọc được → đóng «không kết luận».
NGAY_DONG = 21.0
#: Tự kiểm: còn «đang chạy» quá ngần này ngày = kẹt; video mới đủ bìa mà quá ngần này giờ chưa đặt = đặt hỏng.
NGAY_KET_TU_KIEM = 30.0
GIO_CHUA_DAT_TU_KIEM = 30.0
SO_LOI_TOI_DA = 4
#: Kênh vừa bị Studio báo không có quyền A/B trong ngần này ngày → không thử.
NGAY_KHONG_QUYEN = 7
#: Thăm dò nút trên video hẹn lịch: kết quả «không» thì thăm lại sau ngần này ngày.
NGAY_THAM_LAI = 14
TOI_DA_BIEN_THE = 3
TT_CHO, TT_DANG, TT_XONG, TT_BO, TT_LOI, TT_KHONG_QUYEN, TT_DA_CO = (
    "cho", "dang_chay", "xong", "bo", "loi", "khong_quyen", "da_co")
#: Video có mục ở các trạng thái này → A/B tiêu đề nhường (bìa ưu tiên).
TT_GIU = (TT_CHO, TT_DANG, TT_XONG)
KL_THANG, KL_KHONG = "thang", "khong_ket_luan"
#: Cặp thắng/thua từ thử nghiệm KHÔNG KẾT LUẬN: trọng số mềm theo chênh phần thời gian xem (chênh ≥ `CHENH_DU` = đủ mềm).
W_MEM, CHENH_DU = 0.25, 0.10
#: Bằng chứng A/B của một họ đạt ngần này cặp (quy đổi trọng số) thì được dịch hậu nghiệm CTR tối đa.
N_AB_DU = 6.0
NHAN = "ABC"
_RE_ARM = re.compile(r"ARM_(\d+)\b")
_RE_THUMB = re.compile(r"thumb_(\d+)\.", re.I)
_RE_BIA_N = re.compile(r"-bia-(\d+)\.jpe?g$", re.I)


# ── tiện ích ────────────────────────────────────────────────────────────────

def _luc(t: Optional[_dt.datetime] = None) -> str:
    return (t or _dt.datetime.now()).replace(microsecond=0).isoformat()


def _gio(chu: Any) -> Optional[_dt.datetime]:
    s = str(chu or "").strip()
    for dang in ("%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return _dt.datetime.strptime(s[:19] if s[:4].isdigit() else s[:16], dang)
        except ValueError:
            continue
    return None


def _doc_json(duong: str) -> Any:
    try:
        with io.open(duong, encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json(duong: str, du: Any) -> None:
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    with io.open(duong + ".tam", "w", encoding="utf-8") as tep:
        json.dump(du, tep, ensure_ascii=False, indent=1)
    os.replace(duong + ".tam", duong)


def sha1_tep(duong: str) -> str:
    h = hashlib.sha1()  # noqa: S324 — nhận diện tệp
    try:
        with open(duong, "rb") as tep:
            for khoi in iter(lambda: tep.read(1 << 16), b""):
                h.update(khoi)
    except OSError:
        return ""
    return h.hexdigest()


def _so(x: Any) -> Optional[float]:
    if isinstance(x, bool) or x is None:
        return None
    try:
        return float(str(x).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def _co(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    s = str(x if x is not None else "").strip().lower()
    return True if s in ("true", "1", "yes", "co", "bat", "on") else False if s in (
        "false", "0", "no", "khong", "tat", "off") else None


def _luot(kenh: str, ma_goi: str) -> str:
    return ma_goi[len(kenh) + 1:] if ma_goi.startswith(kenh + "-") else ma_goi.rsplit("-", 1)[-1]


def _vm(goc: str) -> str:
    try:
        from .studio_may import thu_muc_vm  # noqa: PLC0415
        return thu_muc_vm(goc)
    except Exception:  # noqa: BLE001
        return os.path.join(goc, "vm")


# ── công tắc + cài đặt ──────────────────────────────────────────────────────

def _kenh_yaml(goc: str, kenh: str) -> Dict[str, Any]:
    try:
        from .kenh import TEP_KENH, doc_yaml  # noqa: PLC0415
        return doc_yaml(os.path.join(goc, "CHANNEL", kenh, TEP_KENH)) or {}
    except Exception:  # noqa: BLE001
        return {}


def bat(cai: Any) -> bool:
    """`bia_ab` trong kenh.yaml thắng; không khai → như A/B tiêu đề: theo `giam_doc_studio` (kênh mà giám đốc KHÔNG được
    sửa Studio — như TL4-T7 — mặc định TẮT, chủ bật bằng `bia_ab: true`). `giam_doc: tat` → tắt."""
    cai = getattr(cai, "cai", cai) or {}
    if str(cai.get("giam_doc") or "").strip().lower() == "tat":
        return False
    rieng = _co(cai.get("bia_ab"))
    if rieng is not None:
        return rieng
    return bool(_co(cai.get("giam_doc_studio")))


def doc_cai(goc: str, de: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mặc định ← `workspace/cai-dat.json: bia_ab` ← `de`."""
    cai = dict(CAI_DAT_MAC_DINH)
    tep = _doc_json(os.path.join(goc, "workspace", "cai-dat.json"))
    if isinstance(tep, dict) and isinstance(tep.get(KHOA_CAI), dict):
        cai.update({k: v for k, v in tep[KHOA_CAI].items() if not str(k).startswith("_")})
    if de:
        cai.update(de)
    return cai


def _so_video(goc: str) -> Dict[str, Any]:
    du = _doc_json(os.path.join(_vm(goc), "logs", "so-video-id.json"))
    return du if isinstance(du, dict) else {}


def trong_gio_cam(goc: str, bay: _dt.datetime, cai: Dict[str, Any], so_video: Optional[Dict[str, Any]] = None) -> str:
    """'' khi được mở thử nghiệm / đọc kết quả; câu lý do khi trong khung cấm (cố định + video BẤT KỲ kênh nào hẹn công
    khai trong `phut_truoc_lich` phút tới)."""
    p = bay.hour * 60 + bay.minute
    for tu, den in cai.get("gio_cam") or []:
        try:
            a, b = int(tu[:2]) * 60 + int(tu[3:5]), int(den[:2]) * 60 + int(den[3:5])
        except (TypeError, ValueError):
            continue
        if a <= p < b:
            return "khung cấm {0}–{1}".format(tu, den)
    phut = float(cai.get("phut_truoc_lich") or 0)
    if phut > 0:
        for k, m in (so_video if so_video is not None else _so_video(goc)).items():
            lich = _gio((m or {}).get("lich_dat") or (m or {}).get("lich")) if isinstance(m, dict) else None
            if lich and 0 <= (lich - bay).total_seconds() <= phut * 60:
                return "video {0} hẹn công khai lúc {1:%H:%M} — không mở thử nghiệm trong {2:g} phút trước giờ đăng".format(
                    str(k).split("/", 1)[-1], lich, phut)
    return ""


# ── sổ ──────────────────────────────────────────────────────────────────────

def duong_so(goc: str, kenh: str) -> str:
    try:
        from .doi_thu_kenh import thu_muc_nghien_cuu  # noqa: PLC0415
        return os.path.join(thu_muc_nghien_cuu(goc, kenh), TEP)
    except Exception:  # noqa: BLE001
        return os.path.join(goc, "CHANNEL", kenh, "nghien-cuu", TEP)


def doc_toan_so(goc: str, kenh: str) -> Dict[str, Any]:
    du = _doc_json(duong_so(goc, kenh))
    du = du if isinstance(du, dict) else {}
    return {"kenh": kenh, "meta": du.get("meta") if isinstance(du.get("meta"), dict) else {},
            "muc": [m for m in du.get("muc") or [] if isinstance(m, dict)]}


def doc_so(goc: str, kenh: str) -> List[Dict[str, Any]]:
    return doc_toan_so(goc, kenh)["muc"]


def ghi_toan_so(goc: str, kenh: str, so: Dict[str, Any]) -> None:
    _ghi_json(duong_so(goc, kenh), {"kenh": kenh, "meta": so.get("meta") or {}, "muc": (so.get("muc") or [])[-400:]})


def muc_cua(ds: Sequence[Dict[str, Any]], vid: str) -> Optional[Dict[str, Any]]:
    """Mục MỚI NHẤT của video."""
    return next((m for m in reversed(list(ds)) if m.get("video_id") == vid), None)


def dang_chay(goc: str, kenh: str, vid: str) -> bool:
    """Video đang có thử nghiệm bìa A/B của máy chạy (không đổi bìa trực tiếp lúc này)."""
    m = muc_cua(doc_so(goc, kenh), vid)
    return bool(m and m.get("trang_thai") == TT_DANG)


# ── 3 bìa của gói: A (đang chạy) + B/C (hạng nhì/ba của lô) ─────────────────

def _so_thumb(ten: Any) -> Optional[int]:
    m = _RE_THUMB.search(str(ten or ""))
    return int(m.group(1)) if m else None


def bien_the_goi(goc: str, kenh: str, ma_goi: str) -> List[Dict[str, Any]]:
    """[{nhan A|B|C, tep (bản hồ sơ), so (số tấm của lô), ma (ý-biến), ho (họ kiểu chữ), diem_gk, diem_bam, dau_ok,
    ly_dau}] — CHỈ ĐỌC (hồ sơ `ho-so-video/<mã>.json` + `anh/`, `_lo/xep-hang.json` của lượt, sổ họ `bia-so-cai.json`)."""
    hs = _doc_json(os.path.join(goc, "CHANNEL", kenh, "ho-so-video", ma_goi + ".json"))
    hs = hs if isinstance(hs, dict) else {}
    anh = os.path.join(goc, "CHANNEL", kenh, "ho-so-video", "anh")
    luot = str(hs.get("luot") or _luot(kenh, ma_goi))
    xh = _doc_json(os.path.join(goc, "PROJECTS", "AUTO", kenh, luot, "7-thumbnail", "_lo", "xep-hang.json"))
    top = [u for u in ((xh or {}).get("top") or [] if isinstance(xh, dict) else []) if isinstance(u, dict)]
    sc = _doc_json(os.path.join(os.path.dirname(duong_so(goc, kenh)), "bia-so-cai.json"))
    sc = (sc.get(luot) if isinstance(sc, dict) else None) or {}
    ho_lo = str(sc.get("kieu_chu") or sc.get("ho") or "")
    th = hs.get("thumbnail") if isinstance(hs.get("thumbnail"), dict) else {}
    b2 = hs.get("bia_2") if isinstance(hs.get("bia_2"), dict) else {}
    b3 = b2.get("bia_3") if isinstance(b2.get("bia_3"), dict) else {}
    nguon = [("A", os.path.join(anh, ma_goi + ".jpg"), _so_thumb(th.get("tep")) or 1, th.get("diem_giam_khao")),
             ("B", os.path.join(anh, ma_goi + "-bia-2.jpg"), b2.get("so"), b2.get("tong_diem")),
             ("C", os.path.join(anh, ma_goi + "-bia-3.jpg"), b3.get("so"), b3.get("tong_diem"))]
    ra: List[Dict[str, Any]] = []
    for nhan, tep, so, diem in nguon:
        if nhan != "A" and not os.path.isfile(tep):
            continue
        ra.append(dict(_meta_so(top, so, ho_lo), nhan=nhan, tep=tep, so=so, diem_gk=_so(diem), **_dau(tep)))
    return ra


def _meta_so(top: Sequence[Dict[str, Any]], so: Any, ho_lo: str) -> Dict[str, Any]:
    """Ý-biến, họ kiểu chữ, điểm «bấm như thắng» của tấm số `so` (xep-hang.json: `top[so-1]` = thumb_00<so>)."""
    try:
        u = top[int(so) - 1] if so is not None and 1 <= int(so) <= len(top) else {}
    except (TypeError, ValueError):
        u = {}
    return {"ma": str(u.get("ma") or ""), "ho": str(u.get("kieu_chu") or ho_lo or ""),
            "diem_bam": _so((u.get("diem") or {}).get("bam_nhu_thang")) if isinstance(u.get("diem"), dict) else None,
            "diem_lo": _so(u.get("tong"))}


def _dau(tep: str) -> Dict[str, Any]:
    try:
        from . import cong_chu  # noqa: PLC0415
        ly = cong_chu.kiem_dau(tep)
    except Exception as loi:  # noqa: BLE001 — không kiểm được = không có dấu (đóng an toàn)
        ly = "không kiểm được dấu cổng chữ: {0}".format(str(loi)[:80])
    return {"dau_ok": not ly, "ly_dau": ly}


def meta_ung_vien(bt: Sequence[Dict[str, Any]], u: Dict[str, Any], goc: str = "", kenh: str = "",
                  ma_goi: str = "") -> Dict[str, Any]:
    """Ứng viên `studio_may.ung_vien_bia` ({tep, tep_goc, nguon, diem_gk}) → siêu dữ liệu biến thể (so, ma, ho, điểm)."""
    ng = str(u.get("nguon") or "")
    m = re.search(r"ho-so:bia-(\d+)", ng)
    if m:
        x = next((b for b in bt if b["nhan"] == ("B" if m.group(1) == "2" else "C")), None)
        if x:
            return {k: x.get(k) for k in ("so", "ma", "ho", "diem_gk", "diem_bam", "diem_lo")}
    so = _so_thumb(u.get("tep_goc") or u.get("tep"))
    x = next((b for b in bt if so is not None and b.get("so") is not None and int(b["so"]) == so), None)
    if x:
        return {k: x.get(k) for k in ("so", "ma", "ho", "diem_gk", "diem_bam", "diem_lo")}
    ho = next((b.get("ho") for b in bt if b.get("ho")), "")
    return {"so": so, "ma": "", "ho": ho, "diem_gk": _so(u.get("diem_gk")), "diem_bam": None, "diem_lo": None}


# ── kế hoạch phiên (CHỈ ĐỌC) ────────────────────────────────────────────────

def _video_kenh(goc: str, kenh: str, so_video: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Video do TOOL đăng của kênh (`vm/logs/so-video-id.json`): [{video_id, ma_goi, lich}]."""
    ra = []
    for k, m in (so_video if so_video is not None else _so_video(goc)).items():
        if not isinstance(m, dict) or not str(k).startswith(kenh + "/") or not m.get("video_id"):
            continue
        lich = _gio(m.get("lich_dat") or m.get("lich"))
        if lich:
            ra.append({"video_id": str(m["video_id"]), "ma_goi": str(k).split("/", 1)[1], "lich": lich})
    return ra


def thieu_quyen(goc: str, kenh: str, bay: _dt.datetime, so: Optional[Dict[str, Any]] = None) -> str:
    """Lý do kênh chưa dùng được Thử nghiệm A/B: Studio vừa báo (sổ này hoặc sổ A/B tiêu đề) / kênh bị chặn ghim
    (chưa bật tính năng nâng cao). '' = dùng được."""
    so = so if so is not None else doc_toan_so(goc, kenh)
    kq = (so.get("meta") or {}).get("khong_quyen") or {}
    t = _gio(kq.get("luc"))
    if t and (bay - t).days < NGAY_KHONG_QUYEN:
        return "Studio báo kênh chưa dùng được Thử nghiệm A/B ({0})".format(str(kq.get("ly_do") or "")[:100])
    try:
        from . import ab_tieu_de  # noqa: PLC0415
        return ab_tieu_de.kenh_khong_ab(goc, kenh, bay)
    except Exception:  # noqa: BLE001
        return ""


def _ab_tieu_de_muc(goc: str, kenh: str, vid: str) -> Optional[Dict[str, Any]]:
    try:
        from . import ab_tieu_de  # noqa: PLC0415
        return ab_tieu_de.muc_cua(goc, kenh, vid)
    except Exception:  # noqa: BLE001
        return None


def _dang_thang(goc: str, kenh: str, ma_goi: str) -> str:
    try:
        from . import do_bia  # noqa: PLC0415
        return do_bia.video_dang_thang(goc, kenh, ma_goi)
    except Exception:  # noqa: BLE001
        return ""


def ke_hoach(goc: str, kenh: str, bay: Optional[_dt.datetime] = None, *, cai: Optional[Dict[str, Any]] = None,
             so_video: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Việc của bước «bìa A/B» trong phiên kênh (KHÔNG ghi gì): `dat` [{video_id, ma_goi, lich, tuoi_gio, cong_khai,
    bien_the}] (mới trước, ≤ `toi_da_dat_phien`), `doc` [video_id] (thử nghiệm đang chạy cần đọc), `tham_do_len_lich`
    (video hẹn lịch để đọc trạng thái nút một lần), `bo` [{video_id, ma_goi, ly_do, trang_thai}] (không thử được — nơi
    gọi ghi sổ), `hoan` (tạm chưa thử — không ghi sổ, phiên sau xét lại), `ly_do` (vì sao không có gì)."""
    bay = bay or _dt.datetime.now()
    cai = cai or doc_cai(goc)
    ra: Dict[str, Any] = {"kenh": kenh, "dat": [], "doc": [], "tham_do_len_lich": "", "bo": [], "hoan": [], "ly_do": ""}
    if not cai.get("bat", True):
        ra["ly_do"] = "cài đặt bia_ab.bat = false"
        return ra
    if not bat(_kenh_yaml(goc, kenh)):
        ra["ly_do"] = "kênh tắt bia_ab (kenh.yaml)"
        return ra
    so = doc_toan_so(goc, kenh)
    ds = so["muc"]
    ra["doc"] = can_doc_ket_qua(ds, bay, int(cai.get("toi_da_doc_phien") or 3))
    q = thieu_quyen(goc, kenh, bay, so)
    if q:
        ra["ly_do"] = q
        return ra
    sv = so_video if so_video is not None else _so_video(goc)
    ll = (so["meta"].get("len_lich") or {}) if isinstance(so["meta"].get("len_lich"), dict) else {}
    cho_len_lich = bool(_co(cai.get("len_lich"))) and ll.get("tt") == "duoc"
    t_ll = _gio(ll.get("luc"))
    can_tham = not ll.get("tt") or (ll.get("tt") in ("khong", "loi") and (t_ll is None or (bay - t_ll).days >= NGAY_THAM_LAI))
    for v in sorted(_video_kenh(goc, kenh, sv), key=lambda v: v["lich"], reverse=True):
        tuoi = (bay - v["lich"]).total_seconds() / 3600.0
        cong_khai = tuoi >= 0
        if cong_khai and tuoi > TUOI_MOI_GIO:
            continue
        if not cong_khai and -tuoi > GIO_LEN_LICH_TOI:
            continue
        m = muc_cua(ds, v["video_id"])
        if m and (m.get("trang_thai") in (TT_DANG, TT_XONG, TT_BO, TT_KHONG_QUYEN, TT_DA_CO)
                  or (m.get("trang_thai") == TT_LOI and int(m.get("lan_loi") or 0) >= SO_LOI_TOI_DA)):
            continue
        if not cong_khai and not cho_len_lich:
            if can_tham and not ra["tham_do_len_lich"]:
                ra["tham_do_len_lich"] = v["video_id"]
            continue
        abm = _ab_tieu_de_muc(goc, kenh, v["video_id"])
        if abm and abm.get("trang_thai") in ("da_dat", "da_co", "xong"):
            ra["bo"].append(dict(v, lich=_luc(v["lich"]), trang_thai=TT_DA_CO,
                                 ly_do="video đã có Thử nghiệm A/B tiêu đề ({0}) — một thử nghiệm mỗi video".format(
                                     abm.get("trang_thai"))))
            continue
        thang = _dang_thang(goc, kenh, v["ma_goi"])
        if thang:
            ra["bo"].append(dict(v, lich=_luc(v["lich"]), trang_thai=TT_BO,
                                 ly_do="video đang THẮNG — không đặt thử nghiệm: " + thang))
            continue
        bt = bien_the_goi(goc, kenh, v["ma_goi"])
        if not bt or not bt[0]["dau_ok"]:          # tạm (dấu có thể tới sau) — không ghi sổ, phiên sau xét lại
            ra["hoan"].append({"video_id": v["video_id"], "ma_goi": v["ma_goi"], "ly_do": "bìa A (hồ sơ) chưa có dấu "
                               "cổng chữ: " + ((bt[0]["ly_dau"] if bt else "") or "không có bìa hồ sơ")})
            continue
        if len(bt) < 2:
            ra["bo"].append(dict(v, lich=_luc(v["lich"]), trang_thai=TT_BO,
                                 ly_do="gói không còn bìa nhì/ba (hồ sơ -bia-2/-bia-3)"))
            continue
        if len(ra["dat"]) < int(cai.get("toi_da_dat_phien") or 2):
            ra["dat"].append(dict(v, tuoi_gio=round(tuoi, 1), cong_khai=cong_khai, bien_the=bt))
    if not ra["dat"] and not ra["doc"] and not ra["tham_do_len_lich"] and not ra["ly_do"]:
        ra["ly_do"] = "không có video mới cần thử bìa / thử nghiệm cần đọc"
    return ra


def can_dom(goc: str, kenh: str, bay: Optional[_dt.datetime] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """Bước phiên có việc cần Chrome không (RẺ, chỉ đọc đĩa). Không có → tiến trình con thoát ngay, không nối Chrome."""
    bay = bay or _dt.datetime.now()
    cai = doc_cai(goc)
    kh = ke_hoach(goc, kenh, bay, cai=cai)
    if kh["dat"] or kh["doc"] or kh["tham_do_len_lich"]:
        cam = trong_gio_cam(goc, bay, cai)
        if cam:
            return False, cam, kh
        return True, "{0} video đặt thử · {1} đọc kết quả{2}".format(
            len(kh["dat"]), len(kh["doc"]), " · thăm dò video hẹn lịch" if kh["tham_do_len_lich"] else ""), kh
    return False, kh["ly_do"] or "không có việc", kh


# ── ghi sổ sau bước DOM ─────────────────────────────────────────────────────

def _muc_moi(vid: str, ma_goi: str, kenh: str, bay: _dt.datetime) -> Dict[str, Any]:
    return {"id": "bab-{0}-{1}".format(vid, bay.strftime("%Y%m%d%H%M")), "video_id": vid, "ma_goi": ma_goi,
            "luot": _luot(kenh, ma_goi), "trang_thai": TT_CHO, "luc": _luc(bay), "cap_nhat": _luc(bay), "lan_loi": 0}


def ghi_bo(goc: str, kenh: str, ds_bo: Sequence[Dict[str, Any]], bay: Optional[_dt.datetime] = None) -> int:
    """Video không thử được (đã có thử nghiệm khác / đang thắng / thiếu bìa) → một mục `bo`/`da_co` (một lần)."""
    bay = bay or _dt.datetime.now()
    so = doc_toan_so(goc, kenh)
    n = 0
    for b in ds_bo:
        m = muc_cua(so["muc"], b["video_id"])
        if m and m.get("trang_thai") in (TT_BO, TT_DA_CO, TT_DANG, TT_XONG):
            continue
        m = m if m and m.get("trang_thai") in (TT_CHO, TT_LOI) else _muc_moi(b["video_id"], b["ma_goi"], kenh, bay)
        if m not in so["muc"]:
            so["muc"].append(m)
        m.update(trang_thai=b.get("trang_thai") or TT_BO, ly_do=str(b.get("ly_do") or "")[:300], cap_nhat=_luc(bay))
        n += 1
    if n:
        ghi_toan_so(goc, kenh, so)
    return n


def ghi_dat(goc: str, kenh: str, vid: str, ma_goi: str, bien_the: Sequence[Dict[str, Any]], kv: Dict[str, Any],
            bay: Optional[_dt.datetime] = None) -> Dict[str, Any]:
    """Kết quả MỘT lần đặt (`studio_may_dom.test_mot_video`: ket da_dat | da_co | khong_quyen | khong_ung_vien | loi)
    → mục sổ. `bien_the` = các bìa ĐÃ tải theo thứ tự ô (A trước) [{nhan, tep, sha1, so, ma, ho, diem_gk, …}]."""
    bay = bay or _dt.datetime.now()
    so = doc_toan_so(goc, kenh)
    m = muc_cua(so["muc"], vid)
    if not m or m.get("trang_thai") not in (TT_CHO, TT_LOI):
        m = _muc_moi(vid, ma_goi, kenh, bay)
        so["muc"].append(m)
    k = str(kv.get("ket") or "loi")
    m["bien_the"] = [{x: b.get(x) for x in ("nhan", "tep", "sha1", "nguon", "so", "ma", "ho", "diem_gk", "diem_bam",
                                              "diem_lo") if b.get(x) is not None} for b in bien_the][:TOI_DA_BIEN_THE]
    m["so_bien_the"] = len(m["bien_the"])
    m["ket"] = {x: kv.get(x) for x in ("ket", "ly_do", "che_do", "so_bien_the", "so_bia", "trang_thai", "doc_lai")
                if kv.get(x) is not None}
    m["cap_nhat"] = _luc(bay)
    if k == "da_dat":
        m.update(trang_thai=TT_DANG, bat_dau=_luc(bay), ly_do="")
    elif k == "da_co":
        m.update(trang_thai=TT_DA_CO, ly_do="video đã có thử nghiệm khác ({0})".format(kv.get("trang_thai") or "?"))
    elif k == "khong_quyen":
        m.update(trang_thai=TT_KHONG_QUYEN, ly_do=str(kv.get("ly_do") or "")[:300])
        so["meta"]["khong_quyen"] = {"luc": _luc(bay), "ly_do": str(kv.get("ly_do") or "")[:200]}
    elif k == "khong_ung_vien":
        m.update(trang_thai=TT_BO, ly_do="không còn bìa ứng viên qua cổng")
    else:
        lan = int(m.get("lan_loi") or 0) + 1
        m.update(trang_thai=TT_BO if lan >= SO_LOI_TOI_DA else TT_LOI, lan_loi=lan, ly_do=str(kv.get("ly_do") or "")[:300])
    ghi_toan_so(goc, kenh, so)
    if m["trang_thai"] in (TT_DANG, TT_KHONG_QUYEN) or (m["trang_thai"] == TT_BO and k == "loi"):
        _nao(goc, kenh, m, "chon" if m["trang_thai"] == TT_DANG else "loi",
             "A/B bìa {0}: {1} — {2}".format(vid, {TT_DANG: "ĐÃ ĐẶT {0} bìa".format(m["so_bien_the"]),
                                                    TT_KHONG_QUYEN: "kênh chưa có quyền"}.get(m["trang_thai"], "bỏ sau "
                                                                                              "{0} lần lỗi".format(
                                                                                                  m.get("lan_loi"))),
                                             " / ".join("{0}:{1}{2}".format(b.get("nhan"), b.get("ho") or "?",
                                                                            " gk{0:g}".format(b["diem_gk"])
                                                                            if b.get("diem_gk") is not None else "")
                                                        for b in m["bien_the"]) or m.get("ly_do", "")),
             khoa="bia-ab|{0}|{1}".format(m["id"], m["trang_thai"]))
    return m


def danh_dau_phien(goc: str, kenh: str, bay: Optional[_dt.datetime] = None) -> None:
    """Bước phiên vừa chạy (thật): `meta.phien_dau` (lần đầu — tự kiểm chỉ đòi video công khai SAU mốc này) +
    `meta.phien_cuoi`."""
    bay = bay or _dt.datetime.now()
    so = doc_toan_so(goc, kenh)
    so["meta"].setdefault("phien_dau", _luc(bay))
    so["meta"]["phien_cuoi"] = _luc(bay)
    ghi_toan_so(goc, kenh, so)


def ghi_tham_do_len_lich(goc: str, kenh: str, vid: str, nut: Dict[str, Any], bay: Optional[_dt.datetime] = None) -> str:
    """Thăm dò (CHỈ ĐỌC) nút «Thử nghiệm A/B» trên trang sửa của video HẸN LỊCH → `meta.len_lich` {tt duoc | khong |
    loi, bang_chung}. `nut` = {co, tat, chu, loi}. Trả tt."""
    bay = bay or _dt.datetime.now()
    so = doc_toan_so(goc, kenh)
    if nut.get("loi"):
        tt = "loi"
    elif nut.get("co") and not nut.get("tat"):
        tt = "duoc"
    else:
        tt = "khong"
    so["meta"]["len_lich"] = {"tt": tt, "luc": _luc(bay), "video_id": vid,
                              "bang_chung": str(nut.get("chu") or nut.get("loi") or "")[:300]}
    ghi_toan_so(goc, kenh, so)
    return tt


# ── đọc kết quả ─────────────────────────────────────────────────────────────

def _chi_so_arm(x: Any) -> Optional[int]:
    """"CREATOR_EXPERIMENT_ARM_2" → 1 (chỉ số 0); UNSPECIFIED / lạ → None."""
    m = _RE_ARM.search(str(x or ""))
    return int(m.group(1)) - 1 if m and int(m.group(1)) >= 1 else None


def _giay_iso(x: Any) -> str:
    try:
        return _dt.datetime.fromtimestamp(int((x or {}).get("seconds"))).replace(microsecond=0).isoformat()
    except (TypeError, ValueError, AttributeError, OSError, OverflowError):
        return ""


def doc_thu_nghiem(exp: Any) -> Dict[str, Any]:
    """`videoCreatorExperiment` THÔ → {co, khuon (có khoá `state` của khuôn thật), dang_chay, xong, thang (chỉ số nhánh
    | None), chon (bìa YouTube đang cho chạy, chỉ số | None), ti_phan {chỉ số: phần thời gian xem}, so_nhanh, co_bia,
    co_tieu_de, trang_thai_tho, ly_do_xong, bat_dau, ket_thuc, anh [url ô]}. Gói rỗng `{}` → co False."""
    if not isinstance(exp, dict) or not exp:
        return {"co": False, "khuon": False, "dang_chay": False, "xong": False, "thang": None, "chon": None,
                "ti_phan": {}, "so_nhanh": 0, "trang_thai_tho": ""}
    st = str(exp.get("state") or "").upper()
    r = exp.get("result") if isinstance(exp.get("result"), dict) else {}
    rs = str(r.get("resultState") or exp.get("resultState") or "").upper()
    arms = [a for a in exp.get("experimentArmData") or [] if isinstance(a, dict)]
    tp: Dict[int, float] = {}
    for a in r.get("armResults") or []:
        i = _chi_so_arm((a or {}).get("arm")) if isinstance(a, dict) else None
        f = _so((a or {}).get("watchtimeFraction")) if isinstance(a, dict) else None
        if i is not None and f is not None:
            tp[i] = round(f, 4)
    m = re.search(r"ARM_COUNT_(\d+)", str(exp.get("armCount") or ""))
    so_nhanh = int(m.group(1)) if m else len(arms)
    dang = bool(re.search(r"STATE_(STARTED|RUNNING|ACTIVE|PENDING|SCHEDULED)", st))
    xong = bool(st) and not dang and bool(re.search(r"STATE_(FINISHED|COMPLETED?|ENDED|STOPPED|CONCLUDED|EXPIRED)", st))
    cfg = exp.get("experimentConfiguration") if isinstance(exp.get("experimentConfiguration"), dict) else {}
    anh = []
    for a in arms:
        ts = ((a.get("thumbnail") or {}).get("thumbnails") or []) if isinstance(a.get("thumbnail"), dict) else []
        anh.append(str((ts[-1] if ts else {}).get("url") or "") if ts and isinstance(ts[-1], dict) else "")
    return {"co": True, "khuon": bool(st), "dang_chay": dang, "xong": xong, "thang": _chi_so_arm(r.get("winnerArm")),
            "chon": _chi_so_arm(exp.get("selectedArm")), "ti_phan": tp, "so_nhanh": so_nhanh,
            "co_bia": cfg.get("hasThumbnails"), "co_tieu_de": cfg.get("hasTitles"),
            "trang_thai_tho": " ".join(x for x in (st, rs) if x)[:160], "ket_qua_tho": rs,
            "ly_do_xong": str(exp.get("finishedReason") or ""), "bat_dau": _giay_iso(exp.get("experimentStartTime")),
            "ket_thuc": _giay_iso(exp.get("experimentFinishTime")), "anh": anh}


def can_doc_ket_qua(ds: Sequence[Dict[str, Any]], bay: _dt.datetime, toi_da: int = 3) -> List[str]:
    """Video có thử nghiệm của máy ĐANG CHẠY ≥ `NGAY_DOC_KQ_TU` ngày, chưa đọc trong `GIO_DOC_KQ_LAI` giờ — cũ trước."""
    ra: List[Tuple[str, str]] = []
    da: set = set()
    for m in reversed(list(ds)):
        vid = str(m.get("video_id") or "")
        if not vid or vid in da:
            continue
        da.add(vid)
        if m.get("trang_thai") != TT_DANG:
            continue
        t0, t1 = _gio(m.get("bat_dau")), _gio(m.get("doc_kq_luc"))
        if t0 is None or (bay - t0).total_seconds() < NGAY_DOC_KQ_TU * 86400:
            continue
        if t1 is not None and (bay - t1).total_seconds() < GIO_DOC_KQ_LAI * 3600:
            continue
        ra.append((str(m.get("bat_dau")), vid))
    return [v for _t, v in sorted(ra)][:max(0, int(toi_da))]


def ket_qua_tu(m: Dict[str, Any], kt: Dict[str, Any], bay: _dt.datetime) -> Dict[str, Any]:
    """Mục sổ + `doc_thu_nghiem` (đã kết thúc / đã gỡ) → `ket_qua` {ket_luan, thang (A/B/C | None), ti_phan {A: …},
    chon (bìa đang chạy, A/B/C | None), trang_thai_tho, ly_do, luc, ket_thuc}."""
    bt = m.get("bien_the") or []
    nhan = lambda i: (bt[i].get("nhan") if i is not None and i < len(bt) else None) or (  # noqa: E731
        NHAN[i] if i is not None and i < len(NHAN) else None)
    ra: Dict[str, Any] = {"luc": _luc(bay), "trang_thai_tho": kt.get("trang_thai_tho") or "",
                          "ti_phan": {nhan(i): f for i, f in sorted((kt.get("ti_phan") or {}).items()) if nhan(i)},
                          "chon": nhan(kt.get("chon")), "ket_thuc": kt.get("ket_thuc") or "",
                          "ly_do_xong": kt.get("ly_do_xong") or ""}
    if not kt.get("co"):
        ra.update(ket_luan=KL_KHONG, thang=None, ly_do="thử nghiệm không còn trên trang sửa (Studio đã gỡ)")
    elif kt.get("thang") is not None:
        ra.update(ket_luan=KL_THANG, thang=nhan(kt["thang"]), ly_do="")
    else:
        ra.update(ket_luan=KL_KHONG, thang=None, ly_do=str(kt.get("ket_qua_tho") or "không có nhánh thắng")[:120])
    return ra


def ghi_ket_qua(goc: str, kenh: str, vid: str, exp: Any, bay: Optional[_dt.datetime] = None, *,
                doc_duoc: bool = True, ap_ho_so: bool = True) -> Optional[Dict[str, Any]]:
    """Bước DOM vừa đọc `videoCreatorExperiment` của `vid` (`doc_duoc=False` = đọc hỏng). Luôn ghi mốc đọc; kết thúc /
    gỡ → `xong` + `ket_qua` + học + (bìa đang chạy ≠ A) hồ sơ theo bìa thắng; còn chạy quá `NGAY_DONG` ngày → đóng
    «không kết luận». Trả `ket_qua` khi vừa đóng, None khi còn chạy / không có mục."""
    bay = bay or _dt.datetime.now()
    so = doc_toan_so(goc, kenh)
    m = muc_cua(so["muc"], vid)
    if not m or m.get("trang_thai") != TT_DANG:
        return None
    m["doc_kq_luc"] = _luc(bay)
    kt = doc_thu_nghiem(exp) if doc_duoc else None
    kq: Optional[Dict[str, Any]] = None
    if kt is not None:
        m["doc_kq"] = {k: kt.get(k) for k in ("trang_thai_tho", "thang", "chon", "ti_phan", "so_nhanh", "co_bia")}
        if kt.get("co") and kt.get("co_bia") is False:
            kt = dict(kt, xong=True, thang=None)       # thử nghiệm trên video không phải của bìa (ai đó đổi) — đóng
            m["doc_kq"]["lech"] = "thử nghiệm đang chạy không phải thử bìa"
        if kt.get("xong") or not kt.get("co"):
            kq = ket_qua_tu(m, kt, bay)
            if kt.get("co") and kt.get("xong"):
                try:
                    m["doc_kq_tho"] = json.dumps(exp, ensure_ascii=False)[:4000]
                except (TypeError, ValueError):
                    pass
    t0 = _gio(m.get("bat_dau"))
    if kq is None and t0 is not None and (bay - t0).total_seconds() >= NGAY_DONG * 86400:
        kq = {"luc": _luc(bay), "ket_luan": KL_KHONG, "thang": None, "ti_phan": (m.get("doc_kq") or {}).get("ti_phan") or {},
              "chon": None, "ly_do": "đặt quá {0:g} ngày chưa có kết quả".format(NGAY_DONG),
              "trang_thai_tho": (kt or {}).get("trang_thai_tho") or ""}
    if kq is not None:
        m.update(trang_thai=TT_XONG, ket_qua=kq, cap_nhat=_luc(bay))
    ghi_toan_so(goc, kenh, so)
    if kq is not None:
        if ap_ho_so and kq.get("chon") and kq["chon"] != "A":
            try:
                kq["ap_ho_so"] = ap_ban_thang(goc, kenh, m, kq["chon"], bay)
            except Exception as loi:  # noqa: BLE001 — hồ sơ hỏng không làm hỏng sổ
                kq["ap_ho_so"] = "lỗi: {0}".format(str(loi)[:120])
            so = doc_toan_so(goc, kenh)
            m2 = muc_cua(so["muc"], vid)
            if m2 is not None:
                m2["ket_qua"] = kq
                ghi_toan_so(goc, kenh, so)
        _hoc(goc, kenh, m)
    return kq


def dong_qua_han(goc: str, kenh: str, bay: Optional[_dt.datetime] = None) -> List[Dict[str, Any]]:
    """Thử nghiệm đặt quá `NGAY_DONG` ngày mà máy chưa đọc được kết quả (phiên hỏng, kênh mất quyền…) → đóng «không
    kết luận» (không học gì). Trả các mục vừa đóng."""
    bay = bay or _dt.datetime.now()
    so = doc_toan_so(goc, kenh)
    ra = []
    for m in so["muc"]:
        t0 = _gio(m.get("bat_dau"))
        if m.get("trang_thai") == TT_DANG and t0 is not None and (bay - t0).total_seconds() >= NGAY_DONG * 86400 \
                and muc_cua(so["muc"], str(m.get("video_id"))) is m:
            m.update(trang_thai=TT_XONG, cap_nhat=_luc(bay), ket_qua={
                "luc": _luc(bay), "ket_luan": KL_KHONG, "thang": None, "chon": None,
                "ti_phan": (m.get("doc_kq") or {}).get("ti_phan") or {},
                "ly_do": "đặt quá {0:g} ngày chưa đọc được kết quả".format(NGAY_DONG)})
            ra.append(m)
    if ra:
        ghi_toan_so(goc, kenh, so)
        for m in ra:
            _hoc(goc, kenh, m)
    return ra


# ── bìa YouTube áp ≠ A → hồ sơ theo bìa đang chạy (cổng chữ nhất quán) ─────

def _tep_bien_the(goc: str, kenh: str, m: Dict[str, Any], nhan: str) -> str:
    """Tệp có dấu của biến thể `nhan`: tệp đã tải (bản tải lên / bản sao đóng dấu) nếu còn và đúng sha1, không thì bản
    hồ sơ `-bia-2/-bia-3` (cùng bức)."""
    b = next((x for x in m.get("bien_the") or [] if x.get("nhan") == nhan), {})
    ma = str(m.get("ma_goi") or "")
    anh = os.path.join(goc, "CHANNEL", kenh, "ho-so-video", "anh")
    ung = [str(b.get("tep") or "")]
    if nhan in ("B", "C"):
        ung.append(os.path.join(anh, "{0}-bia-{1}.jpg".format(ma, "2" if nhan == "B" else "3")))
    for p in ung:
        if p and os.path.isfile(p) and (not b.get("sha1") or sha1_tep(p) == b.get("sha1") or p != ung[0]):
            return p
    return ""


def ap_ban_thang(goc: str, kenh: str, m: Dict[str, Any], nhan: str, bay: Optional[_dt.datetime] = None) -> str:
    """YouTube đang chạy bìa `nhan` (≠ A) sau thử nghiệm → `ho-so-video/anh/<mã>.jpg` = tấm ấy (MANG DẤU cổng chữ),
    bản cũ vào `anh/_truoc-do-bia/`, `lich_su_sua` (loại bia, `thi_nghiem` = id ván), `thumbnail.chu_khop` theo tấm mới —
    để cửa ra YouTube, vòng học CTR và `do_bia.video_dang_thang` đọc đúng bìa đang chạy. Trả câu tóm tắt."""
    from . import cong_chu, ho_so_video  # noqa: PLC0415
    ma = str(m.get("ma_goi") or "")
    moi = _tep_bien_the(goc, kenh, m, nhan)
    if not ma or not moi:
        return "không còn tệp bìa {0} để đồng bộ hồ sơ".format(nhan)
    ly = cong_chu.kiem_dau(moi)
    if ly:
        return "tệp bìa {0} không có dấu cổng chữ — giữ hồ sơ ({1})".format(nhan, ly[:100])
    anh_hs = ho_so_video.duong_anh_ho_so(goc, kenh, ma)
    if os.path.isfile(anh_hs) and sha1_tep(anh_hs) == sha1_tep(moi):
        return "hồ sơ đã là bìa {0}".format(nhan)
    if os.path.isfile(anh_hs):
        sao = os.path.join(os.path.dirname(anh_hs), "_truoc-do-bia")
        os.makedirs(sao, exist_ok=True)
        if not os.path.exists(os.path.join(sao, os.path.basename(anh_hs))):
            shutil.copy2(anh_hs, os.path.join(sao, os.path.basename(anh_hs)))
            cong_chu.chuyen_dau(anh_hs, os.path.join(sao, os.path.basename(anh_hs)))
    os.makedirs(os.path.dirname(anh_hs), exist_ok=True)
    shutil.copy2(moi, anh_hs + ".tam")
    os.replace(anh_hs + ".tam", anh_hs)
    cong_chu.chuyen_dau(moi, anh_hs)
    # `doi_boi="giam_doc"`: máy (không phải người) đổi sang bìa hạng nhì/ba — `bia_theo_khuon` không coi là bìa tay;
    # `thi_nghiem` = id ván A/B để phân biệt với đổi bìa cứu CTR.
    ho_so_video.ghi_sua(goc, kenh, ma, loai="bia", cu=os.path.basename(anh_hs), moi=os.path.basename(moi),
                        doi_boi="giam_doc", thi_nghiem=str(m.get("id") or ""),
                        ly_do="Thử nghiệm A/B bìa: YouTube chạy bìa {0} sau thử nghiệm".format(nhan), bay_gio=bay)
    ho_so_video.cap_nhat_chu_khop(goc, kenh, ma, cong_chu.tom_tat_dau(anh_hs))
    return "hồ sơ đổi theo bìa {0} (bản cũ ở _truoc-do-bia)".format(nhan)


# ── học: não «bia», cặp họ kiểu chữ, giám khảo ──────────────────────────────

def _nao(goc: str, kenh: str, m: Dict[str, Any], loai: str, noi_dung: str, so: Optional[Dict[str, Any]] = None,
         khoa: str = "") -> None:
    try:
        from . import nao_bo_phan  # noqa: PLC0415
        nao_bo_phan.ghi(goc, "bia", loai, kenh=kenh, ma_goi=str(m.get("ma_goi") or ""), noi_dung=noi_dung[:600],
                        so=so or {"id": m.get("id"), "trang_thai": m.get("trang_thai")}, nguon="bia_ab", khoa=khoa)
    except Exception:  # noqa: BLE001 — não hỏng không chặn
        pass


def _hoc(goc: str, kenh: str, m: Dict[str, Any]) -> None:
    kq = m.get("ket_qua") or {}
    bt = {b.get("nhan"): b for b in m.get("bien_the") or []}
    tp = kq.get("ti_phan") or {}
    phan = " · ".join("{0} {1:.0%}".format(k, v) for k, v in sorted(tp.items()) if isinstance(v, (int, float)))
    if kq.get("ket_luan") == KL_THANG:
        t = bt.get(kq.get("thang")) or {}
        nd = "A/B bìa {0}: người xem chọn {1} (họ {2}, ý {3}, giám khảo {4}){5}".format(
            m.get("video_id"), kq.get("thang"), t.get("ho") or "?", t.get("ma") or "?", t.get("diem_gk"),
            " — thời gian xem " + phan if phan else "")
    else:
        nd = "A/B bìa {0}: KHÔNG KẾT LUẬN ({1}){2}".format(m.get("video_id"), str(kq.get("ly_do") or "")[:80],
                                                         " — thời gian xem " + phan if phan else "")
    _nao(goc, kenh, m, "ket_qua", nd, so={"id": m.get("id"), "ket": kq.get("ket_luan"), "thang": kq.get("thang"),
                                           "chon": kq.get("chon"), "ti_phan": tp,
                                           "ho": {k: b.get("ho") for k, b in bt.items()},
                                           "diem_gk": {k: b.get("diem_gk") for k, b in bt.items()},
                                           "cap": cap_ab(m)},
         khoa="bia-ab|{0}|ket".format(m.get("id")))


def cap_ab(m: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Cặp thắng/thua của MỘT thử nghiệm đã xong: có nhánh thắng → (thắng, mỗi nhánh khác, trọng số 1); không kết luận
    mà có phần thời gian xem → cặp theo thứ tự phần, trọng số mềm `W_MEM` × min(1, chênh / `CHENH_DU`)."""
    if m.get("trang_thai") != TT_XONG:
        return []
    kq = m.get("ket_qua") or {}
    nh = [b.get("nhan") for b in m.get("bien_the") or [] if b.get("nhan")]
    tp = {k: float(v) for k, v in (kq.get("ti_phan") or {}).items() if isinstance(v, (int, float))}
    ra: List[Dict[str, Any]] = []
    if kq.get("ket_luan") == KL_THANG and kq.get("thang") in nh:
        for j in nh:
            if j != kq["thang"]:
                ra.append({"thang": kq["thang"], "thua": j, "w": 1.0})
        return ra
    co = [k for k in nh if k in tp]
    for i, a in enumerate(co):
        for b in co[i + 1:]:
            d = tp[a] - tp[b]
            if abs(d) > 1e-9:
                ra.append({"thang": a if d > 0 else b, "thua": b if d > 0 else a,
                           "w": round(W_MEM * min(1.0, abs(d) / CHENH_DU), 4)})
    return ra


def thong_ke_ho_ab(goc: str, kenh: str, ds: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Dict[str, float]]:
    """Bằng chứng A/B theo HỌ kiểu chữ của kênh: {họ: {thang, thua (Σ trọng số cặp khác họ), n_thu}} — cặp cùng họ
    không nói gì về họ nên bỏ."""
    ds = doc_so(goc, kenh) if ds is None else ds
    ra: Dict[str, Dict[str, float]] = {}
    for m in ds:
        ho = {b.get("nhan"): str(b.get("ho") or "") for b in m.get("bien_the") or []}
        cap = cap_ab(m)
        if cap:
            for h in {x for x in ho.values() if x}:
                ra.setdefault(h, {"thang": 0.0, "thua": 0.0, "n_thu": 0.0})["n_thu"] += 1
        for c in cap:
            a, b = ho.get(c["thang"]), ho.get(c["thua"])
            if not a or not b or a == b:
                continue
            ra.setdefault(a, {"thang": 0.0, "thua": 0.0, "n_thu": 0.0})["thang"] += c["w"]
            ra.setdefault(b, {"thang": 0.0, "thua": 0.0, "n_thu": 0.0})["thua"] += c["w"]
    return {h: {k: round(v, 3) for k, v in x.items()} for h, x in ra.items()}


def dich_hau_nghiem(ab: Dict[str, Any], h: str, s0: float) -> float:
    """Độ dịch CTR hậu nghiệm của họ `h` do bằng chứng A/B (dùng trong `bia_du_lieu.hau_nghiem`): tỉ lệ thắng co về ½
    (Beta(1,1)), × độ lệch CTR kênh `s0`, × min(1, số cặp / `N_AB_DU`). Không có bằng chứng → 0."""
    x = (ab or {}).get(h) if isinstance(ab, dict) else None
    if not isinstance(x, dict):
        return 0.0
    w, l = float(x.get("thang") or 0), float(x.get("thua") or 0)
    if w + l <= 0:
        return 0.0
    p = (w + 1.0) / (w + l + 2.0)
    return (p - 0.5) * float(s0) * min(1.0, (w + l) / N_AB_DU)


def _cap_nghich(a: Sequence[float], b: Sequence[float]) -> Tuple[int, int]:
    """(cặp thuận, cặp nghịch) giữa hai dãy cùng thứ tự — cặp hoà bị bỏ."""
    t = n = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            x, y = a[i] - a[j], b[i] - b[j]
            if x == 0 or y == 0:
                continue
            if (x > 0) == (y > 0):
                t += 1
            else:
                n += 1
    return t, n


def do_giam_khao(goc: str, kenh_ds: Sequence[str], *, diem: str = "diem_gk") -> Dict[str, Any]:
    """Giám khảo bìa lô ↔ người xem thật trên các thử nghiệm đã xong: `top1` = giám khảo xếp nhất đúng nhánh thắng
    (so với `ngau_nhien` = trung bình 1/số nhánh), `tau` = Kendall τ gộp giữa điểm giám khảo và phần thời gian xem (mọi
    thử nghiệm có phần), `n` = số thử nghiệm có ít nhất một cặp dùng được. Theo kênh + gộp."""
    def mot(ds: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        dung = co_thang = 0
        ngau: List[float] = []
        t = ng = n = 0
        for m in ds:
            if m.get("trang_thai") != TT_XONG:
                continue
            kq = m.get("ket_qua") or {}
            bt = [b for b in m.get("bien_the") or [] if isinstance(b.get(diem), (int, float))]
            if len(bt) < 2:
                continue
            if kq.get("ket_luan") == KL_THANG and kq.get("thang"):
                co_thang += 1
                ngau.append(1.0 / len(bt))
                cao = max(float(b[diem]) for b in bt)
                nhat = [b["nhan"] for b in bt if float(b[diem]) == cao]
                dung += 1 if kq["thang"] in nhat and len(nhat) == 1 else 0
            tp = kq.get("ti_phan") or {}
            co = [b for b in bt if isinstance(tp.get(b.get("nhan")), (int, float))]
            if len(co) >= 2:
                a1, a2 = _cap_nghich([float(b[diem]) for b in co], [float(tp[b["nhan"]]) for b in co])
                if a1 + a2:
                    t, ng, n = t + a1, ng + a2, n + 1
        return {"n": n, "co_thang": co_thang, "top1": round(dung / co_thang, 3) if co_thang else None,
                "ngau_nhien": round(sum(ngau) / len(ngau), 3) if ngau else None,
                "tau": round((t - ng) / float(t + ng), 3) if t + ng else None, "cap": t + ng}
    tat: List[Dict[str, Any]] = []
    kenh: Dict[str, Any] = {}
    for k in kenh_ds:
        ds = doc_so(goc, k)
        tat += ds
        kenh[k] = mot(ds)
    return {"chung": mot(tat), "kenh": kenh, "diem": diem}


# ── A/B tiêu đề nhường (một thử nghiệm mỗi video) ───────────────────────────

def uu_tien_bia(goc: str, kenh: str, vid: str, ma_goi: str = "", bay: Optional[_dt.datetime] = None) -> str:
    """'' = A/B tiêu đề được lập cho video; khác → lý do nhường (video có / sắp có thử nghiệm bìa của máy). Chưa có mục
    mà kênh bật bìa A/B, dùng được A/B, gói có A + ≥ 1 bìa nhì/ba CÓ DẤU → nhường cho phiên kênh kế."""
    try:
        bay = bay or _dt.datetime.now()
        if not doc_cai(goc).get("bat", True) or not bat(_kenh_yaml(goc, kenh)):
            return ""
        so = doc_toan_so(goc, kenh)
        m = muc_cua(so["muc"], vid)
        if m:
            if m.get("trang_thai") in TT_GIU:
                return "video có thử nghiệm bìa A/B ({0}) — bìa ưu tiên, một thử nghiệm mỗi video".format(m["trang_thai"])
            if m.get("trang_thai") == TT_LOI and int(m.get("lan_loi") or 0) < SO_LOI_TOI_DA:
                return "thử nghiệm bìa A/B đang thử lại ({0} lần lỗi)".format(m.get("lan_loi"))
            return ""
        if not ma_goi or thieu_quyen(goc, kenh, bay, so):
            return ""
        bt = bien_the_goi(goc, kenh, ma_goi)
        if len(bt) >= 2 and bt[0]["dau_ok"] and any(b["dau_ok"] for b in bt[1:]) and not _dang_thang(goc, kenh, ma_goi):
            return "chờ phiên kênh đặt thử nghiệm bìa ({0} bìa có dấu) — bìa ưu tiên".format(
                sum(1 for b in bt if b["dau_ok"]))
    except Exception:  # noqa: BLE001 — không đọc được thì không chặn A/B tiêu đề
        return ""
    return ""


# ── tự kiểm ─────────────────────────────────────────────────────────────────

def muc_tu_kiem(goc: str, bay: _dt.datetime, kenh_ds: Sequence[str], *, ghi: bool = True,
                bia_song: Optional[Callable[[str], Optional[List[int]]]] = None,
                van_tay: Optional[Callable[[str], Optional[List[int]]]] = None,
                so_video: Optional[Dict[str, Any]] = None,
                can_kiem: Optional[Callable[[str], bool]] = None) -> List[Dict[str, Any]]:
    """Mục cho `core/tu_kiem` ({khoa, viec, tt dat|hong|cho, bang_chung, kenh, nguoi?, can_lam?}):
    · thử nghiệm còn «đang chạy» quá `NGAY_KET_TU_KIEM` ngày → hỏng (kẹt); · đặt hỏng (lỗi ≥ 2 lần / bỏ sau lỗi) → hỏng;
    · video mới đủ bìa mà quá `GIO_CHUA_DAT_TU_KIEM` giờ chưa có mục (bước phiên không chạy?) → hỏng;
    · kênh bật mà chưa có quyền A/B → việc người (xác minh điện thoại / tính năng nâng cao);
    · bìa thắng YouTube đã áp (chon ≠ A) → bìa i.ytimg.com phải TRÙNG vân tay tấm thắng."""
    ra: List[Dict[str, Any]] = []
    sv = so_video if so_video is not None else _so_video(goc)
    for kenh in kenh_ds:
        if ghi and os.path.isfile(duong_so(goc, kenh)):
            dong_qua_han(goc, kenh, bay)          # cả kênh vừa tắt bia_ab: ván cũ vẫn phải được đóng
        if not bat(_kenh_yaml(goc, kenh)):
            continue
        so = doc_toan_so(goc, kenh)
        q = thieu_quyen(goc, kenh, bay, so)
        if q:
            ra.append({"kenh": kenh, "khoa": "bia_ab:quyen:" + kenh, "tt": "cho", "nguoi": True,
                       "viec": "Thử nghiệm A/B bìa kênh {0}".format(kenh), "bang_chung": q[:200],
                       "can_lam": "youtube.com/verify — xác minh số điện thoại (bật tính năng nâng cao) cho kênh "
                                  "{0} để máy chạy A/B 3 bìa".format(kenh)})
        da = set()
        for m in reversed(so["muc"]):
            vid = str(m.get("video_id") or "")
            if vid in da:
                continue
            da.add(vid)
            tt = m.get("trang_thai")
            viec = "A/B bìa {0}".format(m.get("ma_goi") or vid)
            t0 = _gio(m.get("bat_dau"))
            if tt == TT_DANG and t0 is not None:
                tuoi = (bay - t0).total_seconds() / 86400.0
                ra.append({"kenh": kenh, "khoa": "bia_ab:chay:" + vid, "viec": viec,
                           "tt": "hong" if tuoi > NGAY_KET_TU_KIEM else "dat",
                           "bang_chung": "đang chạy {0:.1f} ngày{1}".format(
                               tuoi, " — KẸT (> {0:g} ngày)".format(NGAY_KET_TU_KIEM) if tuoi > NGAY_KET_TU_KIEM else "")})
            elif tt == TT_LOI and int(m.get("lan_loi") or 0) >= 2 or (tt == TT_BO and int(m.get("lan_loi") or 0) >= 1):
                t = _gio(m.get("cap_nhat"))
                if t and (bay - t).days <= 7:
                    ra.append({"kenh": kenh, "khoa": "bia_ab:dat:" + vid, "viec": viec, "tt": "hong",
                               "bang_chung": "đặt thử nghiệm hỏng {0} lần: {1}".format(m.get("lan_loi"),
                                                                                    str(m.get("ly_do") or "")[:160])})
            elif tt == TT_XONG and (m.get("ket_qua") or {}).get("chon") not in (None, "A") and bia_song and van_tay:
                t = _gio((m.get("ket_qua") or {}).get("luc"))
                if t is None or (bay - t).days > 7:
                    continue
                nh = m["ket_qua"]["chon"]
                khoa = "bia_ab:song:" + vid
                if can_kiem is not None and not can_kiem(khoa):
                    ra.append({"kenh": kenh, "khoa": khoa, "viec": viec + " — bìa đang chạy = bìa {0}".format(nh),
                               "giu": True, "tt": "cho", "bang_chung": ""})
                    continue
                tep = _tep_bien_the(goc, kenh, m, nh)
                mong, song = (van_tay(tep) if tep else None), bia_song(vid)
                d = sum(x != y for x, y in zip(mong, song)) if mong and song and len(mong) == len(song) else None
                ra.append({"kenh": kenh, "khoa": "bia_ab:song:" + vid, "viec": viec + " — bìa đang chạy = bìa {0}".format(nh),
                           "tt": "cho" if d is None else ("dat" if d <= 20 else "hong" if d >= 40 else "cho"),
                           "bang_chung": "không so được bìa i.ytimg.com" if d is None else
                           "bìa i.ytimg.com lệch vân tay {0}/256 so với bìa {1}".format(d, nh)})
        dau = _gio((so.get("meta") or {}).get("phien_dau"))    # chỉ đòi video công khai SAU lần đầu bước phiên chạy
        for v in _video_kenh(goc, kenh, sv) if dau is not None else []:
            tuoi = (bay - v["lich"]).total_seconds() / 3600.0
            if not (GIO_CHUA_DAT_TU_KIEM <= tuoi <= TUOI_MOI_GIO) or v["video_id"] in da or q or v["lich"] < dau:
                continue
            bt = bien_the_goi(goc, kenh, v["ma_goi"])
            abm = _ab_tieu_de_muc(goc, kenh, v["video_id"])
            if len(bt) < 2 or not bt[0]["dau_ok"] or (abm and abm.get("trang_thai") in ("da_dat", "da_co", "xong")):
                continue
            ra.append({"kenh": kenh, "khoa": "bia_ab:chua_dat:" + v["video_id"], "tt": "hong",
                       "viec": "A/B bìa {0}".format(v["ma_goi"]),
                       "bang_chung": "video công khai {0:.0f} giờ, đủ {1} bìa mà chưa đặt thử nghiệm (bước «bìa A/B» "
                                     "của phiên kênh không chạy?)".format(tuoi, len(bt))})
    return ra


# ── dự báo (CHỈ ĐỌC) ────────────────────────────────────────────────────────

def du_bao(goc: str, kenh_ds: Sequence[str], bay: Optional[_dt.datetime] = None, ngay: float = 2.0,
           so_video: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Gói sắp lên (hẹn công khai trong `ngay` ngày tới + vừa công khai ≤ `TUOI_MOI_GIO` giờ) và gói chờ đăng (DONE):
    mỗi gói có mấy bìa qua cổng (A + B/C có dấu), có đặt thử được không và vì sao; ước số nhãn mỗi tuần."""
    bay = bay or _dt.datetime.now()
    sv = so_video if so_video is not None else _so_video(goc)
    cai = doc_cai(goc)
    goi: List[Dict[str, Any]] = []
    for k in kenh_ds:
        bat_k = bat(_kenh_yaml(goc, k))
        q = thieu_quyen(goc, k, bay)
        da = set()
        for v in _video_kenh(goc, k, sv):
            gio = (v["lich"] - bay).total_seconds() / 3600.0
            if not (-TUOI_MOI_GIO <= gio <= ngay * 24):
                continue
            da.add(v["ma_goi"])
            goi.append(_dong_du_bao(goc, k, v["ma_goi"], v["video_id"], v["lich"], gio, bat_k, q))
        try:
            from . import cong_chu  # noqa: PLC0415
            cho = cong_chu.goi_cho_dang(goc, k)
        except Exception:  # noqa: BLE001
            cho = []
        for g in cho:
            ma = str(g.get("ma") or "")
            if ma and ma not in da:
                goi.append(_dong_du_bao(goc, k, ma, "", None, None, bat_k, q))
    n_ok = [g for g in goi if g["se_thu"]]
    so_kenh = len({g["kenh"] for g in goi})
    kenh_thu = sorted({g["kenh"] for g in goi if g["bat"] and not g["quyen"]})
    goi_thu = [g for g in goi if g["kenh"] in kenh_thu]
    ty_le = len(n_ok) / float(len(goi_thu)) if goi_thu else 0.0     # trên gói của kênh thử được
    tuan = 7 * len(kenh_thu)                         # 1 video/ngày/kênh
    return {"luc": _luc(bay), "goi": goi, "so_goi": len(goi), "se_thu": len(n_ok),
            "can_dau_lai": sum(1 for g in goi if g.get("can_dau_lai")), "ty_le_du_bia": round(ty_le, 3),
            "kenh_co_goi": so_kenh, "kenh_thu_duoc": kenh_thu,
            "uoc_tuan": {"video": tuan, "thu_nghiem": round(tuan * ty_le, 1),
                         "cap_so_sanh": round(tuan * ty_le * (sum(min(3, g["so_bia"]) * (min(3, g["so_bia"]) - 1) / 2.0
                                                                  for g in n_ok) / len(n_ok) if n_ok else 0), 1)},
            "cai": {k: cai.get(k) for k in ("bat", "len_lich", "toi_da_dat_phien")}}


def _dong_du_bao(goc: str, kenh: str, ma: str, vid: str, lich: Optional[_dt.datetime], gio: Optional[float],
                 bat_k: bool, q: str) -> Dict[str, Any]:
    bt = bien_the_goi(goc, kenh, ma)
    co_dau = [b["nhan"] for b in bt if b["dau_ok"]]
    so_bia = len(co_dau) if bt and bt[0]["dau_ok"] else 0
    abm = _ab_tieu_de_muc(goc, kenh, vid) if vid else None
    da_co = bool(abm and abm.get("trang_thai") in ("da_dat", "da_co", "xong"))
    thang = _dang_thang(goc, kenh, ma) if vid else ""
    a_ok = bool(bt and bt[0]["dau_ok"])
    ly = ("kênh tắt bia_ab" if not bat_k else q if q else
          "đã có Thử nghiệm A/B tiêu đề" if da_co else "đang thắng" if thang else
          "bìa A chưa có dấu" if not a_ok else "chỉ có bìa A" if len(bt) < 2 else
          "" if so_bia >= 2 else "bìa nhì/ba chưa có dấu — bước phiên đọc lại + đóng dấu bản sao (có thể trượt)")
    duoc = bat_k and not q and not da_co and not thang and a_ok
    return {"kenh": kenh, "ma_goi": ma, "video": bool(vid), "lich": _luc(lich) if lich else "",
            "gio_toi": None if gio is None else round(gio, 1), "bia": [b["nhan"] for b in bt], "co_dau": co_dau,
            "ho": [b.get("ho") for b in bt], "so_bia": so_bia, "bat": bat_k, "quyen": q,
            "se_thu": bool(duoc and so_bia >= 2), "can_dau_lai": bool(duoc and so_bia < 2 and len(bt) >= 2),
            "ly_do": ly}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """`python -X utf8 -m core.bia_ab du-bao [--ngay 2]` — CHỈ ĐỌC: gói sắp lên có mấy bìa qua cổng, ước nhãn/tuần.
    `ke-hoach --kenh K` — việc bước phiên của một kênh (chỉ đọc)."""
    import argparse  # noqa: PLC0415
    ap = argparse.ArgumentParser(prog="core.bia_ab")
    ap.add_argument("lenh", choices=("du-bao", "ke-hoach", "giam-khao"))
    ap.add_argument("--kenh", default="")
    ap.add_argument("--ngay", type=float, default=2.0)
    ap.add_argument("--goc", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    try:
        from .kenh import liet_ke_kenh  # noqa: PLC0415
        kenh_ds = [a.kenh] if a.kenh else liet_ke_kenh(a.goc)
    except Exception:  # noqa: BLE001
        kenh_ds = [a.kenh] if a.kenh else []
    if a.lenh == "ke-hoach":
        for k in kenh_ds:
            kh = ke_hoach(a.goc, k)
            print(json.dumps({x: (kh[x] if x != "dat" else [{y: v.get(y) for y in ("ma_goi", "tuoi_gio", "cong_khai")}
                                                            for v in kh["dat"]]) for x in kh}, ensure_ascii=False,
                             default=str))
        return 0
    if a.lenh == "giam-khao":
        print(json.dumps(do_giam_khao(a.goc, kenh_ds), ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(du_bao(a.goc, kenh_ds, ngay=a.ngay), ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
