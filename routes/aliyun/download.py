#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云识别结果下载
"""

import os
from flask import request, jsonify, send_file
from stslib.cfg import ROOT_DIR
from aliyun import aliyun_web_tool


def _txt_to_pdf(txt_path: str) -> str:
    """
    将纯文本文件简单转换为 PDF，并返回生成的 PDF 路径。
    如果缺少依赖或转换失败，会抛出异常，由调用方处理。
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as e:
        raise RuntimeError("服务器未安装 reportlab 库，请先运行: pip install reportlab") from e

    base, _ = os.path.splitext(txt_path)
    pdf_path = base + ".pdf"

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    margin_x = 40
    margin_y = 40
    line_height = 18
    y = height - margin_y

    # 注册中文字体，优先使用项目内 fonts 目录，其次尝试常见系统字体
    font_name = "Helvetica"
    try:
        candidate_paths = [
            os.path.join(ROOT_DIR, "fonts", "NotoSansSC-Regular.otf"),
            os.path.join(ROOT_DIR, "fonts", "NotoSansSC-Regular.ttf"),
            os.path.join(ROOT_DIR, "fonts", "msyh.ttc"),
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/STSongTi.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont("CNFont", path))
                font_name = "CNFont"
                break
    except Exception:
        # 字体注册失败就继续用默认字体（英文不受影响）
        font_name = "Helvetica"

    c.setFont(font_name, 12)

    # 每行显示的最大字符数（按你示例那行长度，适当保守一点）
    max_chars_per_line = 38

    with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            # 跳过 TXT 文件头部的一些辅助信息行（识别时间、URL、分隔线等）
            if (
                line.startswith("识别时间: ")
                or line.startswith("音频URL: ")
                or line.startswith("说话人识别: ")
                or set(line) == {"="}
            ):
                continue
            # 保留空行作为分段
            if not line:
                y -= line_height
                if y < margin_y:
                    c.showPage()
                    c.setFont(font_name, 12)  # 新页面需要重新设置字体，避免中文变方块
                    y = height - margin_y
                continue

            # 简单按字符数折行（中英文都统一按一个字符算）
            while line:
                chunk = line[:max_chars_per_line]
                line = line[max_chars_per_line:]
                c.drawString(margin_x, y, chunk)
                y -= line_height
                if y < margin_y:
                    c.showPage()
                    c.setFont(font_name, 12)  # 每翻页后重新设置中文字体
                    y = height - margin_y

    c.save()
    return pdf_path


def aliyun_download():
    """下载阿里云识别结果文件（默认将文字结果生成为 PDF 下载）"""
    record_id = request.args.get("id", "").strip()
    file_type = request.args.get("type", "text").strip().lower()
    if not record_id:
        return jsonify({"code": 1, "msg": "记录ID不能为空"})

    record = aliyun_web_tool.get_record_by_id(record_id)
    if not record:
        return jsonify({"code": 1, "msg": "未找到对应历史记录"})

    # 文字结果：历史中保存的是 txt 路径，这里默认转成 PDF 再下载
    is_text_like = file_type in ("text", "txt", "pdf")
    if file_type == "json":
        file_rel_path = record.get("json_path")
    else:
        file_rel_path = record.get("text_path")

    if not file_rel_path:
        return jsonify({"code": 1, "msg": "记录中未找到对应的文件路径"})

    full_path = os.path.join(ROOT_DIR, file_rel_path)
    if not os.path.exists(full_path):
        return jsonify({"code": 1, "msg": "文件不存在: " + file_rel_path})

    try:
        # JSON 结果或显式要求原始文本，直接返回原文件
        if not is_text_like or file_rel_path.lower().endswith(".json"):
            return send_file(full_path, as_attachment=True, download_name=os.path.basename(full_path))

        # 其余视为“文字”结果：优先尝试转为 PDF 下载
        try:
            pdf_path = _txt_to_pdf(full_path)
            pdf_name = os.path.basename(pdf_path)
            return send_file(pdf_path, as_attachment=True, download_name=pdf_name, mimetype="application/pdf")
        except Exception as e:
            # 如果 PDF 转换失败，回退为原始 txt 下载，并把错误信息写入日志
            from flask import current_app
            current_app.logger.error(f'[aliyun_download] PDF 转换失败，回退为 txt 下载: {e}')
            return send_file(full_path, as_attachment=True, download_name=os.path.basename(full_path))

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[aliyun_download]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})
        
