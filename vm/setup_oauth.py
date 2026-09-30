# -*- coding: utf-8 -*-
"""Dang nhap YouTube cho TUNG KENH (OAuth) - viet cho NGUOI KHONG BIET LAP TRINH.

Dung:
    python vm\\setup_oauth.py --kenh TL1-T7

Khong go duoc dong lenh tren? Xem tung buoc co anh chu mo ta trong
docs\\DANG-VA-BINH-LUAN.md - lam tu dau toi cuoi, khong can hieu code.

Script nay CHI la lop KIEM TRA + HUONG DAN quanh ham `setup_channel()` da co
san trong `may_cmt.py` (KHONG viet lai luong OAuth tu dau, dung dung y "tan
dung cai co san"). Viec no lam:

    1. Kiem 3 dieu kien PHAI co truoc khi dung mang: co thu vien Python chua,
       kenh da co token chua (co roi thi KHONG lam lai, tranh mat token dang
       dung), co file OAuth client (`vm/clients/<kenh>.json`) chua.
    2. Con thieu gi -> NOI RO thieu gi va phai lam gi tiep (thuong la doc
       docs/DANG-VA-BINH-LUAN.md), KHONG dong mang, KHONG mo Chrome.
    3. Du dieu kien -> mo DUNG trinh duyet cua kenh do (nep GPM/Chrome
       portable <kenh>\\<kenh>.exe, dung ho so tai <thu_muc_cha_MyTool>\\
       <kenh>\\Data\\profile - xem core/mang_youtube.py va
       may_cmt.channel_browser_exe()) va TU BAM qua cac man dang nhap/dong y
       (ham `setup_channel()` cua may_cmt.py, DrissionPage dieu khien).
    4. Khong tim thay trinh duyet rieng cua kenh (hoac chay voi co --thu-cong)
       -> chuyen sang duong lui: IN RA MOT DUONG DAN, nguoi dung tu dan vao
       DUNG trinh duyet cua kenh ho muon dang nhap, dang nhap tay, script tu
       nhan ket qua qua may chu loopback cua thu vien Google chinh thuc
       (`InstalledAppFlow.run_local_server`) - khong phai dan lai ma code ve
       tay, khong phai biet lap trinh.

Xong ca hai duong, token duoc luu dung cho `may_cmt.py` doc (`vm/tokens/
<kenh>.json`) - kenh do lap tuc dung duoc ca hai viec: tu tra loi binh luan
VA tu dang binh luan mo dau (xem `may_cmt.dang_binh_luan_moi`).
"""
from __future__ import annotations

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import may_cmt  # noqa: E402  - module canh day, khong phai goi cai ngoai


def _dong_ke(dong: str = "") -> None:
    print("=" * 64)
    if dong:
        print(dong)
        print("=" * 64)


def kiem_tra_truoc(kenh: str):
    """Ba dieu kien PHAI co truoc khi dung mang/Chrome.

    Tra `(True, duong_client_secret)` khi du dieu kien, hoac
    `(False, cau_giai_thich)` khi con thieu gi do - nguoi goi CHI in ra va
    dung, khong lam gi kem theo (khong goi mang, khong mo Chrome)."""
    if may_cmt.build is None:
        return False, (
            "Thieu thu vien Python can thiet ({0}).\n"
            "Chay CAI-DAT-VPS.bat roi mo lai cua so nay.".format(
                may_cmt._THIEU_THU_VIEN))

    duong_token = may_cmt.token_path(kenh)
    if os.path.isfile(duong_token):
        return False, (
            "Kenh {0} DA CO token roi:\n  {1}\n"
            "KHONG can dang nhap lai. Neu muon doi sang tai khoan khac, xoa "
            "file tren roi chay lai dung lenh nay.".format(kenh, duong_token))

    client_file = may_cmt.client_secret_path(kenh)
    if not client_file or not os.path.isfile(client_file):
        return False, (
            "Kenh {0}: CHUA co file OAuth client trong vm/clients/.\n"
            "Lam theo TUNG BUOC trong docs/DANG-VA-BINH-LUAN.md de tao va tai file "
            "client_secret ve, dat vao vm/clients/{0}.json (hoac 1 file .json "
            "duy nhat dung chung cho moi kenh) roi chay lai lenh nay.".format(kenh))

    return True, client_file


def _setup_thu_cong(kenh: str, client_file: str) -> None:
    """Duong lui KHONG can DrissionPage/trinh duyet rieng cua kenh: in ra MOT
    DUONG DAN, nguoi dung tu dan vao trinh duyet minh muon, dang nhap tay.

    Dung `InstalledAppFlow.run_local_server` cua chinh thu vien Google (KHONG
    tu viet may chu bat code) - vua ngan gon vua da duoc kiem chung. Nguoi
    dung KHONG phai dan lai ma xac thuc: trinh duyet se tu quay ve dia chi
    loopback ma ham nay dang lang nghe."""
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # cho phep redirect http://localhost
    flow = may_cmt.InstalledAppFlow.from_client_secrets_file(client_file, may_cmt.SCOPES)
    thong_bao = (
        "\n"
        "Mo DUNG NGUYEN duong dan duoi day trong trinh duyet ban DA DANG NHAP\n"
        "tai khoan cua kenh {0} (khong phai tai khoan ca nhan):\n\n"
        "    {{url}}\n\n"
        "Dang nhap xong, bam \"Tiep tuc\"/\"Cho phep\" toi cung - cua so nay se\n"
        "TU NHAN ket qua, khong can lam gi them.\n".format(kenh))
    creds = flow.run_local_server(
        port=0, open_browser=False, authorization_prompt_message=thong_bao,
        success_message="Xac thuc thanh cong! Ban co the dong tab nay.")
    may_cmt.save_credentials(kenh, creds)


def chay(kenh: str, thu_cong: bool = False) -> int:
    """Than lenh, tach khoi main() de test goi truc tiep duoc. Tra ma thoat
    (0 = xong, 1 = con thieu/loi)."""
    ok, thong_tin = kiem_tra_truoc(kenh)
    if not ok:
        print(thong_tin)
        return 1
    client_file = thong_tin

    browser_exe = may_cmt.channel_browser_exe(kenh)
    co_browser = os.path.isfile(browser_exe)

    _dong_ke("DANG NHAP KENH {0}".format(kenh))
    print("- File OAuth client : {0}".format(client_file))
    print("- Trinh duyet kenh  : {0}{1}".format(
        browser_exe, "" if co_browser else "  (KHONG THAY tren may nay)"))
    print("- Token se luu vao  : {0}".format(may_cmt.token_path(kenh)))
    print()

    if co_browser and not thu_cong:
        print("Se TU DONG mo dung trinh duyet cua kenh {0} va tu bam qua cac "
              "man dang nhap/dong y. DUNG dong cua so trinh duyet nay - neu "
              "man hinh dung lai cho chon TAI KHOAN, hay tu bam chon DUNG "
              "tai khoan cua kenh nay (khong bam nham tai khoan ca nhan)."
              .format(kenh))
        may_cmt.setup_channel(kenh)
    else:
        if not co_browser:
            print("KHONG tim thay trinh duyet rieng cua kenh {0} tren may nay "
                  "({1}).".format(kenh, browser_exe))
        print("Chuyen sang CHE DO THU CONG:")
        print("  1. Mo DUNG trinh duyet cua kenh {0} (da dang nhap san tai "
              "khoan kenh do).".format(kenh))
        print("  2. Dan nguyen duong dan se hien ra ben duoi vao thanh dia "
              "chi, bam Enter.")
        print("  3. Dang nhap DUNG tai khoan KENH, bam Cho phep toi cung.")
        print("  4. Xong tu dong quay lai cua so nay - khong can lam gi them.")
        print()
        _setup_thu_cong(kenh, client_file)

    if os.path.isfile(may_cmt.token_path(kenh)):
        _dong_ke()
        print("XONG. Kenh {0} da san sang: tu tra loi binh luan VA tu dang "
              "binh luan mo dau cho video moi.".format(kenh))
        return 0

    _dong_ke()
    print("CHUA XONG - khong thay token duoc luu.")
    print("Thu lai lenh nay, hoac them co --thu-cong de tu dan link thay vi "
          "de tool tu dieu khien trinh duyet. Xem docs/DANG-VA-BINH-LUAN.md.")
    return 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Dang nhap YouTube (OAuth) cho MOT kenh - xem docs/DANG-VA-BINH-LUAN.md")
    ap.add_argument("--kenh", help="Ma kenh, vi du TL1-T7")
    ap.add_argument("--thu-cong", action="store_true",
                    help="Bo qua tu dong dieu khien Chrome, in duong dan de tu dan")
    args = ap.parse_args(argv)

    if not args.kenh:
        print("Dung: python vm\\setup_oauth.py --kenh <TEN_KENH>")
        cac_kenh = may_cmt.discover_channels()
        if cac_kenh:
            print("Cac kenh tool tim thay tren may nay: " + ", ".join(cac_kenh))
        else:
            print("Chua tim thay kenh nao (thu muc <TEN>\\<TEN>.exe canh vm/).")
        return 1

    return chay(args.kenh.strip(), thu_cong=bool(args.thu_cong))


if __name__ == "__main__":
    ma = main()
    try:
        input("\nBam Enter de dong cua so nay...")
    except Exception:
        pass
    raise SystemExit(ma)
