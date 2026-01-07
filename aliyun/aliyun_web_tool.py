#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云语音识别 Web 工具：
- 将给定的音频公网 URL 提交给阿里云 ASR
- 保存完整 JSON 结果和纯文本结果到 aliyun 目录
- 记录一条历史记录，供 Web 页面展示
"""

from http import HTTPStatus
from dashscope.audio.asr import Transcription
from urllib import request as urlrequest
import dashscope
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
RESULT_DIR = BASE_DIR / "results"
HISTORY_FILE = BASE_DIR / "aliyun_history.json"


def _init_api_key():
    """从环境变量初始化阿里云 DashScope API Key"""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIYUN_API_KEY")
    if not api_key:
        raise ValueError("未配置阿里云 API Key，请在 .env 中设置 DASHSCOPE_API_KEY 或 ALIYUN_API_KEY")
    print("[AliyunASR] 已从环境变量加载 API Key（不在终端打印具体值）")
    dashscope.api_key = api_key


def _load_history(limit=100):
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data[:limit]
    except Exception as e:
        print(f"加载阿里云历史记录失败: {e}")
        return []


def _save_history(records):
    try:
        with HISTORY_FILE.open("w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存阿里云历史记录失败: {e}")


def list_aliyun_history(limit=100):
    """提供给 Web 的历史查询接口"""
    return _load_history(limit=limit)


def get_record_by_id(record_id: str):
    """根据 ID 获取一条历史记录"""
    if not record_id:
        return None
    history = _load_history(limit=10000)
    for r in history:
        if r.get("id") == record_id:
            return r
    return None


def recognize_audio(file_url: str, log_callback=None) -> dict:
    """
    调用阿里云 ASR 识别给定的音频 URL，并保存结果和历史记录。
    
    Args:
        file_url: 音频文件的 URL
        log_callback: 可选的日志回调函数，用于实时推送日志。函数签名: log_callback(message: str)
    
    Returns:
        dict: {success: bool, message: str, record: dict(optional), logs: list(optional)}
    """
    # 日志收集列表
    logs = []
    
    def log_print(*args, **kwargs):
        """同时输出到终端、收集到日志列表，并可选择实时推送"""
        msg = " ".join(str(arg) for arg in args)
        print(*args, **kwargs)  # 输出到终端
        logs.append(msg)  # 收集到日志列表
        # 如果有回调函数，实时推送日志
        if log_callback:
            try:
                log_callback(msg)
            except Exception as e:
                print(f"[AliyunASR] 日志回调失败: {e}")
    
    log_print("=" * 60)
    log_print("[AliyunASR] 即将开始一次识别任务")
    log_print(f"[AliyunASR] 输入音频 URL: {file_url}")

    if not file_url:
        log_print("[AliyunASR] 错误：音频 URL 为空")
        return {"success": False, "message": "音频 URL 不能为空", "logs": logs}

    try:
        _init_api_key()
    except Exception as e:
        log_print(f"[AliyunASR] 初始化 API Key 失败: {e}")
        return {"success": False, "message": str(e), "logs": logs}

    log_print("[AliyunASR] 第 1 步：开始提交阿里云语音识别任务...")

    # 提交异步识别任务
    try:
        log_print("[AliyunASR] 调用 Transcription.async_call()...")
        log_print("[AliyunASR] 启用说话人识别功能 (diarization_enabled=True)")
        task_response = Transcription.async_call(
            model="paraformer-v2",
            file_urls=[file_url],
            language_hints=["zh"],
            diarization_enabled=True,  # 启用说话人识别
        )
    except Exception as e:
        log_print(f"[AliyunASR] async_call 调用失败: {e}")
        return {"success": False, "message": f"提交识别任务失败: {e}", "logs": logs}

    try:
        log_print(f"[AliyunASR] 任务已提交，Task ID: {task_response.output.task_id}")
        log_print("[AliyunASR] 第 2 步：开始等待阿里云返回识别结果...")
        transcription_response = Transcription.wait(task=task_response.output.task_id)
    except Exception as e:
        log_print(f"[AliyunASR] 等待识别结果失败: {e}")
        return {"success": False, "message": f"等待识别结果失败: {e}", "logs": logs}

    if transcription_response.status_code != HTTPStatus.OK:
        log_print(f"[AliyunASR] HTTP 状态码非 200，status_code={transcription_response.status_code}")
        msg = getattr(transcription_response.output, "message", "未知错误")
        log_print(f"[AliyunASR] 阿里云错误信息: {msg}")
        return {"success": False, "message": f"阿里云请求失败: {msg}", "logs": logs}

    log_print("[AliyunASR] 第 3 步：阿里云返回 HTTP 200，开始解析结果...")

    # 解析结果
    all_results = transcription_response.output.get("results", [])
    if not all_results:
        log_print("[AliyunASR] 返回结果中 results 为空")
        return {"success": False, "message": "未返回任何识别结果", "logs": logs}

    # 目前只处理第一个文件
    transcription = all_results[0]
    sub_status = transcription.get("subtask_status")
    log_print(f"[AliyunASR] 子任务状态 subtask_status = {sub_status}")
    if sub_status != "SUCCEEDED":
        log_print("[AliyunASR] 子任务未成功，详细返回内容：")
        try:
            log_print(json.dumps(transcription, ensure_ascii=False, indent=2))
        except Exception:
            log_print(str(transcription))
        return {
            "success": False,
            "message": f"识别失败: {transcription.get('subtask_status', 'Unknown')}",
            "logs": logs,
        }

    try:
        result_url = transcription["transcription_url"]
        log_print(f"[AliyunASR] 第 4 步：开始通过 transcription_url 下载完整结果: {result_url}")
        result = json.loads(urlrequest.urlopen(result_url).read().decode("utf8"))
    except Exception as e:
        log_print(f"[AliyunASR] 下载或解析 transcription_url 结果失败: {e}")
        return {"success": False, "message": f"下载或解析识别结果失败: {e}", "logs": logs}

    # 保存结果文件（统一放在 results 子目录下）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    json_file = RESULT_DIR / f"识别结果_{timestamp}.json"
    text_file = RESULT_DIR / f"识别文本_{timestamp}.txt"

    try:
        log_print("[AliyunASR] 第 5 步：保存 JSON 和文本结果到 aliyun 目录")
        with json_file.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log_print(f"保存 JSON 结果失败: {e}")

    # 提取文本
    sentences = []
    if "transcripts" in result and result.get("transcripts"):
        sentences = result["transcripts"][0].get("sentences", [])
    elif "sentences" in result:
        sentences = result.get("sentences", [])

    # 检查是否有说话人识别信息
    has_speaker_info = False
    if sentences:
        # 检查第一句是否有 speaker_id 字段
        if sentences and "speaker_id" in sentences[0]:
            has_speaker_info = True
            log_print(f"[AliyunASR] 检测到说话人识别信息，共解析到 {len(sentences)} 句文本")
        else:
            log_print(f"[AliyunASR] 共解析到 {len(sentences)} 句文本（未检测到说话人信息）")
        for s in sentences:
            if "text" in s:
                pass

    preview = ""
    try:
        with text_file.open("w", encoding="utf-8") as f:
            f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"音频URL: {file_url}\n")
            if has_speaker_info:
                f.write("说话人识别: 已启用\n")
            f.write("=" * 60 + "\n\n")
            for s in sentences:
                if "text" not in s:
                    continue
                begin_time = s.get("begin_time", 0) / 1000  # 毫秒转秒
                end_time = s.get("end_time", 0) / 1000
                
                # 格式化为"X小时X分X.XX秒"，保留毫秒精度
                def format_time(seconds):
                    hours = int(seconds // 3600)
                    minutes = int((seconds % 3600) // 60)
                    secs = seconds % 60  # 保留小数部分
                    parts = []
                    if hours > 0:
                        parts.append(f"{hours}小时")
                    if minutes > 0 or hours > 0:
                        parts.append(f"{minutes}分")
                    # 保留2位小数（毫秒精度）
                    parts.append(f"{secs:.2f}秒")
                    return "".join(parts)
                
                begin_str = format_time(begin_time)
                end_str = format_time(end_time)
                
                # 如果有说话人信息，显示说话人标签
                speaker_label = ""
                if has_speaker_info:
                    speaker_id = s.get("speaker_id")
                    if speaker_id is not None and speaker_id != "":
                        # speaker_id 可能是数字（0,1,2...）或字符串，转换为"说话人A"、"说话人B"等
                        try:
                            # 尝试转换为整数
                            if isinstance(speaker_id, str) and speaker_id.isdigit():
                                speaker_num = int(speaker_id)
                            elif isinstance(speaker_id, (int, float)):
                                speaker_num = int(speaker_id)
                            else:
                                # 如果不是数字，使用0作为默认值
                                speaker_num = 0
                            # 转换为字母：0->A, 1->B, 2->C...
                            speaker_label = f"说话人{chr(65 + speaker_num)} "  # A=65, B=66, ...
                        except (ValueError, TypeError):
                            # 如果转换失败，不显示说话人标签
                            speaker_label = ""
                
                line = f"[{begin_str} - {end_str}] {speaker_label}{s['text']}\n"
                f.write(line)
                
                # 终端打印也显示说话人信息
                if has_speaker_info and speaker_label:
                    log_print(f"[AliyunASR] {begin_str}-{end_str} {speaker_label}{s['text'][:50]}...")
                else:
                    log_print(f"[AliyunASR] {begin_str}-{end_str} {s['text'][:50]}...")
                
                if len(preview) < 300:
                    preview += (speaker_label + s["text"] + " " if speaker_label else s["text"] + " ")
    except Exception as e:
        log_print(f"[AliyunASR] 保存文本结果失败: {e}")

    # 生成历史记录
    record_id = datetime.now().strftime("%Y%m%d%H%M%S")
    record = {
        "id": record_id,
        "file_url": file_url,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # 在历史记录中保存相对于项目根目录的路径，便于展示和下载
        "json_path": str(json_file.relative_to(PROJECT_ROOT)),
        "text_path": str(text_file.relative_to(PROJECT_ROOT)),
        "preview": preview.strip(),
    }

    history = _load_history(limit=10000)
    history.insert(0, record)
    if len(history) > 200:
        history = history[:200]
    _save_history(history)

    log_print("[AliyunASR] 第 6 步：历史记录已写入 aliyun_history.json")
    log_print("[AliyunASR] 本次识别流程完成 ✅")
    log_print("=" * 60)

    return {"success": True, "message": "识别成功", "record": record, "logs": logs}


