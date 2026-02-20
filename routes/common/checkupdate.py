#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查更新
"""

from flask import jsonify
from stslib import cfg


def checkupdate():
    """检查更新"""
    return jsonify({'code': 0, "msg": cfg.updatetips})

