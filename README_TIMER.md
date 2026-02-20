# 系统定时任务快速指南

## 快速安装

运行安装脚本（会自动检测 Python 路径并安装）：

```bash
./install_system_timer.sh
```

## 手动安装

### 1. 测试脚本

```bash
python3 update_server_cache.py
```

### 2. 安装 launchd 定时任务

```bash
# 复制 plist 文件
cp com.apple.update_server_cache.plist ~/Library/LaunchAgents/

# 加载并启动
launchctl load ~/Library/LaunchAgents/com.apple.update_server_cache.plist
launchctl start com.apple.update_server_cache
```

## 管理命令

```bash
# 查看状态
launchctl list | grep update_server_cache

# 停止任务
launchctl stop com.apple.update_server_cache

# 启动任务
launchctl start com.apple.update_server_cache

# 卸载任务
launchctl unload ~/Library/LaunchAgents/com.apple.update_server_cache.plist
```

## 查看日志

```bash
# 标准输出
tail -f logs/update_cache.log

# 错误日志
tail -f logs/update_cache_error.log
```

## 注意事项

1. **已从 Flask 应用移除定时任务**：`start.py` 和 `app_main.py` 中的定时任务启动代码已被注释
2. **定时任务独立运行**：每 10 秒自动更新一次服务器文件列表缓存
3. **日志文件**：日志保存在 `logs/` 目录下

## 故障排查

如果定时任务没有运行：

1. 检查日志文件是否有错误
2. 手动运行脚本测试：`python3 update_server_cache.py`
3. 检查任务状态：`launchctl list | grep update_server_cache`
4. 查看系统日志：`log show --predicate 'process == "launchd"' --last 1h`

