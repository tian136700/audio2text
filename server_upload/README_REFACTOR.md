# upload_to_server_tool.py 重构说明

## 概述

`upload_to_server_tool.py` 文件已重构为多个模块，以提高代码的可维护性和可读性。

## 新的文件结构

### 1. `config.py` - 配置模块
- **功能**: 管理所有服务器配置信息
- **内容**: 
  - 服务器连接配置（HOST, PORT, USER, PASSWORD, KEY_PATH）
  - 文件存储路径配置（SERVER_UPLOAD_DIR）
  - 公网访问 URL 配置（PUBLIC_URL_PREFIX）
  - 历史记录文件路径（HISTORY_FILE）
- **依赖**: `dotenv`（环境变量加载）

### 2. `utils.py` - 工具函数模块
- **功能**: 提供各种工具函数
- **内容**:
  - `get_audio_duration()`: 获取音频文件时长
  - `filename_to_pinyin()`: 文件名转拼音
  - `format_duration_for_filename()`: 格式化时长为文件名格式
  - `parse_duration_from_filename()`: 从文件名解析时长
  - `format_duration()`: 格式化时长为可读字符串
- **依赖**: `pypinyin`（可选，用于拼音转换）

### 3. `ssh_client.py` - SSH 客户端模块
- **功能**: 封装 SSH 连接和 SFTP 操作
- **内容**:
  - `SSHClient` 类：提供连接、SFTP、命令执行等功能
  - 支持上下文管理器（`with` 语句）
- **依赖**: `paramiko`

### 4. `history.py` - 历史记录模块
- **功能**: 管理历史记录的保存和加载
- **内容**:
  - `save_history_record()`: 保存历史记录（优先数据库，回退到 JSON）
  - `load_history()`: 加载历史记录（优先数据库，回退到 JSON）
- **依赖**: `db` 模块（数据库操作）

### 5. `file_operations.py` - 文件操作模块
- **功能**: 提供服务器文件操作功能
- **内容**:
  - `list_server_files()`: 列出服务器上的文件
  - `delete_server_file_by_id()`: 删除服务器上的文件
- **依赖**: `config`, `utils`, `history`, `ssh_client`

### 6. `upload_to_server_tool.py` - 主模块（重构后）
- **功能**: 提供主要的上传接口
- **内容**:
  - `upload_file_to_server()`: 上传文件到服务器的主函数
  - 导出所有子模块的函数和变量（保持向后兼容）
- **依赖**: 所有其他模块

## 向后兼容性

为了保持向后兼容，`upload_to_server_tool.py` 导出了以下内容：

### 导出的配置变量
```python
SERVER_HOST = config.SERVER_HOST
SERVER_PORT = config.SERVER_PORT
SERVER_USER = config.SERVER_USER
SERVER_PASSWORD = config.SERVER_PASSWORD
SERVER_KEY_PATH = config.SERVER_KEY_PATH
SERVER_UPLOAD_DIR = config.SERVER_UPLOAD_DIR
PUBLIC_URL_PREFIX = config.PUBLIC_URL_PREFIX
HISTORY_FILE = config.HISTORY_FILE
```

### 导出的函数
```python
# 工具函数
get_audio_duration = utils.get_audio_duration
filename_to_pinyin = utils.filename_to_pinyin
format_duration_for_filename = utils.format_duration_for_filename
parse_duration_from_filename = utils.parse_duration_from_filename
format_duration = utils.format_duration

# 文件操作函数
list_server_files = file_operations.list_server_files
delete_server_file_by_id = file_operations.delete_server_file_by_id

# 历史记录函数
load_history = history.load_history
save_history_record = history.save_history_record
```

## 使用方式

### 原有代码无需修改
```python
from server_upload import upload_to_server_tool

# 这些调用方式仍然有效
upload_to_server_tool.upload_file_to_server(...)
upload_to_server_tool.list_server_files(...)
upload_to_server_tool.SERVER_HOST
```

### 新的模块化使用方式（推荐）
```python
from server_upload import config, utils, ssh_client, file_operations, history

# 直接使用子模块
config.SERVER_HOST
utils.get_audio_duration(...)
file_operations.list_server_files(...)
```

## 优势

1. **更好的代码组织**: 每个模块职责单一，易于理解和维护
2. **更容易查找问题**: 问题定位更精确，不需要在 1000+ 行的文件中搜索
3. **更容易测试**: 每个模块可以独立测试
4. **更容易扩展**: 新功能可以添加到相应的模块中
5. **向后兼容**: 现有代码无需修改即可使用

## 注意事项

- 所有模块使用相对导入（`from . import ...`）
- 配置模块在导入时会加载环境变量
- SSH 客户端支持上下文管理器，推荐使用 `with` 语句
- 历史记录模块优先使用数据库，JSON 文件作为回退方案
