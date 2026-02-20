#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用主入口
所有功能已模块化到 routes/ 目录下
"""

# ============================================================================
# 必须在导入任何库之前设置 OpenMP 环境变量（防止崩溃）
# ============================================================================
from routes.core import env
env.setup_environment()

# ============================================================================

from dotenv import load_dotenv
from routes.core import app as core_app_module
from routes.core import routes as core_routes_module
from routes.core import main as core_main_module

# 加载 .env 文件
load_dotenv()

# 创建 Flask 应用
app = core_app_module.create_app()

# 注册所有路由
core_routes_module.register_routes(app)


def main():
    """启动入口"""
    core_main_module.main(app)


if __name__ == '__main__':
    main()
