#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将截取的文件转换为文字
"""

import os
import queue
import threading
import json
import traceback
from flask import request, Response
from stslib import cfg
from aliyun import cut_convert_to_text as cut_convert_module


def cut_convert_to_text():
    """将截取的文件转换为文字（使用 SSE 推送进度）"""
    def send_log(message):
        """发送日志到前端（SSE 格式）"""
        message_escaped = message.replace('\n', '\\n').replace('\r', '\\r')
        return f"data: {message_escaped}\n\n"
    
    def generate():
        """生成器函数，用于流式传输"""
        log_queue = queue.Queue()
        result_container = {'result': None, 'error': None, 'finished': False}
        
        # 在请求上下文中获取数据
        file_name = request.form.get("file_name", "").strip()
        if not file_name:
            yield send_log("[转文字] 错误: 文件名不能为空")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": "文件名不能为空"
            }, ensure_ascii=False) + "\n\n"
            return
        
        # 构建文件路径和 URL
        cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
        file_path = os.path.join(cut_dir, file_name)
        
        if not os.path.exists(file_path):
            yield send_log(f"[转文字] 错误: 文件不存在: {file_name}")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": f"文件不存在: {file_name}"
            }, ensure_ascii=False) + "\n\n"
            return
        
        # 生成文件 URL（使用本地服务器地址）
        # cfg.web_address 形如 127.0.0.1:5023
        file_url = f"http://{cfg.web_address}/static/cut/{file_name}"
        
        def log_callback(msg):
            """日志回调函数，将日志放入队列"""
            log_queue.put(msg)
        
        def convert_task():
            """在后台线程中执行转换任务"""
            try:
                result_container['result'] = cut_convert_module.convert_cut_file_to_text(
                    file_path, file_url, log_callback=log_callback
                )
            except Exception as e:
                result_container['error'] = e
            finally:
                result_container['finished'] = True
        
        try:
            yield send_log("[转文字][Flask] 收到转文字请求，开始处理...")
            
            # 启动转换任务线程
            task_thread = threading.Thread(target=convert_task)
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
            task_thread.join(timeout=300)  # 5分钟超时
            
            # 发送剩余的日志
            while not log_queue.empty():
                try:
                    log_msg = log_queue.get(timeout=0.1)
                    yield send_log(log_msg)
                except queue.Empty:
                    break
            
            # 发送最终结果
            if result_container['error']:
                yield send_log(f"[转文字] 处理失败: {str(result_container['error'])}")
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": str(result_container['error'])
                }, ensure_ascii=False) + "\n\n"
            elif result_container['result'] and result_container['result'].get("success"):
                yield send_log("[转文字] 处理完成 ✅")
                yield "event: end\ndata: " + json.dumps({
                    "code": 0,
                    "msg": "转换成功",
                    "data": result_container['result']
                }, ensure_ascii=False) + "\n\n"
            else:
                error_msg = result_container['result'].get('message', '未知错误') if result_container['result'] else '未知错误'
                yield send_log(f"[转文字] 处理失败: {error_msg}")
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": error_msg
                }, ensure_ascii=False) + "\n\n"
                
        except Exception as e:
            yield send_log(f"[转文字][Flask] 错误: {str(e)}")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": str(e)
            }, ensure_ascii=False) + "\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })

