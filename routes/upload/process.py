#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理上传到服务器的任务
"""

import os
import queue
import threading
import json
from flask import request, Response
from server_upload import upload_to_server_tool


def upload_to_server_process():
    """处理上传到服务器的任务（使用 SSE 推送进度）"""
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
        
        def upload_task():
            """在后台线程中执行上传任务"""
            try:
                temp_file = request.form.get("temp_file", "").strip()
                if not temp_file or not os.path.exists(temp_file):
                    result_container['error'] = Exception("临时文件不存在")
                    return
                
                # 获取客户端 IP 地址
                uploader_ip = request.remote_addr
                # 如果使用了代理，尝试从 X-Forwarded-For 获取真实 IP
                if request.headers.get('X-Forwarded-For'):
                    uploader_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
                elif request.headers.get('X-Real-IP'):
                    uploader_ip = request.headers.get('X-Real-IP')
                
                result_container['result'] = upload_to_server_tool.upload_file_to_server(
                    temp_file, 
                    log_callback=log_callback,
                    uploader_ip=uploader_ip
                )
                
                # 删除临时文件
                try:
                    os.remove(temp_file)
                    log_callback("[上传] 临时文件已清理")
                except:
                    pass
                    
            except Exception as e:
                result_container['error'] = e
            finally:
                result_container['finished'] = True
        
        try:
            yield send_log("[上传][Flask] 收到处理请求，开始处理...")
            
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
            task_thread.join(timeout=30)
            
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
            elif result_container['result'] and result_container['result'].get("success"):
                yield send_log("[上传] 处理完成 ✅")
                yield "event: end\ndata: " + json.dumps({
                    "code": 0,
                    "msg": "上传成功",
                    "data": result_container['result'].get("record")
                }, ensure_ascii=False) + "\n\n"
            else:
                error_msg = result_container['result'].get('error', '未知错误') if result_container['result'] else '未知错误'
                yield send_log(f"[上传] 处理失败: {error_msg}")
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": error_msg
                }, ensure_ascii=False) + "\n\n"
                
        except Exception as e:
            yield send_log(f"[上传][Flask] 错误: {str(e)}")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": str(e)
            }, ensure_ascii=False) + "\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

