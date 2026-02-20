#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
密码生成相关路由处理函数
"""

from flask import request, render_template, jsonify
from stslib import cfg
import stslib
import password_generator


def password_generator_page():
    """随机密码生成独立页面"""
    sets = cfg.parse_ini()
    return render_template(
        "password_generator.html",
        version=stslib.version_str,
        lang_code=cfg.lang_code,
        language=cfg.LANG,
        devtype=sets.get("devtype"),
        current_page='/password_generator',
    )


def generate_password():
    """生成随机密码"""
    try:
        length = int(request.form.get("length", 16))
        count = int(request.form.get("count", 1))
        include_uppercase = request.form.get("include_uppercase") == "true"
        include_lowercase = request.form.get("include_lowercase") == "true"
        include_digits = request.form.get("include_digits") == "true"
        include_special = request.form.get("include_special") == "true"
        exclude_similar = request.form.get("exclude_similar") == "true"
        exclude_ambiguous = request.form.get("exclude_ambiguous") == "true"
        
        # 验证参数
        if length < 8 or length > 128:
            return jsonify({"code": 1, "msg": "密码长度必须在 8-128 之间"})
        
        if count < 1 or count > 50:
            return jsonify({"code": 1, "msg": "生成数量必须在 1-50 之间"})
        
        if not include_uppercase and not include_lowercase and not include_digits and not include_special:
            return jsonify({"code": 1, "msg": "请至少选择一种字符类型"})
        
        # 生成密码
        if count == 1:
            result = password_generator.generate_password(
                length=length,
                include_uppercase=include_uppercase,
                include_lowercase=include_lowercase,
                include_digits=include_digits,
                include_special=include_special,
                exclude_similar=exclude_similar,
                exclude_ambiguous=exclude_ambiguous
            )
            passwords = [result]
        else:
            passwords = password_generator.generate_multiple_passwords(
                count=count,
                length=length,
                include_uppercase=include_uppercase,
                include_lowercase=include_lowercase,
                include_digits=include_digits,
                include_special=include_special,
                exclude_similar=exclude_similar,
                exclude_ambiguous=exclude_ambiguous
            )
        
        return jsonify({"code": 0, "msg": "生成成功", "data": passwords})
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'[generate_password]error: {e}')
        return jsonify({"code": 1, "msg": str(e)})

