#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传文件到服务器
"""

import os
from flask import request, jsonify
from stslib import cfg
from werkzeug.utils import secure_filename


def upload_to_server():
    """上传文件到服务器"""
    try:
        if 'file' not in request.files:
            return jsonify({"code": 1, "msg": "没有上传文件"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"code": 1, "msg": "文件名为空"})
        
        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_file = os.path.join(cfg.TMP_DIR, filename)
        file.save(temp_file)
        
        # 返回临时文件路径，让前端通过 SSE 获取处理进度
        return jsonify({
            "code": 0,
            "msg": "文件接收成功",
            "data": {
                "temp_file": temp_file,
                "filename": filename
            }
        })
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[upload_to_server]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

