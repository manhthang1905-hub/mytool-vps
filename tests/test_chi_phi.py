"""`core.chi_phi` — sổ chi phí THẬT, ghép `GET /v1/usage` với sổ tu-chay.

Không gọi mạng: bài kiểm tự dựng `payload` giả đúng khuôn `/v1/usage`
(`buckets`/`by_type`, xem `core/account.fetch_usage`) và sổ tu-chay giả trong
`tmp_path`. Lượt gọi mạng THẬT chỉ chạy khi gõ tay `python -m core.chi_phi`.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chi_phi  # noqa: E402


def _payload(ngay: str, cost: str, videos: int, by_type=None) -> dict:
    return {
        "object": "usage", "group_by": "day",
        "buckets": [{
            "key": ngay, "label": ngay, "jobs": 10, "succeeded": 9, "failed": 1,
            "cost": cost, "spend": cost,
            "usage": {"characters": 0, "audio_seconds": 0, "images": 0, "videos": videos},
            "by_type": by_type or {},
        }],
    }


def _ghi_tu_chay(goc: str, ngay: str, goi_da_bao: list) -> None:
    thu_muc = os.path.join(goc, "workspace", "tu-chay")
    os.makedirs(thu_muc, exist_ok=True)
    runs = []
    for ma_goi in goi_da_bao:
        runs.append({"ket_qua": [{"kenh": ma_goi.split("-")[0], "ok": True,
                                  "tom_tat": "đã bàn giao gói {0} — xong.".format(ma_goi)}]})
    with open(os.path.join(thu_muc, "{0}.json".format(ngay)), "w", encoding="utf-8") as tep:
        json.dump({"ngay": ngay, "runs": runs}, tep, ensure_ascii=False)


def test_so_video_ban_giao_dem_theo_tap_khong_trung(tmp_path):
    goc = str(tmp_path)
    # Cùng một gói xuất hiện lại ở lượt chạy sau trong ngày (kênh chưa có việc
    # mới, sổ lặp câu cũ) — phải đếm MỘT, không phải hai.
    _ghi_tu_chay(goc, "2026-09-28", ["TL1-T7-0007", "TL1-T7-0007", "TL2-T7-0003"])
    assert chi_phi.so_video_ban_giao_ngay(goc, "2026-09-28") == 2


def test_so_video_ban_giao_ngay_khong_co_so_tra_ve_0(tmp_path):
    assert chi_phi.so_video_ban_giao_ngay(str(tmp_path), "2026-09-28") == 0


def test_tinh_chi_phi_ngay_uu_tien_ban_giao_that(tmp_path):
    goc = str(tmp_path)
    _ghi_tu_chay(goc, "2026-09-28", ["TL1-T7-0007"])
    payload = _payload("2026-09-28", "58733909411", 149,
                       {"tts": "5883909411", "image": "8150000000", "video": "44700000000"})
    cs = chi_phi.tinh_chi_phi_ngay(goc, "2026-09-28", payload)
    assert cs.tong_micro == 58733909411
    assert cs.so_video_api == 149
    assert cs.so_video_ban_giao == 1
    # Có sổ tu-chay: đ/video chia cho video BÀN GIAO thật, không phải job API.
    assert cs.so_video_doi_chieu == 1
    assert cs.moi_video_micro == 58733909411
    assert cs.nguon_so_video == "sổ tu-chay"


def test_tinh_chi_phi_ngay_lui_ve_job_api_khi_chua_ban_giao(tmp_path):
    goc = str(tmp_path)  # không có sổ tu-chay ngày này
    payload = _payload("2026-09-29", "70911000000", 188)
    cs = chi_phi.tinh_chi_phi_ngay(goc, "2026-09-29", payload)
    assert cs.so_video_ban_giao == 0
    assert cs.so_video_doi_chieu == 188
    assert cs.nguon_so_video != "sổ tu-chay"
    assert "chưa có video bàn giao" in cs.dong_mot_dong()


def test_ghi_va_doc_lai_khong_mang(tmp_path):
    goc = str(tmp_path)
    cs = chi_phi.ChiPhiNgay(ngay="2026-09-28", tong_micro=58733909411,
                            theo_loai_micro={"video": 44700000000}, so_video_api=149,
                            so_video_ban_giao=1, goi_luc="2026-09-29T11:19:18Z")
    chi_phi.ghi_ngay(goc, cs)
    assert os.path.isfile(chi_phi.duong_file_ngay(goc, "2026-09-28"))
    lai = chi_phi.doc_ngay(goc, "2026-09-28")
    assert lai == cs

    # Ghi nguyên tử: không để lại tệp .tam rơi vãi.
    assert not os.path.isfile(chi_phi.duong_file_ngay(goc, "2026-09-28") + ".tam")


def test_doc_ngay_chua_co_so_tra_ve_none(tmp_path):
    assert chi_phi.doc_ngay(str(tmp_path), "2026-09-28") is None


def test_dong_mot_dong_rong_khi_chua_co_so(tmp_path):
    assert chi_phi.dong_mot_dong(str(tmp_path)) == ""


def test_lay_va_luu_goi_client_dung_mot_luot_va_ghi_so(tmp_path, monkeypatch):
    goc = str(tmp_path)
    _ghi_tu_chay(goc, "2026-09-28", ["TL1-T7-0007"])

    so_lan_goi = {"n": 0}

    class _UsageGia:
        def retrieve(self, *, from_=None, to=None, group_by=None):
            so_lan_goi["n"] += 1
            assert group_by == "day"  # MỘT lượt group_by=day, không gọi thêm group_by=type
            return _payload("2026-09-28", "58733909411", 149,
                            {"video": "44700000000"})

    class _ClientGia:
        usage = _UsageGia()

    cs = chi_phi.lay_va_luu(_ClientGia(), goc, "2026-09-28")
    assert so_lan_goi["n"] == 1
    assert cs.tong_micro == 58733909411
    lai = chi_phi.doc_ngay(goc, "2026-09-28")
    assert lai is not None and lai.tong_micro == 58733909411


def test_hom_qua_doc_dung_ngay(tmp_path, monkeypatch):
    import datetime

    goc = str(tmp_path)
    hom_qua = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    cs = chi_phi.ChiPhiNgay(ngay=hom_qua, tong_micro=1_000_000, so_video_ban_giao=1)
    chi_phi.ghi_ngay(goc, cs)
    lai = chi_phi.hom_qua(goc)
    assert lai is not None and lai.ngay == hom_qua
