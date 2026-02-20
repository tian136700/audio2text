#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看历史截取记录
"""

from flask import request, jsonify
from cut import cut_tool
from server_upload import server_files_cache


def cut_history():
    """查看历史截取记录"""
    try:
        grouped = request.args.get('grouped', 'false').lower() == 'true'
        check_uploaded = request.args.get('check_uploaded', 'false').lower() == 'true'
        
        if grouped:
            data = cut_tool.list_cut_history_grouped()
        else:
            data = cut_tool.list_cut_history()
        
        # 如果需要检查上传状态，获取服务器文件列表并检查
        if check_uploaded:
            server_files = server_files_cache.get_cached_files()
            if grouped:
                # 分组数据：检查每个分组的每个片段
                for group in data:
                    all_uploaded = True
                    for segment in group.get("segments", []):
                        is_uploaded, upload_info = cut_tool.check_file_uploaded(
                            segment["file_name"], 
                            server_files
                        )
                        segment["is_uploaded"] = is_uploaded
                        segment["upload_info"] = upload_info if is_uploaded else {}
                        if not is_uploaded:
                            all_uploaded = False
                    # 标记分组是否全部已上传
                    group["all_uploaded"] = all_uploaded and len(group.get("segments", [])) > 0
            else:
                # 平铺数据：检查每个文件
                for item in data:
                    is_uploaded, upload_info = cut_tool.check_file_uploaded(
                        item["file_name"], 
                        server_files
                    )
                    item["is_uploaded"] = is_uploaded
                    item["upload_info"] = upload_info if is_uploaded else {}
        
        return jsonify({"code": 0, "data": data})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

