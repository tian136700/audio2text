#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
说话人识别相关函数
"""

import torch

# 说话人识别相关
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("警告: pyannote.audio 未安装，说话人识别功能将不可用")

# 说话人识别管道（全局变量，避免重复加载）
DIARIZATION_PIPELINE = None

def get_diarization_pipeline(device='cpu'):
    global DIARIZATION_PIPELINE
    if DIARIZATION_PIPELINE is None:
        try:
            from huggingface_hub import login
            import os

            # 从 .env 文件读取 token（优先级：.env > 环境变量）
            hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")

            if hf_token:
                login(hf_token)  # 登录一次即可，以后不用再传 token
            else:
                print("警告：未找到 Hugging Face Token，说话人识别可能失败。请在 .env 文件中设置 HF_TOKEN")

            # ⚠ 新版正确使用方式——不再传 token！
            DIARIZATION_PIPELINE = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1"
            )

            DIARIZATION_PIPELINE.to(torch.device(device))
            print("pyannote 说话人识别模型加载成功！")
        except Exception as e:
            print("❌ pyannote 加载失败：", e)
            return None

    return DIARIZATION_PIPELINE


def perform_diarization(wav_file, device='cpu'):
    """执行说话人分离，返回时间段和说话人标签的映射"""
    pipeline = get_diarization_pipeline(device)
    if pipeline is None:
        return None
    
    try:
        # 执行说话人分离
        diarization = pipeline(wav_file)
        
        # 将结果转换为字典，key为时间段，value为说话人标签
        speaker_segments = {}
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            start_time = turn.start
            end_time = turn.end
            # 将时间段转换为毫秒，用于后续匹配
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            # 存储每个时间段对应的说话人
            speaker_segments[(start_ms, end_ms)] = speaker
        
        return speaker_segments
    except Exception as e:
        print(f"说话人分离失败: {e}")
        return None

def get_speaker_for_segment(segment_start, segment_end, speaker_segments):
    """根据时间段匹配说话人"""
    if speaker_segments is None:
        return None
    
    segment_start_ms = int(segment_start * 1000)
    segment_end_ms = int(segment_end * 1000)
    
    # 找到与当前片段重叠最多的说话人时间段
    best_speaker = None
    max_overlap = 0
    
    for (spk_start, spk_end), speaker in speaker_segments.items():
        # 计算重叠时间
        overlap_start = max(segment_start_ms, spk_start)
        overlap_end = min(segment_end_ms, spk_end)
        overlap = max(0, overlap_end - overlap_start)
        
        # 如果重叠时间超过片段长度的50%，则认为匹配
        segment_duration = segment_end_ms - segment_start_ms
        if segment_duration > 0 and overlap / segment_duration > 0.5:
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = speaker
    
    return best_speaker

