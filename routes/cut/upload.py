#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传音频文件
"""

import os
from flask import request, jsonify
from stslib import cfg


def upload():
    """上传音频文件"""
    try:
        # 获取上传的文件
        audio_file = request.files['audio']
        # 获取原始文件名和扩展名
        noextname, ext = os.path.splitext(audio_file.filename)
        ext = ext.lower()
        
        # 保存原始文件，保持原始格式
        saved_file = os.path.join(cfg.TMP_DIR, f'{noextname}{ext}')
        
        # 如果文件已存在且大小大于0，直接返回
        if os.path.exists(saved_file) and os.path.getsize(saved_file) > 0:
            return jsonify({'code': 0, 'msg': cfg.transobj['lang1'], "data": os.path.basename(saved_file)})
        
        # 保存上传的文件，保持原始格式
        audio_file.save(saved_file)
        
        # 返回成功的响应，使用原始文件名
        return jsonify({'code': 0, 'msg': cfg.transobj['lang1'], "data": os.path.basename(saved_file)})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[upload]error: {e}')
        return jsonify({'code': 2, 'msg': cfg.transobj['lang2']})

