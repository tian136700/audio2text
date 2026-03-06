#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具函数模块

包含文件名处理、时长格式化、音频时长获取等工具函数。
"""

import os
import re
import subprocess

# 尝试导入 pypinyin，如果没有安装则使用备用方案
try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
    print("[server_upload.utils] 警告：未安装 pypinyin 库，文件名拼音转换功能将不可用。请运行: pip install pypinyin")


def get_audio_duration(file_path):
    """
    获取音频文件时长（秒）
    
    Args:
        file_path: 音频文件路径
    
    Returns:
        float: 时长（秒），失败返回 0
    """
    try:
        # 使用 ffprobe 获取时长
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return duration
    except Exception as e:
        print(f"获取音频时长失败: {e}")
    return 0


def filename_to_pinyin(filename):
    """
    将文件名转换为拼音（去除扩展名）
    
    Args:
        filename: 文件名（可以包含路径）
    
    Returns:
        str: 拼音字符串，用下划线连接
    """
    # 获取文件名（不含路径和扩展名）
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    if not HAS_PYPINYIN:
        # 如果没有 pypinyin，返回原文件名（只保留字母数字和下划线）
        return re.sub(r'[^\w]', '_', base_name)
    
    try:
        # 使用 pypinyin 转换为拼音
        pinyin_list = lazy_pinyin(base_name, style=Style.NORMAL)
        # 将拼音列表用下划线连接，并转换为小写
        pinyin_str = '_'.join(pinyin_list).lower()
        # 清理特殊字符，只保留字母、数字和下划线
        pinyin_str = re.sub(r'[^\w]', '_', pinyin_str)
        # 去除连续的下划线
        pinyin_str = re.sub(r'_+', '_', pinyin_str)
        # 去除首尾下划线
        pinyin_str = pinyin_str.strip('_')
        return pinyin_str if pinyin_str else 'file'
    except Exception as e:
        print(f"文件名转拼音失败: {e}，使用原文件名")
        return re.sub(r'[^\w]', '_', base_name)


def format_duration_for_filename(seconds):
    """
    格式化时长为适合文件名的格式（如：3分10秒 -> 3m10s）
    
    Args:
        seconds: 秒数
    
    Returns:
        str: 格式化的时长，如 "3m10s" 或 "1h23m45s"
    """
    if seconds <= 0:
        return "0s"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:  # 如果没有小时和分钟，至少显示秒数
        parts.append(f"{secs}s")
    
    return ''.join(parts)


def parse_duration_from_filename(filename):
    """
    从文件名中解析时长（文件名格式：xxx_3m10s_20260107123456.mp3）
    
    Args:
        filename: 文件名
    
    Returns:
        float: 时长（秒），如果解析失败返回 0
    """
    try:
        # 移除扩展名
        name_without_ext = os.path.splitext(filename)[0]
        # 使用正则表达式匹配时长格式：数字+h/m/s（如：1h23m45s, 3m10s, 30s）
        # 匹配模式：(\d+h)?(\d+m)?(\d+s)?
        pattern = r'(\d+h)?(\d+m)?(\d+s)?'
        # 查找所有匹配（文件名中可能有多个这样的模式，取最后一个）
        matches = re.finditer(pattern, name_without_ext)
        duration_str = None
        for match in matches:
            if match.group(0):  # 如果匹配到非空字符串
                duration_str = match.group(0)
        
        if not duration_str:
            return 0
        
        # 解析时长字符串
        hours = 0
        minutes = 0
        seconds = 0
        
        if 'h' in duration_str:
            hours_match = re.search(r'(\d+)h', duration_str)
            if hours_match:
                hours = int(hours_match.group(1))
        
        if 'm' in duration_str:
            minutes_match = re.search(r'(\d+)m', duration_str)
            if minutes_match:
                minutes = int(minutes_match.group(1))
        
        if 's' in duration_str:
            seconds_match = re.search(r'(\d+)s', duration_str)
            if seconds_match:
                seconds = int(seconds_match.group(1))
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return float(total_seconds) if total_seconds > 0 else 0
    except Exception as e:
        print(f"从文件名解析时长失败: {e}")
        return 0


def format_duration(seconds):
    """
    格式化时长为可读字符串
    
    Args:
        seconds: 秒数
    
    Returns:
        str: 格式化的时长，如 "01:23:45"
    """
    if seconds <= 0:
        return "00:00:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
