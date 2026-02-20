#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转MP3格式页面
"""

from flask import render_template
from stslib import cfg
import stslib


def convert_mp3_page():
    """转MP3格式独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "convert_mp3.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/convert_mp3',
    )

