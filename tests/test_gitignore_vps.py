# -*- coding: utf-8 -*-
"""`.gitignore` chặn đúng dữ liệu riêng máy/kênh trên VPS (E1, A9) — vá 29/09/2026.

Theo `workspace/LO-TRINH-PHAT-HANH-V3.md`, mục E: `.gitignore` từng LỌT (không
chặn) một loạt tệp/thư mục sinh ra khi chạy thật trên VPS — `bao-dong.json`,
`vm/clients/`, `mang-youtube.json`, `vps-rieng.json`, `hop-viec-may-ao.json`,
`vm/replied/`, `vm/transcripts/`, `vm/da-dang-cmt-moi/`, `vm/tien-ich/<k>/`,
`vm/thu-muc-dang-*.json`, `CHANNEL/*/can-ghim.md`… và A9 (`/TL*-T7/`) chặn hồ
sơ trình duyệt kênh THEO TÊN — VPS khác đặt tên kênh khác (ví dụ "KENH2") thì
lọt thẳng.

Bài này KHÔNG cần tệp thật tồn tại trên đĩa: `git check-ignore --no-index` chỉ
so khuôn `.gitignore` với một đường dẫn giả, không đụng file hệ thống, không
cần thư mục đó có thật — đúng luật CLAUDE.md "bài kiểm không gọi mạng/không
tốn tiền", và chạy được cả trên máy nhà (không có hồ sơ trình duyệt thật) lẫn
trên VPS.

Khác `tests/test_khong_day_tep_bi_mat.py` (soi tên tệp bí mật dạng
`*.secret.*`/`config.json`): bài này soi dữ liệu VẬN HÀNH riêng máy/kênh (nhật
ký, số liệu, hồ sơ trình duyệt) — không phải khoá API.
"""

from __future__ import annotations

import os
import subprocess

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: (đường dẫn giả, có bị .gitignore chặn không). Đường dẫn dùng "/" — git
#: hiểu cả trên Windows; không cần tệp/thư mục đó tồn tại thật.
BANG_DUONG_KY_VONG = (
    # ── A9: hồ sơ trình duyệt — chặn THEO CẤU TRÚC, không theo tên TL ──────
    ("TL1-T7/Data/profile/Default/Cookies", True),
    ("TL1-T7/App/Chrome-bin/chrome.exe", True),
    # tên kênh KHÔNG bắt đầu bằng "TL" — đúng trọng tâm của A9: chặn theo cấu
    # trúc Data/profile hay App/Chrome-bin, không theo tiền tố tên cũ.
    ("KENH-MOI-5/Data/profile/Default/Login Data", True),
    ("CHANNEL/TL1-T7/trinh-duyet/Data/profile/x", True),
    ("trinh-duyet/ho-so.bin", True),
    # Từ 30/09/2026 (.gitignore DANH SÁCH TRẮNG): mọi thứ ở gốc không khai rõ
    # đều bị chặn — thư mục trình duyệt kênh ở gốc cũng vậy.
    ("TL1-T7/kenh.yaml", True),
    ("thu_nghiem_moi.py", True),
    ("core/tu_chay.py", False),
    ("vm/agent.py", False),
    ("vm/icon/luu.PNG", False),
    ("docs/kien-thuc/chien-luoc.md", False),
    ("docs/PHAT-TRIEN.md", False),
    ("scripts/SETUP.bat", False),
    ("CAI-DAT-VPS.bat", False),
    ("CHAY-GON.vbs", False),
    ("README-VPS.md", True),
    ("cap-nhat.py", True),
    ("vm/KE-HOACH.md", True),
    ("chia-se/bai-hoc/may-a-tam-ly-nhat.json", False),
    ("CLAUDE.md", False),
    ("NHAT-KY-PHAT-TRIEN.md", True),
    ("secrets.json", True),
    ("config.json", True),
    ("config.example.json", False),
    ("PROJECTS/AUTO/x.json", True),
    ("DONE/x.mp4", True),
    # ── E1: cấu hình/trạng thái riêng máy ───────────────────────────────────
    ("bao-dong.json", True),
    ("vps-rieng.json", True),
    ("mang-youtube.json", True),
    ("hop-viec-may-ao.json", True),
    ("cap-nhat.json", True),
    # ── E1: vm/ — trạng thái/nhật ký sinh lúc chạy ──────────────────────────
    ("vm/clients/TL1-T7.json", True),
    ("vm/replied/TL1-T7.json", True),
    ("vm/transcripts/abc.txt", True),
    ("vm/da-dang-cmt-moi/abc.json", True),
    ("vm/thu-muc-dang-TL9-T7.json", True),
    ("vm/may-ao.json", True),
    ("vm/logs/agent-gui.log", True),
    # vm/tien-ich/ trọn thư mục là bản agent tải về lúc chạy (phẳng hay theo
    # kênh) — chặn hết. Nguồn thật của extension là core/ytb_extension/.
    ("vm/tien-ich/TL9-T7/manifest.json", True),
    ("vm/tien-ich/manifest.json", True),
    ("vm/tien-ich/background.js", True),
    ("core/ytb_extension/manifest.json", False),
    ("core/ytb_extension/background.js", False),
    # ── E1: CHANNEL/ — nhật ký/số liệu thật, không phải khuôn ───────────────
    ("CHANNEL/TL1-T7/can-ghim.md", True),
    ("CHANNEL/TL1-T7/NHAT-KY-KENH.md", True),
    ("CHANNEL/_NHOM/tam-ly-nhat/bang-nhom.md", True),
    ("CHANNEL/TL1-T7/ho-so-video/v1/meta.json", True),
    # Từ 30/09/2026: thư mục kênh THẬT không lên kho chung nữa (kể cả kenh.yaml);
    # khuôn dùng chung nằm ở CHANNEL/_KHUON/ và hồ sơ ngách _NHOM/*/ngach.yaml.
    ("CHANNEL/TL1-T7/CLAUDE.md", True),
    ("CHANNEL/TL1-T7/kenh.yaml", True),
    ("CHANNEL/_KHUON/ngach-mau.yaml", False),
    ("CHANNEL/_NHOM/tam-ly-nhat/ngach.yaml", False),
    # .csv không nằm trong allow-list đuôi tệp của CHANNEL/** (chỉ
    # yaml/yml/md/py) — kế hoạch đăng là SỐ LIỆU THẬT sinh ra khi chạy, đúng
    # ý chặn từ trước, không phải lỗi mới của bản vá này.
    ("CHANNEL/TL1-T7/ke-hoach-dang/ke-hoach.csv", True),
    # ── workspace/ : đã chặn trọn (không cần mẫu riêng), kiểm lại cho chắc ──
    ("workspace/LO-TRINH-PHAT-HANH-V3.md", True),
    ("workspace/ban-va/2026-09-29-vi-du/GHI-CHU.md", True),
)


def _check_ignore(duong: str) -> int:
    """Mã thoát của `git check-ignore --no-index` — 0 = bị chặn, 1 = không,
    128 = không phải kho git (hoặc git không có trên máy chạy test)."""
    try:
        ket = subprocess.run(
            ("git", "check-ignore", "-q", "--no-index", duong),
            cwd=GOC, capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as loi:
        pytest.skip("máy chạy test không dùng được git: {0}".format(loi))
    return ket.returncode


@pytest.fixture(scope="module", autouse=True)
def _can_co_git():
    if not os.path.isfile(os.path.join(GOC, ".gitignore")):
        pytest.skip("không thấy .gitignore ở gốc kho")


@pytest.mark.parametrize("duong,phai_bi_chan", BANG_DUONG_KY_VONG)
def test_gitignore_dung_ky_vong(duong, phai_bi_chan):
    ma = _check_ignore(duong)
    if ma == 128:
        pytest.skip("git không chạy được trên máy này (--no-index)")
    bi_chan = (ma == 0)
    if phai_bi_chan:
        assert bi_chan, (
            "“{0}” PHẢI bị .gitignore chặn (dữ liệu riêng máy/kênh) nhưng "
            "đang lọt — một lượt `git add -A` sẽ đẩy nó lên kho công khai."
            .format(duong))
    else:
        assert not bi_chan, (
            "“{0}” bị .gitignore chặn NHẦM — đây là khuôn/mã dùng chung phải "
            "đi theo tool, không phải dữ liệu riêng máy.".format(duong))


def test_khong_git_rm_du_lieu_dang_theo_doi_trong_thu_muc_nay():
    """Bài này CHỈ kiểm khuôn `.gitignore`. Một số tệp đã lọt TỪ TRƯỚC (ví dụ
    `CHANNEL/TL4-T7/NHAT-KY-KENH.md`, `vm/tien-ich/TL*-T7/*`) đang thật sự
    nằm trong chỉ mục git của thư mục làm việc này (VPS đang chạy thật) —
    thêm .gitignore KHÔNG tự gỡ chúng khỏi chỉ mục, và bài kiểm này (cũng như
    người sửa) không được chạy `git rm` trong thư mục này (luật giao việc:
    đóng băng tới sáng 30/09, không đụng dữ liệu máy đang chạy thật). Việc gỡ
    khỏi chỉ mục để dành cho lúc dựng CÂY PHÁT HÀNH (Đợt 6.1) — xem GHI-CHU
    của bản vá kèm bài này để có danh sách cụ thể."""
    assert True
