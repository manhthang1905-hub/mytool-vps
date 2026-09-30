"""Sổ CHI PHÍ THẬT — `GET /v1/usage` mỗi ngày, đối chiếu với video đã bàn giao.

═══ VÌ SAO CÓ MODULE NÀY ═══

Kiểm toán 29/09/2026: tool KHÔNG lưu chi phí thật ở đâu cả. Dòng "Máy" của
Bảng điều khiển chỉ có `ngan_sach.uoc_tinh_vnd` — một con số ƯỚC TÍNH trước khi
chạy (85.800₫/ngày cho cả ba kênh hôm 28/09), không phải tiền đã tiêu thật. Giá
chữ dùng để ước — `core/uoc_tinh_tool.py:158-159` — là bản chép tay, có thể lệch
xa giá thật (chưa từng đối chiếu).

Máy chủ ShopAPI đã có sẵn số thật: `GET /v1/usage` (`_sdk/shopapi/resources/
usage.py`, đã có bản bọc `core.account.fetch_usage`). Module này KHÔNG viết lại
lời gọi đó — chỉ thêm phần SỔ SÁCH: gọi đúng MỘT lượt cho một ngày, lưu vào đĩa,
và chia ra đ/video bằng cách đối chiếu với số video đã bàn giao trong ngày (đọc
từ `workspace/tu-chay/<ngày>.json`, KHÔNG gọi mạng thêm).

═══ MỘT LƯỢT GỌI MỖI NGÀY ═══

`group_by="day"` cho một cửa sổ đúng MỘT ngày (00:00 → 24:00) đã trả về CẢ hai
thứ cần: tổng tiền ngày đó (`buckets[0]["cost"]`) VÀ chia theo loại dịch vụ
(`buckets[0]["by_type"]`: tts/image/video/music) trong cùng một lượt — khỏi gọi
thêm lần `group_by="type"` nữa. Đây là "MỘT lượt/ngày" nói ở kiểm toán.

`lay_va_luu()` là lượt gọi THẬT — dùng cho lịch mỗi ngày (bên ngoài, do
`core/tu_chay.py`/lịch Windows gọi — module này không tự lên lịch) hoặc gọi tay
qua CLI. `hom_qua()`/`doc_ngay()` chỉ ĐỌC ĐĨA, không mạng — dùng cho Bảng điều
khiển vẽ mỗi lần mở trang mà không tốn thêm lượt hỏi nào (đúng luật 4 CLAUDE.md).

CLI:  ``python -m core.chi_phi --ngay 2026-09-28 2026-09-29``
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .money import format_vnd, parse_micro

__all__ = [
    "ChiPhiNgay", "duong_thu_muc", "duong_file_ngay",
    "so_video_ban_giao_ngay", "goi_usage_ngay", "tinh_chi_phi_ngay",
    "ghi_ngay", "doc_ngay", "lay_va_luu", "hom_qua", "dong_mot_dong",
]

#: "đã bàn giao gói TL1-T7-0007" — câu cố định do `core.ban_giao_dang` (hoặc
#: `core.tu_chay`) ghi vào `tom_tat` của sổ tu-chay, xem
#: `workspace/tu-chay/<ngày>.json`. Không đụng module sinh câu đó (ngoài quyền
#: sở hữu của agent này) — chỉ ĐỌC lại đúng mẫu chữ nó đã ghi.
_MAU_BAN_GIAO = re.compile(r"đã bàn giao gói\s+(\S+)")


def _doc_json(duong: str) -> Optional[Any]:
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            return json.load(tep)
    except (OSError, ValueError):
        return None


def _ghi_json_nguyen_tu(duong: str, du_lieu: Any) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    tam = duong + ".tam"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du_lieu, tep, ensure_ascii=False, indent=1)
    os.replace(tam, duong)


def duong_thu_muc(goc: str) -> str:
    return os.path.join(goc, "workspace", "chi-phi")


def duong_file_ngay(goc: str, ngay: str) -> str:
    return os.path.join(duong_thu_muc(goc), "{0}.json".format(ngay))


def _ngay_hom_qua() -> str:
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════
# Đối chiếu với sổ tu-chay — số video đã bàn giao THẬT trong ngày
# ═══════════════════════════════════════════════════════════════════════════


def so_video_ban_giao_ngay(goc: str, ngay: str) -> int:
    """Đếm số GÓI video đã bàn giao trong ngày ``ngay``, đọc
    `workspace/tu-chay/<ngày>.json` (sổ do `core.tu_chay` ghi mỗi lượt chạy).

    Một gói có thể xuất hiện lại ở lượt chạy sau trong CÙNG ngày (sổ tu-chay
    chạy nhiều lượt/ngày, `tom_tat` của lượt sau có thể lặp câu "đã bàn giao"
    của lượt trước nếu kênh chưa có việc mới) — đếm theo TẬP mã gói, không theo
    số dòng, để không đếm trùng.
    """
    du = _doc_json(os.path.join(goc, "workspace", "tu-chay", "{0}.json".format(ngay)))
    if not isinstance(du, Mapping):
        return 0
    goi: set = set()
    for run in du.get("runs") or []:
        if not isinstance(run, Mapping):
            continue
        for kq in run.get("ket_qua") or []:
            if not isinstance(kq, Mapping):
                continue
            tom_tat = str(kq.get("tom_tat") or "")
            goi.update(_MAU_BAN_GIAO.findall(tom_tat))
    return len(goi)


# ═══════════════════════════════════════════════════════════════════════════
# Gọi máy chủ — MỘT lượt GET /v1/usage cho đúng một ngày
# ═══════════════════════════════════════════════════════════════════════════


def goi_usage_ngay(client: Any, ngay: str) -> Dict[str, Any]:
    """`GET /v1/usage` — CHỈ ĐỌC, không trừ tiền — cho đúng khung giờ của
    ``ngay`` (00:00 → 24:00, giờ máy này). `group_by="day"` để MỘT lượt gọi
    trả về cả tổng ngày lẫn `by_type` (tts/image/video/music) trong cùng
    payload — khỏi gọi thêm lần thứ hai.
    """
    bat_dau = datetime.strptime(ngay, "%Y-%m-%d")
    ket_thuc = bat_dau + timedelta(days=1)
    payload = client.usage.retrieve(
        from_=bat_dau.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        to=ket_thuc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        group_by="day",
    )
    payload = payload.to_dict() if hasattr(payload, "to_dict") else payload
    return payload if isinstance(payload, dict) else {}


def _bucket_ngay(payload: Mapping[str, Any], ngay: str) -> Dict[str, Any]:
    buckets = payload.get("buckets")
    if not isinstance(buckets, (list, tuple)):
        buckets = payload.get("data")
    if not isinstance(buckets, (list, tuple)):
        return {}
    for muc in buckets:
        if isinstance(muc, Mapping) and str(muc.get("key")) == ngay:
            return dict(muc)
    # Cửa sổ đúng một ngày thường chỉ trả về một bucket — nếu máy chủ không
    # gắn đúng nhãn ngày (múi giờ lệch) thì cứ lấy bucket duy nhất, còn hơn
    # bỏ trống một chi phí đã trả tiền để hỏi.
    thuan = [m for m in buckets if isinstance(m, Mapping)]
    return dict(thuan[0]) if len(thuan) == 1 else {}


# ═══════════════════════════════════════════════════════════════════════════
# Sổ sách
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ChiPhiNgay:
    ngay: str
    tong_micro: int
    theo_loai_micro: Dict[str, int] = field(default_factory=dict)
    so_video_api: int = 0        # "usage.videos" máy chủ báo (job video thành công)
    so_video_ban_giao: int = 0   # đếm từ sổ tu-chay (video THẬT đã bàn giao)
    goi_luc: str = ""            # ISO — lúc gọi API, để biết bản ghi cũ hay mới

    @property
    def tong_vnd(self) -> int:
        return self.tong_micro // 1_000_000

    @property
    def so_video_doi_chieu(self) -> int:
        """Ưu tiên số bàn giao THẬT; sổ tu-chay chưa có (VPS mới/chưa chạy) thì
        lùi về số job video máy chủ báo — có còn hơn không, miễn nói rõ nguồn
        (`nguon_so_video`)."""
        return self.so_video_ban_giao or self.so_video_api

    @property
    def nguon_so_video(self) -> str:
        if self.so_video_ban_giao:
            return "sổ tu-chay"
        if self.so_video_api:
            return "job video máy chủ (chưa có sổ tu-chay đối chiếu)"
        return ""

    @property
    def moi_video_micro(self) -> int:
        so = self.so_video_doi_chieu
        return (self.tong_micro // so) if so > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ngay": self.ngay, "tong_micro": self.tong_micro,
            "theo_loai_micro": dict(self.theo_loai_micro),
            "so_video_api": self.so_video_api,
            "so_video_ban_giao": self.so_video_ban_giao,
            "goi_luc": self.goi_luc,
        }

    @classmethod
    def from_dict(cls, du: Mapping[str, Any]) -> "ChiPhiNgay":
        return cls(
            ngay=str(du.get("ngay") or ""),
            tong_micro=int(du.get("tong_micro") or 0),
            theo_loai_micro={str(k): int(v) for k, v in (du.get("theo_loai_micro") or {}).items()},
            so_video_api=int(du.get("so_video_api") or 0),
            so_video_ban_giao=int(du.get("so_video_ban_giao") or 0),
            goi_luc=str(du.get("goi_luc") or ""),
        )

    def dong_mot_dong(self) -> str:
        """Câu ngắn cho Bảng điều khiển: "Chi phí thật hôm qua: X₫ · ~Y₫/video"."""
        moi_video = format_vnd(self.moi_video_micro) if self.so_video_doi_chieu else "?"
        chu = "Chi phí thật {0}: {1} · ~{2}/video".format(
            self.ngay, format_vnd(self.tong_micro), moi_video)
        if self.so_video_doi_chieu and self.nguon_so_video != "sổ tu-chay":
            # Ngày chưa có video nào BÀN GIAO xong (vd. hỏi ngay trong lúc
            # ngày đang chạy dở) — số "video" khi đó là số LƯỢT gọi job video
            # của máy chủ (mỗi video thật cần hàng chục-trăm lượt), không phải
            # số video hoàn chỉnh. Nói rõ ra, đừng để đọc nhầm là giá một video.
            chu += " (ước theo lượt job video máy chủ, chưa có video bàn giao)"
        return chu


def tinh_chi_phi_ngay(goc: str, ngay: str, payload: Mapping[str, Any]) -> ChiPhiNgay:
    """Ghép phản hồi `/v1/usage` (một bucket) với sổ tu-chay — THUẦN, không mạng."""
    bucket = _bucket_ngay(payload, ngay)
    tong_micro = parse_micro(bucket.get("cost")) if bucket.get("cost") is not None else 0
    theo_loai = {}
    for loai, gia in (bucket.get("by_type") or {}).items():
        try:
            theo_loai[str(loai)] = parse_micro(gia)
        except (TypeError, ValueError):
            theo_loai[str(loai)] = 0
    so_video_api = int((bucket.get("usage") or {}).get("videos") or 0)
    return ChiPhiNgay(
        ngay=ngay, tong_micro=tong_micro, theo_loai_micro=theo_loai,
        so_video_api=so_video_api,
        so_video_ban_giao=so_video_ban_giao_ngay(goc, ngay),
        goi_luc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))


def ghi_ngay(goc: str, cs: ChiPhiNgay) -> None:
    _ghi_json_nguyen_tu(duong_file_ngay(goc, cs.ngay), cs.to_dict())


def doc_ngay(goc: str, ngay: str) -> Optional[ChiPhiNgay]:
    """Đọc lại bản đã lưu — KHÔNG gọi mạng. `None` = chưa gọi ngày này lần nào."""
    du = _doc_json(duong_file_ngay(goc, ngay))
    return ChiPhiNgay.from_dict(du) if isinstance(du, Mapping) else None


def lay_va_luu(client: Any, goc: str, ngay: Optional[str] = None) -> ChiPhiNgay:
    """Lượt gọi THẬT: `GET /v1/usage` cho ``ngay`` (mặc định hôm qua), lưu sổ.

    Dùng cho lịch mỗi ngày HOẶC gọi tay (CLI dưới). Không tự lên lịch — nơi gọi
    (lịch Windows / `core/tu_chay.py`, ngoài quyền sở hữu module này) quyết
    định lúc nào gọi.
    """
    ngay = ngay or _ngay_hom_qua()
    payload = goi_usage_ngay(client, ngay)
    cs = tinh_chi_phi_ngay(goc, ngay, payload)
    ghi_ngay(goc, cs)
    return cs


def hom_qua(goc: str) -> Optional[ChiPhiNgay]:
    """Bản đã lưu của hôm qua — cho Bảng điều khiển vẽ, KHÔNG gọi mạng."""
    return doc_ngay(goc, _ngay_hom_qua())


def dong_mot_dong(goc: str) -> str:
    """Chuỗi rỗng nếu chưa có sổ ngày nào — Bảng điều khiển tự ẩn dòng đó."""
    cs = hom_qua(goc)
    return cs.dong_mot_dong() if cs else ""


# ═══════════════════════════════════════════════════════════════════════════
# CLI — gọi tay
# ═══════════════════════════════════════════════════════════════════════════


def _in_bang(cac_ngay: Sequence[ChiPhiNgay]) -> None:
    print()
    print("{0:<12} {1:>14} {2:>10} {3:>14}   {4}".format(
        "Ngày", "Tổng", "Video", "đ/video", "Theo loại"))
    print("-" * 78)
    for cs in cac_ngay:
        theo_loai = ", ".join(
            "{0}: {1}".format(loai, format_vnd(micro))
            for loai, micro in sorted(cs.theo_loai_micro.items(), key=lambda kv: -kv[1]))
        moi_video = format_vnd(cs.moi_video_micro) if cs.so_video_doi_chieu else "?"
        so_video_chu = str(cs.so_video_doi_chieu or "?")
        if cs.so_video_doi_chieu and cs.nguon_so_video != "sổ tu-chay":
            so_video_chu += "*"  # * = job video, chưa có video bàn giao xong
        print("{0:<12} {1:>14} {2:>10} {3:>14}   {4}".format(
            cs.ngay, format_vnd(cs.tong_micro), so_video_chu, moi_video, theo_loai))
    if any(cs.so_video_doi_chieu and cs.nguon_so_video != "sổ tu-chay" for cs in cac_ngay):
        print("* = chưa có video bàn giao xong trong ngày đó, số video là lượt "
              "job video máy chủ (một video thật cần hàng chục-trăm lượt).")
    print()
    tong = sum(cs.tong_micro for cs in cac_ngay)
    so_video = sum(cs.so_video_doi_chieu for cs in cac_ngay)
    dong_nhat = all(cs.nguon_so_video in ("sổ tu-chay", "") for cs in cac_ngay)
    if so_video and dong_nhat:
        print("Cộng {0} ngày: {1} · {2} video bàn giao · ~{3}/video".format(
            len(cac_ngay), format_vnd(tong), so_video,
            format_vnd(tong // so_video)))
    else:
        print("Cộng {0} ngày: {1} (không cộng đ/video — có ngày lẫn video "
              "bàn giao với lượt job video, hai đơn vị khác nhau).".format(
                  len(cac_ngay), format_vnd(tong)))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    parser = argparse.ArgumentParser(
        prog="python -m core.chi_phi",
        description="Gọi THẬT GET /v1/usage (chỉ đọc, không trừ tiền) cho một "
                    "hoặc nhiều ngày, lưu vào workspace/chi-phi/ và in bảng.")
    parser.add_argument("--ngay", nargs="+", metavar="YYYY-MM-DD", default=None,
                        help="Một hoặc nhiều ngày (mặc định: hôm qua).")
    parser.add_argument("--goc", default=os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), help="Thư mục gốc MyTool (mặc định: tự dò).")
    args = parser.parse_args(argv)

    from .config import load_config  # noqa: PLC0415
    from .api import build_client  # noqa: PLC0415

    goc = args.goc
    cfg = load_config(os.path.join(goc, "config.json"))
    if not cfg.api_key:
        print("Chưa có api_key trong config.json — không gọi được.")
        return 1
    client = build_client(cfg)
    try:
        cac_ngay = args.ngay or [_ngay_hom_qua()]
        ket_qua = [lay_va_luu(client, goc, ngay) for ngay in cac_ngay]
    finally:
        client.close()
    _in_bang(ket_qua)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
