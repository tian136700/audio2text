#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的服务器文件列表缓存更新脚本
可以单独运行，也可以作为系统定时任务运行

使用方法：
1. 直接运行：python update_server_cache.py
2. 作为系统定时任务：使用 launchd 或 cron
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from server_upload.server_files_cache import _update_cache, _load_cache_from_file

def main():
    """主函数：更新服务器文件列表缓存"""
    try:
        # 加载已有缓存
        _load_cache_from_file()
        
        # 执行更新
        _update_cache()
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 缓存更新任务执行完成")
        return 0
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 缓存更新任务执行失败: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

