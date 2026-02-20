#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除截取的文件
"""

from flask import request, jsonify
from cut import cut_tool


def delete_cut_file():
    """删除截取的文件"""
    try:
        file_name = request.form.get("file_name", "").strip()
        if not file_name:
            return jsonify({"code": 1, "msg": "文件名不能为空"})
        
        success, msg = cut_tool.delete_cut_file(file_name)
        if success:
            return jsonify({"code": 0, "msg": msg})
        else:
            return jsonify({"code": 1, "msg": msg})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

