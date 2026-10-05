# -*- coding: utf-8 -*-
"""core/dong_bo_git.py — lớp QUÉT bí mật/dữ liệu kênh (kiểm toàn kho 06/10/2026).

Mọi chuỗi "bí mật" ở đây là MẪU TỔNG HỢP, ghép lúc chạy (không chuỗi nào nằm
nguyên trong mã nguồn) — chính tệp này cũng phải qua được lớp quét khi `day`.
Một test dựng kho git TẠM trong tmp_path (vài commit, không mạng).
"""

import io
import os
import subprocess

import pytest

from core import dong_bo_git as d

A35 = "A" * 20 + "b" * 15


def _loai(chu, rel="x.py", tu_cam=()):
    return {loai for loai, _ in d.quet_noi_dung(rel, chu, d._BoKhop(list(tu_cam)))}


# ── mẫu mới ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("chuoi, loai", [
    ("TOKEN = '" + "1234567890" + ":" + A35 + "'", "token bot Telegram"),
    ("rt = '" + "1//0" + "g" * 40 + "'", "refresh token Google OAuth (1//0…)"),
    ("at = '" + "ya29" + "." + "Q" * 30 + "'", "access token Google (ya29.…)"),
    ('{"refresh' + '_token": "' + "z" * 30 + '"}', "refresh_token có giá trị"),
    ("Cookie: " + "SAPI" + "SID=" + "Qw" * 12 + ";", "cookie phiên Google/YouTube"),
    ("__Secure-" + "3PSID=" + "k" * 30, "cookie phiên Google/YouTube"),
    ("sid = '" + "S-1-5-21" + "-1234567-2345678-3456789-1001'", "SID tài khoản Windows"),
    ("khoa_aes = '" + "ab" * 20 + "'", "khoá hex dài gán cho biến bí mật"),
    ('"chat' + '_id": "' + "-100" + "4719" + "2836'", "chat id Telegram"),
    ("https://" + "studio.youtube.com/channel/" + "UC" + "q8Zk2Lm3Np4Rs5Tv6Wx7Yz", "id kênh thật trong URL Studio"),
])
def test_mau_moi_bat_dung_loai(chuoi, loai):
    assert loai in _loai(chuoi)


def test_trich_luon_da_che_khong_in_nguyen_chuoi():
    bi_mat = "1//0" + "Zx9" * 15
    ra = d.quet_noi_dung("a.py", "k = '" + bi_mat + "'\n", d._BoKhop([]))
    assert ra and all(bi_mat not in trich and bi_mat[:8] not in trich for _l, trich in ra)
    email = "chu.kenh" + "@" + "thatsu-mail.com"
    ra = d.quet_noi_dung("a.md", "lien he " + email, d._BoKhop([]))
    assert ra == [("email", "dòng 1: c***@thatsu-mail.com")]


def test_mau_gia_ro_rang_khong_bao_cho_mau_it_dac_trung():
    assert _loai('"chat' + '_id": "' + "98765" + "4321" + '"') == set()
    assert _loai("studio.youtube.com/channel/" + "UC" + "x" * 22) == set()
    # nhưng KHOÁ thì không bao giờ được miễn vì "trông giả"
    assert "khoá API dạng sk-…" in _loai("k = 'sk-" + "A" * 30 + "'")


def test_dau_bo_qua_va_che_dong():
    assert _loai("rt = '" + "1//0" + "g" * 40 + "'  # " + d.DAU_BO_QUA) == set()
    dong = "push lỗi: token " + "ghp_" + "a1B2" * 9 + " gửi " + "ai.do" + "@" + "thatsu-mail.com"
    sach = d.che_dong(dong)
    assert "ghp_" + "a1B2" * 9 not in sach and "ai.do@" not in sach and "a***@thatsu-mail.com" in sach


# ── đường cấm ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("rel", [
    "vm/logs/agent.log.txt", "workspace/cai-dat.json", "DONE/x.mp4.json", "bi-mat/khoa.dpapi",
    "CHANNEL/TL1-T7/kenh.yaml", "CHANNEL/K9/nghien-cuu/doi-thu.csv", "CHANNEL/_NHOM/ngach-x/bang-nhom.csv",
    "core/du_lieu/x.sqlite", "tests/x.dpapi", "core/kenh.yaml", "vm/tien-ich/TL1/cau-hinh.json",
    "scripts/User Data/Default/Cookies", "core/so-chu-de.jsonl", "docs/bang.csv".replace("docs/", "core/"),
    "ui_qt/secrets.json",
])
def test_duong_cam(rel):
    assert d.duong_cam(rel)


@pytest.mark.parametrize("rel", [
    "core/dong_bo_git.py", "CHANNEL/_KHUON/kenh-mau/kenh.yaml", "CHANNEL/_NHOM/ngach-x/ngach.yaml",
    "CHANNEL/_NHOM/ngach-x/INSIGHT-CHON-CONTENT.md", "CHANNEL/README.md", "tests/du-lieu/bang.csv",
    "vm/config.example.json", "core/secrets.py", "docs/ke-hoach.example.csv",
])
def test_duong_duoc_phep(rel):
    assert d.duong_cam(rel) == ""


def test_csv_nhieu_dong_youtube_la_du_lieu_kenh():
    dau = "Kênh,Link\n"
    dong = ["k{0},https://www.youtube.com/watch?v=Ab{0}cdEfGh1".format(i) for i in range(3)]
    assert "dữ liệu YouTube dạng bảng/dòng" in _loai(dau + "\n".join(dong), rel="tests/x.csv")
    assert "dữ liệu YouTube dạng bảng/dòng" not in _loai(dau + "\n".join(dong[:2]), rel="tests/x.csv")
    assert "dữ liệu YouTube dạng bảng/dòng" not in _loai(dau + "\n".join(dong), rel="core/x.py")


# ── chuỗi riêng máy: đọc từ tệp kế hoạch, ngôn ngữ nào cũng được ─────────────


def _kenh_gia(goc, ma="KX1"):
    k = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(os.path.join(k, "ke-hoach-dang"))
    os.makedirs(os.path.join(k, "thiet-lap"))
    io.open(os.path.join(k, "kenh.yaml"), "w", encoding="utf-8").write('ma: KX1\nten: "Kenh Mau Rieng"\n')
    io.open(os.path.join(k, "thiet-lap", "ho-so.json"), "w", encoding="utf-8").write(
        '{"ten": "霞の心理学テスト", "handle": "@kenhmau-rieng", "danh_sach_phat": [{"ten": "가짜 재생목록 이름"}]}')
    with io.open(os.path.join(k, "ke-hoach-dang", "ke-hoach.csv"), "w", encoding="utf-8-sig") as f:
        f.write("Mã gói,Tiêu đề,Mô tả,Video ID\n")
        f.write("0001,소리 없이 강한 사람들의 세 가지 습관,x,Qz8kLm2Np4R\n")      # Hàn
        f.write("0002,คนที่เงียบมักคิดลึกกว่าที่คุณคิด,x,\n")                     # Thái
        f.write("0003,静かな人ほど本当は強い理由,x,https://youtu.be/Vt7Rq2Lm9Xa\n")  # Nhật, id trong URL
        f.write("0004,ngắn,x,\n")                                           # quá ngắn: bỏ
    return k


def test_tu_cam_doc_tieu_de_moi_ngon_ngu_va_video_id(tmp_path):
    _kenh_gia(str(tmp_path))
    tc = dict((c, l) for l, c in d.tu_cam_cua_may(str(tmp_path)))
    assert "소리 없이 강한 사람들의 세 가지 습관" in tc and "คนที่เงียบมักคิดลึกกว่าที่คุณคิด" in tc
    assert "静かな人ほど本当は強い理由" in tc and "ngắn" not in tc
    assert {"Qz8kLm2Np4R", "Vt7Rq2Lm9Xa", "Kenh Mau Rieng", "霞の心理学テスト", "@kenhmau-rieng",
            "가짜 재생목록 이름"} <= set(tc)


def test_quet_them_bat_tieu_de_handle_va_video_id_that(tmp_path):
    _kenh_gia(str(tmp_path))
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "a.py").write_text(
        "# vd: 静かな人ほど本当は強い理由\nURL = 'https://youtu.be/Qz8kLm2Np4R'\nH = '@KenhMau-Rieng'\n",
        encoding="utf-8")
    ra = d.quet_them(str(tmp_path), ["core/a.py"])
    loai = [x[1] for x in ra]
    assert any(l.startswith("tiêu đề video kênh thật") for l in loai)
    assert any(l.startswith("video id kênh thật") for l in loai)
    assert any(l.startswith("tên/định danh kênh thật") for l in loai)  # handle không phân biệt hoa thường
    assert all("静かな" not in x[2] and "Qz8kLm2Np4R" not in x[2] for x in ra)


def test_goc_du_lieu_tu_worktree_ve_cay_chinh(tmp_path):
    chinh = tmp_path / "MyTool"
    (chinh / "CHANNEL" / "K1").mkdir(parents=True)
    (chinh / "CHANNEL" / "K1" / "kenh.yaml").write_text("ten: x\n", encoding="utf-8")
    gd = chinh / ".git" / "worktrees" / "wt"
    gd.mkdir(parents=True)
    (gd / "commondir").write_text("../..\n", encoding="utf-8")
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: {0}\n".format(gd), encoding="utf-8")
    assert os.path.normcase(d.goc_du_lieu(str(wt))) == os.path.normcase(str(chinh))
    assert d.goc_du_lieu(str(chinh)) == str(chinh)


def test_thay_the_giu_hinh_dang():
    cap = dict(d.thay_the_giu_hinh(["Qz8kLm2Np4R", "UC" + "q8Zk2Lm3Np4Rs5Tv6Wx7Yz", "@kenhmau-rieng",
                                     "tieu de that rat dai"]))
    assert len(cap["Qz8kLm2Np4R"]) == 11 and d._giong_video_id(cap["Qz8kLm2Np4R"])
    assert d._MAU_KENH_ID.fullmatch(cap["UC" + "q8Zk2Lm3Np4Rs5Tv6Wx7Yz"])
    assert cap["@kenhmau-rieng"].startswith("@kenh-mau-") and cap["tieu de that rat dai"].startswith("***DA-XOA")


# ── quét TOÀN LỊCH SỬ trên một kho git tạm ──────────────────────────────────


def _g(goc, *ts):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false",
                    *ts], cwd=goc, check=True, capture_output=True)


@pytest.fixture
def kho_tam(tmp_path):
    goc = str(tmp_path)
    _g(goc, "init", "-q")
    (tmp_path / "core").mkdir()
    (tmp_path / "workspace").mkdir()
    (tmp_path / "core" / "a.py").write_text("RT = '" + "1//0" + "Hk7" * 12 + "'\n", encoding="utf-8")
    (tmp_path / "workspace" / "cai-dat.json").write_text("{}", encoding="utf-8")
    _g(goc, "add", "-A")
    _g(goc, "commit", "-q", "-m", "lan 1")
    (tmp_path / "core" / "a.py").write_text("RT = ''\n# Kenh Mau Rieng\n", encoding="utf-8")
    _g(goc, "rm", "-q", "workspace/cai-dat.json")
    _g(goc, "add", "-A")
    _g(goc, "commit", "-q", "-m", "lan 2: bo Kenh Mau Rieng")
    return goc


def test_quet_lich_su_thay_ca_thu_da_xoa_khoi_head(kho_tam):
    ph = d.quet_lich_su(kho_tam, ("HEAD",), tu_cam=[("tên/định danh kênh thật (KX1)", "Kenh Mau Rieng")])
    theo = {(g["loai"], g["duong"]): g for g in ph}
    tk = theo[("refresh token Google OAuth (1//0…)", "core/a.py")]
    assert tk["trong_head"] is False and len(tk["commit"]) == 1 and tk["chuoi"]
    ten = theo[("tên/định danh kênh thật (KX1)", "core/a.py")]
    assert ten["trong_head"] is True
    assert ("tên/định danh kênh thật (KX1)", "(thông điệp/tác giả commit)") in theo
    assert any(k[0].startswith("đường cấm") and k[1] == "workspace/cai-dat.json" for k in theo)


def test_lenh_quet_lich_su_in_bang_da_che_va_ghi_tep_thay_the(kho_tam, monkeypatch, capsys, tmp_path_factory):
    monkeypatch.setattr(d, "tu_cam_cua_may", lambda goc, **k: [("tên/định danh kênh thật (KX1)", "Kenh Mau Rieng")])
    monkeypatch.setattr(d, "_ghi_nhat_ky", lambda goc, dong: None)
    ngoai = tmp_path_factory.mktemp("ngoai") / "thay.txt"
    assert d.main(["--goc", kho_tam, "quet", "--lich-su", "--ref", "HEAD", "--ghi-thay-the", str(ngoai)]) == 1
    ra = capsys.readouterr().out
    assert "| mức |" in ra and "git filter-repo --invert-paths --path 'workspace/cai-dat.json'" in ra
    assert "1//0" + "Hk7" not in ra and "Kenh Mau Rieng" not in ra
    thay = ngoai.read_text(encoding="utf-8")
    assert "literal:Kenh Mau Rieng==>***DA-XOA-" in thay and "literal:RT = '" not in thay
    # tệp thay thế không được nằm trong kho (trừ thư mục bị chặn như workspace/)
    assert d.main(["--goc", kho_tam, "quet", "--lich-su", "--ref", "HEAD",
                   "--ghi-thay-the", os.path.join(kho_tam, "core", "thay.txt")]) == 3
