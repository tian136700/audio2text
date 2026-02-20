#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云语音识别页面
"""

from flask import render_template
from stslib import cfg
import stslib


def aliyun_asr_page():
    """阿里云语音识别独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "aliyun_asr.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/aliyun_asr',
    )

