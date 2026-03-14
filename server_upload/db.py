#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据库连接和操作模块
用于存储服务器文件缓存数据
"""

import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量（强制使用 .env 中的配置，覆盖系统环境变量）
load_dotenv(override=True)

# MySQL 配置（从环境变量读取）
# 真实的用户名和密码请放在 .env 文件中，这里不要写明文密码，也不要在日志中打印出来
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "")  # 用户名必须从 .env 配置，不提供默认值
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")  # 密码必须从 .env 配置，不提供默认值
DB_NAME = os.getenv("MYSQL_DATABASE", "stt_db")
DB_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")

# 如需排查连接问题，可临时打开下面的示例，但务必不要打印明文密码：
# print(f"[server_upload.db] DEBUG DB_USER={repr(DB_USER)}, DB_PASSWORD='***hidden***'")

# 尝试导入 pymysql
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
    print("[server_upload.db] 警告：未安装 pymysql 库，MySQL 功能将不可用。请运行: pip install pymysql")


def ensure_database_exists():
    """
    确保数据库存在，如果不存在则创建
    """
    if not HAS_PYMYSQL:
        return
    
    try:
        # 先连接到 MySQL 服务器（不指定数据库）
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            charset=DB_CHARSET
        )
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        if not cursor.fetchone():
            # 数据库不存在，创建它
            # 根据字符集选择合适的排序规则
            collation = "utf8mb4_unicode_ci" if DB_CHARSET == "utf8mb4" else f"{DB_CHARSET}_general_ci"
            cursor.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET {DB_CHARSET} COLLATE {collation}")
            conn.commit()
            print(f"[server_upload.db] 已创建数据库: {DB_NAME}")
        else:
            print(f"[server_upload.db] 数据库已存在: {DB_NAME}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[server_upload.db] 检查/创建数据库失败: {e}")
        raise


def get_connection():
    """
    获取 MySQL 数据库连接
    
    Returns:
        pymysql.Connection: 数据库连接对象
    """
    if not HAS_PYMYSQL:
        raise ImportError("未安装 pymysql 库，请运行: pip install pymysql")
    
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def migrate_table_structure():
    """
    迁移表结构：将 VARCHAR id 改为 INT AUTO_INCREMENT id，并添加 file_id 字段
    这个函数只需要运行一次
    """
    if not HAS_PYMYSQL:
        print("[server_upload.db] 跳过表结构迁移（未安装 pymysql）")
        return
    
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset=DB_CHARSET,
            cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()
        
        # 检查 id 字段的类型
        cursor.execute("""
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'id'
        """, (DB_NAME,))
        result = cursor.fetchone()
        
        if not result:
            print("[server_upload.db] 表不存在，无需迁移")
            cursor.close()
            conn.close()
            return
        
        if result['DATA_TYPE'].upper() != 'VARCHAR':
            print("[server_upload.db] 表结构已是最新，无需迁移")
            cursor.close()
            conn.close()
            return
        
        print("[server_upload.db] 开始迁移表结构...")
        
        # 1. 添加 file_id 字段（如果不存在）
        try:
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'file_id'", (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE server_files ADD COLUMN file_id VARCHAR(255) COMMENT '文件ID（原文件名）' AFTER id")
                print("[server_upload.db] 已添加 file_id 字段")
        except Exception as e:
            print(f"[server_upload.db] 添加 file_id 字段时出错: {e}")
        
        # 2. 将旧的 id 值复制到 file_id
        try:
            cursor.execute("UPDATE server_files SET file_id = id WHERE file_id IS NULL OR file_id = ''")
            conn.commit()
            print("[server_upload.db] 已将旧 id 值复制到 file_id")
        except Exception as e:
            print(f"[server_upload.db] 复制 id 到 file_id 时出错: {e}")
        
        # 3. 创建临时表（新结构）
        cursor.execute("DROP TABLE IF EXISTS server_files_new")
        cursor.execute("""
            CREATE TABLE server_files_new (
                id INT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
                file_id VARCHAR(255) COMMENT '文件ID（原文件名）',
                file_name VARCHAR(500) NOT NULL COMMENT '文件名',
                original_name VARCHAR(500) COMMENT '原始文件名（上传前的中文名称）',
                upload_time DATETIME COMMENT '文件上传时间',
                upload_duration DECIMAL(10, 3) COMMENT '上传耗时（秒）',
                uploader_ip VARCHAR(50) COMMENT '操作人IP地址',
                file_size BIGINT COMMENT '文件大小（字节）',
                file_size_mb DECIMAL(10, 2) COMMENT '文件大小（MB）',
                file_duration DECIMAL(10, 2) COMMENT '文件时长（秒）',
                file_duration_str VARCHAR(20) COMMENT '文件时长（字符串格式）',
                download_url VARCHAR(1000) COMMENT '下载链接',
                remote_path VARCHAR(1000) COMMENT '服务器路径',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_upload_time (upload_time),
                INDEX idx_file_name (file_name),
                INDEX idx_file_id (file_id),
                INDEX idx_uploader_ip (uploader_ip)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 4. 复制数据到新表（按照上传时间排序，旧的在前，新的在后）
        # 这样 AUTO_INCREMENT 会按照时间顺序分配 1,2,3,4... 的 ID
        cursor.execute("""
            INSERT INTO server_files_new 
            (file_id, file_name, original_name, upload_time, upload_duration, uploader_ip,
             file_size, file_size_mb, file_duration, file_duration_str, 
             download_url, remote_path, created_at, updated_at)
            SELECT 
                COALESCE(file_id, id) as file_id,
                file_name, original_name, upload_time, upload_duration, uploader_ip,
                file_size, file_size_mb, file_duration, file_duration_str,
                download_url, remote_path, created_at, updated_at
            FROM server_files
            ORDER BY upload_time ASC
        """)
        
        # 5. 验证数据完整性（在重命名前）
        cursor.execute("SELECT COUNT(*) as cnt FROM server_files")
        old_count = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) as cnt FROM server_files_new")
        new_count = cursor.fetchone()['cnt']
        
        if new_count != old_count:
            print(f"[server_upload.db] 错误：数据数量不一致！新表 {new_count} 条，旧表 {old_count} 条")
            cursor.execute("DROP TABLE server_files_new")
            conn.commit()
            cursor.close()
            conn.close()
            raise Exception("数据迁移失败：数据数量不一致")
        
        print(f"[server_upload.db] 数据验证通过：新旧表都有 {new_count} 条记录")
        
        # 6. 直接删除旧表并重命名新表（不保留备份）
        cursor.execute("DROP TABLE server_files")
        cursor.execute("RENAME TABLE server_files_new TO server_files")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("[server_upload.db] 表结构迁移完成！旧表已删除，只保留新表 server_files")
        
    except Exception as e:
        print(f"[server_upload.db] 表结构迁移失败: {e}")
        raise


def cleanup_old_backup_table():
    """
    将备份表 server_files_old 改为正式表 server_files
    删除原来的 server_files 空表
    """
    if not HAS_PYMYSQL:
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 检查备份表是否存在
        cursor.execute("""
            SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files_old'
        """, (DB_NAME,))
        
        if cursor.fetchone():
            # 检查主表是否存在
            cursor.execute("""
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files'
            """, (DB_NAME,))
            
            main_table_exists = cursor.fetchone()
            
            # 获取备份表的数据量
            cursor.execute("SELECT COUNT(*) as cnt FROM server_files_old")
            old_count = cursor.fetchone()['cnt']
            
            if main_table_exists:
                # 主表存在，直接删除主表
                print(f"[server_upload.db] 删除原来的 server_files 表（备份表有 {old_count} 条数据）")
                cursor.execute("DROP TABLE server_files")
            
            # 将备份表重命名为正式表
            print(f"[server_upload.db] 将 server_files_old 重命名为 server_files（包含 {old_count} 条数据）")
            cursor.execute("RENAME TABLE server_files_old TO server_files")
            conn.commit()
            print("[server_upload.db] 完成！server_files_old 已改为正式表 server_files")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[server_upload.db] 处理备份表时出错: {e}")
        import traceback
        traceback.print_exc()


def init_database():
    """
    初始化数据库表结构
    如果表不存在则创建
    """
    if not HAS_PYMYSQL:
        print("[server_upload.db] 跳过数据库初始化（未安装 pymysql）")
        return
    
    try:
        # 确保数据库存在
        ensure_database_exists()
        
        # 清理旧的备份表（如果存在）
        cleanup_old_backup_table()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # 创建 server_files_cache_meta 表（存储缓存元信息）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_files_cache_meta (
                id INT PRIMARY KEY AUTO_INCREMENT,
                last_update DATETIME,
                update_count INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_meta (id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 创建 server_files 表（存储文件列表）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS server_files (
                id INT PRIMARY KEY AUTO_INCREMENT COMMENT '自增ID',
                file_id VARCHAR(255) COMMENT '文件ID（原文件名，用于兼容旧数据）',
                file_name VARCHAR(500) NOT NULL COMMENT '文件名',
                original_name VARCHAR(500) COMMENT '原始文件名（上传前的中文名称）',
                upload_time DATETIME COMMENT '文件上传时间',
                upload_duration DECIMAL(10, 3) COMMENT '上传耗时（秒）',
                uploader_ip VARCHAR(50) COMMENT '操作人IP地址',
                file_size BIGINT COMMENT '文件大小（字节）',
                file_size_mb DECIMAL(10, 2) COMMENT '文件大小（MB）',
                file_duration DECIMAL(10, 2) COMMENT '文件时长（秒）',
                file_duration_str VARCHAR(20) COMMENT '文件时长（字符串格式）',
                download_url VARCHAR(1000) COMMENT '下载链接',
                remote_path VARCHAR(1000) COMMENT '服务器路径',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                INDEX idx_upload_time (upload_time),
                INDEX idx_file_name (file_name),
                INDEX idx_file_id (file_id),
                INDEX idx_uploader_ip (uploader_ip)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # 检查并添加新字段（如果表已存在，添加缺失的字段）
        try:
            cursor.execute("ALTER TABLE server_files ADD COLUMN IF NOT EXISTS upload_duration DECIMAL(10, 3) COMMENT '上传耗时（秒）' AFTER upload_time")
        except:
            pass  # 字段可能已存在或数据库不支持 IF NOT EXISTS
        
        try:
            cursor.execute("ALTER TABLE server_files ADD COLUMN IF NOT EXISTS uploader_ip VARCHAR(50) COMMENT '操作人IP地址' AFTER upload_duration")
        except:
            pass
        
        # 检查并添加 file_id 字段（用于存储原文件名）
        try:
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'file_id'", (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE server_files ADD COLUMN file_id VARCHAR(255) COMMENT '文件ID（原文件名）' AFTER id")
        except Exception as e:
            print(f"[server_upload.db] 添加 file_id 字段时出错: {e}")
        
        # 确保 original_name 字段存在
        try:
            cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'original_name'", (DB_NAME,))
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE server_files ADD COLUMN original_name VARCHAR(500) COMMENT '原始文件名（上传前的中文名称）' AFTER file_name")
        except Exception as e:
            print(f"[server_upload.db] 添加 original_name 字段时出错: {e}")
        
        # 检查是否需要迁移表结构（从 VARCHAR id 迁移到 INT id）
        try:
            cursor.execute("""
                SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'id'
            """, (DB_NAME,))
            result = cursor.fetchone()
            
            if result and result['DATA_TYPE'].upper() == 'VARCHAR':
                print("[server_upload.db] 检测到旧表结构（VARCHAR id），需要手动迁移")
                print("[server_upload.db] 提示：请运行 migrate_table_structure() 函数进行迁移")
        except:
            pass
        
        # 初始化元数据表（如果为空）
        cursor.execute("SELECT COUNT(*) as cnt FROM server_files_cache_meta")
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute("""
                INSERT INTO server_files_cache_meta (last_update, update_count)
                VALUES (NULL, 0)
            """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("[server_upload.db] 数据库表初始化完成")
        
    except Exception as e:
        print(f"[server_upload.db] 数据库初始化失败: {e}")
        raise


def get_cache_meta():
    """
    获取缓存元信息
    
    Returns:
        dict: {
            "last_update": datetime or None,
            "update_count": int
        }
    """
    if not HAS_PYMYSQL:
        return {"last_update": None, "update_count": 0}
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_update, update_count FROM server_files_cache_meta LIMIT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {
                "last_update": result['last_update'].strftime("%Y-%m-%d %H:%M:%S") if result['last_update'] else None,
                "update_count": result['update_count'] or 0
            }
        return {"last_update": None, "update_count": 0}
    except Exception as e:
        print(f"[server_upload.db] 获取缓存元信息失败: {e}")
        return {"last_update": None, "update_count": 0}


def update_cache_meta(last_update=None, increment_count=True):
    """
    更新缓存元信息
    
    Args:
        last_update: 最后更新时间（datetime 对象或字符串），如果为 None 则使用当前时间
        increment_count: 是否增加更新计数
    """
    if not HAS_PYMYSQL:
        return
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if last_update is None:
            last_update = datetime.now()
        elif isinstance(last_update, str):
            last_update = datetime.strptime(last_update, "%Y-%m-%d %H:%M:%S")
        
        if increment_count:
            cursor.execute("""
                UPDATE server_files_cache_meta 
                SET last_update = %s, update_count = update_count + 1
                LIMIT 1
            """, (last_update,))
        else:
            cursor.execute("""
                UPDATE server_files_cache_meta 
                SET last_update = %s
                LIMIT 1
            """, (last_update,))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[server_upload.db] 更新缓存元信息失败: {e}")


def save_files(files):
    """
    同步文件列表到数据库（增量更新，不清空表）
    - 服务器上有的文件：根据 file_name 更新或插入
    - 数据库有、服务器没有的：删除该记录
    
    Args:
        files: 服务器文件列表，每个文件是一个字典
    """
    if not HAS_PYMYSQL:
        return
    
    conn = None
    try:
        conn = get_connection()
        conn.autocommit(False)  # 开启事务
        cursor = conn.cursor()
        
        server_file_names = [f.get('file_name', '') for f in files if f.get('file_name')]
        
        # 1. 逐个更新或插入服务器上的文件
        for file_info in files:
            file_name = file_info.get('file_name', '')
            if not file_name:
                continue
            
            # 处理 upload_time
            upload_time = file_info.get('upload_time')
            if upload_time and isinstance(upload_time, str):
                try:
                    upload_time = datetime.strptime(upload_time, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    upload_time = None
            
            original_name = file_info.get('original_name', '')
            
            # 检查是否已存在（根据 file_name）
            cursor.execute(
                "SELECT id FROM server_files WHERE file_name = %s LIMIT 1",
                (file_name,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 已存在：只更新服务器相关字段，original_name 保持不变（仅上传时写入）
                cursor.execute("""
                    UPDATE server_files SET
                        file_id = %s, upload_time = %s, upload_duration = %s,
                        uploader_ip = %s, file_size = %s, file_size_mb = %s,
                        file_duration = %s, file_duration_str = %s,
                        download_url = %s, remote_path = %s
                    WHERE file_name = %s
                """, (
                    file_info.get('id', ''),
                    upload_time,
                    file_info.get('upload_duration'),
                    file_info.get('uploader_ip', ''),
                    file_info.get('file_size'),
                    file_info.get('file_size_mb'),
                    file_info.get('file_duration'),
                    file_info.get('file_duration_str', ''),
                    file_info.get('download_url', ''),
                    file_info.get('remote_path', ''),
                    file_name
                ))
            else:
                # 不存在：插入
                cursor.execute("""
                    INSERT INTO server_files
                    (file_id, file_name, original_name, upload_time, upload_duration, uploader_ip,
                     file_size, file_size_mb, file_duration, file_duration_str,
                     download_url, remote_path)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    file_info.get('id', ''),
                    file_name,
                    original_name,
                    upload_time,
                    file_info.get('upload_duration'),
                    file_info.get('uploader_ip', ''),
                    file_info.get('file_size'),
                    file_info.get('file_size_mb'),
                    file_info.get('file_duration'),
                    file_info.get('file_duration_str', ''),
                    file_info.get('download_url', ''),
                    file_info.get('remote_path', '')
                ))
        
        # 2. 删除数据库有、服务器没有的记录
        if server_file_names:
            placeholders = ','.join(['%s'] * len(server_file_names))
            cursor.execute(
                f"DELETE FROM server_files WHERE file_name NOT IN ({placeholders})",
                server_file_names
            )
            deleted = cursor.rowcount
        else:
            # 服务器无文件时，清空数据库（服务器是权威来源）
            cursor.execute("DELETE FROM server_files")
            deleted = cursor.rowcount
        
        conn.commit()
        cursor.close()
        print(f"[server_upload.db] 同步完成：更新/插入 {len(files)} 个文件，删除 {deleted} 条多余记录")
    except Exception as e:
        if conn:
            conn.rollback()
            print(f"[server_upload.db] 同步文件列表失败，已回滚: {e}")
        raise
    finally:
        if conn:
            try:
                conn.autocommit(True)
            except Exception:
                pass
            conn.close()


def save_single_file(file_info):
    """
    保存单条文件记录到数据库（插入新记录，不删除现有数据）
    
    Args:
        file_info: 文件信息字典
    
    Returns:
        int: 新插入记录的 id（自增ID）
    """
    if not HAS_PYMYSQL:
        return None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 处理 upload_time
        upload_time = file_info.get('upload_time')
        if upload_time and isinstance(upload_time, str):
            try:
                upload_time = datetime.strptime(upload_time, "%Y-%m-%d %H:%M:%S")
            except:
                upload_time = None
        
        # 直接使用传入的 original_name，不做任何处理（只在上传时写入）
        original_name = file_info.get('original_name', '')
        file_name = file_info.get('file_name', '')
        
        # 检查是否已存在相同记录（根据文件名和上传时间判断，避免重复）
        if upload_time:
            cursor.execute("""
                SELECT id FROM server_files 
                WHERE file_name = %s AND upload_time = %s
                LIMIT 1
            """, (file_name, upload_time))
            existing = cursor.fetchone()
            if existing:
                # 记录已存在，返回现有记录的 id（不更新 original_name）
                return existing['id']
        
        # 插入新记录
        cursor.execute("""
            INSERT INTO server_files 
            (file_id, file_name, original_name, upload_time, upload_duration, uploader_ip,
             file_size, file_size_mb, file_duration, file_duration_str, 
             download_url, remote_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            file_info.get('id', ''),  # file_id: 原文件名或ID
            file_name,
            original_name,  # 上传前的中文名称（如果和file_name相同则留空）
            upload_time,  # 上传时间
            file_info.get('upload_duration'),  # 上传耗时（秒）
            file_info.get('uploader_ip', ''),  # 操作人IP地址
            file_info.get('file_size'),
            file_info.get('file_size_mb'),
            file_info.get('file_duration'),
            file_info.get('file_duration_str', ''),
            file_info.get('download_url', ''),
            file_info.get('remote_path', '')
        ))
        
        # 获取新插入记录的 id
        new_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[server_upload.db] 保存单条文件记录成功，id: {new_id}")
        return new_id
    except Exception as e:
        print(f"[server_upload.db] 保存单条文件记录失败: {e}")
        raise


def get_files(limit=1000):
    """
    从数据库获取文件列表
    
    Args:
        limit: 限制返回数量
    
    Returns:
        list: 文件列表
    """
    if not HAS_PYMYSQL:
        return []
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 检查 id 字段的类型
        cursor.execute("""
            SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'server_files' AND COLUMN_NAME = 'id'
        """, (DB_NAME,))
        id_type_result = cursor.fetchone()
        id_is_int = id_type_result and id_type_result['DATA_TYPE'].upper() in ('INT', 'INTEGER', 'BIGINT')
        
        cursor.execute("""
            SELECT 
                id, file_id, file_name, original_name, 
                DATE_FORMAT(upload_time, '%%Y-%%m-%%d %%H:%%i:%%S') as upload_time,
                upload_duration, uploader_ip,
                file_size, file_size_mb, file_duration, file_duration_str,
                download_url, remote_path
            FROM server_files
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        
        files = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 转换为字典列表
        result = []
        for row in files:
            # 兼容处理：如果 id 是 VARCHAR（旧结构），使用 id 值本身；如果是 INT（新结构），转换为整数
            row_id = row['id']
            if id_is_int:
                # 新结构：id 是 INT，直接使用
                file_id = int(row_id) if row_id is not None else None
            else:
                # 旧结构：id 是 VARCHAR（文件名），需要生成一个数字ID用于显示
                # 使用行号作为临时ID，或者使用 hash
                file_id = hash(str(row_id)) % 2147483647  # 转换为正数，避免负数
                if file_id < 0:
                    file_id = -file_id
            
            result.append({
                'id': file_id,  # ID（兼容新旧结构）
                'file_id': row.get('file_id') or (row_id if not id_is_int else ''),  # 原文件名（兼容旧数据）
                'file_name': row['file_name'],
                'original_name': row.get('original_name') or '',  # 上传前的中文名称
                'upload_time': row['upload_time'],  # 上传时间
                'upload_duration': float(row['upload_duration']) if row['upload_duration'] else None,  # 上传耗时（秒）
                'uploader_ip': row['uploader_ip'] or '',  # 操作人IP地址
                'file_size': int(row['file_size']) if row['file_size'] else 0,
                'file_size_mb': float(row['file_size_mb']) if row['file_size_mb'] else 0.0,
                'file_duration': float(row['file_duration']) if row['file_duration'] else 0.0,
                'file_duration_str': row['file_duration_str'] or '',
                'download_url': row['download_url'] or '',
                'remote_path': row['remote_path'] or ''
            })
        
        return result
    except Exception as e:
        print(f"[server_upload.db] 获取文件列表失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_file_by_id(file_id):
    """
    根据文件ID获取单条文件记录
    
    Args:
        file_id: 文件ID（必须是自增ID整数）
    
    Returns:
        dict: 文件记录，如果不存在返回 None
    """
    if not HAS_PYMYSQL:
        return None
    
    try:
        # 转换为整数ID
        if isinstance(file_id, str):
            if not file_id.isdigit():
                raise ValueError("id必须是整数")
            file_id = int(file_id)
        elif not isinstance(file_id, int):
            raise ValueError("id必须是整数")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, file_id, file_name, original_name, 
                DATE_FORMAT(upload_time, '%%Y-%%m-%%d %%H:%%i:%%S') as upload_time,
                upload_duration, uploader_ip,
                file_size, file_size_mb, file_duration, file_duration_str,
                download_url, remote_path
            FROM server_files
            WHERE id = %s
            LIMIT 1
        """, (file_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return None
        
        # 转换为字典格式（与 get_files 返回格式一致）
        return {
            'id': int(row['id']) if row['id'] is not None else None,
            'file_id': row.get('file_id') or '',
            'file_name': row['file_name'],
            'original_name': row.get('original_name') or '',
            'upload_time': row['upload_time'],
            'upload_duration': float(row['upload_duration']) if row['upload_duration'] else None,
            'uploader_ip': row['uploader_ip'] or '',
            'file_size': int(row['file_size']) if row['file_size'] else 0,
            'file_size_mb': float(row['file_size_mb']) if row['file_size_mb'] else 0.0,
            'file_duration': float(row['file_duration']) if row['file_duration'] else 0.0,
            'file_duration_str': row['file_duration_str'] or '',
            'download_url': row['download_url'] or '',
            'remote_path': row['remote_path'] or ''
        }
    except ValueError as e:
        print(f"[server_upload.db] 参数错误: {e}")
        raise
    except Exception as e:
        print(f"[server_upload.db] 获取文件记录失败: {e}")
        return None


def update_file_by_id(file_id, **kwargs):
    """
    根据文件ID更新文件记录，id为必填项
    
    Args:
        file_id: 文件ID（必须是自增ID整数，必填项）
        **kwargs: 要更新的字段，如 original_name, file_name 等
    
    Returns:
        bool: 是否更新成功
    """
    if not HAS_PYMYSQL:
        return False
    
    # id为必填项，验证参数
    if file_id is None:
        raise ValueError("id为必填项，不能为空")
    
    if not kwargs:
        return False
    
    try:
        # 转换为整数ID
        if isinstance(file_id, str):
            if not file_id.isdigit():
                raise ValueError("id必须是整数")
            file_id = int(file_id)
        elif not isinstance(file_id, int):
            raise ValueError("id必须是整数")
        
        # 构建更新语句
        allowed_fields = ['original_name', 'file_name', 'upload_time', 'upload_duration', 
                         'uploader_ip', 'file_size', 'file_size_mb', 'file_duration', 
                         'file_duration_str', 'download_url', 'remote_path']
        
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = %s")
                values.append(value)
        
        if not updates:
            return False
        
        values.append(file_id)
        
        conn = get_connection()
        cursor = conn.cursor()
        sql = f"UPDATE server_files SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(sql, values)
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return affected > 0
    except ValueError as e:
        print(f"[server_upload.db] 参数错误: {e}")
        raise
    except Exception as e:
        print(f"[server_upload.db] 更新文件记录失败: {e}")
        return False


def delete_file_by_id(file_id):
    """
    根据文件ID删除文件记录，id为必填项
    只支持通过自增ID（整数）删除
    
    Args:
        file_id: 文件ID（必须是自增ID整数，必填项）
    
    Returns:
        bool: 是否删除成功
    """
    if not HAS_PYMYSQL:
        return False
    
    # id为必填项，验证参数
    if file_id is None:
        raise ValueError("id为必填项，不能为空")
    
    try:
        # 转换为整数ID
        if isinstance(file_id, str):
            if not file_id.isdigit():
                raise ValueError("id必须是整数")
            file_id = int(file_id)
        elif not isinstance(file_id, int):
            raise ValueError("id必须是整数")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM server_files WHERE id = %s", (file_id,))
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        return affected > 0
    except ValueError as e:
        print(f"[server_upload.db] 参数错误: {e}")
        raise
    except Exception as e:
        print(f"[server_upload.db] 删除文件记录失败: {e}")
        return False

