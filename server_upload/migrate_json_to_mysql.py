#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 server_files_cache.json 的数据迁移到 MySQL 数据库
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径，以便导入 server_upload 模块
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server_upload import db

def migrate():
    """执行迁移"""
    print("=" * 60)
    print("开始迁移 server_files_cache.json 到 MySQL")
    print("=" * 60)
    
    # 初始化数据库
    print("\n1. 初始化数据库表...")
    try:
        db.init_database()
        print("✓ 数据库表初始化完成")
    except Exception as e:
        print(f"✗ 数据库表初始化失败: {e}")
        return
    
    # 迁移表结构（如果需要）
    print("\n1.5. 检查表结构迁移...")
    try:
        db.migrate_table_structure()
        print("✓ 表结构检查完成")
    except Exception as e:
        print(f"⚠ 表结构迁移检查失败（可能已是最新结构）: {e}")
    
    # 读取 JSON 文件
    print("\n2. 读取 JSON 文件...")
    cache_file = Path(__file__).resolve().parent / "server_files_cache.json"
    
    if not cache_file.exists():
        print(f"✗ JSON 文件不存在: {cache_file}")
        return
    
    try:
        with cache_file.open("r", encoding="utf-8") as f:
            cache_data = json.load(f)
        files = cache_data.get("files", [])
        print(f"✓ 读取到 {len(files)} 个文件")
    except Exception as e:
        print(f"✗ 读取 JSON 文件失败: {e}")
        return
    
    # 保存到数据库
    print("\n3. 保存到数据库...")
    try:
        # 为旧数据添加缺失的字段（如果不存在）
        for file_info in files:
            if 'upload_duration' not in file_info:
                file_info['upload_duration'] = None
            if 'uploader_ip' not in file_info:
                file_info['uploader_ip'] = ''
            # 处理 original_name：如果和 file_name 相同或为空，则留空（表示没有中文名称）
            original_name = file_info.get('original_name', '')
            file_name = file_info.get('file_name', '')
            if original_name == file_name or not original_name:
                file_info['original_name'] = ''  # 留空，表示暂时没有中文名称
        
        db.save_files(files)
        print(f"✓ 成功保存 {len(files)} 个文件到数据库")
    except Exception as e:
        print(f"✗ 保存到数据库失败: {e}")
        return
    
    # 更新元信息
    print("\n4. 更新缓存元信息...")
    try:
        last_update = cache_data.get("last_update")
        update_count = cache_data.get("update_count", 0)
        db.update_cache_meta(last_update, increment_count=False)
        # 手动设置更新计数
        if update_count > 0:
            import pymysql
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE server_files_cache_meta SET update_count = %s LIMIT 1", (update_count,))
            conn.commit()
            cursor.close()
            conn.close()
        print("✓ 缓存元信息更新完成")
    except Exception as e:
        print(f"✗ 更新缓存元信息失败: {e}")
    
    # 验证数据
    print("\n5. 验证数据...")
    try:
        db_files = db.get_files(limit=1000)
        print(f"✓ 数据库中有 {len(db_files)} 个文件")
        if len(db_files) == len(files):
            print("✓ 数据迁移成功，文件数量一致")
        else:
            print(f"⚠ 警告：文件数量不一致（JSON: {len(files)}, DB: {len(db_files)}）")
    except Exception as e:
        print(f"✗ 验证数据失败: {e}")
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)

if __name__ == "__main__":
    migrate()

