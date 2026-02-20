# 系统定时任务设置说明（Mac）

本说明将指导您如何将服务器文件列表缓存更新任务设置为 Mac 系统级别的定时任务。

## 方法一：使用 launchd（推荐）

### 1. 修改 plist 文件路径

编辑 `com.apple.update_server_cache.plist` 文件，确保以下路径正确：

- **Python 路径**：`/Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python`
- **脚本路径**：`/Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py`
- **工作目录**：`/Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt`

### 2. 创建日志目录

```bash
mkdir -p /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs
```

### 3. 安装定时任务

```bash
# 复制 plist 文件到系统目录
cp com.apple.update_server_cache.plist ~/Library/LaunchAgents/

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.apple.update_server_cache.plist
```

### 4. 管理定时任务

```bash
# 启动定时任务
launchctl start com.apple.update_server_cache

# 停止定时任务
launchctl stop com.apple.update_server_cache

# 卸载定时任务
launchctl unload ~/Library/LaunchAgents/com.apple.update_server_cache.plist

# 查看定时任务状态
launchctl list | grep update_server_cache
```

### 5. 查看日志

```bash
# 查看标准输出日志
tail -f logs/update_cache.log

# 查看错误日志
tail -f logs/update_cache_error.log
```

## 方法二：使用 cron（备选）

### 1. 编辑 crontab

```bash
crontab -e
```

### 2. 添加定时任务（每10秒执行一次）

```cron
* * * * * /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py >> /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs/update_cache.log 2>&1
* * * * * sleep 10 && /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py >> /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs/update_cache.log 2>&1
* * * * * sleep 20 && /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py >> /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs/update_cache.log 2>&1
* * * * * sleep 30 && /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py >> /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs/update_cache.log 2>&1
* * * * * sleep 40 && /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py >> /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs/update_cache.log 2>&1
* * * * * sleep 50 && /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/update_server_cache.py >> /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/logs/update_cache.log 2>&1
```

**注意**：cron 最小间隔是 1 分钟，要实现每 10 秒执行一次，需要使用多个任务配合 sleep。

## 方法三：手动测试运行

在设置系统定时任务之前，可以先手动测试脚本：

```bash
# 进入项目目录
cd /Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt

# 激活虚拟环境（如果需要）
source venv/bin/activate

# 运行脚本
python update_server_cache.py
```

## 从 Flask 应用中移除定时任务

设置好系统定时任务后，需要从 Flask 应用中移除定时任务的启动代码：

1. 编辑 `start.py`，删除或注释掉：
   ```python
   # server_files_cache.start_cache_thread()
   ```

2. 编辑 `app_main.py`，删除或注释掉所有：
   ```python
   # server_files_cache.start_cache_thread()
   ```

## 注意事项

1. **环境变量**：确保系统定时任务能够访问到必要的环境变量（如 `.env` 文件中的配置）
2. **Python 路径**：确保 plist 文件中的 Python 路径正确
3. **权限**：确保脚本有执行权限：`chmod +x update_server_cache.py`
4. **日志目录**：确保日志目录存在且有写入权限

## 故障排查

如果定时任务没有运行：

1. 检查日志文件是否有错误信息
2. 手动运行脚本测试是否正常
3. 检查 launchd 状态：`launchctl list | grep update_server_cache`
4. 查看系统日志：`log show --predicate 'process == "launchd"' --last 1h`

