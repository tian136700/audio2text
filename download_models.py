#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提前下载所有模型脚本
用于在首次使用前下载所有需要的模型，避免使用时再下载
"""

import os
import sys

# 设置环境变量（必须在导入任何库之前）
os.environ.setdefault('OBJC_DISABLE_INITIALIZE_FORK_SAFETY', 'YES')
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')
os.environ.setdefault('VECLIB_MAXIMUM_THREADS', '1')
os.environ.setdefault('OMP_DYNAMIC', 'FALSE')
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
os.environ.setdefault('KMP_INIT_AT_FORK', 'FALSE')
os.environ.setdefault('OMP_PROC_BIND', 'close')
os.environ.setdefault('OMP_PLACES', 'cores')
os.environ.setdefault('KMP_BLOCKTIME', '0')
os.environ.setdefault('KMP_SETTINGS', '0')
os.environ.setdefault('KMP_AFFINITY', 'disabled')
os.environ.setdefault('KMP_SHARED_MEMORY', 'disabled')
os.environ.setdefault('OMP_SHARED_MEMORY', 'disabled')

from dotenv import load_dotenv
import stslib
from stslib import cfg
from faster_whisper import WhisperModel

# 加载 .env 文件
load_dotenv()

# 可用的 Whisper 模型列表（按大小和效果排序）
# 推荐下载：base, small, medium, large-v3（根据需求选择）
# 注意：已移除英语专用模型（.en），通用模型支持所有语言包括英语
WHISPER_MODELS = [
    "tiny",           # 最小模型，速度最快，效果一般
    # "tiny.en",      # 英语专用小模型（已移除，通用模型支持英语）
    "base",           # 基础模型，速度快，效果一般（推荐）
    # "base.en",      # 英语专用基础模型（已移除，通用模型支持英语）
    "small",          # 小模型，速度和效果平衡（推荐）
    # "small.en",     # 英语专用小模型（已移除，通用模型支持英语）
    "medium",         # 中等模型，效果较好（推荐）
    # "medium.en",    # 英语专用中等模型（已移除，通用模型支持英语）
    "large-v3",       # 大模型，效果最好，但速度慢（推荐）
    "large-v2",       # 大模型 v2 版本
    "large",          # 大模型（旧版）
]


def download_whisper_models():
    """下载所有 Whisper 模型"""
    print("=" * 60)
    print("开始下载 Whisper 语音识别模型...")
    print("=" * 60)
    
    models_dir = os.path.join(cfg.ROOT_DIR, "models")
    os.makedirs(models_dir, exist_ok=True)
    print(f"模型保存目录: {models_dir}\n")
    
    sets = cfg.parse_ini()
    device = sets.get('devtype', 'cpu')
    
    success_count = 0
    fail_count = 0
    
    for model_name in WHISPER_MODELS:
        print(f"\n[{success_count + fail_count + 1}/{len(WHISPER_MODELS)}] 正在下载模型: {model_name}")
        print("-" * 60)
        
        try:
            # 检查模型是否已存在
            model_path = os.path.join(models_dir, model_name)
            if os.path.exists(model_path) and os.listdir(model_path):
                print(f"✓ 模型 {model_name} 已存在，跳过下载")
                success_count += 1
                continue
            
            # 下载模型
            print(f"正在从 Hugging Face 下载 {model_name}...")
            model = WhisperModel(
                model_name,
                device=device,
                download_root=models_dir
            )
            print(f"✓ 模型 {model_name} 下载成功！")
            success_count += 1
            
            # 释放内存
            del model
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"✗ 模型 {model_name} 下载失败: {str(e)}")
            fail_count += 1
            continue
    
    print("\n" + "=" * 60)
    print(f"Whisper 模型下载完成！")
    print(f"成功: {success_count}, 失败: {fail_count}")
    print("=" * 60)
    return success_count, fail_count


def download_pyannote_model():
    """下载 pyannote 说话人识别模型"""
    print("\n" + "=" * 60)
    print("开始下载 pyannote 说话人识别模型...")
    print("=" * 60)
    
    try:
        from pyannote.audio import Pipeline
        from huggingface_hub import login
        import torch
    except ImportError:
        print("✗ pyannote.audio 未安装，跳过说话人识别模型下载")
        print("  如需使用说话人识别功能，请运行: pip install pyannote.audio")
        return False
    
    # 检查 Hugging Face Token
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("✗ 未找到 Hugging Face Token，跳过说话人识别模型下载")
        print("  请在 .env 文件中设置 HF_TOKEN")
        print("  获取 Token: https://huggingface.co/settings/tokens")
        return False
    
    try:
        # 登录 Hugging Face
        print("正在登录 Hugging Face...")
        login(hf_token)
        print("✓ 登录成功")
        
        # 下载模型
        print("正在下载 pyannote/speaker-diarization-3.1...")
        print("（这可能需要几分钟，请耐心等待...）")
        
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1"
        )
        
        print("✓ pyannote 说话人识别模型下载成功！")
        print("  模型已缓存到 Hugging Face 缓存目录")
        
        # 释放内存
        del pipeline
        import gc
        gc.collect()
        
        return True
        
    except Exception as e:
        print(f"✗ pyannote 模型下载失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("模型预下载工具")
    print("=" * 60)
    print("\n此脚本将帮助您提前下载所有需要的模型，避免使用时再下载。")
    print("注意：模型文件较大，下载可能需要较长时间，请确保网络连接稳定。\n")
    
    # 询问用户要下载哪些模型
    print("请选择要下载的模型类型：")
    print("1. 仅下载 Whisper 语音识别模型")
    print("2. 仅下载 pyannote 说话人识别模型")
    print("3. 下载所有模型（推荐）")
    print("4. 自定义选择 Whisper 模型")
    
    choice = input("\n请输入选项 (1-4，直接回车默认选择3): ").strip()
    if not choice:
        choice = "3"
    
    if choice == "1":
        download_whisper_models()
    elif choice == "2":
        download_pyannote_model()
    elif choice == "3":
        download_whisper_models()
        download_pyannote_model()
    elif choice == "4":
        print("\n可用的 Whisper 模型：")
        for i, model in enumerate(WHISPER_MODELS, 1):
            print(f"  {i}. {model}")
        
        selected = input("\n请输入要下载的模型编号（用逗号分隔，如 1,2,3）: ").strip()
        if selected:
            try:
                indices = [int(x.strip()) - 1 for x in selected.split(',')]
                selected_models = [WHISPER_MODELS[i] for i in indices if 0 <= i < len(WHISPER_MODELS)]
                
                if selected_models:
                    print(f"\n将下载以下模型: {', '.join(selected_models)}")
                    models_dir = os.path.join(cfg.ROOT_DIR, "models")
                    os.makedirs(models_dir, exist_ok=True)
                    sets = cfg.parse_ini()
                    device = sets.get('devtype', 'cpu')
                    
                    for model_name in selected_models:
                        print(f"\n正在下载: {model_name}")
                        try:
                            model = WhisperModel(
                                model_name,
                                device=device,
                                download_root=models_dir
                            )
                            print(f"✓ {model_name} 下载成功")
                            del model
                            import gc
                            gc.collect()
                        except Exception as e:
                            print(f"✗ {model_name} 下载失败: {str(e)}")
                else:
                    print("未选择有效模型")
            except ValueError:
                print("输入格式错误")
        else:
            print("未选择任何模型")
    else:
        print("无效选项")
        return
    
    print("\n" + "=" * 60)
    print("所有模型下载任务已完成！")
    print("=" * 60)
    print("\n提示：")
    print("- Whisper 模型保存在: models/ 目录")
    print("- pyannote 模型保存在 Hugging Face 缓存目录")
    print("- 现在可以正常使用语音识别功能了\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断下载")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

