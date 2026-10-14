# -*- coding: utf-8 -*-
"""14/10/2026 — BOM (U+FEFF) kẹt giữa kenh.yaml không được làm hỏng khối lồng nhau."""
from core.kenh import doc_yaml


def test_bom_giua_tep_van_doc_khoi_long_nhau(tmp_path):
    p = tmp_path / "kenh.yaml"
    p.write_text("# đầu tệp\n﻿# khuôn chép vào\nma: \"K1\"\nchuyen_doi_sub:\n  bat: true\n", encoding="utf-8")
    d = doc_yaml(str(p))
    assert d["ma"] == "K1" and d["chuyen_doi_sub"] == {"bat": True} and "bat" not in d
