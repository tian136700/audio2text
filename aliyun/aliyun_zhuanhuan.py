from http import HTTPStatus
from dashscope.audio.asr import Transcription
from urllib import request
import dashscope
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量读取 API Key
api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIYUN_API_KEY")
if not api_key:
    raise ValueError("未配置阿里云 API Key，请在 .env 中设置 DASHSCOPE_API_KEY 或 ALIYUN_API_KEY")
dashscope.api_key = api_key

print("=" * 60)
print("开始提交阿里云语音识别任务...")

# 从环境变量读取服务器音频基础 URL（例如：http://你的服务器IP或域名/audio）
AUDIO_BASE_URL = os.getenv("SERVER_PUBLIC_URL_PREFIX", "http://127.0.0.1/audio")
TEST_AUDIO_PATH = os.getenv("SERVER_TEST_AUDIO_PATH", "test.m4a")
TEST_AUDIO_URL = f"{AUDIO_BASE_URL.rstrip('/')}/{TEST_AUDIO_PATH}"

print("音频文件URL:", TEST_AUDIO_URL)
print("=" * 60)

# 使用你的腾讯云服务器音频URL
task_response = Transcription.async_call(
    model='paraformer-v2',
    file_urls=[TEST_AUDIO_URL],
    language_hints=['zh']  # 指定为中文识别
)

print(f"任务已提交，Task ID: {task_response.output.task_id}")
print("正在等待识别完成，请稍候...")

transcription_response = Transcription.wait(task=task_response.output.task_id)

print("=" * 60)
print("识别任务完成！")
print("=" * 60)

if transcription_response.status_code == HTTPStatus.OK:
    for idx, transcription in enumerate(transcription_response.output['results'], 1):
        print(f"\n【文件 {idx}】")
        if transcription['subtask_status'] == 'SUCCEEDED':
            url = transcription['transcription_url']
            print(f"识别成功！正在获取结果...")
            result = json.loads(request.urlopen(url).read().decode('utf8'))
            
            # 保存识别结果到文件（先保存，再显示）
            save_dir = os.path.dirname(os.path.abspath(__file__))  # aliyun 文件夹
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存完整 JSON 结果
            json_file = os.path.join(save_dir, f"识别结果_{timestamp}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            print(f"\n✅ 完整结果已保存: {json_file}")
            
            # 提取文本内容（根据实际数据结构）
            sentences = []
            if 'transcripts' in result and len(result.get('transcripts', [])) > 0:
                # 阿里云返回格式：transcripts[0]['sentences']
                sentences = result['transcripts'][0].get('sentences', [])
            elif 'sentences' in result:
                # 备用格式：直接有 sentences
                sentences = result.get('sentences', [])
            
            if sentences:
                # 保存纯文本结果
                text_file = os.path.join(save_dir, f"识别文本_{timestamp}.txt")
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"音频URL: {TEST_AUDIO_URL}\n")
                    f.write("=" * 60 + "\n\n")
                    for sentence in sentences:
                        if 'text' in sentence:
                            # 计算时间（毫秒转秒）
                            begin_time = sentence.get('begin_time', 0) / 1000
                            end_time = sentence.get('end_time', 0) / 1000
                            # 格式化时间
                            begin_str = f"{int(begin_time//3600):02d}:{int((begin_time%3600)//60):02d}:{begin_time%60:05.2f}"
                            end_str = f"{int(end_time//3600):02d}:{int((end_time%3600)//60):02d}:{end_time%60:05.2f}"
                            f.write(f"[{begin_str} - {end_str}] {sentence['text']}\n")
                print(f"✅ 文本结果已保存: {text_file}")
                
                # 显示部分文本内容（前5句）
                print("\n" + "-" * 60)
                print("文本内容预览（前5句）：")
                print("-" * 60)
                for i, sentence in enumerate(sentences[:5]):
                    if 'text' in sentence:
                        print(sentence['text'])
                if len(sentences) > 5:
                    print(f"... (共 {len(sentences)} 句，完整内容请查看保存的文件)")
            else:
                print("⚠️  未找到文本内容")
        else:
            print('❌ 识别失败！')
            print(f"状态: {transcription.get('subtask_status', 'Unknown')}")
            print(f"详细信息: {transcription}")
else:
    print('❌ 请求失败！')
    print(f"错误信息: {transcription_response.output.message}")