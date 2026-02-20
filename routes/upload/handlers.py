#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传到服务器相关路由处理函数
"""

import os
import queue
import threading
import json
from flask import request, render_template, jsonify, Response, stream_with_context
from stslib import cfg
import stslib
from werkzeug.utils import secure_filename
from server_upload import upload_to_server_tool, server_files_cache


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
        filename = secure_filename(file.filename)
        temp_file = os.path.join(cfg.TMP_DIR, filename)
        file.save(temp_file)
        
        # 返回临时文件路径，让前端通过 SSE 获取处理进度
        return jsonify({
            "code": 0,
            "msg": "文件接收成功",
            "data": {
                "temp_file": temp_file,
                "filename": filename
            }
        })
            
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[upload_to_server]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})


def upload_to_server_process():
    """处理上传到服务器的任务（使用 SSE 推送进度）"""
    def send_log(message):
        """发送日志到前端（SSE 格式）"""
        message_escaped = message.replace('\n', '\\n').replace('\r', '\\r')
        return f"data: {message_escaped}\n\n"
    
    def generate():
        """生成器函数，用于流式传输"""
        # 在请求上下文中获取数据（在启动线程之前）
        temp_file = request.form.get("temp_file", "").strip()
        if not temp_file:
            yield send_log("[上传] 错误：临时文件路径为空")
            yield "event: end\ndata: " + json.dumps({
                "code": 1,
                "msg": "临时文件路径为空"
            }, ensure_ascii=False) + "\n\n"
            return
        
        log_queue = queue.Queue()
        result_container = {'result': None, 'error': None, 'finished': False}
        
        def log_callback(msg):
            """日志回调函数，将日志放入队列"""
            try:
                log_queue.put(msg, timeout=0.1)
            except queue.Full:
                # 队列满了，忽略这条日志（避免阻塞）
                pass
            except Exception as e:
                # 其他错误，记录但不影响上传任务
                print(f"[upload_to_server_process] log_callback 错误: {e}")
        
        def upload_task(temp_file_path):
            """在后台线程中执行上传任务"""
            try:
                if not temp_file_path or not os.path.exists(temp_file_path):
                    result_container['error'] = Exception("临时文件不存在")
                    return
                
                result_container['result'] = upload_to_server_tool.upload_file_to_server(
                    temp_file_path, 
                    log_callback=log_callback
                )
                
                # 删除临时文件
                try:
                    os.remove(temp_file_path)
                    # 尝试发送日志，但如果客户端已断开则忽略错误
                    try:
                        log_callback("[上传] 临时文件已清理")
                    except (BrokenPipeError, ConnectionError, OSError):
                        pass  # 客户端已断开，忽略
                except:
                    pass
                    
            except Exception as e:
                error_msg = str(e)
                # 检查是否是 Broken pipe 错误，如果是则不作为错误处理（因为上传可能已成功）
                if 'Broken pipe' in error_msg or 'BrokenPipeError' in error_msg or 'Errno 32' in error_msg:
                    # Broken pipe 错误，检查上传是否成功
                    if result_container.get('result') and result_container['result'].get("success"):
                        # 上传成功，只是发送日志时出错，不作为错误
                        print(f"[upload_to_server_process] Broken pipe 错误，但上传已成功: {e}")
                    else:
                        # 上传失败，记录错误
                        result_container['error'] = e
                else:
                    # 其他错误，正常处理
                    result_container['error'] = e
            finally:
                result_container['finished'] = True
        
        try:
            yield send_log("[上传][Flask] 收到处理请求，开始处理...")
            
            # 启动上传任务线程（传递数据，而不是在线程中访问 request）
            task_thread = threading.Thread(target=upload_task, args=(temp_file,))
            task_thread.daemon = True
            task_thread.start()
            
            # 实时推送日志
            while not result_container['finished'] or not log_queue.empty():
                try:
                    log_msg = log_queue.get(timeout=0.1)
                    yield send_log(log_msg)
                except queue.Empty:
                    continue
                except (GeneratorExit, BrokenPipeError, ConnectionError, OSError) as e:
                    # 客户端断开连接，优雅退出
                    print(f"[upload_to_server_process] 客户端断开连接: {e}")
                    return
                except Exception as e:
                    # 其他错误，记录但继续
                    print(f"[upload_to_server_process] 发送日志时出错: {e}")
                    continue
            
            # 等待任务完成
            task_thread.join(timeout=30)
            
            # 发送剩余的日志
            while not log_queue.empty():
                try:
                    log_msg = log_queue.get(timeout=0.1)
                    yield send_log(log_msg)
                except queue.Empty:
                    break
                except (GeneratorExit, BrokenPipeError, ConnectionError, OSError) as e:
                    # 客户端断开连接，优雅退出
                    print(f"[upload_to_server_process] 客户端断开连接: {e}")
                    return
                except Exception as e:
                    print(f"[upload_to_server_process] 发送日志时出错: {e}")
                    break
            
            # 发送最终结果
            # 先检查上传是否成功（即使有 Broken pipe 错误，如果上传成功也应该返回成功）
            upload_success = result_container['result'] and result_container['result'].get("success")
            is_broken_pipe_error = False
            
            # 检查错误是否是 Broken pipe
            if result_container.get('error'):
                error_msg = str(result_container['error'])
                if 'Broken pipe' in error_msg or 'BrokenPipeError' in error_msg or 'Errno 32' in error_msg:
                    is_broken_pipe_error = True
            
            try:
                if upload_success:
                    # 上传成功，即使有 Broken pipe 错误也返回成功
                    yield send_log("[上传] 处理完成 ✅")
                    yield "event: end\ndata: " + json.dumps({
                        "code": 0,
                        "msg": "上传成功",
                        "data": result_container['result'].get("record")
                    }, ensure_ascii=False) + "\n\n"
                elif is_broken_pipe_error:
                    # Broken pipe 错误，但检查上传是否实际成功（可能在上传过程中成功但最后发送日志时出错）
                    if result_container.get('result') and result_container['result'].get("success"):
                        yield send_log("[上传] 处理完成 ✅")
                        yield "event: end\ndata: " + json.dumps({
                            "code": 0,
                            "msg": "上传成功",
                            "data": result_container['result'].get("record")
                        }, ensure_ascii=False) + "\n\n"
                    else:
                        # Broken pipe 且上传失败，返回错误
                        error_msg = str(result_container['error'])
                        yield send_log(f"[上传] 处理失败: {error_msg}")
                        yield "event: end\ndata: " + json.dumps({
                            "code": 1, 
                            "msg": error_msg
                        }, ensure_ascii=False) + "\n\n"
                elif result_container.get('error'):
                    # 真正的错误（不是 Broken pipe）
                    error_msg = str(result_container['error'])
                    yield send_log(f"[上传] 处理失败: {error_msg}")
                    yield "event: end\ndata: " + json.dumps({
                        "code": 1, 
                        "msg": error_msg
                    }, ensure_ascii=False) + "\n\n"
                else:
                    # 其他错误
                    error_msg = result_container['result'].get('error', '未知错误') if result_container.get('result') else '未知错误'
                    yield send_log(f"[上传] 处理失败: {error_msg}")
                    yield "event: end\ndata: " + json.dumps({
                        "code": 1,
                        "msg": error_msg
                    }, ensure_ascii=False) + "\n\n"
            except (GeneratorExit, BrokenPipeError, ConnectionError, OSError) as e:
                # 客户端断开连接，但任务已完成
                # 如果上传成功，记录成功日志；否则记录错误
                if upload_success:
                    print(f"[upload_to_server_process] 上传成功，但客户端断开连接: {e}")
                else:
                    print(f"[upload_to_server_process] 发送最终结果时客户端断开连接: {e}")
                return
                
        except (GeneratorExit, BrokenPipeError, ConnectionError, OSError) as e:
            # 客户端断开连接，优雅退出
            print(f"[upload_to_server_process] 客户端断开连接: {e}")
            return
        except Exception as e:
            try:
                yield send_log(f"[上传][Flask] 错误: {str(e)}")
                yield "event: end\ndata: " + json.dumps({
                    "code": 1,
                    "msg": str(e)
                }, ensure_ascii=False) + "\n\n"
            except (GeneratorExit, BrokenPipeError, ConnectionError, OSError):
                # 即使发送错误信息时也断开，直接返回
                print(f"[upload_to_server_process] 发送错误信息时客户端断开连接")
                return
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })


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

