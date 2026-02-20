#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页路由
"""

from flask import render_template
from stslib import cfg
import stslib


def index():
    """首页"""
    sets = cfg.parse_ini()
    return render_template("index.html",
       devtype=sets.get('devtype'),
       lang_code=cfg.lang_code,
       language=cfg.LANG,
       version=stslib.version_str,
       root_dir=cfg.ROOT_DIR.replace('\\', '/'),
       current_page='/',
       model_list=cfg.sets.get('model_list')
    )

