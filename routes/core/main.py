#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用启动入口
"""

import os
import threading
from gevent.pywsgi import WSGIServer
from stslib import cfg, tool
from routes.core.handler import CustomRequestHandler
from routes.whisper.shibie import shibie


def main(app):
    """
    启动入口：
    - 开发模式：设置环境变量 DEV=1，使用 Flask 自带服务器，支持代码自动重载
      DEV=1 python start.py
    - 正常模式：直接 python start.py，使用 gevent 生产服务器
    """
    # 默认认为是开发模式（尤其是从 PyCharm/IDE 直接运行时）
    # 如需关闭自动重载，可在环境变量中设置 DEV=0
    dev_mode = os.environ.get("DEV", "1") == "1"

    if dev_mode:
        # 开发模式：自动重载，改代码自动生效（适合本机调试）
        print("当前以开发模式运行（DEV=1），启用 Flask 自动重载...")
        threading.Thread(target=tool.checkupdate).start()
        threading.Thread(target=shibie).start()
        # 服务器文件列表缓存定时任务已改为系统定时任务，请参考 SYSTEM_TIMER_SETUP.md
        # server_files_cache.start_cache_thread()
        host, port = cfg.web_address.split(':')
        # debug=True 会启用调试和自动重载
        app.run(host=host, port=int(port), debug=True, use_reloader=True)
    else:
        # 生产模式：保持原来的 gevent 启动方式
        http_server = None
        try:
            threading.Thread(target=tool.checkupdate).start()
            threading.Thread(target=shibie).start()
            # 服务器文件列表缓存定时任务已改为系统定时任务，请参考 SYSTEM_TIMER_SETUP.md
            # server_files_cache.start_cache_thread()
            try:
                if cfg.devtype=='cpu':
                    print('\n如果设备使用英伟达显卡并且CUDA环境已正确安装，可修改set.ini中\ndevtype=cpu 为 devtype=cuda, 然后重新启动以加快识别速度\n')
                host = cfg.web_address.split(':')
                http_server = WSGIServer((host[0], int(host[1])), app, handler_class=CustomRequestHandler)
                threading.Thread(target=tool.openweb, args=(cfg.web_address,)).start()
                http_server.serve_forever()
            finally:
                if http_server:
                    http_server.stop()
        except Exception as e:
            if http_server:
                http_server.stop()
            print("error:" + str(e))
            app.logger.error(f"[app]start error:{str(e)}")

