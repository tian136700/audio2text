#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传到服务器相关路由处理函数
"""

import os
import queue
import threading
import json
from datetime import datetime
from flask import request, render_template, jsonify, Response, stream_with_context
from stslib import cfg
import stslib
from werkzeug.utils import secure_filename
from server_upload import upload_to_server_tool, server_files_cache, db as db_module


def upload_to_server_page():
    """上传到服务器独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "upload_to_server.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/upload_to_server',
    )


def upload_to_server():
    """上传文件到服务器"""
    try:
        if 'file' not in request.files:
            return jsonify({"code": 1, "msg": "没有上传文件"})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"code": 1, "msg": "文件名为空"})
        
        # 保存临时文件
        raw_filename = file.filename or ""  # 浏览器选择的原始文件名（保留中文，用于 original_name）
        # 临时文件路径用安全文件名，防止路径遍历（如 ../../etc/passwd）
        safe_filename = secure_filename(raw_filename) or "unnamed_file"
        print(f"[upload_to_server] 源文件名称(原始): {raw_filename!r}")
        print(f"[upload_to_server] 源文件名称(安全化): {safe_filename!r}")
        temp_file = os.path.join(cfg.TMP_DIR, safe_filename)
        file.save(temp_file)
        
        # ================== 先写入数据库一条占位记录 ==================
        try:
            file_size = os.path.getsize(temp_file)
        except Exception:
            file_size = 0
        
        file_size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0
        # 获取本地临时文件的时长，用于占位显示
        try:
            file_duration = upload_to_server_tool.get_audio_duration(temp_file)
        except Exception:
            file_duration = 0
        file_duration_str = upload_to_server_tool.format_duration(file_duration) if file_duration > 0 else "00:00:00"
        
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uploader_ip = request.remote_addr or ""
        
        # 占位记录：file_name 先留空，original_name 使用浏览器选择的原始文件名（保留中文）
        placeholder_record = {
            "id": safe_filename,          # 临时 id，保存后会被 new_id 覆盖
            "file_name": "",              # 服务器文件名稍后更新
            "original_name": raw_filename, # 原文件中文名称 = 上传前的文件名（保留中文）
            "upload_time": upload_time,
            "upload_duration": None,
            "uploader_ip": uploader_ip,
            "file_size": file_size,
            "file_size_mb": file_size_mb,
            "file_duration": round(file_duration, 2) if file_duration else 0,
            "file_duration_str": file_duration_str,
            "download_url": "",
            "remote_path": "",
        }
        
        try:
            new_id = db_module.save_single_file(placeholder_record)
            if new_id:
                placeholder_record["id"] = new_id  # 使用自增ID
        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f'[upload_to_server] 保存占位记录失败: {e}')
            # 占位记录失败不影响后续上传，但前端可能无法显示进度条
            placeholder_record["id"] = None
        
        # 返回临时文件路径和占位记录信息，让前端立刻在历史记录中显示这一条，并开始真正上传
        return jsonify({
            "code": 0,
            "msg": "文件接收成功",
            "data": {
                "temp_file": temp_file,
                # 原始文件名（浏览器里选择的文件名，用于"原文件中文名称"列，保留中文）
                "filename": raw_filename,
                "record": placeholder_record
            }
        })
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[upload_to_server]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


def upload_to_server_process():
    """处理上传到服务器的任务（简化版：不再推送日志，只返回最终结果）"""
    try:
        temp_file = request.form.get("temp_file", "").strip()
        original_name = request.form.get("original_name", "").strip()
        record_id = request.form.get("record_id", "").strip()
        print(f"[upload_to_server_process] 源文件名称(前端传入): {original_name!r}")
        
        if not temp_file or not os.path.exists(temp_file):
            return jsonify({"code": 1, "msg": "临时文件不存在"})
        
        # 获取客户端 IP 地址
        uploader_ip = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            uploader_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            uploader_ip = request.headers.get('X-Real-IP')
        
        # 执行真正的上传任务（同步执行），并在内部根据 record_id 更新数据库记录
        result = upload_to_server_tool.upload_file_to_server(
            temp_file,
            log_callback=None,  # 不再推送日志
            uploader_ip=uploader_ip,
            original_name=original_name or None,
            record_id=record_id or None
        )
        
        # 删除临时文件
        try:
            os.remove(temp_file)
        except Exception:
            pass
        
        if result.get("success"):
            record = result.get("record", {})
            return jsonify({"code": 0, "msg": "上传成功", "data": record})
        else:
            error_msg = result.get("error", "上传失败")
            return jsonify({"code": 1, "msg": error_msg})
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[upload_to_server_process]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


def upload_history():
    """获取上传历史记录（从 MySQL 或 JSON 文件读取，通过 server_files_cache 模块）"""
    try:
        limit = int(request.args.get('limit', 100))
        
        # 使用 server_files_cache 模块（自动处理 MySQL/JSON 切换）
        from server_upload import server_files_cache
        history = server_files_cache.get_cached_files()
        cache_info = server_files_cache.get_cache_info()
        
        # 限制返回数量
        history = history[:limit]
        
        # 在返回数据中添加缓存更新时间信息
        from flask import current_app
        if current_app:
            current_app.logger.info(f'[upload_history] 返回 {len(history)} 条记录')
        
        return jsonify({
            "code": 0, 
            "msg": "获取成功", 
            "data": history,
            "cache_info": {
                "last_update": cache_info.get("last_update"),
                "is_updating": cache_info.get("is_updating", False),
                "update_count": cache_info.get("update_count", 0)
            }
        })
    except Exception as e:
        from flask import current_app
        import traceback
        error_msg = str(e)
        if current_app:
            current_app.logger.error(f'[upload_history]error: {error_msg}')
            current_app.logger.error(traceback.format_exc())
        return jsonify({"code": 1, "msg": error_msg, "data": []})


def upload_history_cache_info():
    """获取缓存信息（最后更新时间等，通过 server_files_cache 模块）"""
    try:
        from server_upload import server_files_cache
        info = server_files_cache.get_cache_info()
        return jsonify({"code": 0, "msg": "获取成功", "data": info})
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[upload_history_cache_info]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


def delete_upload():
    """删除一条上传记录，同时删除服务器上的对应文件和数据库记录"""
    record_id = request.form.get("id", "").strip()
    if not record_id:
        return jsonify({"code": 1, "msg": "记录ID不能为空"})

    try:
        # 先获取文件信息（用于删除服务器文件）
        from server_upload import db as db_module
        files = db_module.get_files(limit=10000)
        file_info = None
        for f in files:
            if str(f.get('id')) == str(record_id):
                file_info = f
                break
        
        if not file_info:
            return jsonify({"code": 1, "msg": "记录不存在"})
        
        remote_path = file_info.get('remote_path') or file_info.get('file_name')
        file_name = file_info.get('file_name', '未知文件')
        
        # 删除服务器上的文件
        from flask import current_app
        if current_app:
            current_app.logger.info(f'[delete_upload] 开始删除文件: {file_name}, remote_path: {remote_path}')
        
        result = upload_to_server_tool.delete_server_file_by_id(record_id)
        if not result.get("success"):
            error_msg = result.get("message", "删除服务器文件失败")
            if current_app:
                current_app.logger.error(f'[delete_upload] 删除服务器文件失败: {error_msg}')
            return jsonify({"code": 1, "msg": f"删除服务器文件失败: {error_msg}"})
        
        if current_app:
            current_app.logger.info(f'[delete_upload] 服务器文件删除成功: {file_name}')
        
        # 删除数据库记录
        try:
            db_module.delete_file_by_id(int(record_id))
            if current_app:
                current_app.logger.info(f'[delete_upload] 数据库记录删除成功: ID={record_id}')
            return jsonify({"code": 0, "msg": f"删除成功（服务器文件 {file_name} 和数据库记录已删除）"})
        except Exception as e:
            # 即使数据库删除失败，也返回成功（因为服务器文件已删除）
            if current_app:
                current_app.logger.error(f'[delete_upload] 删除数据库记录失败: {e}')
            return jsonify({"code": 0, "msg": f"服务器文件 {file_name} 已删除，但数据库记录删除失败: {str(e)}"})
            
    except ValueError as e:
        return jsonify({"code": 1, "msg": f"ID格式错误: {str(e)}"})
    except Exception as e:
        from flask import current_app
        if current_app:
            current_app.logger.error(f'[delete_upload]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


def batch_delete_upload():
    """批量删除上传记录，同时删除服务器上的对应文件和数据库记录"""
    ids_json = request.form.get("ids", "").strip()
    if not ids_json:
        return jsonify({"code": 1, "msg": "记录ID列表不能为空"})
    
    try:
        ids = json.loads(ids_json)
        if not isinstance(ids, list) or len(ids) == 0:
            return jsonify({"code": 1, "msg": "记录ID列表格式错误"})
    except json.JSONDecodeError:
        return jsonify({"code": 1, "msg": "记录ID列表JSON格式错误"})
    
    from flask import current_app
    from server_upload import db as db_module
    
    success_count = 0
    failed_count = 0
    failed_ids = []
    
    # 获取所有文件信息
    try:
        files = db_module.get_files(limit=10000)
        file_dict = {str(f.get('id')): f for f in files}
    except Exception as e:
        if current_app:
            current_app.logger.error(f'[batch_delete_upload] 获取文件列表失败: {e}')
        return jsonify({"code": 1, "msg": f"获取文件列表失败: {str(e)}"})
    
    # 逐个删除
    for record_id in ids:
        try:
            record_id_str = str(record_id).strip()
            if not record_id_str:
                failed_count += 1
                failed_ids.append(str(record_id))
                continue
            
            file_info = file_dict.get(record_id_str)
            if not file_info:
                if current_app:
                    current_app.logger.warning(f'[batch_delete_upload] 记录不存在: ID={record_id_str}')
                failed_count += 1
                failed_ids.append(record_id_str)
                continue
            
            file_name = file_info.get('file_name', '未知文件')
            
            # 删除服务器上的文件
            if current_app:
                current_app.logger.info(f'[batch_delete_upload] 开始删除文件: {file_name}, ID={record_id_str}')
            
            result = upload_to_server_tool.delete_server_file_by_id(record_id_str)
            if not result.get("success"):
                error_msg = result.get("message", "删除服务器文件失败")
                if current_app:
                    current_app.logger.error(f'[batch_delete_upload] 删除服务器文件失败: ID={record_id_str}, {error_msg}')
                failed_count += 1
                failed_ids.append(record_id_str)
                continue
            
            if current_app:
                current_app.logger.info(f'[batch_delete_upload] 服务器文件删除成功: {file_name}')
            
            # 删除数据库记录
            try:
                db_module.delete_file_by_id(int(record_id_str))
                if current_app:
                    current_app.logger.info(f'[batch_delete_upload] 数据库记录删除成功: ID={record_id_str}')
                success_count += 1
            except Exception as e:
                # 即使数据库删除失败，也计入成功（因为服务器文件已删除）
                if current_app:
                    current_app.logger.error(f'[batch_delete_upload] 删除数据库记录失败: ID={record_id_str}, {e}')
                success_count += 1  # 服务器文件已删除，算作成功
                
        except ValueError as e:
            if current_app:
                current_app.logger.error(f'[batch_delete_upload] ID格式错误: {record_id}, {e}')
            failed_count += 1
            failed_ids.append(str(record_id))
        except Exception as e:
            if current_app:
                current_app.logger.error(f'[batch_delete_upload] 删除失败: ID={record_id}, {e}')
            failed_count += 1
            failed_ids.append(str(record_id))
    
    # 返回结果
    msg = f"批量删除完成：成功 {success_count} 条"
    if failed_count > 0:
        msg += f"，失败 {failed_count} 条"
    
    return jsonify({
        "code": 0,
        "msg": msg,
        "data": {
            "success_count": success_count,
            "failed_count": failed_count,
            "failed_ids": failed_ids,
            "total_count": len(ids)
        }
    })

