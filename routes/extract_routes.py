#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动提取路由处理函数到各个模块
"""
import re
import os

# 读取 app_main.py
with open('app_main.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# 找到第一个 main() 函数，只处理前面的内容
main_idx = None
for i, line in enumerate(lines):
    if 'def main():' in line and i < 1800:
        main_idx = i
        break

if main_idx:
    lines = lines[:main_idx+200]  # 保留 main 函数
    content = '\n'.join(lines)

print(f"处理 {len(lines)} 行代码")
