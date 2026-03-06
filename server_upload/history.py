#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录管理模块

提供历史记录的保存和加载功能（JSON 文件回退逻辑）。
"""

import os
import json
from datetime import datetime
from . import config


def save_history_record(record):
    """
    保存历史记录到数据库（优先）或 JSON 文件（回退）
    
    Args:
        record: 记录字典
    """
    # 优先使用数据库
    try:
        from . import db as db_module
        # 保存到数据库（会自动去重）
        new_id = db_module.save_single_file(record)
        # 更新 record 中的 id 为数据库的自增ID
        if new_id:
            record['id'] = new_id
        return
    except ImportError:
        print("[server_upload.history] 警告：无法导入数据库模块，回退到 JSON 文件")
    except Exception as e:
        print(f"[server_upload.history] 保存到数据库失败，回退到 JSON 文件: {e}")
    
    # 回退到 JSON 文件（兼容旧代码）
    # 确保目录存在
    os.makedirs(os.path.dirname(config.HISTORY_FILE), exist_ok=True)
    
    # 读取现有记录（加载所有记录用于去重检查）
    history = load_history(limit=10000)  # 加载所有记录用于去重
    
    # 检查是否已存在相同记录（根据文件名和上传时间判断，避免重复）
    # 如果最近1秒内有相同文件名的记录，认为是重复上传，不添加
    record_time = datetime.strptime(record['upload_time'], "%Y-%m-%d %H:%M:%S")
    is_duplicate = False
    for existing_record in history[:5]:  # 只检查最近5条记录
        if existing_record.get('file_name') == record['file_name']:
            try:
                existing_time = datetime.strptime(existing_record.get('upload_time', ''), "%Y-%m-%d %H:%M:%S")
                time_diff = abs((record_time - existing_time).total_seconds())
                if time_diff < 2:  # 2秒内的相同文件名记录认为是重复
                    is_duplicate = True
                    break
            except:
                pass
    
    # 如果不是重复记录，才添加
    if not is_duplicate:
        # 添加新记录（插入到开头）
        history.insert(0, record)
    
    # 限制记录数量（最多保留 1000 条）
    if len(history) > 1000:
        history = history[:1000]
    
    # 保存到文件
    with open(config.HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def load_history(limit=100):
    """
    加载历史记录（优先从数据库读取）
    
    Args:
        limit: 返回记录数量限制
    
    Returns:
        list: 历史记录列表
    """
    # 优先使用数据库
    try:
        from . import db as db_module
        files = db_module.get_files(limit=limit)
        return files
    except ImportError:
        print("[server_upload.history] 警告：无法导入数据库模块，回退到 JSON 文件")
    except Exception as e:
        print(f"[server_upload.history] 从数据库读取失败，回退到 JSON 文件: {e}")
    
    # 回退到 JSON 文件（兼容旧代码）
    if not os.path.exists(config.HISTORY_FILE):
        return []
    
    try:
        with open(config.HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        # 返回最新的 limit 条记录
        return history[:limit]
    except Exception as e:
        print(f"加载历史记录失败: {e}")
        return []
