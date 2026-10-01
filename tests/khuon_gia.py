"""Khuôn tạo kênh GIẢ cho bài kiểm (`core/khuon.py`, hộp "Tạo kênh mới") — không phụ thuộc máy.

Kho không mang dữ liệu khuôn ba mảnh (`CHANNEL/_KHUON/nganh|ve|van-hoa|chien-luoc`) — mỗi VPS tự soạn
bằng hộp "Sửa khuôn", hoặc dùng `python -m core.khoi_tao_ngach`. Bài kiểm vì thế dựng một bộ khuôn
tối thiểu nhưng ĐỦ LUẬT (16 khoá vẽ, 5 khoá văn hoá + bộ số theo tiếng, ảnh nhân vật, lời nhắc bắt
buộc, hai chiến lược đè lời nhắc) ngay trong thư mục tạm.

`dung(goc)` → đường `CHANNEL/_KHUON/` vừa dựng. Mọi giá trị một dòng, không nháy kép/gạch ngược
(đúng luật `khuon._dong_yaml`).
"""

from __future__ import annotations

import base64
import io
import os

from core.khuon import KHOA_VAN_HOA, KHOA_VE

#: PNG 1×1 hợp lệ — ảnh nhân vật mẫu của bộ vẽ giả.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

NGANH = "tam-ly"
VE = ("ao-len-than", "phan-bang-den", "but-chi")
VAN_HOA = {
    "ja": {"ten": "Nhật Bản", "ngon_ngu": "ja", "ky_tu_moi_phut": 298, "chu_bia_hoa": False},
    "vi": {"ten": "Việt Nam", "ngon_ngu": "vi", "ky_tu_moi_phut": 832, "chu_bia_hoa": True},
    "en": {"ten": "Anh — Mỹ", "ngon_ngu": "en", "ky_tu_moi_phut": 920, "chu_bia_hoa": True},
}
LOI_NHAC_NGANH = {
    "1-tieu-de.md": "Đặt tiêu đề bằng <<LANGUAGE>> cho: <<COMPETITOR_TITLE>>\nTITLE: <tiêu đề>\n",
    "2-viet.md": "Viết lại kịch bản bằng <<NGON_NGU>>, khoảng <<CHARS>> ký tự.\n\n<<COMPETITOR_TRANSCRIPT>>\n",
    "3-sua.md": "Rà soát kịch bản bằng <<NGON_NGU>> — mỗi câu một dòng.\n\n<<DRAFT>>\n",
    "6-seo.md": "Viết mô tả SEO bằng <<LANGUAGE>> cho <<TITLE>>.\nDESCRIPTION:\nHASHTAGS:\nKEYWORDS:\n",
    "7-canh.md": "Chia cảnh cho kịch bản, mỗi cảnh một lời tả ảnh.\n\n<<DRAFT>>\n",
    "8-thumbnail.md": "Viết 3 lời nhắc ảnh bìa cho <<TITLE>> — <<THUMB>>.\n",
}
CHIEN_LUOC = {
    "cover": ({"ten": "Cover — hay hơn bản gốc", "mo_ta": "Mổ bản gốc rồi dựng lại cho giữ người tốt hơn",
               "can_ban_goc": True},
              {"2-viet.md": "Viết bản HAY HƠN bằng <<NGON_NGU>> theo phân tích:\n<<PHAN_TICH>>\n",
               "2a-phan-tich.md": "Đọc bản gốc: HAY ở chỗ nào, CHƯA HAY ở chỗ nào.\n<<COMPETITOR_TRANSCRIPT>>\n",
               "3-sua.md": "Bản này ĐÃ HAY HƠN BẢN GỐC CHƯA? Sửa theo phân tích.\n<<PHAN_TICH>>\n<<DRAFT>>\n"}),
    "sang-tao": ({"ten": "Sáng tạo — không cần bản gốc", "mo_ta": "Tự viết từ ý tưởng", "can_ban_goc": False},
                 {"2-viet.md": "Triển khai ý tưởng thành kịch bản bằng <<NGON_NGU>>.\n<<IDEA>>\n",
                  "3-sua.md": "Rà soát cho đọc thành tiếng tự nhiên.\n<<DRAFT>>\n"}),
}


def _ghi(duong: str, chu: str) -> None:
    os.makedirs(os.path.dirname(duong), exist_ok=True)
    with io.open(duong, "w", encoding="utf-8", newline="\n") as tep:
        tep.write(chu)


def _yaml(cap) -> str:
    dong = []
    for k, v in cap.items():
        if isinstance(v, bool):
            dong.append("{0}: {1}".format(k, "true" if v else "false"))
        elif isinstance(v, (int, float)):
            dong.append("{0}: {1}".format(k, v))
        else:
            dong.append('{0}: "{1}"'.format(k, v))
    return "\n".join(dong) + "\n"


def dung(goc: str) -> str:
    """Dựng `CHANNEL/_KHUON/` giả trong `goc` (ghi thêm, không xoá thứ đang có). Trả đường thư mục."""
    khuon = os.path.join(goc, "CHANNEL", "_KHUON")
    _ghi(os.path.join(khuon, "nganh", NGANH, "nganh.yaml"), _yaml({
        "ten": "Tâm lý", "mo_ta": "Chân dung một kiểu người, giải thích bằng tâm lý học",
        "phut_muc_tieu": 12, "engine": "veo3", "so_thumbnail": 3, "mo_hinh": "claude-sonnet-5",
        "dot_phu_de": False, "am_luong_nhac": 0.12}))
    for ten, chu in LOI_NHAC_NGANH.items():
        _ghi(os.path.join(khuon, "nganh", NGANH, "prompt", ten), chu)
    for i, ma in enumerate(VE):
        cap = {"ten": "Bộ vẽ {0}".format(i + 1), "mo_ta": "Nét vẽ phẳng mẫu số {0}".format(i + 1)}
        cap.update({k: "{0} of style {1}".format(k, ma) for k in KHOA_VE})
        _ghi(os.path.join(khuon, "ve", ma, "ve.yaml"), _yaml(cap))
        with open(os.path.join(khuon, "ve", ma, "nv1.png"), "wb") as tep:
            tep.write(PNG_1X1 + ma.encode("ascii"))   # mỗi bộ một ảnh KHÁC byte
    for ma, so in VAN_HOA.items():
        cap = {"ten": so["ten"], "mo_ta": "Khán giả {0}".format(so["ten"])}
        cap.update({k: "{0} for {1} viewers".format(k, so["ten"]) for k in KHOA_VAN_HOA})
        cap.update({"ngon_ngu": so["ngon_ngu"], "giong_van": "natural, warm",
                    "ky_tu_moi_phut": so["ky_tu_moi_phut"], "chu_bia_hoa": so["chu_bia_hoa"],
                    "ghi_chu_do_dai": "Số mẫu của bài kiểm."})
        _ghi(os.path.join(khuon, "van-hoa", ma + ".yaml"), _yaml(cap))
    for ma, (cai, loi_nhac) in CHIEN_LUOC.items():
        _ghi(os.path.join(khuon, "chien-luoc", ma, "chien-luoc.yaml"), _yaml(cai))
        for ten, chu in loi_nhac.items():
            _ghi(os.path.join(khuon, "chien-luoc", ma, ten), chu)
    return khuon
