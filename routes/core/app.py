#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 应用初始化
"""

import logging
import os
from flask import Flask
from logging.handlers import RotatingFileHandler
import warnings
warnings.filterwarnings('ignore')
from stslib.cfg import ROOT_DIR


def create_app():
    """
    创建并配置 Flask 应用
    
    Returns:
        Flask: 配置好的 Flask 应用实例
    """
    # 配置日志
    # 禁用 Werkzeug 默认的日志处理器
    log = logging.getLogger('werkzeug')
    log.handlers[:] = []
    log.setLevel(logging.WARNING)
    
    # 创建 Flask 应用
    app = Flask(
        __name__,
        static_folder=os.path.join(ROOT_DIR, 'static'),
        static_url_path='/static',
        template_folder=os.path.join(ROOT_DIR, 'templates')
    )
    
    # 配置根日志记录器
    root_log = logging.getLogger()  # Flask的根日志记录器
    root_log.handlers = []
    root_log.setLevel(logging.WARNING)
    
    # 配置应用日志
    app.logger.setLevel(logging.WARNING)  # 设置日志级别为 WARNING
    # 创建 RotatingFileHandler 对象，设置写入的文件路径和大小限制
    file_handler = RotatingFileHandler(
        os.path.join(ROOT_DIR, 'sts.log'),
        maxBytes=1024 * 1024,
        backupCount=5
    )
    # 创建日志的格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # 设置文件处理器的级别和格式
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(formatter)
    # 将文件处理器添加到日志记录器中
    app.logger.addHandler(file_handler)
    
    return app

