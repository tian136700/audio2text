#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Whisper 语音识别处理
"""

import os
from flask import request, jsonify
from stslib import cfg


def process():
    """处理识别任务"""
    wav_name = request.form.get("wav_name","").strip()
    if not wav_name:
        return jsonify({"code": 1, "msg": f"No file had uploaded"})
    model = request.form.get("model")
    # 语言
    language = request.form.get("language")
    # 返回格式 json txt srt
    data_type = request.form.get("data_type")
    # 是否启用说话人识别
    enable_speaker = request.form.get("enable_speaker", "off") == "on"
    wav_file = os.path.join(cfg.TMP_DIR, wav_name)
    if not os.path.exists(wav_file):
        return jsonify({"code": 1, "msg": f"{wav_file} {cfg.transobj['lang5']}"})

    key=f'{wav_name}{model}{language}{data_type}{enable_speaker}'
    #重设结果为none
    cfg.progressresult[key]=None
    # 重设进度为0
    cfg.progressbar[key]=0
    #存入任务队列
    cfg.TASK_QUEUE.append({"wav_name":wav_name, "model":model, "language":language, "data_type":data_type, "wav_file":wav_file, "key":key, "enable_speaker":enable_speaker})
    return jsonify({"code":0, "msg":"ing"})

