#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机密码生成页面
"""

from flask import render_template
from stslib import cfg
import stslib


def password_generator_page():
    """随机密码生成独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "password_generator.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/password_generator',
    )

