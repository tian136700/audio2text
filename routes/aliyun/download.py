#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云识别结果下载
"""

import os
from flask import request, jsonify, send_file
from stslib.cfg import ROOT_DIR
from aliyun import aliyun_web_tool


def aliyun_download():
    """下载阿里云识别结果文件（文本或 JSON）"""
    record_id = request.args.get("id", "").strip()
    file_type = request.args.get("type", "text").strip().lower()
    if not record_id:
        return jsonify({"code": 1, "msg": "记录ID不能为空"})

    record = aliyun_web_tool.get_record_by_id(record_id)
    if not record:
        return jsonify({"code": 1, "msg": "未找到对应历史记录"})

    if file_type == "json":
        file_rel_path = record.get("json_path")
    else:
        file_rel_path = record.get("text_path")

    if not file_rel_path:
        return jsonify({"code": 1, "msg": "记录中未找到对应的文件路径"})

    full_path = os.path.join(ROOT_DIR, file_rel_path)
    if not os.path.exists(full_path):
        return jsonify({"code": 1, "msg": "文件不存在: " + file_rel_path})

    try:
        return send_file(full_path, as_attachment=True, download_name=os.path.basename(full_path))
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[aliyun_download]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

