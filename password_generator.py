#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机密码生成工具
"""

import random
import string
from typing import Dict, List


def generate_password(
    length: int = 16,
    include_uppercase: bool = True,
    include_lowercase: bool = True,
    include_digits: bool = True,
    include_special: bool = True,
    exclude_similar: bool = True,
    exclude_ambiguous: bool = True
) -> Dict:
    """
    生成随机密码
    
    Args:
        length: 密码长度（8-128）
        include_uppercase: 包含大写字母
        include_lowercase: 包含小写字母
        include_digits: 包含数字
        include_special: 包含特殊字符
        exclude_similar: 排除相似字符（如 0, O, l, 1）
        exclude_ambiguous: 排除易混淆字符（如 I, l, |）
    
    Returns:
        Dict: 包含密码和强度信息的字典
    """
    # 验证长度
    if length < 8:
        length = 8
    elif length > 128:
        length = 128
    
    # 构建字符集
    chars = ""
    
    if include_uppercase:
        chars += string.ascii_uppercase
    if include_lowercase:
        chars += string.ascii_lowercase
    if include_digits:
        chars += string.digits
    if include_special:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # 排除相似字符
    if exclude_similar:
        similar_chars = "0O1lI"
        chars = ''.join(c for c in chars if c not in similar_chars)
    
    # 排除易混淆字符
    if exclude_ambiguous:
        ambiguous_chars = "Il|1O0"
        chars = ''.join(c for c in chars if c not in ambiguous_chars)
    
    # 确保至少包含每种类型的字符
    password_chars = []
    char_sets = []
    
    if include_uppercase:
        uppercase_chars = string.ascii_uppercase
        if exclude_similar:
            uppercase_chars = ''.join(c for c in uppercase_chars if c not in "O")
        if exclude_ambiguous:
            uppercase_chars = ''.join(c for c in uppercase_chars if c not in "I")
        if uppercase_chars:
            char_sets.append(uppercase_chars)
            password_chars.append(random.choice(uppercase_chars))
    
    if include_lowercase:
        lowercase_chars = string.ascii_lowercase
        if exclude_similar:
            lowercase_chars = ''.join(c for c in lowercase_chars if c not in "l1")
        if exclude_ambiguous:
            lowercase_chars = ''.join(c for c in lowercase_chars if c not in "l|")
        if lowercase_chars:
            char_sets.append(lowercase_chars)
            password_chars.append(random.choice(lowercase_chars))
    
    if include_digits:
        digit_chars = string.digits
        if exclude_similar:
            digit_chars = ''.join(c for c in digit_chars if c not in "01")
        if exclude_ambiguous:
            digit_chars = ''.join(c for c in digit_chars if c not in "01")
        if digit_chars:
            char_sets.append(digit_chars)
            password_chars.append(random.choice(digit_chars))
    
    if include_special:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if exclude_ambiguous:
            special_chars = ''.join(c for c in special_chars if c not in "|")
        if special_chars:
            char_sets.append(special_chars)
            password_chars.append(random.choice(special_chars))
    
    # 如果字符集为空，使用默认字符集
    if not chars:
        chars = string.ascii_letters + string.digits
    
    # 填充剩余长度
    remaining_length = length - len(password_chars)
    for _ in range(remaining_length):
        password_chars.append(random.choice(chars))
    
    # 打乱顺序
    random.shuffle(password_chars)
    password = ''.join(password_chars)
    
    # 计算密码强度
    strength = calculate_strength(
        password, include_uppercase, include_lowercase, 
        include_digits, include_special
    )
    
    return {
        "password": password,
        "length": len(password),
        "strength": strength["level"],
        "strength_score": strength["score"],
        "strength_text": strength["text"]
    }


def calculate_strength(
    password: str,
    has_uppercase: bool,
    has_lowercase: bool,
    has_digits: bool,
    has_special: bool
) -> Dict:
    """
    计算密码强度
    
    Returns:
        Dict: 包含强度等级、分数和文本的字典
    """
    score = 0
    length = len(password)
    
    # 长度评分
    if length >= 16:
        score += 3
    elif length >= 12:
        score += 2
    elif length >= 8:
        score += 1
    
    # 字符类型评分
    char_types = sum([has_uppercase, has_lowercase, has_digits, has_special])
    score += char_types
    
    # 复杂度评分
    if length >= 20 and char_types >= 3:
        score += 2
    elif length >= 12 and char_types >= 2:
        score += 1
    
    # 确定强度等级
    if score >= 8:
        level = "very_strong"
        text = "非常强"
    elif score >= 6:
        level = "strong"
        text = "强"
    elif score >= 4:
        level = "medium"
        text = "中等"
    elif score >= 2:
        level = "weak"
        text = "弱"
    else:
        level = "very_weak"
        text = "很弱"
    
    return {
        "level": level,
        "score": score,
        "text": text
    }


def generate_multiple_passwords(count: int = 5, **kwargs) -> List[Dict]:
    """
    生成多个密码
    
    Args:
        count: 生成数量（1-50）
        **kwargs: 传递给 generate_password 的参数
    
    Returns:
        List[Dict]: 密码列表
    """
    if count < 1:
        count = 1
    elif count > 50:
        count = 50
    
    passwords = []
    for _ in range(count):
        passwords.append(generate_password(**kwargs))
    
    return passwords

