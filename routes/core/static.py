#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态文件路由
"""

from flask import send_from_directory


def static_files(app, filename):
    """静态文件路由"""
    return send_from_directory(app.config['STATIC_FOLDER'], filename)

