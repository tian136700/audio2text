#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义请求处理器
"""

from gevent.pywsgi import WSGIHandler


class CustomRequestHandler(WSGIHandler):
    """自定义请求处理器，禁用日志输出"""
    def log_request(self):
        pass

