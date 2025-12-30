<div align="center">

**中文简体** | [English](./docs/en/README_EN.md)

</div>

---

<div align="center">

[👑 捐助本项目](https://pyvideotrans.com/about)

</div>

---

# 语音识别转文字工具

一个功能强大的**离线本地**语音识别转文字工具，基于 `faster-whisper` 开源模型，可将视频/音频中的人类声音识别并转为文字。支持多种输出格式、说话人识别、音频截取等功能，完全本地运行，无需联网，可部署在内网环境。

## ✨ 主要特性

- 🎯 **离线运行**：完全本地化处理，无需联网，保护隐私
- 🎤 **多格式支持**：支持 JSON、SRT 字幕、纯文本、易读格式（时分秒）等多种输出格式
- 👥 **说话人识别**：自动识别音频中的不同说话人，标注为"说话人A"、"说话人B"等
- ✂️ **音频截取**：支持按时间段截取音频片段，并保存下载
- 🧪 **测试识别**：支持先识别前 5 分钟音频进行测试，确认效果后再完整处理
- 🌍 **多语言支持**：支持中文、英语、日语、韩语、法语、德语等多种语言
- ⚡ **CUDA 加速**：支持 NVIDIA GPU 加速，大幅提升识别速度
- 🔌 **API 接口**：提供 RESTful API，兼容 OpenAI API 格式
- 🎨 **Web 界面**：友好的 Web 操作界面，支持拖拽上传

## 📋 功能列表

### 1. 语音识别
- 支持多种音频/视频格式：mp4、mp3、flac、wav、aac、m4a、avi、mkv、mpeg、mov
- 自动转换为 WAV 格式进行处理
- 实时显示识别进度
- 支持批量文件处理

### 2. 说话人识别（Speaker Diarization）
- 基于 `pyannote.audio` 模型
- 自动识别音频中的不同说话人
- 输出格式：`说话人A   0小时0分16秒 - 0小时4分53秒   说话内容`
- 需要 Hugging Face Token（仅用于下载模型，数据不上传）

### 3. 音频截取
- 独立页面操作
- 支持按时间段截取（格式：00:00:00）
- 截取后自动保存到 `static/cut/` 目录
- 查看历史截取记录
- 显示截取时间段、时长、文件大小等信息

### 4. 输出格式
- **JSON**：包含时间戳和文本的 JSON 格式
- **SRT**：标准字幕文件格式
- **Text**：纯文本格式
- **Readable**：易读格式，显示为"X小时Y分Z秒 - X小时Y分Z秒 文本内容"

## 🚀 快速开始

### 方式一：预编译版本（Windows）

1. [下载预编译版本](https://github.com/jianchang512/stt/releases)
2. 解压到任意目录，如 `E:/stt`
3. 双击 `start.exe`，等待浏览器自动打开
4. 上传音频/视频文件开始识别

### 方式二：源码部署（Linux/Mac/Windows）

#### 环境要求

- Python 3.9 - 3.11
- FFmpeg（用于音频/视频处理）

#### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/jianchang512/stt.git
   cd stt
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **安装 FFmpeg**
   - **Windows**：解压项目中的 `ffmpeg.7z`，将 `ffmpeg.exe` 和 `ffprobe.exe` 放到项目目录
   - **Linux**：`sudo apt-get install ffmpeg`（Ubuntu/Debian）
   - **Mac**：`brew install ffmpeg`

5. **下载模型**
   - [下载模型压缩包](https://github.com/jianchang512/stt/releases/tag/0.0)
   - 根据需要下载模型（tiny/base/small/medium/large-v3）
   - 解压后将文件夹放到项目根目录的 `models` 文件夹内

6. **配置环境变量（可选，用于说话人识别）**
   ```bash
   # 复制示例文件
   cp env.example .env
   
   # 编辑 .env 文件，填入你的 Hugging Face Token
   # 获取 Token：https://huggingface.co/settings/tokens
   ```

7. **启动服务**
   ```bash
   python start.py
   ```

8. **访问应用**
   - 浏览器会自动打开 `http://127.0.0.1:9977`
   - 或手动访问该地址

## ⚙️ 配置说明

### 配置文件：`set.ini`

```ini
; 服务地址和端口
web_address=127.0.0.1:9977

; 界面语言：en 或 zh（留空自动检测）
lang=

; 设备类型：cpu 或 cuda（需要配置 CUDA 环境）
devtype=cpu

; 识别参数（降低这些值可以减少显存使用）
beam_size=5
best_of=5

; VAD（语音活动检测）：false 使用更少 GPU 内存，true 使用更多
vad=true

; 温度参数：0 使用更少 GPU 内存，值越高使用越多
temperature=0

; 是否基于前文：false 使用更少 GPU 内存，true 使用更多
condition_on_previous_text=false

; 中文提示词（可选）
initial_prompt_zh=

; 可用模型列表
model_list=tiny,tiny.en,base,base.en,small,small.en,medium,medium.en,large-v1,large-v2,large-v3,large-v3-turbo

; OpenCC 配置：s2t（简体→繁体）或 t2s（繁体→简体）
opencc = t2s
```

### 环境变量：`.env`

```bash
# Hugging Face Token（用于说话人识别功能）
# 获取方式：https://huggingface.co/settings/tokens
HF_TOKEN=your_huggingface_token_here
```

## 📖 使用指南

### Web 界面使用

1. **上传文件**
   - 点击上传区域选择文件
   - 或直接拖拽文件到上传区域

2. **选择参数**
   - **发音语言**：选择音频中的语言
   - **选择模型**：根据需求选择模型（tiny 最快但精度较低，large-v3 最精确但需要更多资源）
   - **返回格式**：选择输出格式
   - **说话人识别**：开启后会自动识别不同说话人

3. **测试识别（可选）**
   - 点击"测试识别（前5分钟）"按钮
   - 查看识别效果，确认无误后再进行完整识别

4. **开始识别**
   - 点击"立即识别"按钮
   - 等待识别完成，结果会显示在下方文本框中

5. **导出结果**
   - 点击"导出文本"按钮下载识别结果

### 音频截取功能

1. 点击侧边栏中的"音频截取"菜单
2. 上传音频文件
3. 输入开始时间和结束时间（格式：00:00:00）
4. 点击"截取并保存"
5. 在历史记录中查看和下载截取的音频

## 🔌 API 接口

### 基础识别接口

**接口地址**：`http://127.0.0.1:9977/api`

**请求方法**：POST

**请求参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| file | file | 音视频文件（二进制上传） |
| language | string | 语言代码（zh/en/ja/ko/fr/de/es/th/it/pt/vi/ar/tr/ru） |
| model | string | 模型名称（tiny/base/small/medium/large-v3） |
| response_format | string | 返回格式（text/json/srt） |

**响应格式**：

```json
{
  "code": 0,
  "msg": "ok",
  "data": "识别后的文本内容"
}
```

**示例代码**：

```python
import requests

url = "http://127.0.0.1:9977/api"
files = {"file": open("audio.wav", "rb")}
data = {
    "language": "zh",
    "model": "base",
    "response_format": "json"
}
response = requests.post(url, files=files, data=data, timeout=600)
print(response.json())
```

### OpenAI 兼容接口

**接口地址**：`http://127.0.0.1:9977/v1/audio/transcriptions`

**使用示例**：

```python
from openai import OpenAI

client = OpenAI(
    api_key='123',
    base_url='http://127.0.0.1:9977/v1'
)

audio_file = open("audio.wav", "rb")
transcription = client.audio.transcriptions.create(
    model="tiny",
    file=audio_file,
    response_format="text"  # 支持 text、srt 格式
)

print(transcription.text)
```

## 🎯 模型说明

| 模型 | 大小 | 速度 | 精度 | 适用场景 |
|------|------|------|------|----------|
| tiny | ~39MB | 最快 | 较低 | 快速测试、资源受限环境 |
| base | ~74MB | 快 | 中等 | 日常使用、平衡选择 |
| small | ~244MB | 中等 | 较好 | 一般精度要求 |
| medium | ~769MB | 较慢 | 好 | 较高精度要求 |
| large-v3 | ~1550MB | 最慢 | 最好 | 高精度要求、专业场景 |

**注意**：
- 如果没有 NVIDIA GPU 或未配置 CUDA 环境，不建议使用 large-v3 模型，可能导致内存耗尽
- 显存不足 8GB 时，尽量避免使用 large-v3 模型，尤其是处理大于 20MB 的视频时

## ⚡ CUDA 加速配置

### 安装 CUDA

1. **升级显卡驱动**到最新版本

2. **安装 CUDA Toolkit**
   - 下载地址：https://developer.nvidia.com/cuda-downloads
   - 选择与你的系统匹配的版本

3. **安装 cuDNN**
   - 下载地址：https://developer.nvidia.com/rdp/cudnn-archive
   - 选择与 CUDA 版本匹配的 cuDNN

4. **验证安装**
   ```bash
   # 检查 CUDA 版本
   nvcc --version
   
   # 检查 GPU 状态
   nvidia-smi
   
   # 测试 CUDA（在项目目录下）
   python testcuda.py
   ```

5. **配置使用 CUDA**
   - 编辑 `set.ini` 文件
   - 将 `devtype=cpu` 改为 `devtype=cuda`
   - 重启应用

### 安装 CUDA 版本的 PyTorch

```bash
pip uninstall -y torch
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

## 🐛 常见问题

### 1. 中文输出繁体字

- 在 `set.ini` 中设置 `opencc = t2s`（繁体→简体）

### 2. CUDA 相关错误

**错误：`cublasxx.dll` 不存在**
- 下载 [cuBLAS](https://github.com/jianchang512/stt/releases/download/0.0/cuBLAS_win.7z)
- 解压后将 dll 文件复制到 `C:/Windows/System32` 目录

**错误：尚未执行完毕就闪退**
- 检查是否正确安装了 cuDNN
- 如果显存不足，改用 medium 或更小的模型
- 显存不足 8GB 时，避免使用 large-v3 模型

### 3. 控制台警告信息

**警告：`[W:onnxruntime:Default, onnxruntime_pybind_state.cc:1983 ...] Init provider bridge failed.`**
- 可以忽略，不影响使用

### 4. 说话人识别功能不可用

- 确保已安装 `pyannote.audio`：`pip install pyannote.audio`
- 确保在 `.env` 文件中配置了 `HF_TOKEN`
- 确保已接受 pyannote 模型的使用条款：https://huggingface.co/pyannote/speaker-diarization-3.1

### 5. 开发模式

- 设置环境变量 `DEV=1` 启用开发模式（自动重载）
- 开发模式：`DEV=1 python start.py`
- 生产模式：直接 `python start.py`（使用 gevent 服务器）

## 📁 项目结构

```
stt/
├── start.py              # 主程序入口
├── cut_tool.py           # 音频截取工具
├── requirements.txt      # Python 依赖
├── set.ini              # 配置文件
├── env.example          # 环境变量示例
├── .env                 # 环境变量（需自行创建）
├── models/             # 模型存储目录
├── static/              # 静态文件目录
│   ├── cut/            # 截取的音频文件
│   └── tmp/            # 临时文件
├── templates/          # HTML 模板
│   ├── index.html      # 主页面
│   └── cut.html        # 音频截取页面
└── stslib/            # 工具库
    ├── cfg.py         # 配置管理
    └── tool.py        # 工具函数
```

## 🤝 相关项目

- [视频翻译配音工具](https://github.com/jianchang512/pyvideotrans)：翻译字幕并配音
- [声音克隆工具](https://github.com/jianchang512/clone-voice)：用任意音色合成语音
- [人声背景乐分离](https://github.com/jianchang512/vocal-separate)：极简的人声和背景音乐分离工具

## 🙏 致谢

本项目主要依赖以下开源项目：

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)：快速语音识别模型
- [Flask](https://github.com/pallets/flask)：Web 框架
- [FFmpeg](https://ffmpeg.org/)：音视频处理
- [Layui](https://layui.dev)：前端 UI 框架
- [pyannote.audio](https://github.com/pyannote/pyannote-audio)：说话人识别

## 📄 许可证

请查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

- 遇到问题？[提交 Issue](https://github.com/jianchang512/stt/issues)
- 需要帮助？[加入 Discord](https://discord.gg/TMCM2PfHzQ)

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

</div>
