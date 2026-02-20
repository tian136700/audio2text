#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截取文件转文字功能：
- 将截取的音频文件转换为文字
- 使用阿里云 ASR 进行识别
- 生成 TXT 和 Word 文档（Word 字体为宋体）
"""

import os
import queue
import threading
from pathlib import Path
from aliyun.convert_to_doc import convert_to_word


def convert_cut_file_to_text(file_path, file_url, log_callback=None):
    """
    将截取的音频文件转换为文字
    
    Args:
        file_path: 本地文件路径
        file_url: 文件的 URL（用于阿里云识别）
        log_callback: 可选的日志回调函数，用于实时推送日志。函数签名: log_callback(message: str)
    
    Returns:
        dict: {
            "success": bool,
            "message": str,
            "text_path": str (可选),
            "word_path": str (可选),
            "word_url": str (可选),
            "word_filename": str (可选)
        }
    """
    def log_print(*args, **kwargs):
        """同时输出到终端、并可选择实时推送"""
        msg = " ".join(str(arg) for arg in args)
        print(*args, **kwargs)  # 输出到终端
        # 如果有回调函数，实时推送日志
        if log_callback:
            try:
                log_callback(msg)
            except Exception as e:
                print(f"[CutConvert] 日志回调失败: {e}")
    
    log_print("=" * 60)
    log_print("[CutConvert] 开始转文字任务")
    log_print(f"[CutConvert] 文件路径: {file_path}")
    log_print(f"[CutConvert] 文件 URL: {file_url}")

    # 延迟导入阿里云工具，避免因依赖缺失/配置问题直接导致 500
    try:
        from aliyun import aliyun_web_tool
    except Exception as e:
        err = f"加载阿里云识别模块失败: {e}"
        log_print(f"[CutConvert] 错误: {err}")
        return {
            "success": False,
            "message": err
        }
    
    if not os.path.exists(file_path):
        log_print(f"[CutConvert] 错误: 文件不存在: {file_path}")
        return {
            "success": False,
            "message": f"文件不存在: {file_path}"
        }
    
    try:
        log_print("[CutConvert] 第 1 步：开始调用阿里云识别...")
        
        # 调用阿里云识别
        result = aliyun_web_tool.recognize_audio(file_url, log_callback=log_callback)
        
        if not result.get("success"):
            error_msg = result.get("message", "识别失败")
            log_print(f"[CutConvert] 识别失败: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
        
        # 获取识别结果文件路径
        record = result.get("record", {})
        text_path = record.get("text_path")
        
        if not text_path:
            log_print("[CutConvert] 错误: 未找到识别结果文件")
            return {
                "success": False,
                "message": "未找到识别结果文件"
            }
        
        # 转换为绝对路径
        BASE_DIR = Path(__file__).resolve().parent
        PROJECT_ROOT = BASE_DIR.parent
        text_path = os.path.join(PROJECT_ROOT, text_path)
        
        if not os.path.exists(text_path):
            log_print(f"[CutConvert] 错误: 识别结果文件不存在: {text_path}")
            return {
                "success": False,
                "message": f"识别结果文件不存在: {text_path}"
            }
        
        log_print(f"[CutConvert] 第 2 步：识别完成，文本文件: {text_path}")
        log_print("[CutConvert] 开始转换为 Word 文档...")
        
        # 转换为 Word（字体为宋体）
        word_path = convert_to_word(text_path)
        
        log_print(f"[CutConvert] Word 文档已生成: {word_path}")
        
        # 生成下载 URL（相对于 static 目录）
        word_filename = os.path.basename(word_path)
        word_url = f"/static/aliyun/results/{word_filename}"
        
        log_print("[CutConvert] 转文字任务完成 ✅")
        log_print("=" * 60)
        
        return {
            "success": True,
            "message": "转换成功",
            "text_path": text_path,
            "word_path": word_path,
            "word_url": word_url,
            "word_filename": word_filename
        }
        
    except Exception as e:
        import traceback
        error_msg = f"转文字失败: {str(e)}"
        log_print(f"[CutConvert] 错误: {error_msg}")
        log_print(f"[CutConvert] 异常详情: {traceback.format_exc()}")
        return {
            "success": False,
            "message": error_msg
        }

