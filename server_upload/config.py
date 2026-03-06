#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器上传配置模块

所有敏感信息（服务器 IP、用户名、密码等）从环境变量 / 配置文件中读取，
避免直接写在代码里，便于安全地提交到 git。
"""

import os
from dotenv import load_dotenv

# 加载 .env 等环境配置（如果已在主程序中加载，这里再次调用也没问题）
load_dotenv()

# ==================== 配置信息（从环境变量获取） ====================
# 服务器配置
SERVER_HOST = os.getenv("SERVER_UPLOAD_HOST")            # 服务器 IP 或域名
SERVER_PORT = int(os.getenv("SERVER_UPLOAD_PORT", "22")) # SSH 端口，默认 22
SERVER_USER = os.getenv("SERVER_UPLOAD_USER", "root")    # SSH 用户名
SERVER_PASSWORD = os.getenv("SERVER_UPLOAD_PASSWORD")    # SSH 密码（推荐只用环境变量配置）
SERVER_KEY_PATH = os.getenv("SERVER_UPLOAD_KEY_PATH") or None  # SSH 私钥路径（可选）

# 服务器上的文件存储路径（如：/data/audio）
SERVER_UPLOAD_DIR = os.getenv("SERVER_UPLOAD_DIR", "/data/audio")

# 服务器公网访问 URL 前缀（如：http://你的服务器IP或域名/audio）
PUBLIC_URL_PREFIX = os.getenv("SERVER_PUBLIC_URL_PREFIX")

# 历史记录文件路径（放在当前功能文件夹下）
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "upload_history.json")
