#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云语音识别历史记录
"""

from flask import request, jsonify
from aliyun import aliyun_web_tool


def aliyun_history():
    """获取阿里云语音识别历史记录"""
    try:
        limit = int(request.args.get("limit", 100))
        history = aliyun_web_tool.list_aliyun_history(limit=limit)
        return jsonify({"code": 0, "msg": "获取成功", "data": history})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[aliyun_history]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

