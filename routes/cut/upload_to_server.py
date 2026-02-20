#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传截取的文件到服务器
"""

import os
import queue
import threading
import json
import traceback
from flask import request, Response
from stslib import cfg
from server_upload import upload_to_server_tool
from cut import cut_tool


def upload_cut_file_to_server():
    """上传截取的文件到服务器（使用 SSE 推送进度）"""
    def send_log(message):
        """发送日志到前端（SSE 格式）"""
        message_escaped = message.replace('\n', '\\n').replace('\r', '\\r')
        return f"data: {message_escaped}\n\n"
    
    def generate():
        """生成器函数，用于流式传输"""
        log_queue = queue.Queue()
        result_container = {'result': None, 'error': None, 'finished': False}
        
        # 在请求上下文中获取数据，然后传递给线程
        file_name = request.form.get("file_name", "").strip()
        if not file_name:
            yield send_log("[上传] 错误: 文件名不能为空")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": "文件名不能为空"
            }, ensure_ascii=False) + "\n\n"
            return
        
        # 构建文件路径
        cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
        file_path = os.path.join(cut_dir, file_name)
        
        if not os.path.exists(file_path):
            yield send_log(f"[上传] 错误: 文件不存在: {file_name}")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": f"文件不存在: {file_name}"
            }, ensure_ascii=False) + "\n\n"
            return
        
        def log_callback(msg):
            """日志回调函数，将日志放入队列"""
            log_queue.put(msg)
        
        def upload_task():
            """在后台线程中执行上传任务"""
            try:
                result_container['result'] = upload_to_server_tool.upload_file_to_server(
                    file_path, 
                    log_callback=log_callback
                )
                # 上传成功后，标记文件已上传
                if result_container['result'] and result_container['result'].get("success"):
                    cut_tool._save_uploaded_file(file_name)
                    
            except Exception as e:
                result_container['error'] = e
            finally:
                result_container['finished'] = True
        
        try:
            yield send_log("[上传][Flask] 收到上传请求，开始处理...")
            
            # 启动上传任务线程
            task_thread = threading.Thread(target=upload_task)
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
            task_thread.join(timeout=60)
            
            # 发送剩余的日志
            while not log_queue.empty():
                try:
                    log_msg = log_queue.get(timeout=0.1)
                    yield send_log(log_msg)
                except queue.Empty:
                    break
            
            # 发送最终结果
            if result_container['error']:
                yield send_log(f"[上传] 处理失败: {str(result_container['error'])}")
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": str(result_container['error'])
                }, ensure_ascii=False) + "\n\n"
            elif result_container['result']:
                if result_container['result'].get('success'):
                    yield send_log("[上传] 上传完成 ✅")
                    yield "event: end\ndata: " + json.dumps({
                        "code": 0,
                        "msg": "上传成功",
                        "data": result_container['result'].get('record', {})
                    }, ensure_ascii=False) + "\n\n"
                else:
                    yield send_log(f"[上传] 上传失败: {result_container['result'].get('error', '未知错误')}")
                    yield "event: end\ndata: " + json.dumps({
                        "code": 1,
                        "msg": result_container['result'].get('error', '上传失败')
                    }, ensure_ascii=False) + "\n\n"
            else:
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": "上传任务未完成"
                }, ensure_ascii=False) + "\n\n"
                
        except Exception as e:
            yield send_log(f"[上传][Flask] 异常详情: {traceback.format_exc()}")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": str(e)
            }, ensure_ascii=False) + "\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

