#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云识别结果预览
"""

import os
from flask import request, send_file
from stslib.cfg import ROOT_DIR
from aliyun import aliyun_web_tool


def aliyun_preview():
    """预览阿里云识别结果（在浏览器新窗口中打开文本文件）"""
    record_id = request.args.get("id", "").strip()
    if not record_id:
        return "记录ID不能为空", 400

    record = aliyun_web_tool.get_record_by_id(record_id)
    if not record:
        return "未找到对应历史记录", 404

    file_rel_path = record.get("text_path")
    if not file_rel_path:
        return "记录中未找到文本文件路径", 404

    full_path = os.path.join(ROOT_DIR, file_rel_path)
    if not os.path.exists(full_path):
        return "文件不存在: " + file_rel_path, 404

    try:
        return send_file(full_path, as_attachment=False)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[aliyun_preview]error: {e}')
        return f"预览出错: {e}", 500

