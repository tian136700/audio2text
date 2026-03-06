#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH 客户端模块

提供 SSH 连接和 SFTP 操作的封装。
"""

import paramiko
from . import config


class SSHClient:
    """SSH 客户端封装类"""
    
    def __init__(self):
        self.ssh = None
        self.sftp = None
    
    def connect(self):
        """
        连接到服务器
        
        Raises:
            ValueError: 如果配置不完整
        """
        if not config.SERVER_HOST:
            raise ValueError("SERVER_UPLOAD_HOST 未配置，请在 .env 或环境变量中设置服务器地址")
        if not (config.SERVER_PASSWORD or config.SERVER_KEY_PATH):
            raise ValueError("需要配置 SERVER_UPLOAD_PASSWORD 或 SERVER_UPLOAD_KEY_PATH 才能连接服务器")
        
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if config.SERVER_KEY_PATH:
            private_key = paramiko.RSAKey.from_private_key_file(config.SERVER_KEY_PATH)
            self.ssh.connect(
                hostname=config.SERVER_HOST,
                port=config.SERVER_PORT,
                username=config.SERVER_USER,
                pkey=private_key
            )
        else:
            self.ssh.connect(
                hostname=config.SERVER_HOST,
                port=config.SERVER_PORT,
                username=config.SERVER_USER,
                password=config.SERVER_PASSWORD
            )
    
    def open_sftp(self):
        """打开 SFTP 连接"""
        if not self.ssh:
            raise RuntimeError("请先调用 connect() 连接服务器")
        self.sftp = self.ssh.open_sftp()
        return self.sftp
    
    def exec_command(self, command):
        """
        执行远程命令
        
        Args:
            command: 要执行的命令
        
        Returns:
            tuple: (stdin, stdout, stderr)
        """
        if not self.ssh:
            raise RuntimeError("请先调用 connect() 连接服务器")
        return self.ssh.exec_command(command)
    
    def close(self):
        """关闭连接"""
        if self.sftp:
            try:
                self.sftp.close()
            except Exception:
                pass
            self.sftp = None
        
        if self.ssh:
            try:
                self.ssh.close()
            except Exception:
                pass
            self.ssh = None
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
        return False
