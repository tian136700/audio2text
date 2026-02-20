#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云语音识别 - 普通识别接口
"""

from flask import request, jsonify
from aliyun import aliyun_web_tool


def aliyun_recognize():
    """使用阿里云对给定的音频 URL 进行语音识别"""
    file_url = request.form.get("file_url", "").strip()
    flask_log1 = f"[AliyunASR][Flask] 收到前端识别请求，file_url = {file_url}"
    print(flask_log1)
    if not file_url:
        return jsonify({"code": 1, "msg": "音频URL不能为空", "logs": [flask_log1]})

    try:
        flask_log2 = "[AliyunASR][Flask] 调用 aliyun_web_tool.recognize_audio() 开始后端识别流程"
        print(flask_log2)
        result = aliyun_web_tool.recognize_audio(file_url)
        flask_log3 = f"[AliyunASR][Flask] 后端识别流程返回: {result}"
        print(flask_log3)
        
        # 将 Flask 层的日志添加到日志列表的开头
        logs = result.get("logs", [])
        logs.insert(0, flask_log1)
        logs.insert(1, flask_log2)
        logs.append(flask_log3)
        result["logs"] = logs
        
        if result.get("success"):
            return jsonify({
                "code": 0, 
                "msg": result.get("message", "识别成功"), 
                "data": result.get("record"),
                "logs": logs
            })
        else:
            return jsonify({
                "code": 1, 
                "msg": result.get("message", "识别失败"),
                "logs": logs
            })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[aliyun_recognize]error: {e}')
        error_log = f"[AliyunASR][Flask] 异常抛出: {e}"
        print(error_log)
        error_logs = [flask_log1]
        if 'flask_log2' in locals():
            error_logs.append(flask_log2)
        error_logs.append(error_log)
        return jsonify({"code": 1, "msg": str(e), "logs": error_logs})

