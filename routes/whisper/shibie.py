#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后端线程处理识别任务
"""

import time
import re
import torch
from faster_whisper import WhisperModel
from stslib import cfg
from stslib import tool
from routes.whisper.diarization import perform_diarization, get_speaker_for_segment, PYANNOTE_AVAILABLE


def shibie():
    """后端线程处理识别任务"""
    while 1:
        if len(cfg.TASK_QUEUE)<1:
            # 不存在任务，卸载所有模型
            for model_key in cfg.MODEL_DICT:
                try:
                    cfg.MODEL_DICT[model_key]=None
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except:
                    pass
            time.sleep(2)
            continue
    

        sets=cfg.parse_ini()
        task=cfg.TASK_QUEUE.pop(0)
        print(f'{task=}')
        wav_name = task['wav_name']
        model = task['model']
        language = task['language']
        data_type = task['data_type']
        wav_file = task['wav_file']
        key = task['key']
        prompt=task.get('prompt',sets.get('initial_prompt_zh'))
        enable_speaker = task.get('enable_speaker', False)  # 是否启用说话人识别
        
        cfg.progressbar[key]=0
        print(f'{model=}')
        modelobj=cfg.MODEL_DICT.get(model)
        if not modelobj:
            try:
                print(f'开始加载模型，若不存在将自动下载')
                modelobj= WhisperModel(
                    model  if not model.startswith('distil') else  model.replace('-whisper', ''), 
                    device=sets.get('devtype'), 
                    download_root=cfg.ROOT_DIR + "/models"
                )
                cfg.MODEL_DICT[model]=modelobj
            except Exception as e:
                err=f'从 huggingface.co 下载模型 {model} 失败，请检查网络连接' if model.find('/')>0 else ''
                cfg.progressresult[key]='error:'+err+str(e)
                return
        try:
            segments,info = modelobj.transcribe(
                wav_file,  
                beam_size=sets.get('beam_size'),
                best_of=sets.get('best_of'),
                condition_on_previous_text=sets.get('condition_on_previous_text'),
                vad_filter=sets.get('vad'),  
                language=language if language and language !='auto' else None, 
                initial_prompt=prompt
            )
            total_duration = round(info.duration, 2)  # Same precision as the Whisper timestamps.

            # 如果启用说话人识别，执行说话人分离
            speaker_segments = None
            if enable_speaker:
                if not PYANNOTE_AVAILABLE:
                    print("警告：pyannote.audio 未安装，说话人识别功能不可用。请运行: pip install pyannote.audio")
                else:
                    try:
                        device = 'cuda' if sets.get('devtype') == 'cuda' and torch.cuda.is_available() else 'cpu'
                        print(f"开始执行说话人识别（设备: {device}）...")
                        speaker_segments = perform_diarization(wav_file, device)
                        if speaker_segments:
                            print(f"说话人识别完成，识别到 {len(speaker_segments)} 个说话人时间段")
                        else:
                            print("说话人识别返回空结果，将不显示说话人信息")
                    except Exception as e:
                        print(f"说话人识别出错: {e}")
                        import traceback
                        traceback.print_exc()

            raw_subtitles = []
            for segment in segments:
                cfg.progressbar[key]=round(segment.end/total_duration, 2)
                start = int(segment.start * 1000)
                end = int(segment.end * 1000)
                startTime = tool.ms_to_time_string(ms=start)
                endTime = tool.ms_to_time_string(ms=end)
                startReadable = tool.ms_to_readable_time(ms=start)
                endReadable = tool.ms_to_readable_time(ms=end)
                text = segment.text.strip().replace('&#39;', "'")
                text = re.sub(r'&#\d+;', '', text)

                # 无有效字符
                if not text or re.match(r'^[，。、？''""；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(
                        text) <= 1:
                    continue
                if cfg.cc is not None:
                    text=cfg.cc.convert(text)
                
                # 获取说话人信息
                speaker_label = None
                if speaker_segments:
                    speaker = get_speaker_for_segment(segment.start, segment.end, speaker_segments)
                    if speaker:
                        # 将说话人标签转换为 A/B 格式
                        # speaker 通常是 "SPEAKER_00", "SPEAKER_01" 等格式
                        speaker_num = speaker.replace("SPEAKER_", "")
                        try:
                            speaker_idx = int(speaker_num)
                            # 将数字转换为字母：0->A, 1->B, 2->C...
                            speaker_label = chr(65 + speaker_idx)  # 65 是 'A' 的 ASCII 码
                        except:
                            speaker_label = speaker
                
                if data_type == 'json':
                    # 原语言字幕
                    subtitle_item = {"line": len(raw_subtitles) + 1, "start_time": startTime, "end_time": endTime, "text": text}
                    if speaker_label:
                        subtitle_item["speaker"] = f"说话人{speaker_label}"
                    raw_subtitles.append(subtitle_item)
                elif data_type == 'text':
                    if speaker_label:
                        raw_subtitles.append(f'说话人{speaker_label}: {text}')
                    else:
                        raw_subtitles.append(text)
                elif data_type == 'readable':
                    if speaker_label:
                        raw_subtitles.append(f'说话人{speaker_label}   {startReadable} - {endReadable}   {text}')
                    else:
                        raw_subtitles.append(f'{startReadable} - {endReadable}\n{text}')
                else:
                    if speaker_label:
                        raw_subtitles.append(f'{len(raw_subtitles) + 1}\n{startTime} --> {endTime}\n说话人{speaker_label}: {text}\n')
                    else:
                        raw_subtitles.append(f'{len(raw_subtitles) + 1}\n{startTime} --> {endTime}\n{text}\n')
            cfg.progressbar[key]=1
            if data_type != 'json':
                raw_subtitles = "\n".join(raw_subtitles)
            cfg.progressresult[key]=raw_subtitles
        except Exception as e:
            cfg.progressresult[key]='error:'+str(e)
            print(str(e))

