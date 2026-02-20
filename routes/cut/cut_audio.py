#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截取音频
"""

import os
from flask import request, jsonify
from stslib import cfg
from cut import cut_tool


def cut_audio():
    """根据开始/结束时间截取音频"""
    wav_name = request.form.get("wav_name", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()

    if not wav_name:
        return jsonify({"code": 1, "msg": "源音频文件不能为空"})
    if not start_time or not end_time:
        return jsonify({"code": 1, "msg": "开始时间和结束时间不能为空"})

    src_wav = os.path.join(cfg.TMP_DIR, wav_name)
    if not os.path.exists(src_wav):
        return jsonify({"code": 1, "msg": f"源音频不存在: {wav_name}"})

    try:
        out_path, url = cut_tool.cut_audio_segment(src_wav, start_time, end_time)
        file_name = os.path.basename(out_path)
        return jsonify(
            {
                "code": 0,
                "msg": "截取成功",
                "file_name": file_name,
                "url": url,
            }
        )
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

