#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量设置
必须在导入任何库之前设置 OpenMP 环境变量（防止崩溃）
"""

import os


def setup_environment():
    """
    设置 OpenMP 和其他环境变量
    必须在导入任何库之前调用
    """
    # macOS 特定：禁用 Objective-C fork 安全检查（关键！）
    os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')
    
    # OpenMP 基础设置
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    os.environ.setdefault('MKL_NUM_THREADS', '1')
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
    os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '1')
    os.environ.setdefault('OMP_DYNAMIC', 'FALSE')
    os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')  # 关键：允许重复的 OpenMP 库
    
    # Fork 相关保护（防止 fork 时崩溃）
    os.environ.setdefault('KMP_INIT_AT_FORK', 'FALSE')
    os.environ.setdefault('OMP_PROC_BIND', 'close')
    os.environ.setdefault('OMP_PLACES', 'cores')
    os.environ.setdefault('KMP_BLOCKTIME', '0')
    os.environ.setdefault('KMP_SETTINGS', '0')
    os.environ.setdefault('KMP_AFFINITY', 'disabled')
    
    # 完全禁用共享内存（macOS 权限问题）
    os.environ.setdefault('KMP_SHARED_MEMORY', 'disabled')
    os.environ.setdefault('OMP_SHARED_MEMORY', 'disabled')

