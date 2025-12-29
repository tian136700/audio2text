import os
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
    从 src_wav 中按时间段截取音频

    :param src_wav: 源 wav 文件绝对路径
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

    base, _ = os.path.splitext(os.path.basename(src_wav))
    out_name = f"{base}_{int(start_sec):06d}_{int(end_sec):06d}.wav"
    out_path = os.path.join(cut_dir, out_name)

    # 使用 ffmpeg 截取音频，保持原编码（copy）
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
    if rs != "ok":
        raise RuntimeError(f"截取音频失败: {rs}")

    # Flask 的 static 目录映射为 /static
    url = f"/static/cut/{out_name}"
    return out_path, url


def list_cut_history(limit: int = 50) -> List[Dict]:
    """
    获取历史截取记录（按时间倒序）
    """
    cut_dir = os.path.join(cfg.STATIC_DIR, "cut")
    if not os.path.exists(cut_dir):
        return []

    items: List[Dict] = []
    for name in os.listdir(cut_dir):
        path = os.path.join(cut_dir, name)
        if not os.path.isfile(path):
            continue
        stat = os.stat(path)
        items.append(
            {
                "file_name": name,
                "url": f"/static/cut/{name}",
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
        )

    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items[:limit]


