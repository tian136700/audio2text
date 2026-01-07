#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能分段工具
使用 VAD（语音活动检测）在静音点智能切分音频，避免在说话中间截断
"""

import os
import time
from typing import List, Dict, Tuple
from faster_whisper import WhisperModel
from stslib import cfg, tool


def detect_silence_segments(
    wav_file: str,
    min_silence_duration: float = 1.5,  # 最小静音时长（秒）
    target_segment_duration: float = 300.0,  # 目标每段5分钟（300秒）
    max_segment_duration: float = 600.0,  # 最大每段10分钟
) -> List[Dict]:
    """
    使用 VAD 检测静音点，智能分段音频
    
    :param wav_file: 音频文件路径
    :param min_silence_duration: 最小静音时长（秒），用于判断分段点
    :param target_segment_duration: 目标每段时长（秒），尽量接近但不强制
    :param max_segment_duration: 最大每段时长（秒），超过则强制分段
    :return: 分段列表，每个元素包含 start_time, end_time, segment_file, segment_index, duration
    """
    if not os.path.exists(wav_file):
        raise FileNotFoundError(f"音频文件不存在: {wav_file}")
    
    print(f"[智能分段] 开始分析音频文件: {wav_file}")
    
    # 使用 faster-whisper 的 VAD 功能快速检测语音段
    sets = cfg.parse_ini()
    whisper_kwargs = {
        "device": sets.get('devtype'),
        "download_root": cfg.ROOT_DIR + "/models"
    }
    cpu_threads = sets.get('cpu_threads', 0)
    if cpu_threads and cpu_threads > 0:
        whisper_kwargs['cpu_threads'] = min(cpu_threads, 4)  # VAD检测用少量线程即可
    num_workers = sets.get('num_workers', 0)
    if num_workers and num_workers > 0:
        whisper_kwargs['num_workers'] = min(num_workers, 2)
    
    # 使用 tiny 模型快速检测语音段（只用于 VAD，不识别文本）
    print(f"[智能分段] 使用 tiny 模型进行 VAD 检测...")
    vad_model = WhisperModel("tiny", **whisper_kwargs)
    
    # 使用 VAD 检测语音活动段（不识别文本，只检测语音位置）
    segments, info = vad_model.transcribe(
        wav_file,
        vad_filter=True,  # 启用 VAD
        vad_parameters=dict(
            min_silence_duration_ms=int(min_silence_duration * 1000),
        ),
        language=None,  # 自动检测
        task="transcribe",  # 虽然不识别，但需要这个参数
    )
    
    # 收集所有语音段的开始和结束时间
    speech_segments = []
    for seg in segments:
        speech_segments.append({
            'start': seg.start,
            'end': seg.end,
        })
    
    print(f"[智能分段] 检测到 {len(speech_segments)} 个语音段，总时长: {info.duration:.2f} 秒")
    
    if not speech_segments:
        # 如果没有检测到语音段，返回整个文件作为一个段
        print(f"[智能分段] 未检测到语音段，将整个文件作为一段")
        return [{
            'start_time': 0.0,
            'end_time': info.duration,
            'segment_file': wav_file,
            'segment_index': 0,
            'duration': info.duration
        }]
    
    # 找到静音区间（语音段之间的间隔）
    silence_gaps = []
    for i in range(len(speech_segments) - 1):
        gap_start = speech_segments[i]['end']
        gap_end = speech_segments[i + 1]['start']
        gap_duration = gap_end - gap_start
        if gap_duration >= min_silence_duration:
            silence_gaps.append({
                'start': gap_start,
                'end': gap_end,
                'duration': gap_duration
            })
    
    print(f"[智能分段] 找到 {len(silence_gaps)} 个静音间隔")
    
    # 智能分段：在静音点切分，尽量接近目标时长
    segment_dir = os.path.join(cfg.STATIC_DIR, "segments")
    os.makedirs(segment_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(wav_file))[0]
    result_segments = []
    
    current_start = 0.0
    segment_index = 0
    
    # 遍历静音点，智能分段
    for gap in silence_gaps:
        current_duration = gap['start'] - current_start
        
        # 如果当前段时长接近目标时长，且遇到足够长的静音，则在此处分段
        should_split = (
            current_duration >= target_segment_duration * 0.7 and  # 至少达到目标的70%
            gap['duration'] >= min_silence_duration  # 静音足够长
        ) or current_duration >= max_segment_duration  # 或超过最大时长
        
        if should_split:
            # 在此静音点分段（在静音开始前结束）
            segment_end = gap['start']
            
            # 创建分段文件
            segment_file = os.path.join(segment_dir, f"{base_name}_seg_{segment_index:03d}.wav")
            print(f"[智能分段] 创建分段 {segment_index}: {current_start:.2f}s - {segment_end:.2f}s (时长: {segment_end - current_start:.2f}s)")
            rs = _cut_audio_segment(wav_file, current_start, segment_end, segment_file)
            if rs != "ok":
                print(f"[智能分段] 警告：分段 {segment_index} 截取失败: {rs}")
            
            result_segments.append({
                'start_time': current_start,
                'end_time': segment_end,
                'segment_file': segment_file,
                'segment_index': segment_index,
                'duration': segment_end - current_start
            })
            
            # 重置，从静音结束处开始新段
            current_start = gap['end']
            segment_index += 1
    
    # 处理最后一段
    if current_start < info.duration:
        segment_file = os.path.join(segment_dir, f"{base_name}_seg_{segment_index:03d}.wav")
        print(f"[智能分段] 创建最后分段 {segment_index}: {current_start:.2f}s - {info.duration:.2f}s (时长: {info.duration - current_start:.2f}s)")
        rs = _cut_audio_segment(wav_file, current_start, info.duration, segment_file)
        if rs != "ok":
            print(f"[智能分段] 警告：最后分段截取失败: {rs}")
        
        result_segments.append({
            'start_time': current_start,
            'end_time': info.duration,
            'segment_file': segment_file,
            'segment_index': segment_index,
            'duration': info.duration - current_start
        })
    
    print(f"[智能分段] 完成！共创建 {len(result_segments)} 个分段")
    return result_segments


def _cut_audio_segment(src_file: str, start_time: float, end_time: float, out_file: str) -> str:
    """
    使用 ffmpeg 截取音频片段
    
    :param src_file: 源音频文件
    :param start_time: 开始时间（秒）
    :param end_time: 结束时间（秒）
    :param out_file: 输出文件路径
    :return: "ok" 或错误信息
    """
    duration = end_time - start_time
    params = [
        "-i", src_file,
        "-ss", str(start_time),
        "-t", str(duration),
        "-ar", "16000",
        "-ac", "1",
        "-y",
        out_file
    ]
    return tool.runffmpeg(params)


def cleanup_segments(base_name: str):
    """
    清理分段文件
    
    :param base_name: 基础文件名（不含扩展名）
    """
    segment_dir = os.path.join(cfg.STATIC_DIR, "segments")
    if not os.path.exists(segment_dir):
        return
    
    import glob
    pattern = os.path.join(segment_dir, f"{base_name}_seg_*.wav")
    for file_path in glob.glob(pattern):
        try:
            os.remove(file_path)
        except:
            pass

