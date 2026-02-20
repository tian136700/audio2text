import os
import time
from typing import Tuple, List, Dict
import threading

from stslib import cfg, tool


# 转换任务进度字典 {task_id: {"progress": 0-100, "status": "processing|completed|error", "message": ""}}
CONVERT_PROGRESS = {}
CONVERT_LOCK = threading.Lock()


def convert_to_mp3(src_file: str, task_id: str = None) -> Tuple[str, str]:
    """
    将音频文件转换为 MP3 格式

    :param src_file: 源音频文件绝对路径
    :param task_id: 任务ID，用于跟踪进度
    :return: (输出文件绝对路径, 可下载的 URL)
    """
    if not os.path.exists(src_file):
        raise FileNotFoundError(f"源音频不存在: {src_file}")

    # 更新进度：开始转换
    if task_id:
        with CONVERT_LOCK:
            CONVERT_PROGRESS[task_id] = {
                "progress": 10,
                "status": "processing",
                "message": "正在准备转换..."
            }

    # 转换文件保存目录：static/convert
    convert_dir = os.path.join(cfg.STATIC_DIR, "convert")
    os.makedirs(convert_dir, exist_ok=True)

    # 获取源文件名（不含扩展名）和扩展名
    base_name = os.path.splitext(os.path.basename(src_file))[0]
    out_name = f"{base_name}.mp3"
    out_path = os.path.join(convert_dir, out_name)

    # 如果文件已存在，添加时间戳避免覆盖
    if os.path.exists(out_path):
        timestamp = int(time.time())
        out_name = f"{base_name}_{timestamp}.mp3"
        out_path = os.path.join(convert_dir, out_name)

    if task_id:
        with CONVERT_LOCK:
            CONVERT_PROGRESS[task_id] = {
                "progress": 30,
                "status": "processing",
                "message": "正在转换音频格式..."
            }

    # 使用 ffmpeg 转换为 MP3
    # 参数说明：
    # -i: 输入文件
    # -codec:a libmp3lame: 使用 MP3 编码器
    # -q:a 2: 音频质量（0-9，0最高质量，2是高质量）
    # -y: 覆盖输出文件（虽然我们已经检查了，但加上更安全）
    params = [
        "-i",
        src_file,
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "2",  # 高质量 MP3
        "-y",
        out_path,
    ]

    if task_id:
        with CONVERT_LOCK:
            CONVERT_PROGRESS[task_id] = {
                "progress": 50,
                "status": "processing",
                "message": "正在编码 MP3..."
            }

    rs = tool.runffmpeg(params)
    if rs != "ok":
        if task_id:
            with CONVERT_LOCK:
                CONVERT_PROGRESS[task_id] = {
                    "progress": 0,
                    "status": "error",
                    "message": f"转换失败: {rs}"
                }
        raise RuntimeError(f"转换音频失败: {rs}")

    if task_id:
        with CONVERT_LOCK:
            CONVERT_PROGRESS[task_id] = {
                "progress": 90,
                "status": "processing",
                "message": "正在完成转换..."
            }

    # 验证输出文件是否存在
    if not os.path.exists(out_path):
        if task_id:
            with CONVERT_LOCK:
                CONVERT_PROGRESS[task_id] = {
                    "progress": 0,
                    "status": "error",
                    "message": "转换失败：输出文件未生成"
                }
        raise RuntimeError("转换失败：输出文件未生成")

    if task_id:
        with CONVERT_LOCK:
            CONVERT_PROGRESS[task_id] = {
                "progress": 100,
                "status": "completed",
                "message": "转换完成"
            }

    # Flask 的 static 目录映射为 /static
    url = f"/static/convert/{out_name}"
    return out_path, url


def get_convert_progress(task_id: str) -> Dict:
    """
    获取转换进度

    :param task_id: 任务ID
    :return: 进度信息字典
    """
    with CONVERT_LOCK:
        return CONVERT_PROGRESS.get(task_id, {
            "progress": 0,
            "status": "unknown",
            "message": "任务不存在"
        })


def clear_convert_progress(task_id: str):
    """
    清除转换进度（转换完成后可以清理）

    :param task_id: 任务ID
    """
    with CONVERT_LOCK:
        if task_id in CONVERT_PROGRESS:
            del CONVERT_PROGRESS[task_id]


def list_convert_history(limit: int = 50) -> List[Dict]:
    """
    获取历史转换记录（从数据库 server_files 表读取，按上传时间倒序）

    :param limit: 返回记录数量限制
    :return: 历史记录列表
    """
    # 优先从数据库读取
    try:
        from server_upload import db as db_module
        files = db_module.get_files(limit=limit)
        
        items: List[Dict] = []
        for file_info in files:
            file_name = file_info.get('file_name', '')
            # 只处理 MP3 文件（或者所有文件，因为转换后的文件可能在服务器上）
            # 检查文件是否在 convert 目录中
            convert_dir = os.path.join(cfg.STATIC_DIR, "convert")
            convert_file_path = os.path.join(convert_dir, file_name)
            
            # 如果文件在 convert 目录中，或者文件是 MP3 格式，则包含在转换历史中
            if file_name.lower().endswith('.mp3') or os.path.exists(convert_file_path):
                # 获取文件大小（优先从数据库，否则从文件系统）
                file_size = file_info.get('file_size', 0)
                if not file_size and os.path.exists(convert_file_path):
                    try:
                        file_size = os.path.getsize(convert_file_path)
                    except:
                        file_size = 0
                
                # 获取操作时间（优先从数据库的上传时间）
                upload_time = file_info.get('upload_time', '')
                mtime = None
                mtime_str = upload_time
                
                # 如果数据库中没有时间，尝试从文件系统获取
                if not upload_time and os.path.exists(convert_file_path):
                    try:
                        mtime = os.path.getmtime(convert_file_path)
                        mtime_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                    except:
                        mtime_str = ""
                
                # 获取下载 URL（优先使用数据库中的 download_url，否则使用 convert 目录的 URL）
                download_url = file_info.get('download_url', '')
                if not download_url:
                    download_url = f"/static/convert/{file_name}"
                
                # 获取原始文件名（中文名称）
                original_name = file_info.get('original_name', '')
                if not original_name:
                    # 如果没有中文名称，尝试从文件名提取（去除时间戳后缀）
                    base_name = os.path.splitext(file_name)[0]
                    if '_' in base_name:
                        parts = base_name.rsplit('_', 1)
                        if len(parts) == 2 and parts[1].isdigit():
                            original_name = parts[0]
                        else:
                            original_name = base_name
                    else:
                        original_name = base_name
                
                items.append({
                    "id": file_info.get('id', 0),  # 数据库自增ID
                    "file_id": file_info.get('file_id', ''),  # 文件ID（原文件名）
                    "file_name": file_name,
                    "original_name": original_name,  # 原始文件名（中文名称，如果没有则留空）
                    "url": download_url,
                    "download_url": file_info.get('download_url', download_url),  # 下载链接
                    "size": file_size,
                    "size_mb": file_info.get('file_size_mb', round(file_size / (1024 * 1024), 2)),
                    "file_duration": file_info.get('file_duration', 0),  # 文件时长（秒）
                    "file_duration_str": file_info.get('file_duration_str', ''),  # 文件时长（字符串格式）
                    "upload_time": file_info.get('upload_time', ''),  # 上传时间
                    "upload_duration": file_info.get('upload_duration'),  # 上传耗时（秒）
                    "uploader_ip": file_info.get('uploader_ip', ''),  # 操作人IP地址
                    "remote_path": file_info.get('remote_path', ''),  # 服务器路径
                    "mtime": mtime,
                    "mtime_str": mtime_str,
                })
        
        # 按操作时间降序排序（最新的在前）
        items.sort(key=lambda x: x.get("mtime_str", ""), reverse=True)
        
        return items[:limit]
    except ImportError:
        print("[convert_mp3_tool] 警告：无法导入数据库模块，回退到文件系统")
    except Exception as e:
        print(f"[convert_mp3_tool] 从数据库读取转换历史失败: {e}")
    
    # 回退到文件系统读取（兼容旧代码）
    convert_dir = os.path.join(cfg.STATIC_DIR, "convert")
    if not os.path.exists(convert_dir):
        return []

    items: List[Dict] = []
    for name in os.listdir(convert_dir):
        path = os.path.join(convert_dir, name)
        if not os.path.isfile(path):
            continue

        # 只处理 .mp3 文件
        if not name.lower().endswith('.mp3'):
            continue

        stat = os.stat(path)
        mtime = stat.st_mtime
        size = stat.st_size

        # 获取原始文件名（去除时间戳后缀）
        base_name = os.path.splitext(name)[0]
        # 如果文件名包含时间戳（格式：base_timestamp），提取原始名称
        if '_' in base_name:
            parts = base_name.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                original_name = parts[0]
            else:
                original_name = base_name
        else:
            original_name = base_name

        items.append(
            {
                "file_name": name,
                "original_name": original_name,  # 原始文件名（不含扩展名）
                "url": f"/static/convert/{name}",
                "size": size,
                "size_mb": round(size / (1024 * 1024), 2),  # 转换为 MB
                "mtime": mtime,
                "mtime_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
            }
        )

    # 按操作时间降序排序（最新的在前）
    items.sort(key=lambda x: x["mtime"], reverse=True)

    # 添加ID字段（从1开始，按时间倒序）
    for idx, item in enumerate(items[:limit], start=1):
        item["id"] = idx

    return items[:limit]

