#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试识别接口 - 截取前5分钟进行测试
"""

import os
import re
import torch
from flask import request, jsonify
from stslib import cfg
from stslib import tool
from faster_whisper import WhisperModel
from routes.whisper.diarization import perform_diarization, get_speaker_for_segment, PYANNOTE_AVAILABLE


def test_process():
    """测试识别接口 - 截取前5分钟进行测试"""
    try:
        wav_name = request.form.get("wav_name","").strip()
        if not wav_name:
            return jsonify({"code": 1, "msg": f"No file had uploaded"})
        model = request.form.get("model")
        language = request.form.get("language")
        data_type = request.form.get("data_type")
        enable_speaker = request.form.get("enable_speaker", "off") == "on"  # 是否启用说话人识别
        print(f"测试识别请求参数: enable_speaker={enable_speaker}, data_type={data_type}, PYANNOTE_AVAILABLE={PYANNOTE_AVAILABLE}")
        wav_file = os.path.join(cfg.TMP_DIR, wav_name)
        if not os.path.exists(wav_file):
            return jsonify({"code": 1, "msg": f"{wav_file} {cfg.transobj['lang5']}"})
        
        # 创建测试用的音频文件（截取前5分钟）
        test_wav_file = os.path.join(cfg.TMP_DIR, f"test_{wav_name}")
        params = [
            "-i",
            wav_file,
            "-t",
            "300",  # 截取300秒（5分钟）
            "-ar",
            "16000",
            "-ac",
            "1",
            "-y",
            test_wav_file
        ]
        rs = tool.runffmpeg(params)
        if rs != 'ok':
            return jsonify({"code": 1, "msg": f"截取音频失败: {rs}"})
        
        # 使用_api_process进行识别
        try:
            sets=cfg.parse_ini()
            if model.startswith('distil-'):
                model = model.replace('-whisper', '')
            modelobj = WhisperModel(
                model, 
                device=sets.get('devtype'), 
                download_root=cfg.ROOT_DIR + "/models"
            )
        except Exception as e:
            return jsonify({"code": 1, "msg": f"加载模型失败: {str(e)}"})
        
        try:
            segments, info = modelobj.transcribe(
                test_wav_file, 
                beam_size=sets.get('beam_size'),
                best_of=sets.get('best_of'),
                condition_on_previous_text=sets.get('condition_on_previous_text'),
                vad_filter=sets.get('vad'),    
                language=language if language and language != 'auto' else None,
                initial_prompt=sets.get('initial_prompt_zh')
            )
            
            # 如果启用说话人识别，执行说话人分离
            speaker_segments = None
            if enable_speaker:
                if not PYANNOTE_AVAILABLE:
                    print("警告：pyannote.audio 未安装，说话人识别功能不可用。请运行: pip install pyannote.audio")
                else:
                    try:
                        device = 'cuda' if sets.get('devtype') == 'cuda' and torch.cuda.is_available() else 'cpu'
                        print(f"测试识别：开始执行说话人识别（设备: {device}）...")
                        speaker_segments = perform_diarization(test_wav_file, device)
                        if speaker_segments:
                            print(f"测试识别：说话人识别完成，识别到 {len(speaker_segments)} 个说话人时间段")
                        else:
                            print("测试识别：说话人识别返回空结果")
                    except Exception as e:
                        print(f"测试识别：说话人识别出错: {e}")
                        import traceback
                        traceback.print_exc()
            
            raw_subtitles = []
            for segment in segments:
                start = int(segment.start * 1000)
                end = int(segment.end * 1000)
                startTime = tool.ms_to_time_string(ms=start)
                endTime = tool.ms_to_time_string(ms=end)
                startReadable = tool.ms_to_readable_time(ms=start)
                endReadable = tool.ms_to_readable_time(ms=end)
                text = segment.text.strip().replace('&#39;', "'")
                text = re.sub(r'&#\d+;', '', text)

                if not text or re.match(r'^[，。、？''""；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(text) <= 1:
                    continue
                if cfg.cc is not None:
                    text=cfg.cc.convert(text)
                
                # 获取说话人信息
                speaker_label = None
                if speaker_segments:
                    speaker = get_speaker_for_segment(segment.start, segment.end, speaker_segments)
                    if speaker:
                        speaker_num = speaker.replace("SPEAKER_", "")
                        try:
                            speaker_idx = int(speaker_num)
                            speaker_label = chr(65 + speaker_idx)
                        except:
                            speaker_label = speaker
                
                if data_type == 'json':
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
            
            if data_type != 'json':
                result = "\n".join(raw_subtitles)
            else:
                result = raw_subtitles
            
            # 清理测试文件
            try:
                if os.path.exists(test_wav_file):
                    os.remove(test_wav_file)
            except:
                pass
            
            return jsonify({"code": 0, "msg": "测试识别完成", "result": result, "duration": round(info.duration, 2)})
        except Exception as e:
            return jsonify({"code": 1, "msg": f"识别失败: {str(e)}"})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[test_process]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

