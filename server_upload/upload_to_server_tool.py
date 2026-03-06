#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传文件到服务器工具

所有敏感信息（服务器 IP、用户名、密码等）从环境变量 / 配置文件中读取，
避免直接写在代码里，便于安全地提交到 git。

本模块已重构为多个子模块：
- config.py: 配置信息
- utils.py: 工具函数（文件名处理、时长格式化等）
- ssh_client.py: SSH 连接封装
- file_operations.py: 文件操作（上传、删除、列表）
- history.py: 历史记录管理
"""

import os
import time
from datetime import datetime
from . import config
from . import utils
from . import history
from .ssh_client import SSHClient

# 为了保持向后兼容，导出这些函数和变量
from .file_operations import list_server_files, delete_server_file_by_id
from .history import load_history, save_history_record

# 导出配置变量（保持向后兼容）
SERVER_HOST = config.SERVER_HOST
SERVER_PORT = config.SERVER_PORT
SERVER_USER = config.SERVER_USER
SERVER_PASSWORD = config.SERVER_PASSWORD
SERVER_KEY_PATH = config.SERVER_KEY_PATH
SERVER_UPLOAD_DIR = config.SERVER_UPLOAD_DIR
PUBLIC_URL_PREFIX = config.PUBLIC_URL_PREFIX
HISTORY_FILE = config.HISTORY_FILE

# 导出工具函数（保持向后兼容）
get_audio_duration = utils.get_audio_duration
filename_to_pinyin = utils.filename_to_pinyin
format_duration_for_filename = utils.format_duration_for_filename
parse_duration_from_filename = utils.parse_duration_from_filename
format_duration = utils.format_duration


def upload_file_to_server(local_file_path, remote_filename=None, log_callback=None, uploader_ip=None, original_name=None, record_id=None):
    """
    上传文件到服务器
    
    Args:
        local_file_path: 本地文件路径
        remote_filename: 服务器上的文件名（可选，如果不提供则自动生成：文件名拼音_录音时长_时间戳）
        log_callback: 日志回调函数，用于实时输出处理进度
        uploader_ip: 操作人IP地址（可选）
        original_name: 原始文件名（可选，用于显示）
        record_id: 数据库记录ID（可选，如果提供则更新已有记录）
    
    Returns:
        dict: 包含上传结果的字典
    """
    def log(msg):
        """输出日志"""
        if log_callback:
            try:
                log_callback(msg)
            except (BrokenPipeError, ConnectionError, OSError) as e:
                # 客户端断开连接，记录但不影响上传任务
                print(f"[upload_file_to_server] log_callback 错误（客户端断开）: {e}")
            except Exception as e:
                # 其他错误，记录但不影响上传任务
                print(f"[upload_file_to_server] log_callback 错误: {e}")
        else:
            print(msg)
    
    # 记录上传开始时间
    upload_start_time = time.time()
    
    # 基本配置校验（避免未配置就调用）
    if not config.SERVER_HOST:
        raise ValueError("SERVER_UPLOAD_HOST 未配置，请在 .env 或环境变量中设置服务器地址")
    if not config.PUBLIC_URL_PREFIX:
        raise ValueError("SERVER_PUBLIC_URL_PREFIX 未配置，请在 .env 或环境变量中设置公网 URL 前缀")
    if not (config.SERVER_PASSWORD or config.SERVER_KEY_PATH):
        raise ValueError("需要配置 SERVER_UPLOAD_PASSWORD 或 SERVER_UPLOAD_KEY_PATH 才能连接服务器")

    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"文件不存在: {local_file_path}")
    
    # 如果前端单独传了原始文件名（如 zhou.mp3），优先使用该名称作为"原文件中文名称"
    if original_name:
        orig_display_name = original_name
    else:
        orig_display_name = os.path.basename(local_file_path)
    
    log(f"[上传] 开始处理文件: {orig_display_name}")
    if uploader_ip:
        log(f"[上传] 操作人IP: {uploader_ip}")
    
    # 获取文件信息
    log("[上传] 正在获取文件信息...")
    file_size = os.path.getsize(local_file_path)
    log(f"[上传] 文件大小: {round(file_size / (1024 * 1024), 2)} MB")
    
    log("[上传] 正在获取音频时长...")
    file_duration = utils.get_audio_duration(local_file_path)
    if file_duration > 0:
        log(f"[上传] 音频时长: {utils.format_duration(file_duration)}")
    else:
        log("[上传] 警告: 无法获取音频时长，将使用默认值")
    
    # 如果未指定远程文件名，则自动生成：文件名拼音_录音时长_时间戳
    if remote_filename is None:
        log("[上传] 正在生成新文件名...")
        # 获取原文件名（不含扩展名）的拼音
        pinyin_name = utils.filename_to_pinyin(local_file_path)
        log(f"[上传] 文件名拼音: {pinyin_name}")
        # 格式化时长
        duration_str = utils.format_duration_for_filename(file_duration)
        # 生成时间戳（格式：YYYYMMDDHHMMSS）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # 获取原文件扩展名
        file_ext = os.path.splitext(local_file_path)[1] or '.mp3'
        # 组合新文件名：文件名拼音_录音时长_时间戳.扩展名
        remote_filename = f"{pinyin_name}_{duration_str}_{timestamp}{file_ext}"
        log(f"[上传] 新文件名: {remote_filename}")
    
    # 远程文件路径
    remote_file_path = f"{config.SERVER_UPLOAD_DIR}/{remote_filename}"
    
    # 创建 SSH 客户端
    log(f"[上传] 正在连接服务器 {config.SERVER_HOST}:{config.SERVER_PORT}...")
    ssh_client = SSHClient()
    
    try:
        # 连接服务器
        ssh_client.connect()
        log("[上传] 服务器连接成功")
        
        # 创建远程目录
        log(f"[上传] 正在创建远程目录: {config.SERVER_UPLOAD_DIR}")
        ssh_client.exec_command(f"mkdir -p {config.SERVER_UPLOAD_DIR}")
        
        # 使用 SFTP 上传文件
        log(f"[上传] 开始上传文件到服务器...")
        log(f"[上传] 本地路径: {local_file_path}")
        log(f"[上传] 远程路径: {remote_file_path}")
        sftp = ssh_client.open_sftp()
        
        # paramiko 的 put 方法不支持进度回调，所以我们用另一种方式
        # 先上传，然后显示完成信息
        sftp.put(local_file_path, remote_file_path)
        log(f"[上传] 文件上传完成 ({round(file_size / (1024 * 1024), 2)} MB)")
        sftp.close()
        
        # 设置文件权限（确保 web 服务器可以访问）
        log("[上传] 正在设置文件权限...")
        ssh_client.exec_command(f"chmod 644 {remote_file_path}")
        
        # 生成公网 URL
        # 注意：如果服务器配置了 nginx，需要确保 nginx 配置了 /data/audio 目录的访问
        # 例如 nginx 配置：location /audio { alias /data/audio; }
        log("[上传] 正在生成公网访问链接...")
        public_url = f"{config.PUBLIC_URL_PREFIX}/{remote_filename}"
        log(f"[上传] 公网链接: {public_url}")
        
        # 计算上传耗时
        upload_end_time = time.time()
        upload_duration = round(upload_end_time - upload_start_time, 3)
        log(f"[上传] 上传耗时: {upload_duration} 秒")
        
        # 保存历史记录 / 或更新已有记录
        log("[上传] 正在保存历史记录...")
        record = {
            "id": record_id,  # 如果传入了 record_id，使用它；否则稍后生成
            "file_name": remote_filename,
            "original_name": orig_display_name,  # 上传前的中文名称（浏览器里选择的原始文件名）
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 上传时间
            "upload_duration": upload_duration,  # 上传耗时（秒）
            "uploader_ip": uploader_ip or "",  # 操作人IP地址
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_duration": round(file_duration, 2),
            "file_duration_str": utils.format_duration(file_duration),
            "download_url": public_url,
            "remote_path": remote_file_path
        }
        
        # 如果传入了 record_id，说明数据库中已经有占位记录，这里只做更新不再新增
        if record_id:
            try:
                from . import db as db_module
                
                # 更新数据库记录（不更新 original_name，保持占位记录时的原始文件名）
                update_success = db_module.update_file_by_id(
                    record_id,
                    file_name=record["file_name"],
                    upload_time=record["upload_time"],
                    upload_duration=record["upload_duration"],
                    uploader_ip=record["uploader_ip"],
                    file_size=record["file_size"],
                    file_size_mb=record["file_size_mb"],
                    file_duration=record["file_duration"],
                    file_duration_str=record["file_duration_str"],
                    download_url=record["download_url"],
                    remote_path=record["remote_path"],
                )
                
                if update_success:
                    # 确认更新成功：查询数据库验证记录已更新
                    log("[上传] 数据库更新完成，正在确认更新结果...")
                    max_retries = 3
                    retry_delay = 0.2  # 200ms
                    confirmed = False
                    
                    for attempt in range(max_retries):
                        time.sleep(retry_delay)  # 等待数据库提交完成
                        updated_record = db_module.get_file_by_id(record_id)
                        
                        if updated_record and updated_record.get('file_name') == record["file_name"]:
                            # 确认 file_name 已更新成功
                            confirmed = True
                            log(f"[上传] 历史记录更新已确认（尝试 {attempt + 1}/{max_retries}）")
                            # 使用数据库中的最新数据更新 record（确保数据一致性）
                            record.update(updated_record)
                            record['id'] = record_id  # 确保 ID 正确
                            break
                        else:
                            log(f"[上传] 确认更新失败（尝试 {attempt + 1}/{max_retries}），等待后重试...")
                    
                    if confirmed:
                        log("[上传] 历史记录已更新并确认成功")
                    else:
                        log("[上传] 警告：历史记录更新后确认失败，但文件已上传成功")
                        # 即使确认失败，文件已上传成功，仍然返回成功，但记录警告
                else:
                    log("[上传] 警告：历史记录更新失败（返回 False）")
                    # 即使更新失败，文件已上传成功，仍然返回成功，但记录警告
            except Exception as e:
                log(f"[上传] 更新历史记录失败: {e}")
                import traceback
                traceback.print_exc()
                # 即使更新失败，文件已上传成功，仍然返回成功，但记录错误
        else:
            # 旧逻辑：直接新增一条历史记录
            history.save_history_record(record)
            log("[上传] 历史记录已保存")
        log("[上传] 上传流程完成 ✅")
        
        return {
            "success": True,
            "record": record,
            "url": public_url
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        ssh_client.close()
