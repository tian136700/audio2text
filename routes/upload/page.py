#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传到服务器页面
"""

from flask import render_template
from stslib import cfg
import stslib


def upload_to_server_page():
    """上传到服务器独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "upload_to_server.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/upload_to_server',
    )

