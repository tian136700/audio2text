#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迁移表结构并重新排序 ID
1. 将 id 字段从 VARCHAR 改为 INT AUTO_INCREMENT
2. 按照上传时间排序，重新分配 1,2,3,4... 的 ID（旧的在前，新的在后）
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server_upload import db

def main():
    """执行迁移和重新排序"""
    print("=" * 60)
    print("迁移表结构并重新排序 ID")
    print("=" * 60)
    print("\n需求：")
    print("1. 将 id 字段改为 INT AUTO_INCREMENT")
    print("2. 按照上传时间排序，重新分配 1,2,3,4... 的 ID")
    print("3. 旧的记录在前（ID 小），新的记录在后（ID 大）")
    print("=" * 60)
    
    try:
        # 检查当前表结构
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'id'
        """, (db.DB_NAME,))
        result = cursor.fetchone()
        
        if not result:
            print("\n✗ 表 server_files 不存在")
            cursor.close()
            conn.close()
            return 1
        
        current_type = result['DATA_TYPE'].upper()
        print(f"\n当前 id 字段类型: {current_type}")
        
        cursor.execute("SELECT COUNT(*) as cnt FROM server_files")
        count = cursor.fetchone()['cnt']
        print(f"当前记录数: {count}")
        
        if count == 0:
            print("\n⚠ 表中没有数据，无需迁移")
            cursor.close()
            conn.close()
            return 0
        
        cursor.close()
        conn.close()
        
        if current_type == 'VARCHAR':
            print("\n开始迁移表结构...")
            db.migrate_table_structure()
            print("\n✓ 迁移完成！")
        else:
            print("\n表结构已是最新（id 已是 INT 类型）")
            print("如果需要重新排序 ID，请手动执行以下 SQL：")
            print("""
-- 创建临时表
CREATE TABLE server_files_temp LIKE server_files;

-- 按时间排序插入数据（会自动重新分配 ID）
INSERT INTO server_files_temp 
(file_id, file_name, original_name, upload_time, upload_duration, uploader_ip,
 file_size, file_size_mb, file_duration, file_duration_str, 
 download_url, remote_path, created_at, updated_at)
SELECT 
    file_id, file_name, original_name, upload_time, upload_duration, uploader_ip,
    file_size, file_size_mb, file_duration, file_duration_str,
    download_url, remote_path, created_at, updated_at
FROM server_files
ORDER BY upload_time ASC;

-- 替换原表
DROP TABLE server_files;
RENAME TABLE server_files_temp TO server_files;
            """)
            return 0
        
        # 验证结果
        print("\n验证迁移结果...")
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'id'
        """, (db.DB_NAME,))
        result = cursor.fetchone()
        new_type = result['DATA_TYPE'].upper() if result else 'UNKNOWN'
        print(f"新的 id 字段类型: {new_type}")
        
        # 显示前几条记录，验证 ID 是否按时间排序
        cursor.execute("""
            SELECT id, file_name, upload_time 
            FROM server_files 
            ORDER BY id ASC 
            LIMIT 5
        """)
        print("\n前 5 条记录（按 ID 排序）：")
        for row in cursor.fetchall():
            print(f"  ID: {row['id']}, 文件名: {row['file_name']}, 上传时间: {row['upload_time']}")
        
        cursor.execute("""
            SELECT id, file_name, upload_time 
            FROM server_files 
            ORDER BY upload_time ASC 
            LIMIT 5
        """)
        print("\n前 5 条记录（按上传时间排序）：")
        for row in cursor.fetchall():
            print(f"  ID: {row['id']}, 文件名: {row['file_name']}, 上传时间: {row['upload_time']}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✓ 迁移完成！")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
