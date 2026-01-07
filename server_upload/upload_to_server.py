#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传文件到腾讯云服务器并获取公网 URL
支持通过 SCP/SFTP 上传文件到服务器
"""

import os
import sys
import paramiko
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 配置
load_dotenv()

# ==================== 配置信息 ====================
# 所有敏感信息同样从环境变量中读取，避免写死在脚本里
SERVER_HOST = os.getenv("SERVER_UPLOAD_HOST")
SERVER_PORT = int(os.getenv("SERVER_UPLOAD_PORT", "22"))
SERVER_USER = os.getenv("SERVER_UPLOAD_USER", "root")
SERVER_PASSWORD = os.getenv("SERVER_UPLOAD_PASSWORD")
SERVER_KEY_PATH = os.getenv("SERVER_UPLOAD_KEY_PATH") or None

# 服务器上的文件存储路径（Web 可访问的目录）
SERVER_UPLOAD_DIR = os.getenv("SERVER_UPLOAD_DIR", "/data/audio")

# 服务器公网访问 URL 前缀
PUBLIC_URL_PREFIX = os.getenv("SERVER_PUBLIC_URL_PREFIX")


def upload_file_scp(local_file_path, remote_filename=None):
    """
    通过 SCP 上传文件到服务器
    
    Args:
        local_file_path: 本地文件路径
        remote_filename: 服务器上的文件名（可选，默认使用原文件名）
    
    Returns:
        str: 文件的公网访问 URL
    """
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"文件不存在: {local_file_path}")
    
    if remote_filename is None:
        remote_filename = os.path.basename(local_file_path)
    
    # 远程文件路径
    remote_file_path = f"{SERVER_UPLOAD_DIR}/{remote_filename}"
    
    print(f"正在连接到服务器: {SERVER_HOST}:{SERVER_PORT}")
    print(f"用户: {SERVER_USER}")
    print(f"本地文件: {local_file_path}")
    print(f"远程路径: {remote_file_path}")
    
    # 创建 SSH 客户端
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # 连接服务器
        if SERVER_KEY_PATH:
            # 使用密钥认证
            private_key = paramiko.RSAKey.from_private_key_file(SERVER_KEY_PATH)
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                pkey=private_key
            )
        else:
            # 使用密码认证
            if SERVER_PASSWORD is None:
                raise ValueError("需要设置 SERVER_PASSWORD 或 SERVER_KEY_PATH")
            ssh.connect(
                hostname=SERVER_HOST,
                port=SERVER_PORT,
                username=SERVER_USER,
                password=SERVER_PASSWORD
            )
        
        print("✅ 连接成功！")
        
        # 创建远程目录（如果不存在）
        print(f"检查远程目录: {SERVER_UPLOAD_DIR}")
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {SERVER_UPLOAD_DIR}")
        stdout.channel.recv_exit_status()  # 等待命令执行完成
        
        # 使用 SFTP 上传文件
        print("正在上传文件...")
        sftp = ssh.open_sftp()
        sftp.put(local_file_path, remote_file_path)
        sftp.close()
        
        print(f"✅ 上传成功！")
        
        # 设置文件权限（确保 Web 服务器可以访问）
        print("设置文件权限...")
        ssh.exec_command(f"chmod 644 {remote_file_path}")
        
        # 生成公网 URL
        public_url = f"{PUBLIC_URL_PREFIX}/{remote_filename}"
        print(f"✅ 公网 URL: {public_url}")
        
        return public_url
        
    except Exception as e:
        print(f"❌ 上传失败: {str(e)}")
        raise
    finally:
        ssh.close()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python upload_to_server.py <本地文件路径> [远程文件名]")
        print("\n示例:")
        print("  python upload_to_server.py /path/to/audio.wav")
        print("  python upload_to_server.py /path/to/audio.wav my_audio.wav")
        print("\n⚠️  使用前请先配置脚本中的服务器信息：")
        print("  - SERVER_HOST: 服务器 IP 或域名")
        print("  - SERVER_USER: SSH 用户名")
        print("  - SERVER_PASSWORD: SSH 密码（或使用 SERVER_KEY_PATH）")
        print("  - SERVER_UPLOAD_DIR: 服务器上的上传目录")
        print("  - PUBLIC_URL_PREFIX: 公网访问 URL 前缀")
        sys.exit(1)
    
    local_file = sys.argv[1]
    remote_filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 检查配置
    if SERVER_HOST == "你的服务器IP或域名":
        print("❌ 错误：请先配置服务器信息！")
        print("\n请编辑 upload_to_server.py，填写以下信息：")
        print("  - SERVER_HOST: 服务器 IP 或域名")
        print("  - SERVER_USER: SSH 用户名")
        print("  - SERVER_PASSWORD: SSH 密码（或使用 SERVER_KEY_PATH）")
        print("  - SERVER_UPLOAD_DIR: 服务器上的上传目录（Web 可访问）")
        print("  - PUBLIC_URL_PREFIX: 公网访问 URL 前缀")
        sys.exit(1)
    
    try:
        public_url = upload_file_scp(local_file, remote_filename)
        print("\n" + "=" * 60)
        print("✅ 上传成功！")
        print("=" * 60)
        print(f"公网 URL: {public_url}")
        print("\n你可以使用这个 URL 进行语音识别了！")
        print("\n在 aliyun_zhuanhuan.py 中修改 file_urls 为：")
        print(f'file_urls=["{public_url}"]')
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 上传失败！")
        print("=" * 60)
        print(f"错误信息: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

