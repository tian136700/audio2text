#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频转换相关路由处理函数
"""

import threading
from flask import request, render_template, jsonify
from stslib import cfg
import stslib
import convert_mp3_tool


def convert_mp3_page():
    """转MP3格式独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "convert_mp3.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/convert_mp3',
    )


def convert_audio():
    """将音频文件转换为MP3格式（异步处理）"""
    file_name = request.form.get("file_name", "").strip()
    task_id = request.form.get("task_id", "").strip()

    if not file_name:
        return jsonify({"code": 1, "msg": "源音频文件不能为空"})
    if not task_id:
        return jsonify({"code": 1, "msg": "任务ID不能为空"})

    src_file = os.path.join(cfg.TMP_DIR, file_name)
    if not os.path.exists(src_file):
        return jsonify({"code": 1, "msg": f"源音频不存在: {file_name}"})

    # 在后台线程中执行转换
    def convert_task():
        try:
            convert_mp3_tool.convert_to_mp3(src_file, task_id)
        except Exception as e:
            with convert_mp3_tool.CONVERT_LOCK:
                convert_mp3_tool.CONVERT_PROGRESS[task_id] = {
                    "progress": 0,
                    "status": "error",
                    "message": str(e)
                }

    threading.Thread(target=convert_task, daemon=True).start()

    return jsonify({"code": 0, "msg": "转换任务已启动", "task_id": task_id})


def convert_progress():
    """查询转换进度"""
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"code": 1, "msg": "任务ID不能为空"})

    try:
        progress_data = convert_mp3_tool.get_convert_progress(task_id)
        return jsonify({"code": 0, "data": progress_data})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})


def convert_history():
    """查看历史转换记录"""
    try:
        limit = request.args.get("limit", 50, type=int)
        data = convert_mp3_tool.list_convert_history(limit=limit)
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

