#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测 CPU 信息脚本
用于查看当前系统的 CPU 核心数和线程配置
"""

import os

print("=" * 60)
print("CPU 信息检测")
print("=" * 60)

# 物理核心数（使用 os.cpu_count() 避免 multiprocessing 资源泄漏警告）
physical_cores = os.cpu_count() or 1
print(f"\n物理 CPU 核心数: {physical_cores}")

# 逻辑核心数（包括超线程）
try:
    logical_cores = len(os.sched_getaffinity(0))
except AttributeError:
    logical_cores = os.cpu_count()

print(f"逻辑 CPU 核心数（包括超线程）: {logical_cores}")

# 当前环境变量中的线程设置
print("\n当前环境变量中的线程配置:")
print(f"  OMP_NUM_THREADS: {os.environ.get('OMP_NUM_THREADS', '未设置')}")
print(f"  MKL_NUM_THREADS: {os.environ.get('MKL_NUM_THREADS', '未设置')}")
print(f"  OPENBLAS_NUM_THREADS: {os.environ.get('OPENBLAS_NUM_THREADS', '未设置')}")
print(f"  NUMEXPR_NUM_THREADS: {os.environ.get('NUMEXPR_NUM_THREADS', '未设置')}")
print(f"  VECLIB_MAXIMUM_THREADS: {os.environ.get('VECLIB_MAXIMUM_THREADS', '未设置')}")

print("\n" + "=" * 60)
print("建议配置:")
print("=" * 60)
print(f"对于 {physical_cores} 核 CPU，建议设置线程数为: {physical_cores}")
print(f"或者设置为逻辑核心数: {logical_cores}")
print("\n注意：")
print("- 物理核心数：实际 CPU 核心数量")
print("- 逻辑核心数：包括超线程技术（如果支持）")
print("- 对于计算密集型任务，通常使用物理核心数更稳定")
print("- 可以留一个核心给系统，所以建议设置为: " + str(max(1, physical_cores - 1)) + " 或 " + str(physical_cores))
print("=" * 60)

