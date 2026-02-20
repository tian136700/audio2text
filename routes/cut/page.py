#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频截取页面
"""

from flask import render_template
from stslib import cfg
import stslib


def cut_page():
    """音频截取独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "cut.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/cut',
    )

