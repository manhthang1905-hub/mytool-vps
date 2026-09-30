"""`nghien-cuu/` chỉ được để LỌT đúng một tệp: `tuyen.csv`.

Thư mục ấy chở hai thứ khác hẳn nhau:

* `content.csv`, `doi-thu.txt` — **sổ đối thủ**: link, view, ngày đăng của
  từng video đối thủ. Dữ liệu kinh doanh, kho này công khai nên không được lên.
* `tuyen.csv` — **bản đồ tệp khán giả**: các kiểu người xem của ngành, kèm
  insight và cửa vào. Khuôn sản xuất, cùng họ với `prompt/`. Thiếu nó thì tính
  năng tuyến của tab Nghiên cứu vô dụng với mọi khách nhân bản kênh mẫu.

Bài này canh cả hai chiều vì luật ấy **mong manh theo đúng nghĩa kỹ thuật**:
git không cho re-include một tệp khi THƯ MỤC CHA đã bị loại. Viết
`CHANNEL/*/nghien-cuu/` (có gạch chéo cuối) rồi `!.../tuyen.csv` thì dòng phủ
định im lặng không ăn — không lỗi, không cảnh báo, chỉ là bản đồ không bao giờ
tới được máy khách. Phải viết `nghien-cuu/*` mới đúng.

Ngược lại, sửa hớ tay thành `nghien-cuu/` trần là **sổ đối thủ lên kho công
khai** — hỏng nặng hơn nhiều, và cũng không có tiếng động nào.
"""

from __future__ import annotations

import os
import subprocess

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bi_bo_qua(duong: str) -> bool:
    """`git check-ignore` nói tệp này có bị `.gitignore` bỏ qua không."""
    # `--no-index` kiểm đúng LUẬT cho cả tệp từng được theo dõi từ bản cũ.
    # Không có cờ này, Git luôn trả "không bị bỏ qua" cho tệp đã tracked dù
    # pattern mới đã chặn đúng mọi bản phát sinh về sau.
    ket = subprocess.run(["git", "check-ignore", "-q", "--no-index", duong],
                         cwd=GOC, capture_output=True)
    if ket.returncode not in (0, 1):
        pytest.skip("không chạy được git check-ignore ở đây")
    return ket.returncode == 0


@pytest.mark.parametrize("ten", [
    "content.csv",          # sổ đối thủ — link/view/ngày đăng của đối thủ
    "doi-thu.txt",          # danh sách kênh đối thủ
    "BAN-DO-TEP-KHAN-GIA.md",   # phân tích thị trường của chủ dự án
    "anh/abc.jpg",          # ảnh thumbnail tải về
])
def test_du_lieu_kinh_doanh_KHONG_len_kho(ten):
    assert _bi_bo_qua("CHANNEL/TL4-T7/nghien-cuu/" + ten), (
        "{0} là dữ liệu kinh doanh của khách — kho này công khai".format(ten))


# ── Từ 30/09/2026 (kho chung mytool-vps, `.gitignore` DANH SÁCH TRẮNG): thư mục
# kênh THẬT không lên kho NỮA — kể cả `tuyen.csv`. Bản đồ tuyến dùng chung đi
# theo KHUÔN (`CHANNEL/_KHUON/`) và hồ sơ ngách (`CHANNEL/_NHOM/*/ngach.yaml`).

def test_ban_do_tuyen_cua_kenh_that_KHONG_len_kho():
    assert _bi_bo_qua("CHANNEL/TL4-T7/nghien-cuu/tuyen.csv")
    assert _bi_bo_qua("CHANNEL/timelapse/nghien-cuu/tuyen.csv")


def test_khuon_va_ho_so_ngach_CO_len_kho():
    assert not _bi_bo_qua("CHANNEL/_KHUON/nghien-cuu/tuyen.csv"), (
        "khuôn dùng chung phải đi theo kho; nếu đỏ, xem dòng `!/CHANNEL/_KHUON/`")
    assert not _bi_bo_qua("CHANNEL/_NHOM/tam-ly-nhat/ngach.yaml")
    assert not _bi_bo_qua("CHANNEL/_NHOM/tam-ly-nhat/INSIGHT-CHON-CONTENT.md")
    assert _bi_bo_qua("CHANNEL/_NHOM/tam-ly-nhat/bang-nhom.csv")
    assert _bi_bo_qua("CHANNEL/_NHOM/tam-ly-nhat/nghien-cuu/kenh-do.json")
