#!/bin/bash
# 安装系统定时任务脚本

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.apple.update_server_cache.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "=========================================="
echo "安装服务器文件列表缓存系统定时任务"
echo "=========================================="
echo ""

# 检查 plist 文件是否存在
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "错误: 找不到 $PLIST_SOURCE 文件"
    exit 1
fi

# 检查 Python 环境
if [ -f "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
    echo "✓ 找到虚拟环境: $PYTHON_PATH"
elif command -v python3 &> /dev/null; then
    PYTHON_PATH=$(which python3)
    echo "✓ 使用系统 Python: $PYTHON_PATH"
else
    echo "错误: 找不到 Python 解释器"
    exit 1
fi

# 更新 plist 文件中的路径
echo ""
echo "更新 plist 文件路径..."
sed -i.bak \
    -e "s|/Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt/venv/bin/python|$PYTHON_PATH|g" \
    -e "s|/Users/apple/Documents/其他/童年创伤证据整理/李春容隐私权名誉权纠纷/code/stt|$SCRIPT_DIR|g" \
    "$PLIST_SOURCE"

# 创建日志目录
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
echo "✓ 创建日志目录: $LOG_DIR"

# 确保脚本有执行权限
chmod +x "$SCRIPT_DIR/update_server_cache.py"
echo "✓ 设置脚本执行权限"

# 测试运行脚本
echo ""
echo "测试运行脚本..."
if "$PYTHON_PATH" "$SCRIPT_DIR/update_server_cache.py"; then
    echo "✓ 脚本测试成功"
else
    echo "⚠ 警告: 脚本测试失败，但继续安装..."
fi

# 如果已存在，先卸载
if [ -f "$PLIST_TARGET" ]; then
    echo ""
    echo "检测到已存在的定时任务，先卸载..."
    launchctl unload "$PLIST_TARGET" 2>/dev/null || true
    rm -f "$PLIST_TARGET"
    echo "✓ 已卸载旧任务"
fi

# 复制 plist 文件
echo ""
echo "安装定时任务..."
cp "$PLIST_SOURCE" "$PLIST_TARGET"
echo "✓ 已复制到: $PLIST_TARGET"

# 加载定时任务
launchctl load "$PLIST_TARGET"
echo "✓ 已加载定时任务"

# 启动定时任务
launchctl start com.apple.update_server_cache
echo "✓ 已启动定时任务"

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "管理命令："
echo "  查看状态: launchctl list | grep update_server_cache"
echo "  停止任务: launchctl stop com.apple.update_server_cache"
echo "  启动任务: launchctl start com.apple.update_server_cache"
echo "  卸载任务: launchctl unload $PLIST_TARGET"
echo ""
echo "查看日志："
echo "  标准输出: tail -f $LOG_DIR/update_cache.log"
echo "  错误日志: tail -f $LOG_DIR/update_cache_error.log"
echo ""

