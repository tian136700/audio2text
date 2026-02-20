#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理旧的备份表 server_files_old
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from server_upload import db

def main():
    """清理备份表"""
    print("=" * 60)
    print("清理备份表 server_files_old")
    print("=" * 60)
    
    try:
        # 初始化数据库（会自动清理备份表）
        print("\n正在初始化数据库并清理备份表...")
        db.init_database()
        print("\n✓ 完成！如果存在备份表，已自动删除")
        print("现在数据库中只保留 server_files 表")
    except Exception as e:
        print(f"\n✗ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
