#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的 app_main.py 示例
只保留路由定义，所有处理函数都在 routes/ 目录下的各个模块中
"""

# ============================================================================
# 必须在导入任何库之前设置 OpenMP 环境变量（防止崩溃）
# ============================================================================
import os
os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')
# ... 其他环境变量设置 ...

import logging
from flask import Flask, send_from_directory
from stslib.cfg import ROOT_DIR
from logging.handlers import RotatingFileHandler

# 导入各个模块的处理函数
from routes.cut import handlers as cut_handlers
# from routes.aliyun import handlers as aliyun_handlers
# from routes.upload import handlers as upload_handlers
# from routes.convert import handlers as convert_handlers
# from routes.password import handlers as password_handlers
# from routes.whisper import handlers as whisper_handlers
# from routes.common import handlers as common_handlers

# 配置日志
log = logging.getLogger('werkzeug')
log.handlers[:] = []
log.setLevel(logging.WARNING)

app = Flask(__name__, 
            static_folder=os.path.join(ROOT_DIR, 'static'), 
            static_url_path='/static',
            template_folder=os.path.join(ROOT_DIR, 'templates'))

root_log = logging.getLogger()
root_log.handlers = []
root_log.setLevel(logging.WARNING)

app.logger.setLevel(logging.WARNING)
file_handler = RotatingFileHandler(os.path.join(ROOT_DIR, 'sts.log'), 
                                   maxBytes=1024 * 1024, 
                                   backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)


# ============================================================================
# 路由定义 - 只保留路由装饰器和函数调用
# ============================================================================

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.config['STATIC_FOLDER'], filename)


@app.route('/')
def index():
    from stslib import cfg
    import stslib
    sets = cfg.parse_ini()
    return render_template("index.html",
       devtype=sets.get('devtype'),
       lang_code=cfg.lang_code,
       language=cfg.LANG,
       version=stslib.version_str,
       root_dir=ROOT_DIR.replace('\\', '/'),
       current_page='/',
       model_list=cfg.sets.get('model_list')
    )


# ============================================================================
# Cut 模块路由
# ============================================================================

@app.route('/cut', methods=['GET'])
def cut_page():
    return cut_handlers.cut_page()


@app.route('/upload', methods=['POST'])
def upload():
    return cut_handlers.upload()


@app.route('/cut_audio', methods=['POST'])
def cut_audio():
    return cut_handlers.cut_audio()


@app.route('/cut_history', methods=['GET'])
def cut_history():
    return cut_handlers.cut_history()


@app.route('/cut_convert_to_text', methods=['POST'])
def cut_convert_to_text():
    from flask import stream_with_context
    return stream_with_context(cut_handlers.cut_convert_to_text())


@app.route('/delete_cut_file', methods=['POST'])
def delete_cut_file():
    return cut_handlers.delete_cut_file()


@app.route('/upload_cut_file_to_server', methods=['POST'])
def upload_cut_file_to_server():
    from flask import stream_with_context
    return stream_with_context(cut_handlers.upload_cut_file_to_server())


# ============================================================================
# 其他模块路由（示例，需要继续提取）
# ============================================================================

# @app.route('/aliyun_asr', methods=['GET'])
# def aliyun_asr_page():
#     return aliyun_handlers.aliyun_asr_page()

# @app.route('/aliyun_recognize', methods=['POST'])
# def aliyun_recognize():
#     return aliyun_handlers.aliyun_recognize()

# ... 其他路由 ...


# ============================================================================
# 主函数（保持不变）
# ============================================================================

def main():
    """启动入口"""
    # ... main 函数内容保持不变 ...
    pass


if __name__ == '__main__':
    main()

