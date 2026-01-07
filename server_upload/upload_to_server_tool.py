#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传文件到服务器工具

所有敏感信息（服务器 IP、用户名、密码等）从环境变量 / 配置文件中读取，
避免直接写在代码里，便于安全地提交到 git。
"""

import os
import json
import paramiko
from datetime import datetime
from pathlib import Path
import subprocess
from dotenv import load_dotenv

# 加载 .env 等环境配置（如果已在主程序中加载，这里再次调用也没问题）
load_dotenv()

# ==================== 配置信息（从环境变量获取） ====================
# 服务器配置
SERVER_HOST = os.getenv("SERVER_UPLOAD_HOST")            # 服务器 IP 或域名
SERVER_PORT = int(os.getenv("SERVER_UPLOAD_PORT", "22")) # SSH 端口，默认 22
SERVER_USER = os.getenv("SERVER_UPLOAD_USER", "root")    # SSH 用户名
SERVER_PASSWORD = os.getenv("SERVER_UPLOAD_PASSWORD")    # SSH 密码（推荐只用环境变量配置）
SERVER_KEY_PATH = os.getenv("SERVER_UPLOAD_KEY_PATH") or None  # SSH 私钥路径（可选）

# 服务器上的文件存储路径（如：/data/audio）
SERVER_UPLOAD_DIR = os.getenv("SERVER_UPLOAD_DIR", "/data/audio")

# 服务器公网访问 URL 前缀（如：http://你的服务器IP或域名/audio）
PUBLIC_URL_PREFIX = os.getenv("SERVER_PUBLIC_URL_PREFIX")

# 历史记录文件路径（放在当前功能文件夹下）
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "upload_history.json")


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


def upload_file_to_server(local_file_path, remote_filename=None):
    """
    上传文件到服务器
    
    Args:
        local_file_path: 本地文件路径
        remote_filename: 服务器上的文件名（可选）
    
    Returns:
        dict: 包含上传结果的字典
    """
    # 基本配置校验（避免未配置就调用）
    if not SERVER_HOST:
        raise ValueError("SERVER_UPLOAD_HOST 未配置，请在 .env 或环境变量中设置服务器地址")
    if not PUBLIC_URL_PREFIX:
        raise ValueError("SERVER_PUBLIC_URL_PREFIX 未配置，请在 .env 或环境变量中设置公网 URL 前缀")
    if not (SERVER_PASSWORD or SERVER_KEY_PATH):
        raise ValueError("需要配置 SERVER_UPLOAD_PASSWORD 或 SERVER_UPLOAD_KEY_PATH 才能连接服务器")

    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"文件不存在: {local_file_path}")
    
    if remote_filename is None:
        remote_filename = os.path.basename(local_file_path)
    
    # 获取文件信息
    file_size = os.path.getsize(local_file_path)
    file_duration = get_audio_duration(local_file_path)
    
    # 远程文件路径
    remote_file_path = f"{SERVER_UPLOAD_DIR}/{remote_filename}"
    
    # 创建 SSH 客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 连接服务器
        if SERVER_KEY_PATH:
            private_key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                pkey=private_key
            )
        else:
            if SERVER_PASSWORD is None:
                raise ValueError("需要设置 SERVER_PASSWORD 或 SERVER_KEY_PATH")
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                password=SERVER_PASSWORD
            )
        
        # 创建远程目录
        ssh.exec_command(f"mkdir -p {SERVER_UPLOAD_DIR}")
        
        # 使用 SFTP 上传文件
        sftp = ssh.open_sftp()
        sftp.put(local_file_path, remote_file_path)
        sftp.close()
        
        # 设置文件权限（确保 web 服务器可以访问）
        ssh.exec_command(f"chmod 644 {remote_file_path}")
        
        # 生成公网 URL
        # 注意：如果服务器配置了 nginx，需要确保 nginx 配置了 /data/audio 目录的访问
        # 例如 nginx 配置：location /audio { alias /data/audio; }
        public_url = f"{PUBLIC_URL_PREFIX}/{remote_filename}"
        
        # 生成记录 ID
        record_id = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + str(hash(remote_filename) % 10000)
        
        # 保存历史记录
        record = {
            "id": record_id,
            "file_name": remote_filename,
            "original_name": os.path.basename(local_file_path),
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_duration": round(file_duration, 2),
            "file_duration_str": format_duration(file_duration),
            "download_url": public_url,
            "remote_path": remote_file_path
        }
        
        save_history_record(record)
        
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
        ssh.close()


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


def save_history_record(record):
    """
    保存历史记录到文件
    
    Args:
        record: 记录字典
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
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
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def load_history(limit=100):
    """
    加载历史记录
    
    Args:
        limit: 返回记录数量限制
    
    Returns:
        list: 历史记录列表
    """
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            history = json.load(f)
        # 返回最新的 limit 条记录
        return history[:limit]
    except Exception as e:
        print(f"加载历史记录失败: {e}")
        return []


def list_server_files(limit=100):
    """
    直接从服务器目录列出录音文件，生成历史记录列表（不依赖本地 JSON）

    Args:
        limit: 返回的最大条数

    Returns:
        list[dict]: 与前端表格兼容的记录列表
    """
    # 基本配置校验
    if not SERVER_HOST or not SERVER_UPLOAD_DIR or not PUBLIC_URL_PREFIX:
        print("list_server_files: 服务器配置不完整，返回空列表")
        return []
    if not (SERVER_PASSWORD or SERVER_KEY_PATH):
        print("list_server_files: 未配置密码或密钥，返回空列表")
        return []

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 连接服务器
        if SERVER_KEY_PATH:
            private_key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                pkey=private_key,
            )
        else:
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                password=SERVER_PASSWORD,
            )

        # 使用 SFTP 列出目录中文件
        sftp = ssh.open_sftp()
        try:
            file_attrs = sftp.listdir_attr(SERVER_UPLOAD_DIR)
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

            public_url = f"{PUBLIC_URL_PREFIX.rstrip('/')}/{filename}"
            remote_path = f"{SERVER_UPLOAD_DIR.rstrip('/')}/{filename}"

            record = {
                "id": filename,  # 直接使用文件名作为 ID，删除时也用这个
                "file_name": filename,
                "original_name": filename,
                "upload_time": upload_time,
                "file_size": size,
                "file_size_mb": round(size / (1024 * 1024), 2) if size else 0,
                "file_duration": 0,
                "file_duration_str": "00:00:00",
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
        try:
            ssh.close()
        except Exception:
            pass


def delete_server_file_by_id(record_id):
    """
    根据历史记录 ID 删除服务器上的录音文件，并同步删除本地历史记录。

    Args:
        record_id: 历史记录中的 id 字段

    Returns:
        dict: {success: bool, message: str}
    """
    # 基本配置校验
    if not SERVER_HOST:
        return {"success": False, "message": "SERVER_UPLOAD_HOST 未配置"}
    if not (SERVER_PASSWORD or SERVER_KEY_PATH):
        return {"success": False, "message": "需要配置 SERVER_UPLOAD_PASSWORD 或 SERVER_UPLOAD_KEY_PATH"}

    # 优先从本地历史记录获取 remote_path（兼容旧数据）
    remote_path = None
    history = load_history(limit=10000)
    for r in history:
        if r.get("id") == record_id:
            remote_path = r.get("remote_path")
            break

    # 如果本地记录中没有，就直接按文件名拼接路径（record_id 视为文件名）
    if not remote_path:
        remote_path = f"{SERVER_UPLOAD_DIR.rstrip('/')}/{record_id}"

    # 连接服务器并删除文件
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if SERVER_KEY_PATH:
            private_key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                pkey=private_key,
            )
        else:
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                password=SERVER_PASSWORD,
            )

        cmd = f"rm -f {remote_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()

        if exit_status != 0:
            err_msg = stderr.read().decode("utf-8", errors="ignore")
            return {"success": False, "message": f"服务器删除失败: {err_msg or '未知错误'}"}

        # 本地历史记录中删除这条记录（如果存在）
        if history:
            new_history = [r for r in history if r.get("id") != record_id]
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

        return {"success": True, "message": "服务器文件和历史记录删除成功（如存在）"}
    except Exception as e:
        return {"success": False, "message": f"删除失败: {e}"}
    finally:
        try:
            ssh.close()
        except Exception:
            pass
    
    try:
        history = load_history(limit=10000)  # 加载所有记录
        history = [r for r in history if r.get('id') != record_id]
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"删除历史记录失败: {e}")
        return False

