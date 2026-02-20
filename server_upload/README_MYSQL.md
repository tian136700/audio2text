# MySQL 数据库配置说明

## 概述

`server_files_cache` 模块现在支持将数据存储到 MySQL 数据库，替代原来的 JSON 文件存储方式。

## 数据库表结构

### 1. server_files_cache_meta 表（缓存元信息）

```sql
CREATE TABLE IF NOT EXISTS server_files_cache_meta (
    id INT PRIMARY KEY AUTO_INCREMENT,
    last_update DATETIME COMMENT '最后更新时间',
    update_count INT DEFAULT 0 COMMENT '更新次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_meta (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### 2. server_files 表（文件列表）

```sql
CREATE TABLE IF NOT EXISTS server_files (
    id VARCHAR(255) PRIMARY KEY COMMENT '文件ID（文件名）',
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
    INDEX idx_uploader_ip (uploader_ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**字段说明：**
- `original_name`: 文件上传服务器前的中文名称
- `upload_time`: 文件上传的时间
- `upload_duration`: 上传所消耗的时间（秒，精确到毫秒）
- `uploader_ip`: 操作人的IP地址
- `file_size`, `file_size_mb`: 文件大小
- `file_duration_str`: 文件时长（字符串格式，如 "00:03:08"）
- `download_url`: 下载链接
- `remote_path`: 服务器路径

## 环境变量配置

在 `.env` 文件中添加以下配置：

```env
# MySQL 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=stt_db
MYSQL_CHARSET=utf8mb4
```

## 安装依赖

```bash
pip install pymysql
```

## 初始化数据库

数据库表会在首次使用时自动创建。你也可以手动运行初始化：

```python
from server_upload import db
db.init_database()
```

## 数据迁移

如果已有 `server_files_cache.json` 文件，可以使用迁移脚本将数据导入 MySQL：

```bash
python server_upload/migrate_json_to_mysql.py
```

## 向后兼容

- 如果 MySQL 不可用（未安装 pymysql 或连接失败），系统会自动回退到 JSON 文件存储
- 如果 MySQL 可用，系统会优先使用 MySQL，同时保持 JSON 文件作为备份（可选）

## 使用方式

代码会自动检测 MySQL 是否可用：

1. **优先使用 MySQL**：如果配置了 MySQL 且连接成功，数据会存储到数据库
2. **回退到 JSON**：如果 MySQL 不可用，会自动使用 JSON 文件

无需修改现有代码，`server_files_cache` 模块会自动处理。

