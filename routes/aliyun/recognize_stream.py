#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云语音识别 - 流式传输接口
"""

import queue
import threading
import json
import traceback
from flask import request, Response, stream_with_context
from aliyun import aliyun_web_tool


def aliyun_recognize_stream():
    """使用阿里云对给定的音频 URL 进行语音识别（流式传输日志版本）"""
    # 支持 GET 和 POST
    if request.method == 'GET':
        file_url = request.args.get("file_url", "").strip()
    else:
        file_url = request.form.get("file_url", "").strip()
    
    def send_log(message):
        """发送日志到前端（SSE 格式）"""
        message_escaped = message.replace('\n', '\\n').replace('\r', '\\r')
        return f"data: {message_escaped}\n\n"
    
    def generate():
        """生成器函数，用于流式传输"""
        log_queue = queue.Queue()
        result_container = {'result': None, 'error': None, 'finished': False}
        
        def log_callback(msg):
            """日志回调函数，将日志放入队列"""
            log_queue.put(msg)
        
        def recognize_task():
            """在后台线程中执行识别任务"""
            try:
                result_container['result'] = aliyun_web_tool.recognize_audio(file_url, log_callback=log_callback)
            except Exception as e:
                result_container['error'] = e
            finally:
                result_container['finished'] = True
        
        try:
            # 发送 Flask 层日志
            yield send_log(f"[AliyunASR][Flask] 收到前端识别请求，file_url = {file_url}")
            
            if not file_url:
                yield send_log("[AliyunASR][Flask] 错误：音频URL不能为空")
                yield "event: end\ndata: " + json.dumps({"code": 1, "msg": "音频URL不能为空"}, ensure_ascii=False) + "\n\n"
                return
            
            yield send_log("[AliyunASR][Flask] 调用 aliyun_web_tool.recognize_audio() 开始后端识别流程")
            
            # 启动识别任务线程
            task_thread = threading.Thread(target=recognize_task)
            task_thread.daemon = True
            task_thread.start()
            
            # 实时推送日志
            while not result_container['finished'] or not log_queue.empty():
                try:
                    log_msg = log_queue.get(timeout=0.1)
                    yield send_log(log_msg)
                except queue.Empty:
                    continue
            
            # 等待任务完成
            task_thread.join(timeout=5)
            
            # 发送剩余的日志
            while not log_queue.empty():
                try:
                    log_msg = log_queue.get_nowait()
                    yield send_log(log_msg)
                except queue.Empty:
                    break
            
            yield send_log(f"[AliyunASR][Flask] 后端识别流程完成")
            
            # 发送最终结果
            if result_container['error']:
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": str(result_container['error'])
                }, ensure_ascii=False) + "\n\n"
            elif result_container['result']:
                result = result_container['result']
                if result.get("success"):
                    yield "event: end\ndata: " + json.dumps({
                        "code": 0,
                        "msg": result.get("message", "识别成功"),
                        "data": result.get("record")
                    }, ensure_ascii=False) + "\n\n"
                else:
                    yield "event: end\ndata: " + json.dumps({
                        "code": 1,
                        "msg": result.get("message", "识别失败")
                    }, ensure_ascii=False) + "\n\n"
            else:
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": "识别任务未返回结果"
                }, ensure_ascii=False) + "\n\n"
                
        except Exception as e:
            error_msg = f"[AliyunASR][Flask] 异常抛出: {e}"
            yield send_log(error_msg)
            yield send_log(f"[AliyunASR][Flask] 异常详情: {traceback.format_exc()}")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": str(e)
            }, ensure_ascii=False) + "\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

