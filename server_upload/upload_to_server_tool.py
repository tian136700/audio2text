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
import re
from dotenv import load_dotenv

# 尝试导入 pypinyin，如果没有安装则使用备用方案
try:
    from pypinyin import lazy_pinyin, Style
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False
    print("[upload_to_server_tool] 警告：未安装 pypinyin 库，文件名拼音转换功能将不可用。请运行: pip install pypinyin")

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


def upload_file_to_server(local_file_path, remote_filename=None, log_callback=None, uploader_ip=None):
    """
    上传文件到服务器
    
    Args:
        local_file_path: 本地文件路径
        remote_filename: 服务器上的文件名（可选，如果不提供则自动生成：文件名拼音_录音时长_时间戳）
        log_callback: 日志回调函数，用于实时输出处理进度
        uploader_ip: 操作人IP地址（可选）
    
    Returns:
        dict: 包含上传结果的字典
    """
    import time
    
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
    if not SERVER_HOST:
        raise ValueError("SERVER_UPLOAD_HOST 未配置，请在 .env 或环境变量中设置服务器地址")
    if not PUBLIC_URL_PREFIX:
        raise ValueError("SERVER_PUBLIC_URL_PREFIX 未配置，请在 .env 或环境变量中设置公网 URL 前缀")
    if not (SERVER_PASSWORD or SERVER_KEY_PATH):
        raise ValueError("需要配置 SERVER_UPLOAD_PASSWORD 或 SERVER_UPLOAD_KEY_PATH 才能连接服务器")

    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"文件不存在: {local_file_path}")
    
    log(f"[上传] 开始处理文件: {os.path.basename(local_file_path)}")
    if uploader_ip:
        log(f"[上传] 操作人IP: {uploader_ip}")
    
    # 获取文件信息
    log("[上传] 正在获取文件信息...")
    file_size = os.path.getsize(local_file_path)
    log(f"[上传] 文件大小: {round(file_size / (1024 * 1024), 2)} MB")
    
    log("[上传] 正在获取音频时长...")
    file_duration = get_audio_duration(local_file_path)
    if file_duration > 0:
        log(f"[上传] 音频时长: {format_duration(file_duration)}")
    else:
        log("[上传] 警告: 无法获取音频时长，将使用默认值")
    
    # 如果未指定远程文件名，则自动生成：文件名拼音_录音时长_时间戳
    if remote_filename is None:
        log("[上传] 正在生成新文件名...")
        # 获取原文件名（不含扩展名）的拼音
        pinyin_name = filename_to_pinyin(local_file_path)
        log(f"[上传] 文件名拼音: {pinyin_name}")
        # 格式化时长
        duration_str = format_duration_for_filename(file_duration)
        # 生成时间戳（格式：YYYYMMDDHHMMSS）
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # 获取原文件扩展名
        file_ext = os.path.splitext(local_file_path)[1] or '.mp3'
        # 组合新文件名：文件名拼音_录音时长_时间戳.扩展名
        remote_filename = f"{pinyin_name}_{duration_str}_{timestamp}{file_ext}"
        log(f"[上传] 新文件名: {remote_filename}")
    
    # 远程文件路径
    remote_file_path = f"{SERVER_UPLOAD_DIR}/{remote_filename}"
    
    # 创建 SSH 客户端
    log(f"[上传] 正在连接服务器 {SERVER_HOST}:{SERVER_PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 连接服务器
        if SERVER_KEY_PATH:
            log("[上传] 使用密钥认证连接...")
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
            log("[上传] 使用密码认证连接...")
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                password=SERVER_PASSWORD
            )
        log("[上传] 服务器连接成功")
        
        # 创建远程目录
        log(f"[上传] 正在创建远程目录: {SERVER_UPLOAD_DIR}")
        ssh.exec_command(f"mkdir -p {SERVER_UPLOAD_DIR}")
        
        # 使用 SFTP 上传文件
        log(f"[上传] 开始上传文件到服务器...")
        log(f"[上传] 本地路径: {local_file_path}")
        log(f"[上传] 远程路径: {remote_file_path}")
        sftp = ssh.open_sftp()
        
        # 显示上传进度
        def progress_callback(transferred, total):
            if total > 0:
                percent = (transferred / total) * 100
                transferred_mb = round(transferred / (1024 * 1024), 2)
                total_mb = round(total / (1024 * 1024), 2)
                log(f"[上传] 上传进度: {percent:.1f}% ({transferred_mb} MB / {total_mb} MB)")
        
        # paramiko 的 put 方法不支持进度回调，所以我们用另一种方式
        # 先上传，然后显示完成信息
        sftp.put(local_file_path, remote_file_path)
        log(f"[上传] 文件上传完成 ({round(file_size / (1024 * 1024), 2)} MB)")
        sftp.close()
        
        # 设置文件权限（确保 web 服务器可以访问）
        log("[上传] 正在设置文件权限...")
        ssh.exec_command(f"chmod 644 {remote_file_path}")
        
        # 生成公网 URL
        # 注意：如果服务器配置了 nginx，需要确保 nginx 配置了 /data/audio 目录的访问
        # 例如 nginx 配置：location /audio { alias /data/audio; }
        log("[上传] 正在生成公网访问链接...")
        public_url = f"{PUBLIC_URL_PREFIX}/{remote_filename}"
        log(f"[上传] 公网链接: {public_url}")
        
        # 计算上传耗时
        upload_end_time = time.time()
        upload_duration = round(upload_end_time - upload_start_time, 3)
        log(f"[上传] 上传耗时: {upload_duration} 秒")
        
        # 生成记录 ID
        record_id = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + str(hash(remote_filename) % 10000)
        
        # 保存历史记录
        log("[上传] 正在保存历史记录...")
        record = {
            "id": record_id,
            "file_name": remote_filename,
            "original_name": os.path.basename(local_file_path),  # 上传前的中文名称
            "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 上传时间
            "upload_duration": upload_duration,  # 上传耗时（秒）
            "uploader_ip": uploader_ip or "",  # 操作人IP地址
            "file_size": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_duration": round(file_duration, 2),
            "file_duration_str": format_duration(file_duration),
            "download_url": public_url,
            "remote_path": remote_file_path
        }
        
        save_history_record(record)
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
    保存历史记录到数据库
    
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
        print("[upload_to_server_tool] 警告：无法导入数据库模块，回退到 JSON 文件")
    except Exception as e:
        print(f"[upload_to_server_tool] 保存到数据库失败，回退到 JSON 文件: {e}")
    
    # 回退到 JSON 文件（兼容旧代码）
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
        print("[upload_to_server_tool] 警告：无法导入数据库模块，回退到 JSON 文件")
    except Exception as e:
        print(f"[upload_to_server_tool] 从数据库读取失败，回退到 JSON 文件: {e}")
    
    # 回退到 JSON 文件（兼容旧代码）
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

            # 尝试从文件名中解析时长（如果文件名包含时长信息）
            file_duration = parse_duration_from_filename(filename)
            file_duration_str = format_duration(file_duration) if file_duration > 0 else "00:00:00"

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

    # 优先从数据库获取 remote_path
    remote_path = None
    history = None  # 初始化 history 变量
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
            history = load_history(limit=10000)
            for r in history:
                if str(r.get("id")) == str(record_id):
                    remote_path = r.get("remote_path")
                    break
        except Exception as e:
            print(f"[delete_server_file_by_id] 从历史记录获取文件信息失败: {e}")
            history = None

    # 如果还是没有，就直接按文件名拼接路径（record_id 视为文件名）
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

        # 本地历史记录中删除这条记录（如果存在且是从历史记录加载的）
        if history:
            try:
                new_history = [r for r in history if str(r.get("id")) != str(record_id)]
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[delete_server_file_by_id] 更新历史记录文件失败: {e}")

        return {"success": True, "message": "服务器文件删除成功"}
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

            # 尝试从文件名中解析时长（如果文件名包含时长信息）
            file_duration = parse_duration_from_filename(filename)
            file_duration_str = format_duration(file_duration) if file_duration > 0 else "00:00:00"

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

    # 优先从数据库获取 remote_path
    remote_path = None
    history = None  # 初始化 history 变量
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
            history = load_history(limit=10000)
            for r in history:
                if str(r.get("id")) == str(record_id):
                    remote_path = r.get("remote_path")
                    break
        except Exception as e:
            print(f"[delete_server_file_by_id] 从历史记录获取文件信息失败: {e}")
            history = None

    # 如果还是没有，就直接按文件名拼接路径（record_id 视为文件名）
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

        # 本地历史记录中删除这条记录（如果存在且是从历史记录加载的）
        if history:
            try:
                new_history = [r for r in history if str(r.get("id")) != str(record_id)]
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[delete_server_file_by_id] 更新历史记录文件失败: {e}")

        return {"success": True, "message": "服务器文件删除成功"}
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

            # 尝试从文件名中解析时长（如果文件名包含时长信息）
            file_duration = parse_duration_from_filename(filename)
            file_duration_str = format_duration(file_duration) if file_duration > 0 else "00:00:00"

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

    # 优先从数据库获取 remote_path
    remote_path = None
    history = None  # 初始化 history 变量
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
            history = load_history(limit=10000)
            for r in history:
                if str(r.get("id")) == str(record_id):
                    remote_path = r.get("remote_path")
                    break
        except Exception as e:
            print(f"[delete_server_file_by_id] 从历史记录获取文件信息失败: {e}")
            history = None

    # 如果还是没有，就直接按文件名拼接路径（record_id 视为文件名）
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

        # 本地历史记录中删除这条记录（如果存在且是从历史记录加载的）
        if history:
            try:
                new_history = [r for r in history if str(r.get("id")) != str(record_id)]
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[delete_server_file_by_id] 更新历史记录文件失败: {e}")

        return {"success": True, "message": "服务器文件删除成功"}
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

