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
    获取历史转换记录（按时间倒序）

    :param limit: 返回记录数量限制
    :return: 历史记录列表
    """
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

