#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器文件列表缓存模块
每10秒从服务器获取 /data/audio 目录的文件列表，并保存到 MySQL 数据库
如果 MySQL 不可用，则回退到 JSON 文件
"""

import os
import json
import time
import threading
from pathlib import Path
from . import upload_to_server_tool

# 尝试导入数据库模块
try:
    from . import db as db_module
    USE_MYSQL = True
except ImportError:
    USE_MYSQL = False
    print("[ServerFilesCache] 警告：无法导入数据库模块，将使用 JSON 文件")

# 缓存文件路径（备用，当 MySQL 不可用时使用）
CACHE_DIR = Path(__file__).resolve().parent
CACHE_FILE = CACHE_DIR / "server_files_cache.json"

# 缓存数据（内存缓存，用于快速访问）
_cache_data = {
    "files": [],
    "last_update": None,
    "update_count": 0
}

# 锁，用于线程安全
_cache_lock = threading.Lock()

# 更新锁，确保同一时间只有一个更新任务在执行
_update_lock = threading.Lock()
_is_updating = False

# 后台线程控制
_cache_timer = None
_cache_running = False


def get_cached_files():
    """
    获取缓存的服务器文件列表
    
    Returns:
        list: 文件列表
    """
    # 优先从 MySQL 读取
    if USE_MYSQL:
        try:
            # 确保数据库已初始化
            db_module.init_database()
            files = db_module.get_files(limit=1000)
            with _cache_lock:
                _cache_data["files"] = files
            print(f"[ServerFilesCache] 从 MySQL 读取成功，共 {len(files)} 个文件")
            return files
        except Exception as e:
            print(f"[ServerFilesCache] 从 MySQL 读取失败，使用内存缓存: {e}")
            import traceback
            traceback.print_exc()
    
    # 回退到内存缓存
    with _cache_lock:
        files = _cache_data["files"].copy()
        print(f"[ServerFilesCache] 使用内存缓存，共 {len(files)} 个文件")
        return files


def get_cache_info():
    """
    获取缓存信息
    
    Returns:
        dict: 包含最后更新时间等信息
    """
    # 优先从 MySQL 读取
    if USE_MYSQL:
        try:
            meta = db_module.get_cache_meta()
            files = db_module.get_files(limit=1)  # 只获取数量，不获取全部数据
            file_count = len(db_module.get_files(limit=10000))  # 获取总数
            return {
                "last_update": meta.get("last_update"),
                "update_count": meta.get("update_count", 0),
                "file_count": file_count,
                "is_updating": _is_updating
            }
        except Exception as e:
            print(f"[ServerFilesCache] 从 MySQL 读取缓存信息失败，使用内存缓存: {e}")
    
    # 回退到内存缓存
    with _cache_lock:
        return {
            "last_update": _cache_data["last_update"],
            "update_count": _cache_data["update_count"],
            "file_count": len(_cache_data["files"]),
            "is_updating": _is_updating  # 是否正在更新
        }


def _load_cache_from_file():
    """从 MySQL 或文件加载缓存"""
    global _cache_data
    
    # 优先从 MySQL 加载
    if USE_MYSQL:
        try:
            # 初始化数据库（如果表不存在则创建）
            db_module.init_database()
            
            # 从数据库加载
            files = db_module.get_files(limit=1000)
            meta = db_module.get_cache_meta()
            
            with _cache_lock:
                _cache_data["files"] = files
                _cache_data["last_update"] = meta.get("last_update")
                _cache_data["update_count"] = meta.get("update_count", 0)
            
            print(f"[ServerFilesCache] 从 MySQL 加载缓存，共 {len(files)} 个文件")
            return
        except Exception as e:
            print(f"[ServerFilesCache] 从 MySQL 加载失败，尝试从文件加载: {e}")
    
    # 回退到 JSON 文件
    if CACHE_FILE.exists():
        try:
            with CACHE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
                with _cache_lock:
                    _cache_data = data
            print(f"[ServerFilesCache] 从文件加载缓存，共 {len(_cache_data.get('files', []))} 个文件")
        except Exception as e:
            print(f"[ServerFilesCache] 加载缓存文件失败: {e}")


def _save_cache_to_file():
    """保存缓存到 MySQL 或文件"""
    try:
        with _cache_lock:
            data = _cache_data.copy()
        
        # 优先保存到 MySQL
        if USE_MYSQL:
            try:
                db_module.save_files(data.get("files", []))
                db_module.update_cache_meta(data.get("last_update"), increment_count=True)
                print(f"[ServerFilesCache] 已保存到 MySQL")
                return
            except Exception as e:
                print(f"[ServerFilesCache] 保存到 MySQL 失败，回退到文件: {e}")
        
        # 回退到 JSON 文件
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[ServerFilesCache] 已保存到文件")
    except Exception as e:
        print(f"[ServerFilesCache] 保存缓存失败: {e}")


def _update_cache():
    """更新缓存：从服务器获取文件列表（确保同一时间只有一个更新任务在执行）"""
    global _is_updating
    
    # 使用更新锁确保同一时间只有一个更新任务在执行
    if not _update_lock.acquire(blocking=False):
        # 如果无法获取锁，说明上一次更新还在进行中，跳过本次更新
        print("[ServerFilesCache] 上一次更新还在进行中，跳过本次更新")
        return
    
    try:
        _is_updating = True
        print("[ServerFilesCache] 开始从服务器更新文件列表...")
        files = upload_to_server_tool.list_server_files(limit=1000)  # 获取更多文件
        
        # 处理数据格式：确保符合新的数据库结构
        # list_server_files 返回的 id 是文件名，会被 save_files 用作 file_id
        # original_name 如果和 file_name 相同，save_files 会自动清空
        processed_files = []
        for file_info in files:
            # 确保数据格式正确
            processed_file = {
                'id': file_info.get('id', ''),  # 文件名，会被用作 file_id
                'file_name': file_info.get('file_name', ''),
                'original_name': file_info.get('original_name', ''),  # save_files 会处理，如果和 file_name 相同则留空
                'upload_time': file_info.get('upload_time', ''),
                'upload_duration': file_info.get('upload_duration'),
                'uploader_ip': file_info.get('uploader_ip', ''),
                'file_size': file_info.get('file_size', 0),
                'file_size_mb': file_info.get('file_size_mb', 0),
                'file_duration': file_info.get('file_duration', 0),
                'file_duration_str': file_info.get('file_duration_str', ''),
                'download_url': file_info.get('download_url', ''),
                'remote_path': file_info.get('remote_path', '')
            }
            processed_files.append(processed_file)
        
        # 按上传时间从早到晚排序（与数据库查询保持一致）
        processed_files.sort(key=lambda r: r.get("upload_time", ""), reverse=False)
        
        with _cache_lock:
            _cache_data["files"] = processed_files
            _cache_data["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _cache_data["update_count"] += 1
        
        _save_cache_to_file()
        print(f"[ServerFilesCache] 更新完成，共 {len(processed_files)} 个文件，更新次数: {_cache_data['update_count']}")
    except Exception as e:
        print(f"[ServerFilesCache] 更新缓存失败: {e}")
    finally:
        _is_updating = False
        _update_lock.release()  # 释放锁，允许下一次更新


def _timer_callback():
    """定时器回调函数：执行更新并设置下一次定时器（递归调用）"""
    global _cache_timer, _cache_running
    
    if not _cache_running:
        return
    
    # 执行更新（内部有锁保护，确保串行执行）
    _update_cache()
    
    # 如果还在运行，设置下一次定时器（10秒后）
    if _cache_running:
        _cache_timer = threading.Timer(10.0, _timer_callback)
        _cache_timer.daemon = True
        _cache_timer.start()


def start_cache_thread():
    """启动缓存更新定时任务（使用 threading.Timer，更稳定，兼容 Flask 热更新）"""
    global _cache_timer, _cache_running
    
    # 检测是否在 Flask 重载进程中（避免重复启动）
    # Flask 的 use_reloader=True 会启动两个进程，只在主进程中启动定时任务
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        # 这是在重载进程中，不启动定时任务
        print("[ServerFilesCache] 检测到 Flask 重载进程，跳过定时任务启动")
        return
    
    if _cache_timer is not None:
        print("[ServerFilesCache] 缓存定时任务已在运行")
        return
    
    # 先加载已有缓存
    _load_cache_from_file()
    
    # 启动时立即更新一次
    _update_cache()
    
    # 启动定时任务（使用 threading.Timer，递归调用）
    _cache_running = True
    _cache_timer = threading.Timer(10.0, _timer_callback)
    _cache_timer.daemon = True
    _cache_timer.start()
    print("[ServerFilesCache] 缓存更新定时任务已启动，每10秒更新一次（使用系统 Timer）")


def stop_cache_thread():
    """停止缓存更新定时任务"""
    global _cache_running, _cache_timer
    _cache_running = False
    
    if _cache_timer is not None:
        _cache_timer.cancel()
        _cache_timer = None
    
    print("[ServerFilesCache] 缓存更新定时任务已停止")


# 模块加载时自动启动
if __name__ != "__main__":
    # 延迟启动，避免在导入时就连接服务器
    pass

