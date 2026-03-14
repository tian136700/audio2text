#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据音频 URL 获取最近一次阿里云识别记录
"""

from flask import request, jsonify
from aliyun import aliyun_web_tool


def aliyun_latest_by_url():
    """根据 file_url 查询最近一次识别记录（用于上传页面的“下载文字”按钮）"""
    file_url = request.args.get("file_url", "").strip()
    if not file_url:
        return jsonify({"code": 1, "msg": "file_url 不能为空"})

    try:
        record = aliyun_web_tool.get_latest_record_by_file_url(file_url)
        if not record:
            return jsonify({"code": 1, "msg": "该音频尚未进行阿里云识别"})
        return jsonify({"code": 0, "msg": "获取成功", "data": record})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[aliyun_latest_by_url]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

