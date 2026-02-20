import os
import time
import json
from typing import Tuple, List, Dict

from stslib import cfg, tool


def _parse_time_str(time_str: str) -> int:
    """
    将 00:00:00 格式的时间转换为秒数
    """
    time_str = time_str.strip()
    parts = time_str.split(":")
    if len(parts) != 3:
        raise ValueError("时间格式必须为 00:00:00（时:分:秒）")

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
    except ValueError:
        raise ValueError("时间必须是数字，比如 00:01:30")

    if minutes < 0 or minutes >= 60 or seconds < 0 or seconds >= 60 or hours < 0:
        raise ValueError("时间不合法，请检查小时/分钟/秒")

    return hours * 3600 + minutes * 60 + seconds


def cut_audio_segment(src_wav: str, start_time: str, end_time: str) -> Tuple[str, str]:
    """
    从 src_wav 中按时间段截取音频，保持原始格式

    :param src_wav: 源音频文件绝对路径（可以是任何格式）
    :param start_time: 开始时间字符串 00:00:00
    :param end_time: 结束时间字符串 00:00:00
    :return: (输出文件绝对路径, 可下载的 URL)
    """
    if not os.path.exists(src_wav):
        raise FileNotFoundError(f"源音频不存在: {src_wav}")

    start_sec = _parse_time_str(start_time)
    end_sec = _parse_time_str(end_time)

    if end_sec <= start_sec:
        raise ValueError("结束时间必须大于开始时间")

    duration = end_sec - start_sec

    # 截取文件保存目录：static/cut
    cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
    os.makedirs(cut_dir, exist_ok=True)

    # 获取原始文件的扩展名，保持原始格式
    base, original_ext = os.path.splitext(os.path.basename(src_wav))
    if not original_ext:
        original_ext = '.mp3'  # 默认扩展名，如果原文件没有扩展名
    
    out_name = f"{base}_{int(start_sec):06d}_{int(end_sec):06d}{original_ext}"
    out_path = os.path.join(cut_dir, out_name)

    # 使用 ffmpeg 截取音频，尝试保持原编码（copy），如果失败则重新编码但保持格式
    params = [
        "-ss",
        str(start_sec),
        "-i",
        src_wav,
        "-t",
        str(duration),
        "-acodec",
        "copy",
        out_path,
    ]
    rs = tool.runffmpeg(params)
    
    # 如果 copy 失败（可能因为时间点不在关键帧），尝试重新编码但保持原始格式
    if rs != "ok":
        # 移除输出文件（如果已创建）
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except:
                pass
        
        # 重新编码，但保持原始容器格式
        params = [
            "-ss",
            str(start_sec),
            "-i",
            src_wav,
            "-t",
            str(duration),
            "-c",
            "copy",  # 尝试复制所有流
            out_path,
        ]
        rs = tool.runffmpeg(params)
        if rs != "ok":
            raise RuntimeError(f"截取音频失败: {rs}")

    # Flask 的 static 目录映射为 /static
    url = f"/static/cut/{out_name}"
    return out_path, url


def _seconds_to_time_str(seconds: int) -> str:
    """
    将秒数转换为 00:00:00 格式
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def list_cut_history(limit: int = 50) -> List[Dict]:
    """
    获取历史截取记录（按时间倒序）
    返回平铺列表（保持向后兼容）
    """
    cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
    if not os.path.exists(cut_dir):
        return []

    items: List[Dict] = []
    for name in os.listdir(cut_dir):
        # 过滤掉隐藏文件和 JSON 配置文件
        if name.startswith('.') or name.endswith('.json'):
            continue
        path = os.path.join(cut_dir, name)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        mtime = stat.st_mtime
        
        # 从文件名解析开始和结束时间
        # 文件名格式：base_000300_000600.wav
        base_name, ext = os.path.splitext(name)
        parts = base_name.rsplit('_', 2)
        
        start_time_str = "00:00:00"
        end_time_str = "00:00:00"
        duration_str = "00:00:00"
        original_name = name  # 默认使用完整文件名
        
        if len(parts) >= 3:
            try:
                start_sec = int(parts[-2])
                end_sec = int(parts[-1])
                start_time_str = _seconds_to_time_str(start_sec)
                end_time_str = _seconds_to_time_str(end_sec)
                duration_sec = end_sec - start_sec
                duration_str = _seconds_to_time_str(duration_sec)
                # 提取原始文件名（去掉时间戳部分）
                original_name = '_'.join(parts[:-2]) + ext if len(parts) > 2 else name
            except (ValueError, IndexError):
                pass
        
        items.append(
            {
                "file_name": name,
                "original_name": original_name,  # 原始文件名（用于分组）
                "url": f"/static/cut/{name}",
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),  # 转换为 MB
                "mtime": mtime,
                "mtime_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
                "start_time": start_time_str,
                "end_time": end_time_str,
                "time_range": f"{start_time_str}-{end_time_str}",
                "duration": duration_str,
            }
        )

    # 按操作时间降序排序（最新的在前）
    items.sort(key=lambda x: x["mtime"], reverse=True)
    
    # 添加ID字段（从1开始，按时间倒序）
    for idx, item in enumerate(items[:limit], start=1):
        item["id"] = idx
    
    return items[:limit]


def list_cut_history_grouped(limit: int = 50) -> List[Dict]:
    """
    获取历史截取记录（按原始文件名分组）
    返回树形结构数据
    """
    items = list_cut_history(limit=limit * 10)  # 获取更多数据以便分组
    
    # 按原始文件名分组
    groups: Dict[str, List[Dict]] = {}
    for item in items:
        original_name = item.get("original_name", item["file_name"])
        if original_name not in groups:
            groups[original_name] = []
        groups[original_name].append(item)
    
    # 构建树形结构
    result = []
    for original_name, segments in groups.items():
        # 按时间排序（最新的在前）
        segments.sort(key=lambda x: x["mtime"], reverse=True)
        
        # 计算该录音的总信息
        total_size = sum(s["size"] for s in segments)
        total_size_mb = round(total_size / (1024 * 1024), 2)
        latest_time = max(s["mtime"] for s in segments) if segments else 0
        segment_count = len(segments)
        
        result.append({
            "original_name": original_name,
            "segment_count": segment_count,
            "total_size_mb": total_size_mb,
            "latest_time": latest_time,
            "latest_time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(latest_time)),
            "segments": segments[:limit]  # 限制每个录音的片段数量
        })
    
    # 按最新时间排序（最新的录音在前）
    result.sort(key=lambda x: x["latest_time"], reverse=True)
    
    return result[:limit]  # 限制录音数量


def delete_cut_file(file_name: str) -> Tuple[bool, str]:
    """
    删除截取的文件
    
    :param file_name: 文件名（不包含路径）
    :return: (是否成功, 消息)
    """
    cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
    file_path = os.path.join(cut_dir, file_name)
    
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_name}"
    
    try:
        os.remove(file_path)
        return True, f"删除成功: {file_name}"
    except Exception as e:
        return False, f"删除失败: {str(e)}"


def _get_uploaded_files_record_path() -> str:
    """获取上传记录文件路径"""
    return os.path.join(cfg.STATIC_DIR, "cut", ".uploaded_files.json")


def _load_uploaded_files() -> set:
    """加载已上传文件列表"""
    record_path = _get_uploaded_files_record_path()
    if not os.path.exists(record_path):
        return set()
    try:
        with open(record_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get("files", []))
    except:
        return set()


def _save_uploaded_file(file_name: str):
    """标记文件为已上传"""
    record_path = _get_uploaded_files_record_path()
    uploaded_files = _load_uploaded_files()
    uploaded_files.add(file_name)
    
    try:
        os.makedirs(os.path.dirname(record_path), exist_ok=True)
        with open(record_path, 'w', encoding='utf-8') as f:
            json.dump({"files": list(uploaded_files)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[_save_uploaded_file] 保存失败: {e}")


def check_file_uploaded(file_name: str, server_files: List[Dict] = None) -> Tuple[bool, Dict]:
    """
    检查文件是否已上传到服务器
    直接查本地上传记录文件，简单直接
    
    :param file_name: 本地文件名（不包含路径）
    :param server_files: 服务器文件列表（用于初始化已上传记录）
    :return: (是否已上传, 上传记录信息)
    """
    # 直接查本地记录
    uploaded_files = _load_uploaded_files()
    if file_name in uploaded_files:
        return True, {}
    
    # 如果本地记录中没有，但服务器缓存中有匹配的，也标记为已上传
    # 这样可以自动同步已上传的文件
    if server_files:
        # 获取本地文件大小用于匹配
        cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
        file_path = os.path.join(cut_dir, file_name)
        if os.path.exists(file_path):
            try:
                local_file_size = os.path.getsize(file_path)
                # 在服务器文件中查找匹配的（通过 original_name 或文件大小）
                for server_file in server_files:
                    # 检查 original_name
                    if server_file.get("original_name") == file_name:
                        _save_uploaded_file(file_name)  # 自动同步到本地记录
                        return True, server_file
                    # 检查文件大小（完全匹配）
                    if server_file.get("file_size") == local_file_size:
                        _save_uploaded_file(file_name)  # 自动同步到本地记录
                        return True, server_file
            except:
                pass
    
    return False, {}


