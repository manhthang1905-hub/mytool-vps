"""Số cho panel "Não bộ phận" của trang 8790 (`/nao-bo-phan.json`, tab Não) — CHỈ ĐỌC kho + vault, nhớ đệm 5 phút.

    tinh(goc)                 -> {luc, bo_phan: [...], loi_dang_tang: [...], ban_do}
    chi_tiet(goc, bo_phan)    -> {ma, ten, so_tay (chữ), nhat_ky (đuôi chữ)}
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict

from ._chung import BO_PHAN, doc_chu, duong_db, duong_vault
from .truy_xuat import dong_loi, loi_dang_tang, tom_tat


def tinh(goc: str) -> Dict[str, Any]:
    ra: Dict[str, Any] = {"luc": time.strftime("%Y-%m-%d %H:%M:%S"), "co_kho": os.path.isfile(duong_db(goc)),
                          "bo_phan": [], "loi_dang_tang": [], "ban_do": "nao/bo-phan/_ban-do.md"}
    if ra["co_kho"]:
        ra["bo_phan"] = tom_tat(goc)
        ra["loi_dang_tang"] = [dict(x, dong=dong_loi(x, 200)) for x in loi_dang_tang(goc, 10)]
    return ra


def chi_tiet(goc: str, bo_phan: str) -> Dict[str, Any]:
    if bo_phan not in BO_PHAN:
        return {"loi": "bộ phận lạ"}
    v = os.path.join(duong_vault(goc), bo_phan)
    nk = (doc_chu(os.path.join(v, "nhat-ky.md")) or "").splitlines()
    return {"ma": bo_phan, "ten": BO_PHAN[bo_phan], "so_tay": doc_chu(os.path.join(v, "so-tay.md")) or "",
            "nhat_ky": "\n".join(nk[-60:])}


_NHO: Dict[str, Any] = {"luc": 0.0, "du": None, "goc": ""}
_KHOA = threading.Lock()


def tinh_nho(goc: str, bo_phan: str = "", han: float = 300.0) -> Dict[str, Any]:
    with _KHOA:
        if _NHO["du"] is None or _NHO["goc"] != goc or time.time() - _NHO["luc"] > han:
            _NHO["du"], _NHO["luc"], _NHO["goc"] = tinh(goc), time.time(), goc
        du = dict(_NHO["du"])
    if bo_phan:
        du["chi_tiet"] = chi_tiet(goc, bo_phan)
    return du
