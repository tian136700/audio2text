import requests
import json
import time
import urllib3

# 禁用 SSL 警告（仅用于测试环境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = "ijgWHIwoJANyCZDV7PvhpdZq"
SECRET_KEY = "PDLCussOAw05ydT2rDIzs3zunKHkFr3D"

# 音频文件 URL
AUDIO_URL = "https://files.catbox.moe/nyi9az.wav"


def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    # 添加 verify=False 以绕过 SSL 验证（仅用于测试）
    response = requests.post(url, params=params, verify=False, timeout=30)
    result = response.json()
    if "access_token" in result:
        return result["access_token"]
    else:
        print(f"获取 access_token 失败: {result}")
        return None


def create_transcribe_task(speech_url, format_type="wav", pid=80001, rate=16000):
    """
    创建音频转写任务
    :param speech_url: 音频文件的公网 URL
    :param format_type: 音频格式 (mp3, wav, pcm, m4a, amr)
    :param pid: 语言类型 (80001=中文极速版, 80006=中文音视频字幕, 1737=英文)
    :param rate: 采样率 (固定 16000)
    :return: task_id 或 None
    """
    access_token = get_access_token()
    if not access_token:
        return None
    
    url = f"https://aip.baidubce.com/rpc/2.0/aasr/v1/create?access_token={access_token}"
    
    payload = json.dumps({
        "speech_url": speech_url,
        "format": format_type,
        "pid": pid,
        "rate": rate
    }, ensure_ascii=False)
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print(f"正在创建转写任务...")
    print(f"音频 URL: {speech_url}")
    print(f"格式: {format_type}, PID: {pid}, 采样率: {rate}")
    
    response = requests.post(url, headers=headers, data=payload.encode("utf-8"), verify=False, timeout=30)
    result = response.json()
    
    print(f"创建任务响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if "task_id" in result:
        task_id = result["task_id"]
        print(f"\n✅ 任务创建成功！")
        print(f"Task ID: {task_id}")
        return task_id
    else:
        print(f"\n❌ 任务创建失败:")
        print(f"错误码: {result.get('error_code', 'N/A')}")
        print(f"错误信息: {result.get('error_msg', 'N/A')}")
        return None


def query_transcribe_result(task_id):
    """
    查询转写结果
    :param task_id: 任务 ID
    :return: 识别结果或 None
    """
    access_token = get_access_token()
    if not access_token:
        return None
    
    url = f"https://aip.baidubce.com/rpc/2.0/aasr/v1/query?access_token={access_token}"
    
    payload = json.dumps({
        "task_ids": [task_id]
    }, ensure_ascii=False)
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    response = requests.post(url, headers=headers, data=payload.encode("utf-8"), verify=False, timeout=30)
    result = response.json()
    
    return result


def main():
    print("=" * 60)
    print("百度语音识别 API 测试")
    print("=" * 60)
    
    # 第一步：创建转写任务
    task_id = create_transcribe_task(AUDIO_URL, format_type="wav", pid=80001)
    
    if not task_id:
        print("\n❌ 无法创建任务，程序退出")
        return
    
    # 第二步：轮询查询结果
    print(f"\n开始轮询查询结果（Task ID: {task_id}）...")
    print("提示：识别可能需要一些时间，请耐心等待...\n")
    
    max_attempts = 60  # 最多查询 60 次
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"第 {attempt} 次查询...", end=" ")
        
        result = query_transcribe_result(task_id)
        
        if not result:
            print("查询失败")
            time.sleep(5)
            continue
        
        # 检查结果
        if "tasks_info" in result and len(result["tasks_info"]) > 0:
            task_info = result["tasks_info"][0]
            task_status = task_info.get("task_status", "")
            
            print(f"状态: {task_status}")
            # 打印完整任务信息，便于排查失败原因
            print(json.dumps(task_info, ensure_ascii=False, indent=2))
            
            if task_status == "Success":
                print("\n" + "=" * 60)
                print("✅ 识别成功！")
                print("=" * 60)
                
                # 显示识别结果
                if "task_result" in task_info:
                    task_result = task_info["task_result"]
                    if "result_detail" in task_result:
                        result_detail = task_result["result_detail"]
                        print("\n识别结果：")
                        print("-" * 60)
                        for item in result_detail:
                            start_time = item.get("begin_time", 0)
                            end_time = item.get("end_time", 0)
                            text = item.get("result", "")
                            print(f"[{start_time:.2f}s - {end_time:.2f}s] {text}")
                        print("-" * 60)
                    
                    # 显示完整文本
                    if "result" in task_result:
                        full_text = task_result["result"]
                        print(f"\n完整文本：\n{full_text}")
                
                break
            elif task_status in ["Failed", "Failure"]:
                print("\n❌ 识别失败")
                if "failed_reason" in task_info:
                    print(f"失败原因: {task_info['failed_reason']}")
                elif "task_result" in task_info:
                    # 部分情况下失败原因在 task_result 里
                    print(f"失败详情: {json.dumps(task_info.get('task_result', {}), ensure_ascii=False, indent=2)}")
                break
            elif task_status in ["Created", "Running"]:
                # 任务还在处理中，继续等待
                time.sleep(5)
            else:
                print(f"未知状态: {task_status}")
                time.sleep(5)
        else:
            print("响应格式异常")
            print(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            time.sleep(5)
    
    if attempt >= max_attempts:
        print(f"\n⚠️ 已达到最大查询次数 ({max_attempts})，请稍后手动查询结果")
        print(f"Task ID: {task_id}")


def query_existing_task(task_id):
    """
    查询已存在的任务结果
    :param task_id: 任务 ID
    """
    print("=" * 60)
    print("查询百度语音识别任务结果")
    print("=" * 60)
    print(f"Task ID: {task_id}\n")
    
    max_attempts = 60  # 最多查询 60 次
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"第 {attempt} 次查询...", end=" ")
        
        result = query_transcribe_result(task_id)
        
        if not result:
            print("查询失败")
            time.sleep(5)
            continue
        
        # 检查结果
        if "tasks_info" in result and len(result["tasks_info"]) > 0:
            task_info = result["tasks_info"][0]
            task_status = task_info.get("task_status", "")
            
            print(f"状态: {task_status}")
            
            if task_status == "Success":
                print("\n" + "=" * 60)
                print("✅ 识别成功！")
                print("=" * 60)
                
                # 显示识别结果
                if "task_result" in task_info:
                    task_result = task_info["task_result"]
                    if "result_detail" in task_result:
                        result_detail = task_result["result_detail"]
                        print("\n识别结果（带时间戳）：")
                        print("-" * 60)
                        for item in result_detail:
                            start_time = item.get("begin_time", 0)
                            end_time = item.get("end_time", 0)
                            text = item.get("result", "")
                            print(f"[{start_time:.2f}s - {end_time:.2f}s] {text}")
                        print("-" * 60)
                    
                    # 显示完整文本
                    if "result" in task_result:
                        full_text = task_result["result"]
                        print(f"\n完整文本：\n{full_text}")
                
                break
            elif task_status == "Failed":
                print("\n❌ 识别失败")
                if "failed_reason" in task_info:
                    print(f"失败原因: {task_info['failed_reason']}")
                break
            elif task_status in ["Created", "Running"]:
                # 任务还在处理中，继续等待
                print("（处理中，等待 5 秒后继续查询...）")
                time.sleep(5)
            else:
                print(f"未知状态: {task_status}")
                time.sleep(5)
        else:
            print("响应格式异常")
            print(f"完整响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            time.sleep(5)
    
    if attempt >= max_attempts:
        print(f"\n⚠️ 已达到最大查询次数 ({max_attempts})，请稍后手动查询结果")
        print(f"Task ID: {task_id}")


if __name__ == '__main__':
    import sys
    
    # 如果命令行提供了 task_id，直接查询
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        query_existing_task(task_id)
    else:
        main()
