#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传历史记录
直接从 server_files_cache.json 文件读取
"""

import json
from flask import request, jsonify
from pathlib import Path


def upload_history():
    """获取上传历史记录（直接从 server_files_cache.json 文件读取）"""
    try:
        limit = int(request.args.get('limit', 100))
        
        # 获取 server_files_cache.json 文件路径
        current_file = Path(__file__).resolve()
        # routes/upload/history.py -> server_upload/server_files_cache.json
        project_root = current_file.parent.parent.parent
        cache_file = project_root / "server_upload" / "server_files_cache.json"
        
        if not cache_file.exists():
            return jsonify({
                "code": 0,
                "msg": "server_files_cache.json 文件不存在",
                "data": [],
                "cache_info": {
                    "last_update": None,
                    "is_updating": False,
                    "update_count": 0
                }
            })
        
        # 读取 JSON 文件
        with cache_file.open("r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # server_files_cache.json 的结构是 {"files": [...], "last_update": "...", "update_count": ...}
        # 读取 files 数组
        history = cache_data.get("files", [])
        
        # 限制返回数量
        history = history[:limit]
        
        # 获取缓存信息
        cache_info = {
            "last_update": cache_data.get("last_update"),
            "is_updating": False,  # 直接从文件读取，不涉及更新状态
            "update_count": cache_data.get("update_count", 0)
        }
        
        # 在返回数据中添加缓存更新时间信息
        return jsonify({
            "code": 0, 
            "msg": "获取成功", 
            "data": history,
            "cache_info": cache_info
        })
    except json.JSONDecodeError as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[upload_history]JSON解析失败: {e}')
        return jsonify({
            "code": 1,
            "msg": f"JSON 解析失败: {str(e)}",
            "data": []
        })
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[upload_history]error: {e}')
        return jsonify({"code": 1, "msg": str(e), "data": []})


def upload_history_cache_info():
    """获取缓存信息（最后更新时间等，直接从 server_files_cache.json 读取）"""
    try:
        # 获取 server_files_cache.json 文件路径
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        cache_file = project_root / "server_upload" / "server_files_cache.json"
        
        if not cache_file.exists():
            return jsonify({
                "code": 0,
                "msg": "获取成功",
                "data": {
                    "last_update": None,
                    "is_updating": False,
                    "update_count": 0,
                    "file_count": 0
                }
            })
        
        # 读取 JSON 文件
        with cache_file.open("r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        info = {
            "last_update": cache_data.get("last_update"),
            "is_updating": False,  # 直接从文件读取，不涉及更新状态
            "update_count": cache_data.get("update_count", 0),
            "file_count": len(cache_data.get("files", []))
        }
        
        return jsonify({"code": 0, "msg": "获取成功", "data": info})
    except json.JSONDecodeError as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[upload_history_cache_info]JSON解析失败: {e}')
        return jsonify({"code": 1, "msg": f"JSON 解析失败: {str(e)}"})
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[upload_history_cache_info]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


def delete_upload():
    """删除一条上传记录，同时删除服务器上的对应文件"""
    record_id = request.form.get("id", "").strip()
    if not record_id:
        return jsonify({"code": 1, "msg": "记录ID不能为空"})

    try:
        from server_upload import upload_to_server_tool
        result = upload_to_server_tool.delete_server_file_by_id(record_id)
        if result.get("success"):
            return jsonify({"code": 0, "msg": result.get("message", "删除成功")})
        else:
            return jsonify({"code": 1, "msg": result.get("message", "删除失败")})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[delete_upload]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

