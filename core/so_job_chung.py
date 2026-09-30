"""core/so_job_chung.py — bộ đệm sổ job ShopAPI TOÀN MÁY (liên tiến trình).

═══ MODULE THUẦN — CHƯA NỐI VÀO LUỒNG SỐNG ═══

Việc 1.6 (phần 1) của `workspace/LO-TRINH-PHAT-HANH-V3.md` (Đợt 1, BẮT BUỘC
xong trước Việc 1.4). Cách nối vào `core/auto_khau.py::SoTheoDoi` (Việc 1.3b)
ghi ở `workspace/ban-va/2026-09-29-dot1-khe-uu-tien/GHI-CHU.md`.

═══ VÌ SAO CẦN THÊM MỘT LỚP ĐỆM NỮA ═══

`core/auto_khau.py::SoTheoDoi` đã gom việc hỏi job về MỘT LUỒNG cho mỗi TIẾN
TRÌNH (xem docstring lớp đó): mở 100 job trong cùng một khâu chỉ tốn một luồng
hỏi `GET /v1/jobs` mỗi ~30 giây. Nhưng Đợt 1 mở song song NHIỀU TIẾN TRÌNH
(lớp "api", `core/khe.py`) — mỗi tiến trình lại tự dựng `SoTheoDoi` RIÊNG, nên
N tiến trình vẫn ra N luồng hỏi độc lập, mỗi luồng 30 giây một lần: tổng lượt
hỏi tăng thẳng theo N, đúng thứ CLAUDE.md luật 4 cấm.

Module này thêm một tầng NGOÀI tiến trình: nhiều tiến trình muốn biết "job nào
đã xong" thì chỉ MỘT tiến trình thật sự gọi mạng (khoá tệp `so-job.lock`,
`O_CREAT|O_EXCL` — ai tạo được thì làm "người hỏi"), ghi kết quả vào đệm dùng
chung `so-job.json` (nguyên tử, kèm thời điểm ghi). Tiến trình khác đọc đệm
nếu còn TƯƠI (<35 giây); hết tươi thì tranh làm người hỏi tiếp — KHÔNG BAO GIỜ
tự gọi mạng khi thua tranh, chỉ chờ đệm được người thắng ghi mới rồi đọc lại.
Nhờ vậy tổng lượt `GET /v1/jobs` toàn máy giữ nguyên ~1 lần/30 giây bất kể có
bao nhiêu tiến trình đang chờ.

Cách hỏi bên trong `_hoi_that()` LẶP LẠI đúng cách `SoTheoDoi._mot_luot()` hỏi:
`client.jobs.list(status=..., limit=..., cursor=...)` phân trang cho cả hai
trạng thái `succeeded`/`failed` — không dùng `jobs.get` từng cái (SDK ghi rõ
`jobs.get` tốn ~200 lần so với `jobs.list` một lượt ở phía máy chủ).

Không mạng thật ở đây — `client` là seam do nơi gọi truyền vào (SDK thật hoặc
đồ giả trong bài kiểm).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, Iterable, Optional

from . import khe
from .ghi_dia import ghi_json

__all__ = [
    "NHIP_HOI_TOI_THIEU_GIAY", "TUOI_TUOI_GIAY", "TRANG_THAI_MAC_DINH",
    "duong_khoa", "duong_dem", "lay",
]

#: Luật CLAUDE.md 4: không hỏi dày hơn 30 giây — mốc chốt vì job nhanh nhất
#: cũng đã 30 giây. Hằng này chỉ để tài liệu hoá; nhịp hỏi THẬT do đệm tự nhiên
#: tạo ra (đệm tươi 35 giây thì không ai hỏi lại trong vòng đó).
NHIP_HOI_TOI_THIEU_GIAY = 30.0

#: Đệm còn "tươi" dưới ngần này giây — rộng hơn nhịp hỏi tối thiểu một chút để
#: một lượt hỏi hơi chậm (mạng lag) không làm hai tiến trình cùng tưởng đệm cũ
#: rồi cùng tranh hỏi lại ngay lập tức.
TUOI_TUOI_GIAY = 35.0

TRANG_THAI_MAC_DINH = ("succeeded", "failed")
_SO_MOI_TRANG_MAC_DINH = 200
_CHO_MAC_DINH_GIAY = 10.0
_BUOC_CHO_MAC_DINH_GIAY = 0.05
_TEN_TEP_KHOA = "so-job.lock"
_TEN_TEP_DEM = "so-job.json"


def duong_khoa(goc: str) -> str:
    return os.path.join(goc, "workspace", "khe", _TEN_TEP_KHOA)


def duong_dem(goc: str) -> str:
    return os.path.join(goc, "workspace", "khe", _TEN_TEP_DEM)


def _doc_json(duong: str) -> Optional[Dict[str, Any]]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            du = json.load(tep)
        return du if isinstance(du, dict) else None
    except (OSError, ValueError):
        return None


def _dem_con_tuoi(dem: Optional[Dict[str, Any]], bay_gio: float,
                  tuoi_toi_da: float) -> bool:
    if not dem:
        return False
    try:
        return (bay_gio - float(dem.get("luc_ghi", 0.0))) < tuoi_toi_da
    except (TypeError, ValueError):
        return False


def _tao_khoa(duong: str) -> bool:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    try:
        fd = os.open(duong, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as tep:
        json.dump({"pid": os.getpid(), "bat_dau": time.time()}, tep)
    return True


def _khoa_da_chet(duong: str) -> bool:
    du = _doc_json(duong)
    if du is None:
        return True
    try:
        pid = int(du.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    return not khe.pid_con_song(pid)


def _nha_khoa(duong: str) -> None:
    du = _doc_json(duong)
    if du is not None:
        try:
            if int(du.get("pid") or 0) != os.getpid():
                return
        except (TypeError, ValueError):
            return
    khe.xoa_tep_ben_vung(duong)


def _ma_job(goi: Dict[str, Any]) -> str:
    return str(goi.get("id") or goi.get("job_id") or goi.get("ma") or "")


def _hoi_that(client: Any, trang_thai_can_hoi: Iterable[str],
             so_moi_trang: int, so_trang_toi_da: Optional[int] = None
             ) -> Dict[str, Dict[str, Any]]:
    """Giống hệt cách `SoTheoDoi._mot_luot` hỏi: `jobs.list` theo từng trạng
    thái, phân trang bằng cursor — KHÔNG dùng `jobs.get` từng cái.

    `so_trang_toi_da` (29/09/2026, khi nối vào `SoTheoDoi`): trần số trang MỖI
    trạng thái, như `auto_khau.TRANG_MOI_LUOT` — tài khoản có hàng nghìn job cũ
    thì không được lật hết cả sổ mỗi 30 giây; job đang chờ luôn nằm ở đầu sổ,
    job lọt khỏi trần đã có lưới `_hoi_rieng` của `SoTheoDoi`."""
    ket_qua: Dict[str, Dict[str, Any]] = {}
    for trang_thai in trang_thai_can_hoi:
        con_tro = None
        so_trang = 0
        while True:
            so_trang += 1
            trang = client.jobs.list(status=trang_thai, limit=so_moi_trang,
                                     cursor=con_tro)
            trang = trang if isinstance(trang, dict) else dict(trang)
            for muc in (trang.get("data") or []):
                muc = muc if isinstance(muc, dict) else dict(muc)
                ma = _ma_job(muc)
                if ma:
                    ket_qua[ma] = muc
            con_tro = trang.get("next_cursor")
            if not trang.get("has_more") or not con_tro:
                break
            if so_trang_toi_da is not None and so_trang >= so_trang_toi_da:
                break
    return ket_qua


def lay(goc: str, client: Any, *,
       trang_thai_can_hoi: Iterable[str] = TRANG_THAI_MAC_DINH,
       so_moi_trang: int = _SO_MOI_TRANG_MAC_DINH,
       so_trang_toi_da: Optional[int] = None,
       gio_ham: Callable[[], float] = time.time,
       ngu: Callable[[float], None] = time.sleep,
       tuoi_toi_da: float = TUOI_TUOI_GIAY,
       cho_toi_da: float = _CHO_MAC_DINH_GIAY,
       buoc_cho: float = _BUOC_CHO_MAC_DINH_GIAY) -> Dict[str, Any]:
    """Trả `{"jobs": {ma: goi}, "luc_ghi": <thời điểm ghi đệm>}`.

    Đệm còn tươi (<`tuoi_toi_da` giây) -> đọc thẳng, KHÔNG gọi `client`.
    Đệm cũ -> tranh khoá làm người hỏi; giành được thì gọi `client` (kiểu
    `jobs.list`, xem `_hoi_that`) rồi ghi đệm mới. Thua tranh (khoá đang có
    người giữ VÀ còn sống) thì CHỜ đệm tươi lên (poll `buoc_cho` giây một lần,
    tối đa `cho_toi_da` giây) rồi đọc lại — không tự gọi `client`, để tổng lượt
    hỏi toàn máy không tăng theo số tiến trình. Hết giờ chờ mà đệm vẫn cũ thì
    trả đệm hiện có (dù cũ) — thà một nhịp hơi cũ còn hơn tăng lượt hỏi.

    `gio_ham`/`ngu` là seam cho bài kiểm (đồng hồ giả + không ngủ thật).
    """
    duong_d = duong_dem(goc)
    duong_k = duong_khoa(goc)
    bay_gio = gio_ham()
    dem = _doc_json(duong_d)
    if _dem_con_tuoi(dem, bay_gio, tuoi_toi_da):
        return dem

    if _tao_khoa(duong_k):
        try:
            jobs = _hoi_that(client, trang_thai_can_hoi, so_moi_trang, so_trang_toi_da)
            dem_moi = {"jobs": jobs, "luc_ghi": gio_ham()}
            ghi_json(duong_d, dem_moi, indent=None)
            return dem_moi
        finally:
            _nha_khoa(duong_k)

    het_han = bay_gio + max(0.0, cho_toi_da)
    while True:
        if _khoa_da_chet(duong_k):
            khe.xoa_tep_ben_vung(duong_k)
            return lay(goc, client, trang_thai_can_hoi=trang_thai_can_hoi,
                      so_moi_trang=so_moi_trang, so_trang_toi_da=so_trang_toi_da,
                      gio_ham=gio_ham, ngu=ngu,
                      tuoi_toi_da=tuoi_toi_da, cho_toi_da=cho_toi_da,
                      buoc_cho=buoc_cho)
        dem = _doc_json(duong_d)
        if _dem_con_tuoi(dem, gio_ham(), tuoi_toi_da):
            return dem
        if gio_ham() >= het_han:
            break
        ngu(buoc_cho)
    return dem or {"jobs": {}, "luc_ghi": 0.0}
