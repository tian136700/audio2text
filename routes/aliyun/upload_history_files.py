#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 server_files_cache.json 读取服务器文件缓存，供 /aliyun_asr 页面使用
"""

import os
import json
from flask import jsonify
from pathlib import Path


def aliyun_upload_history_files():
    """
    从 MySQL 或 JSON 文件读取服务器文件缓存（通过 server_files_cache 模块）
    
    Returns:
        JSON: {
            "code": 0,
            "msg": "ok",
            "data": [
                {
                    "file_name": "...",
                    "download_url": "http://...",
                    "original_name": "...",
                    ...
                },
                ...
            ]
        }
    """
    try:
        # 使用 server_files_cache 模块（自动处理 MySQL/JSON 切换）
        from server_upload import server_files_cache
        files_list = server_files_cache.get_cached_files()
        
        # 确保返回的数据格式符合前端期望
        # 前端期望每个元素有 download_url 和 file_name
        # 数据从 MySQL server_files 表获取，包含所有字段
        result_data = []
        for item in files_list:
            if not isinstance(item, dict):
                continue
            
            # 从数据库获取的字段
            download_url = item.get("download_url", "")
            file_name = item.get("file_name", "")  # 原文件名
            original_name = item.get("original_name", "")  # 子文件名称（中文名称）
            
            if not download_url:
                continue
            
            # 显示名称：优先使用 original_name（子文件名称），如果没有则使用 file_name（原文件名）
            display_name = original_name if original_name else file_name
            
            result_data.append({
                "id": item.get("id", 0),  # 数据库自增ID
                "file_id": item.get("file_id", ""),  # 文件ID
                "file_name": file_name,  # 原文件名
                "original_name": original_name,  # 子文件名称（中文名称，如果没有则留空）
                "download_url": download_url,  # 下载链接
                "upload_time": item.get("upload_time", ""),  # 上传时间
                "file_size": item.get("file_size", 0),  # 文件大小（字节）
                "file_size_mb": item.get("file_size_mb", 0),  # 文件大小（MB）
                "file_duration": item.get("file_duration", 0),  # 文件时长（秒）
                "file_duration_str": item.get("file_duration_str", ""),  # 文件时长（字符串格式）
                "upload_duration": item.get("upload_duration"),  # 上传耗时
                "uploader_ip": item.get("uploader_ip", ""),  # 操作人IP
                "remote_path": item.get("remote_path", ""),  # 服务器路径
            })
        
        return jsonify({
            "code": 0,
            "msg": "ok",
            "data": result_data
        })
        
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[aliyun_upload_history_files]error: {e}')
        return jsonify({
            "code": 1,
            "msg": str(e),
            "data": []
        })

