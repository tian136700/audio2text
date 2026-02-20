#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取识别进度和结果
"""

from flask import request, jsonify
from stslib import cfg


def progressbar():
    """前端获取进度及完成后的结果"""
    wav_name = request.form.get("wav_name").strip()
    model_name = request.form.get("model")
    # 语言
    language = request.form.get("language")
    # 返回格式 json txt srt
    data_type = request.form.get("data_type")
    # 是否启用说话人识别
    enable_speaker = request.form.get("enable_speaker", "off") == "on"
    key = f'{wav_name}{model_name}{language}{data_type}{enable_speaker}'
    if key in cfg.progressresult and  isinstance(cfg.progressresult[key],str) and cfg.progressresult[key].startswith('error:'):
        return jsonify({"code":1,"msg":cfg.progressresult[key][6:]})

    progressbar = cfg.progressbar.get(key)
    if progressbar is None:
        return jsonify({"code":1,"msg":"No this file"}),500
    if progressbar>=1:
        return jsonify({"code":0, "data":progressbar, "msg":"ok", "result":cfg.progressresult[key]})
    return jsonify({"code":0, "data":progressbar, "msg":"ok"})

