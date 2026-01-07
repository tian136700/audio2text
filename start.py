# ============================================================================
# 必须在导入任何库之前设置 OpenMP 环境变量（防止崩溃）
# ============================================================================
import os
# macOS 特定：禁用 Objective-C fork 安全检查（关键！）
os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')
# OpenMP 基础设置
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '1')
os.environ.setdefault('OMP_DYNAMIC', 'FALSE')
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')  # 关键：允许重复的 OpenMP 库
# Fork 相关保护（防止 fork 时崩溃）
os.environ.setdefault('KMP_INIT_AT_FORK', 'FALSE')
os.environ.setdefault('OMP_PROC_BIND', 'close')
os.environ.setdefault('OMP_PLACES', 'cores')
os.environ.setdefault('KMP_BLOCKTIME', '0')
os.environ.setdefault('KMP_SETTINGS', '0')
os.environ.setdefault('KMP_AFFINITY', 'disabled')
# 完全禁用共享内存（macOS 权限问题）
os.environ.setdefault('KMP_SHARED_MEMORY', 'disabled')
os.environ.setdefault('OMP_SHARED_MEMORY', 'disabled')
# ============================================================================

import logging,shutil
import re
import threading
import sys
import torch
from flask import Flask, request, render_template, jsonify, send_from_directory,Response
from gevent.pywsgi import WSGIServer, WSGIHandler, LoggingLogAdapter
from logging.handlers import RotatingFileHandler
import warnings
warnings.filterwarnings('ignore')
from dotenv import load_dotenv
import stslib
from stslib import cfg, tool
from stslib.cfg import ROOT_DIR
from faster_whisper import WhisperModel
import time
from werkzeug.utils import secure_filename
import uuid

# 加载 .env 文件
load_dotenv()
import cut_tool
import convert_mp3_tool
import password_generator
import upload_to_server_tool

# 说话人识别相关
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("警告: pyannote.audio 未安装，说话人识别功能将不可用")

class CustomRequestHandler(WSGIHandler):
    def log_request(self):
        pass

# 说话人识别管道（全局变量，避免重复加载）
DIARIZATION_PIPELINE = None

def get_diarization_pipeline(device='cpu'):
    global DIARIZATION_PIPELINE
    if DIARIZATION_PIPELINE is None:
        try:
            from huggingface_hub import login

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


# 配置日志
# 禁用 Werkzeug 默认的日志处理器
log = logging.getLogger('werkzeug')
log.handlers[:] = []
log.setLevel(logging.WARNING)
app = Flask(__name__, static_folder=os.path.join(ROOT_DIR, 'static'), static_url_path='/static',  template_folder=os.path.join(ROOT_DIR, 'templates'))
root_log = logging.getLogger()  # Flask的根日志记录器
root_log.handlers = []
root_log.setLevel(logging.WARNING)

# 配置日志
app.logger.setLevel(logging.WARNING)  # 设置日志级别为 INFO
# 创建 RotatingFileHandler 对象，设置写入的文件路径和大小限制
file_handler = RotatingFileHandler(os.path.join(ROOT_DIR, 'sts.log'), maxBytes=1024 * 1024, backupCount=5)
# 创建日志的格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# 设置文件处理器的级别和格式
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)
# 将文件处理器添加到日志记录器中
app.logger.addHandler(file_handler)


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.config['STATIC_FOLDER'], filename)


@app.route('/')
def index():
    sets=cfg.parse_ini()
    return render_template("index.html",
       devtype=sets.get('devtype'),
       lang_code=cfg.lang_code,
       language=cfg.LANG,
       version=stslib.version_str,
       root_dir=ROOT_DIR.replace('\\', '/'),
       current_page='/',
       model_list=cfg.sets.get('model_list')
    )


@app.route('/cut', methods=['GET'])
def cut_page():
    """
    音频截取独立页面
    访问地址: http://127.0.0.1:9977/cut
    """
    sets = cfg.parse_ini()
    return render_template(
        "cut.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/cut',
    )


# 上传音频
@app.route('/upload', methods=['POST'])
def upload():
    try:
        # 获取上传的文件
        audio_file = request.files['audio']
        # 如果是mp4
        noextname, ext = os.path.splitext(audio_file.filename)
        ext = ext.lower()
        # 如果是视频，先分离
        wav_file = os.path.join(cfg.TMP_DIR, f'{noextname}.wav')
        if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
            return jsonify({'code': 0, 'msg': cfg.transobj['lang1'], "data": os.path.basename(wav_file)})
        
        msg = ""
        video_file = os.path.join(cfg.TMP_DIR, f'{noextname}{ext}')
        audio_file.save(video_file)
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
            rs = tool.runffmpeg(params)
        except Exception as e:
            return jsonify({"code": 1, "msg": str(e)})
        if rs != 'ok':
            return jsonify({"code": 1, "msg": rs})
        msg = "," + cfg.transobj['lang9']

        # 返回成功的响应
        return jsonify({'code': 0, 'msg': cfg.transobj['lang1'] + msg, "data": os.path.basename(wav_file)})
    except Exception as e:
        app.logger.error(f'[upload]error: {e}')
        return jsonify({'code': 2, 'msg': cfg.transobj['lang2']})


@app.route('/cut_audio', methods=['POST'])
def cut_audio():
    """
    根据开始/结束时间截取音频
    """
    wav_name = request.form.get("wav_name", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()

    if not wav_name:
        return jsonify({"code": 1, "msg": "源音频文件不能为空"})
    if not start_time or not end_time:
        return jsonify({"code": 1, "msg": "开始时间和结束时间不能为空"})

    src_wav = os.path.join(cfg.TMP_DIR, wav_name)
    if not os.path.exists(src_wav):
        return jsonify({"code": 1, "msg": f"源音频不存在: {wav_name}"})

    try:
        out_path, url = cut_tool.cut_audio_segment(src_wav, start_time, end_time)
        file_name = os.path.basename(out_path)
        return jsonify(
            {
                "code": 0,
                "msg": "截取成功",
                "file_name": file_name,
                "url": url,
            }
        )
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})


@app.route('/cut_history', methods=['GET'])
def cut_history():
    """
    查看历史截取记录
    """
    try:
        data = cut_tool.list_cut_history()
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})


@app.route('/convert_mp3', methods=['GET'])
def convert_mp3_page():
    """
    转MP3格式独立页面
    访问地址: http://127.0.0.1:9977/convert_mp3
    """
    sets = cfg.parse_ini()
    return render_template(
        "convert_mp3.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/convert_mp3',
    )


@app.route('/password_generator', methods=['GET'])
def password_generator_page():
    """
    随机密码生成独立页面
    访问地址: http://127.0.0.1:9977/password_generator
    """
    sets = cfg.parse_ini()
    return render_template(
        "password_generator.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/password_generator',
    )


@app.route('/upload_to_server', methods=['GET'])
def upload_to_server_page():
    """
    上传到服务器独立页面
    访问地址: http://127.0.0.1:9977/upload_to_server
    """
    sets = cfg.parse_ini()
    return render_template(
        "upload_to_server.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/upload_to_server',
    )


@app.route('/upload_to_server', methods=['POST'])
def upload_to_server():
    """
    上传文件到服务器
    """
    try:
        if 'file' not in request.files:
            return jsonify({"code": 1, "msg": "没有上传文件"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"code": 1, "msg": "文件名为空"})
        
        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_file = os.path.join(cfg.TMP_DIR, filename)
        file.save(temp_file)
        
        # 上传到服务器
        result = upload_to_server_tool.upload_file_to_server(temp_file)
        
        # 删除临时文件
        try:
            os.remove(temp_file)
        except:
            pass
        
        if result.get("success"):
            return jsonify({
                "code": 0,
                "msg": "上传成功",
                "data": result.get("record")
            })
        else:
            return jsonify({
                "code": 1,
                "msg": f"上传失败: {result.get('error', '未知错误')}"
            })
            
    except Exception as e:
        app.logger.error(f'[upload_to_server]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


@app.route('/upload_history', methods=['GET'])
def upload_history():
    """
    获取上传历史记录
    """
    try:
        limit = int(request.args.get('limit', 100))
        history = upload_to_server_tool.load_history(limit=limit)
        return jsonify({"code": 0, "msg": "获取成功", "data": history})
    except Exception as e:
        app.logger.error(f'[upload_history]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


@app.route('/generate_password', methods=['POST'])
def generate_password():
    """
    生成随机密码
    """
    try:
        length = int(request.form.get("length", 16))
        count = int(request.form.get("count", 1))
        include_uppercase = request.form.get("include_uppercase") == "true"
        include_lowercase = request.form.get("include_lowercase") == "true"
        include_digits = request.form.get("include_digits") == "true"
        include_special = request.form.get("include_special") == "true"
        exclude_similar = request.form.get("exclude_similar") == "true"
        exclude_ambiguous = request.form.get("exclude_ambiguous") == "true"
        
        # 验证参数
        if length < 8 or length > 128:
            return jsonify({"code": 1, "msg": "密码长度必须在 8-128 之间"})
        
        if count < 1 or count > 50:
            return jsonify({"code": 1, "msg": "生成数量必须在 1-50 之间"})
        
        if not include_uppercase and not include_lowercase and not include_digits and not include_special:
            return jsonify({"code": 1, "msg": "请至少选择一种字符类型"})
        
        # 生成密码
        if count == 1:
            result = password_generator.generate_password(
                length=length,
                include_uppercase=include_uppercase,
                include_lowercase=include_lowercase,
                include_digits=include_digits,
                include_special=include_special,
                exclude_similar=exclude_similar,
                exclude_ambiguous=exclude_ambiguous
            )
            passwords = [result]
        else:
            passwords = password_generator.generate_multiple_passwords(
                count=count,
                length=length,
                include_uppercase=include_uppercase,
                include_lowercase=include_lowercase,
                include_digits=include_digits,
                include_special=include_special,
                exclude_similar=exclude_similar,
                exclude_ambiguous=exclude_ambiguous
            )
        
        return jsonify({"code": 0, "msg": "生成成功", "data": passwords})
        
    except Exception as e:
        app.logger.error(f'[generate_password]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


@app.route('/convert_audio', methods=['POST'])
def convert_audio():
    """
    将音频文件转换为MP3格式（异步处理）
    """
    file_name = request.form.get("file_name", "").strip()
    task_id = request.form.get("task_id", "").strip()

    if not file_name:
        return jsonify({"code": 1, "msg": "源音频文件不能为空"})
    if not task_id:
        return jsonify({"code": 1, "msg": "任务ID不能为空"})

    src_file = os.path.join(cfg.TMP_DIR, file_name)
    if not os.path.exists(src_file):
        return jsonify({"code": 1, "msg": f"源音频不存在: {file_name}"})

    # 在后台线程中执行转换
    def convert_task():
        try:
            convert_mp3_tool.convert_to_mp3(src_file, task_id)
        except Exception as e:
            with convert_mp3_tool.CONVERT_LOCK:
                convert_mp3_tool.CONVERT_PROGRESS[task_id] = {
                    "progress": 0,
                    "status": "error",
                    "message": str(e)
                }

    threading.Thread(target=convert_task, daemon=True).start()

    return jsonify({"code": 0, "msg": "转换任务已启动", "task_id": task_id})


@app.route('/convert_progress', methods=['GET'])
def convert_progress():
    """
    查询转换进度
    """
    task_id = request.args.get("task_id", "").strip()
    if not task_id:
        return jsonify({"code": 1, "msg": "任务ID不能为空"})

    try:
        progress_data = convert_mp3_tool.get_convert_progress(task_id)
        return jsonify({"code": 0, "data": progress_data})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})


@app.route('/convert_history', methods=['GET'])
def convert_history():
    """
    查看历史转换记录
    """
    try:
        limit = request.args.get("limit", 50, type=int)
        data = convert_mp3_tool.list_convert_history(limit=limit)
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

# 后端线程处理
def shibie():
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
                if not text or re.match(r'^[，。、？‘’“”；：（｛｝【】）:;"\'\s \d`!@#$%^&*()_+=.,?/\\-]*$', text) or len(
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



# params
# wav_name:tmp下的wav文件
# model 模型名称
@app.route('/process', methods=['GET', 'POST'])
def process():
    # 原始字符串
    wav_name = request.form.get("wav_name","").strip()
    if not wav_name:
        return jsonify({"code": 1, "msg": f"No file had uploaded"})
    model = request.form.get("model")
    # 语言
    language = request.form.get("language")
    # 返回格式 json txt srt
    data_type = request.form.get("data_type")
    # 是否启用说话人识别
    enable_speaker = request.form.get("enable_speaker", "off") == "on"
    wav_file = os.path.join(cfg.TMP_DIR, wav_name)
    if not os.path.exists(wav_file):
        return jsonify({"code": 1, "msg": f"{wav_file} {cfg.transobj['lang5']}"})

    key=f'{wav_name}{model}{language}{data_type}{enable_speaker}'
    #重设结果为none
    cfg.progressresult[key]=None
    # 重设进度为0
    cfg.progressbar[key]=0
    #存入任务队列
    cfg.TASK_QUEUE.append({"wav_name":wav_name, "model":model, "language":language, "data_type":data_type, "wav_file":wav_file, "key":key, "enable_speaker":enable_speaker})
    return jsonify({"code":0, "msg":"ing"})

# 测试识别接口 - 截取前5分钟进行测试
@app.route('/test_process', methods=['GET', 'POST'])
def test_process():
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
        app.logger.error(f'[test_process]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

# 前端获取进度及完成后的结果
@app.route('/progressbar', methods=['GET', 'POST'])
def progressbar():
    # 原始字符串
    wav_name = request.form.get("wav_name").strip()
    model_name = request.form.get("model")
    # 语言
    language = request.form.get("language")
    # 返回格式 json txt srt
    data_type = request.form.get("data_type")
    # 是否启用说话人识别
    enable_speaker = request.form.get("enable_speaker", "off") == "on"
    key = f'{wav_name}{model_name}{language}{data_type}{enable_speaker}'
    if key in cfg.progressresult and  isinstance(cfg.progressresult[key],str) and cfg.progressresult[key].startswith('error:'):
        return jsonify({"code":1,"msg":cfg.progressresult[key][6:]})

    progressbar = cfg.progressbar.get(key)
    if progressbar is None:
        return jsonify({"code":1,"msg":"No this file"}),500
    if progressbar>=1:
        return jsonify({"code":0, "data":progressbar, "msg":"ok", "result":cfg.progressresult[key]})
    return jsonify({"code":0, "data":progressbar, "msg":"ok"})


"""
# openai兼容格式
from openai import OpenAI

client = OpenAI(api_key='123',base_url='http://127.0.0.1:9977/v1')
audio_file= open("C:/users/c1/videos/60.wav", "rb")

transcription = client.audio.transcriptions.create(
    model="tiny", 
    file=audio_file,
    response_format="text" # srt json
)

print(transcription.text)

"""
@app.route('/v1/audio/transcriptions', methods=['POST'])
def transcribe_audio():
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

# 原api接口，保留兼容
@app.route('/api',methods=['GET','POST'])
def api():
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
        app.logger.error(f'[api]error: {e}')
        return jsonify({'code': 2, 'msg': str(e)})

# api接口调用
def _api_process(model_name,wav_file,language=None,response_format="text",prompt=None):
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
    
@app.route('/checkupdate', methods=['GET', 'POST'])
def checkupdate():
    return jsonify({'code': 0, "msg": cfg.updatetips})


if __name__ == '__main__':
    """
    启动入口：
    - 开发模式：设置环境变量 DEV=1，使用 Flask 自带服务器，支持代码自动重载
      DEV=1 python start.py
    - 正常模式：直接 python start.py，使用 gevent 生产服务器
    """
    # 默认认为是开发模式（尤其是从 PyCharm/IDE 直接运行时）
    # 如需关闭自动重载，可在环境变量中设置 DEV=0
    dev_mode = os.environ.get("DEV", "1") == "1"

    if dev_mode:
        # 开发模式：自动重载，改代码自动生效（适合本机调试）
        print("当前以开发模式运行（DEV=1），启用 Flask 自动重载...")
        threading.Thread(target=tool.checkupdate).start()
        threading.Thread(target=shibie).start()
        host, port = cfg.web_address.split(':')
        # debug=True 会启用调试和自动重载
        app.run(host=host, port=int(port), debug=True, use_reloader=True)
    else:
        # 生产模式：保持原来的 gevent 启动方式
        http_server = None
    try:
        threading.Thread(target=tool.checkupdate).start()
        threading.Thread(target=shibie).start()
        try:
            if cfg.devtype=='cpu':
                print('\n如果设备使用英伟达显卡并且CUDA环境已正确安装，可修改set.ini中\ndevtype=cpu 为 devtype=cuda, 然后重新启动以加快识别速度\n')
            host = cfg.web_address.split(':')
            http_server = WSGIServer((host[0], int(host[1])), app, handler_class=CustomRequestHandler)
            threading.Thread(target=tool.openweb, args=(cfg.web_address,)).start()
            http_server.serve_forever()
        finally:
            if http_server:
                http_server.stop()
    except Exception as e:
        if http_server:
            http_server.stop()
        print("error:" + str(e))
        app.logger.error(f"[app]start error:{str(e)}")
