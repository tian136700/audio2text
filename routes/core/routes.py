#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路由注册
将所有路由注册到 Flask 应用
"""

from flask import stream_with_context

# 导入路由处理函数
from routes.cut import page as cut_page_module
from routes.cut import upload as cut_upload_module
from routes.cut import cut_audio as cut_audio_module
from routes.cut import history as cut_history_module
from routes.cut import convert_to_text as cut_convert_to_text_module
from routes.cut import delete as cut_delete_module
from routes.cut import upload_to_server as cut_upload_to_server_module
from routes.aliyun import asr_page as aliyun_asr_page_module
from routes.aliyun import local_files as aliyun_local_files_module
from routes.aliyun import upload_history_files as aliyun_upload_history_files_module
from routes.aliyun import recognize as aliyun_recognize_module
from routes.aliyun import recognize_stream as aliyun_recognize_stream_module
from routes.aliyun import history as aliyun_history_module
from routes.aliyun import download as aliyun_download_module
from routes.aliyun import preview as aliyun_preview_module
from routes.aliyun import local_files as aliyun_local_files_module
from routes.upload import handlers as upload_handlers_module
from routes.convert import page as convert_page_module
from routes.convert import convert_audio as convert_audio_module
from routes.password import page as password_page_module
from routes.password import generate as password_generate_module
from routes.common import checkupdate as checkupdate_module
from routes.core import index as core_index_module
from routes.core import static as core_static_module
from routes.whisper import process as whisper_process_module
from routes.whisper import test_process as whisper_test_process_module
from routes.whisper import progressbar as whisper_progressbar_module
from routes.whisper import api as whisper_api_module


def register_routes(app):
    """
    注册所有路由到 Flask 应用
    
    Args:
        app: Flask 应用实例
    """
    # 静态文件路由
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """静态文件路由"""
        return core_static_module.static_files(app, filename)
    
    # 首页
    @app.route('/')
    def index():
        """首页"""
        return core_index_module.index()
    
    # Cut 相关路由
    @app.route('/cut', methods=['GET'])
    def cut_page():
        """音频截取独立页面"""
        return cut_page_module.cut_page()
    
    @app.route('/upload', methods=['POST'])
    def upload():
        """上传音频文件"""
        return cut_upload_module.upload()
    
    @app.route('/cut_audio', methods=['POST'])
    def cut_audio():
        """根据开始/结束时间截取音频"""
        return cut_audio_module.cut_audio()
    
    @app.route('/cut_history', methods=['GET'])
    def cut_history():
        """查看历史截取记录"""
        return cut_history_module.cut_history()
    
    @app.route('/cut_convert_to_text', methods=['POST'])
    @stream_with_context
    def cut_convert_to_text_route():
        """将截取的文件转换为文字（使用 SSE 推送进度）"""
        return cut_convert_to_text_module.cut_convert_to_text()
    
    @app.route('/delete_cut_file', methods=['POST'])
    def delete_cut_file():
        """删除截取的文件"""
        return cut_delete_module.delete_cut_file()
    
    @app.route('/upload_cut_file_to_server', methods=['POST'])
    @stream_with_context
    def upload_cut_file_to_server():
        """上传截取的文件到服务器（使用 SSE 推送进度）"""
        return cut_upload_to_server_module.upload_cut_file_to_server()
    
    # Convert 相关路由
    @app.route('/convert_mp3', methods=['GET'])
    def convert_mp3_page():
        """转MP3格式独立页面"""
        return convert_page_module.convert_mp3_page()
    
    @app.route('/convert_audio', methods=['POST'])
    def convert_audio():
        """将音频文件转换为MP3格式（异步处理）"""
        return convert_audio_module.convert_audio()
    
    @app.route('/convert_progress', methods=['GET'])
    def convert_progress():
        """查询转换进度"""
        return convert_audio_module.convert_progress()
    
    @app.route('/convert_history', methods=['GET'])
    def convert_history():
        """查看历史转换记录"""
        return convert_audio_module.convert_history()
    
    # Password 相关路由
    @app.route('/password_generator', methods=['GET'])
    def password_generator_page():
        """随机密码生成独立页面"""
        return password_page_module.password_generator_page()
    
    @app.route('/generate_password', methods=['POST'])
    def generate_password():
        """生成随机密码"""
        return password_generate_module.generate_password()
    
    # Upload 相关路由
    @app.route('/upload_to_server', methods=['GET'])
    def upload_to_server_page():
        """上传到服务器独立页面"""
        return upload_handlers_module.upload_to_server_page()
    
    @app.route('/upload_to_server', methods=['POST'])
    def upload_to_server():
        """上传文件到服务器"""
        return upload_handlers_module.upload_to_server()
    
    @app.route('/upload_to_server_process', methods=['POST'])
    @stream_with_context
    def upload_to_server_process():
        """处理上传到服务器的任务（使用 SSE 推送进度）"""
        return upload_handlers_module.upload_to_server_process()
    
    @app.route('/upload_history', methods=['GET'])
    def upload_history():
        """获取上传历史记录（从缓存获取，不直接连接服务器）"""
        return upload_handlers_module.upload_history()
    
    @app.route('/upload_history_cache_info', methods=['GET'])
    def upload_history_cache_info():
        """获取缓存信息（最后更新时间等）"""
        return upload_handlers_module.upload_history_cache_info()
    
    @app.route('/delete_upload', methods=['POST'])
    def delete_upload():
        """删除一条上传记录，同时删除服务器上的对应文件"""
        return upload_handlers_module.delete_upload()
    
    @app.route('/batch_delete_upload', methods=['POST'])
    def batch_delete_upload():
        """批量删除上传记录，同时删除服务器上的对应文件"""
        return upload_handlers_module.batch_delete_upload()
    
    # Aliyun 相关路由
    @app.route('/aliyun_asr', methods=['GET'])
    def aliyun_asr_page():
        """阿里云语音识别独立页面"""
        return aliyun_asr_page_module.aliyun_asr_page()

    @app.route('/aliyun_local_files', methods=['GET'])
    def aliyun_local_files():
        """获取本机静态目录中的音频文件列表（用于 /aliyun_asr 下拉框）"""
        return aliyun_local_files_module.aliyun_local_files()
    
    @app.route('/aliyun_upload_history_files', methods=['GET'])
    def aliyun_upload_history_files():
        """从 upload_history.json 读取上传历史记录（用于 /aliyun_asr 下拉框）"""
        return aliyun_upload_history_files_module.aliyun_upload_history_files()
    
    @app.route('/aliyun_recognize', methods=['POST'])
    def aliyun_recognize():
        """使用阿里云对给定的音频 URL 进行语音识别"""
        return aliyun_recognize_module.aliyun_recognize()
    
    @app.route('/aliyun_recognize_stream', methods=['GET', 'POST'])
    @stream_with_context
    def aliyun_recognize_stream():
        """使用阿里云对给定的音频 URL 进行语音识别（流式传输日志版本）"""
        return aliyun_recognize_stream_module.aliyun_recognize_stream()
    
    @app.route('/aliyun_history', methods=['GET'])
    def aliyun_history():
        """获取阿里云语音识别历史记录"""
        return aliyun_history_module.aliyun_history()
    
    @app.route('/aliyun_download', methods=['GET'])
    def aliyun_download():
        """下载阿里云识别结果文件（文本或 JSON）"""
        return aliyun_download_module.aliyun_download()
    
    @app.route('/aliyun_preview', methods=['GET'])
    def aliyun_preview():
        """预览阿里云识别结果（在浏览器新窗口中打开文本文件）"""
        return aliyun_preview_module.aliyun_preview()
    
    # Whisper 相关路由
    @app.route('/process', methods=['GET', 'POST'])
    def process():
        """处理识别任务"""
        return whisper_process_module.process()
    
    @app.route('/test_process', methods=['GET', 'POST'])
    def test_process():
        """测试识别接口 - 截取前5分钟进行测试"""
        return whisper_test_process_module.test_process()
    
    @app.route('/progressbar', methods=['GET', 'POST'])
    def progressbar():
        """前端获取进度及完成后的结果"""
        return whisper_progressbar_module.progressbar()
    
    @app.route('/v1/audio/transcriptions', methods=['POST'])
    def transcribe_audio():
        """OpenAI 兼容格式接口"""
        return whisper_api_module.transcribe_audio()
    
    @app.route('/api', methods=['GET', 'POST'])
    def api():
        """原 API 接口，保留兼容"""
        return whisper_api_module.api()
    
    # Common 相关路由
    @app.route('/checkupdate', methods=['GET', 'POST'])
    def checkupdate():
        """检查更新"""
        return checkupdate_module.checkupdate()

