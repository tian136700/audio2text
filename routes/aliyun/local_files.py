#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提供本机（静态目录）可用的音频文件列表。

说明：
- 由于本地静态资源会与服务器同步，因此 /aliyun_asr 页面不再依赖远端 /data/audio
- 这里直接扫描本项目 static 下的若干目录：tmp / convert / cut
"""

import os
from flask import jsonify
from stslib import cfg


_AUDIO_EXTS = {".mp3", ".mp4", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".mov", ".mkv", ".avi", ".mpeg"}


def _iter_local_audio_files():
    candidates = [
        (cfg.TMP_DIR, "/static/tmp"),
        (os.path.join(cfg.STATIC_DIR, "convert"), "/static/convert"),
        (os.path.join(cfg.STATIC_DIR, "cut"), "/static/cut"),
    ]

    for local_dir, url_prefix in candidates:
        if not local_dir or not os.path.isdir(local_dir):
            continue
        for name in os.listdir(local_dir):
            p = os.path.join(local_dir, name)
            if not os.path.isfile(p):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in _AUDIO_EXTS:
                continue
            try:
                mtime = os.path.getmtime(p)
            except Exception:
                mtime = 0
            yield {
                "file_name": f"{os.path.basename(url_prefix)}/{name}",
                "download_url": f"http://{cfg.web_address}{url_prefix}/{name}",
                "mtime": mtime,
            }


def aliyun_local_files():
    """返回本地静态目录中的音频文件列表（给 /aliyun_asr 下拉框使用）"""
    files = list(_iter_local_audio_files())
    files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    # 前端不需要 mtime 字段
    for f in files:
        f.pop("mtime", None)
    return jsonify({"code": 0, "msg": "ok", "data": files})


