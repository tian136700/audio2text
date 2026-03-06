#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作模块

提供服务器文件的上传、删除、列表等功能。
"""

import os
from datetime import datetime
from . import config
from . import utils
from . import history
from .ssh_client import SSHClient


def list_server_files(limit=100):
    """
    直接从服务器目录列出录音文件，生成历史记录列表（不依赖本地 JSON）

    Args:
        limit: 返回的最大条数

    Returns:
        list[dict]: 与前端表格兼容的记录列表
    """
    # 基本配置校验
    if not config.SERVER_HOST or not config.SERVER_UPLOAD_DIR or not config.PUBLIC_URL_PREFIX:
        print("list_server_files: 服务器配置不完整，返回空列表")
        return []
    if not (config.SERVER_PASSWORD or config.SERVER_KEY_PATH):
        print("list_server_files: 未配置密码或密钥，返回空列表")
        return []

    ssh_client = SSHClient()
    try:
        ssh_client.connect()
        sftp = ssh_client.open_sftp()
        
        try:
            file_attrs = sftp.listdir_attr(config.SERVER_UPLOAD_DIR)
        finally:
            sftp.close()

        records = []
        for attr in file_attrs:
            # 跳过目录
            if hasattr(attr, "st_mode") and str(attr.st_mode).startswith("4"):
                continue

            filename = attr.filename
            size = getattr(attr, "st_size", 0)
            mtime = getattr(attr, "st_mtime", 0)

            upload_time = ""
            if mtime:
                try:
                    upload_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    upload_time = ""

            public_url = f"{config.PUBLIC_URL_PREFIX.rstrip('/')}/{filename}"
            remote_path = f"{config.SERVER_UPLOAD_DIR.rstrip('/')}/{filename}"

            # 尝试从文件名中解析时长（如果文件名包含时长信息）
            file_duration = utils.parse_duration_from_filename(filename)
            file_duration_str = utils.format_duration(file_duration) if file_duration > 0 else "00:00:00"

            record = {
                "id": filename,  # 直接使用文件名作为 ID，删除时也用这个
                "file_name": filename,
                "original_name": filename,  # 上传前的中文名称（从服务器列表获取时可能无法获取，使用文件名）
                "upload_time": upload_time,  # 上传时间
                "upload_duration": None,  # 上传耗时（从服务器列表获取时无法获取）
                "uploader_ip": "",  # 操作人IP地址（从服务器列表获取时无法获取）
                "file_size": size,
                "file_size_mb": round(size / (1024 * 1024), 2) if size else 0,
                "file_duration": round(file_duration, 2),
                "file_duration_str": file_duration_str,
                "download_url": public_url,
                "remote_path": remote_path,
            }
            records.append(record)

        # 按修改时间倒序排序（最近的在前）
        records.sort(key=lambda r: r.get("upload_time", ""), reverse=True)
        return records[:limit]
    except Exception as e:
        print(f"list_server_files 失败: {e}")
        return []
    finally:
        ssh_client.close()


def delete_server_file_by_id(record_id):
    """
    根据历史记录 ID 删除服务器上的录音文件，并同步删除本地历史记录。

    Args:
        record_id: 历史记录中的 id 字段

    Returns:
        dict: {success: bool, message: str}
    """
    # 基本配置校验
    if not config.SERVER_HOST:
        return {"success": False, "message": "SERVER_UPLOAD_HOST 未配置"}
    if not (config.SERVER_PASSWORD or config.SERVER_KEY_PATH):
        return {"success": False, "message": "需要配置 SERVER_UPLOAD_PASSWORD 或 SERVER_UPLOAD_KEY_PATH"}

    # 优先从数据库获取 remote_path
    remote_path = None
    history_data = None  # 初始化 history 变量
    try:
        from . import db as db_module
        files = db_module.get_files(limit=10000)
        for r in files:
            if str(r.get("id")) == str(record_id):
                remote_path = r.get("remote_path")
                break
    except Exception as e:
        print(f"[delete_server_file_by_id] 从数据库获取文件信息失败: {e}")
    
    # 如果数据库中没有，从历史记录获取（兼容旧数据）
    if not remote_path:
        try:
            history_data = history.load_history(limit=10000)
            for r in history_data:
                if str(r.get("id")) == str(record_id):
                    remote_path = r.get("remote_path")
                    break
        except Exception as e:
            print(f"[delete_server_file_by_id] 从历史记录获取文件信息失败: {e}")
            history_data = None

    # 如果还是没有，就直接按文件名拼接路径（record_id 视为文件名）
    if not remote_path:
        remote_path = f"{config.SERVER_UPLOAD_DIR.rstrip('/')}/{record_id}"

    # 连接服务器并删除文件
    ssh_client = SSHClient()
    try:
        ssh_client.connect()
        
        cmd = f"rm -f {remote_path}"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()

        if exit_status != 0:
            err_msg = stderr.read().decode("utf-8", errors="ignore")
            return {"success": False, "message": f"服务器删除失败: {err_msg or '未知错误'}"}

        # 本地历史记录中删除这条记录（如果存在且是从历史记录加载的）
        if history_data:
            try:
                import json
                new_history = [r for r in history_data if str(r.get("id")) != str(record_id)]
                with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[delete_server_file_by_id] 更新历史记录文件失败: {e}")

        return {"success": True, "message": "服务器文件删除成功"}
    except Exception as e:
        return {"success": False, "message": f"删除失败: {e}"}
    finally:
        ssh_client.close()
