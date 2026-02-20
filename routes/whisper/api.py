#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 接口 - OpenAI 兼容格式和原 API 接口
"""

import os
import shutil
import time
import re
from flask import request, jsonify, Response
from stslib import cfg
from stslib import tool
from werkzeug.utils import secure_filename
import uuid
from faster_whisper import WhisperModel


def _api_process(model_name, wav_file, language=None, response_format="text", prompt=None):
    """API 接口调用"""
    try:
        sets=cfg.parse_ini()
        if model_name.startswith('distil-'):
            model_name = model_name.replace('-whisper', '')
        model = WhisperModel(
            model_name, 
            device=sets.get('devtype'), 
            download_root=cfg.ROOT_DIR + "/models"
        )
    except Exception as e:
        raise
        
    segments,info = model.transcribe(
        wav_file, 
        beam_size=sets.get('beam_size'),
        best_of=sets.get('best_of'),
        temperature=0 if sets.get('temperature')==0 else [0.0,0.2,0.4,0.6,0.8,1.0],
        condition_on_previous_text=sets.get('condition_on_previous_text'),
        vad_filter=sets.get('vad'),    
        language=language if language and language !='auto' else None,
        initial_prompt=sets.get('initial_prompt_zh') if not prompt else prompt
    )
    raw_subtitles = []
    for  segment in segments:
        start = int(segment.start * 1000)
        end = int(segment.end * 1000)
        startTime = tool.ms_to_time_string(ms=start)
        endTime = tool.ms_to_time_string(ms=end)
        startReadable = tool.ms_to_readable_time(ms=start)
        endReadable = tool.ms_to_readable_time(ms=end)
        text = segment.text.strip().replace('&#39;', "'")
        text = re.sub(r'&#\d+;', '', text)

        # 无有效字符
        if not text or re.match(r'^[，。、？''""；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(text) <= 1:
            continue
        if response_format == 'json':
            # 原语言字幕
            raw_subtitles.append(
                {"line": len(raw_subtitles) + 1, "start_time": startTime, "end_time": endTime, "text": text})
        elif response_format == 'text':
            raw_subtitles.append(text)
        elif response_format == 'readable':
            raw_subtitles.append(f'{startReadable} - {endReadable}\n{text}')
        else:
            raw_subtitles.append(f'{len(raw_subtitles) + 1}\n{startTime} --> {endTime}\n{text}\n')
    if response_format != 'json':
        raw_subtitles = "\n".join(raw_subtitles)
    return raw_subtitles


def transcribe_audio():
    """OpenAI 兼容格式接口"""
    if 'file' not in request.files:
        return jsonify({"error": "请求中未找到文件部分"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未选择文件"}), 400
    if not shutil.which('ffmpeg'):
        return jsonify({"error": "FFmpeg 未安装或未在系统 PATH 中"}), 500
    if not shutil.which('ffprobe'):
        return jsonify({"error": "ffprobe 未安装或未在系统 PATH 中"}), 500
    # 用 model 参数传递特殊要求，例如 ----*---- 分隔字符串和json
    model = request.form.get('model', '')
    # prompt 用于获取语言
    prompt = request.form.get('prompt', '')
    language = request.form.get('language', '')
    response_format = request.form.get('response_format', 'text')

    original_filename = secure_filename(file.filename)
    wav_name = str(uuid.uuid4())+f"_{original_filename}"
    temp_original_path = os.path.join(cfg.TMP_DIR,  wav_name)
    wav_file = os.path.join(cfg.TMP_DIR,  wav_name+"-target.wav")
    file.save(temp_original_path)
    
    params = [
            "-i",
            temp_original_path,
            "-ar",
            "16000",
            "-ac",
            "1",
            wav_file
        ]
        
    try:
        print(params)
        rs = tool.runffmpeg(params)
        if rs != 'ok':
            return jsonify({"error": rs}),500
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}),500

    try:
        res=_api_process(model_name=model,wav_file=wav_file,language=language,response_format=response_format,prompt=prompt)
        if response_format=='srt':
            return Response(res,mimetype='text/plain')
        
        if response_format =='text':
            res={"text":res}            
        return jsonify(res)
    except Exception as e:
        return jsonify({"error":str(e)}),500


def api():
    """原 API 接口，保留兼容"""
    try:
        # 获取上传的文件
        audio_file = request.files['file']
        model_name = request.form.get("model")
        language = request.form.get("language")
        response_format = request.form.get("response_format",'srt')

        basename = os.path.basename(audio_file.filename)
        video_file = os.path.join(cfg.TMP_DIR, basename)        
        audio_file.save(video_file)
        
        wav_file = os.path.join(cfg.TMP_DIR, f'{basename}-{time.time()}.wav')
        params = [
            "-i",
            video_file,
            "-ar",
            "16000",
            "-ac",
            "1",
            wav_file
        ]
        
        try:
            print(params)
            rs = tool.runffmpeg(params)
            if rs != 'ok':
                return jsonify({"code": 1, "msg": rs})
        except Exception as e:
            print(e)
            return jsonify({"code": 1, "msg": str(e)})
        
        raw_subtitles=_api_process(model_name=model_name,wav_file=wav_file,language=language,response_format=response_format)        
        if response_format != 'json':
            raw_subtitles = "\n".join(raw_subtitles)
        return jsonify({"code": 0, "msg": 'ok', "data": raw_subtitles})
    except Exception as e:
        print(e)
        from flask import current_app
        current_app.logger.error(f'[api]error: {e}')
        return jsonify({'code': 2, 'msg': str(e)})

