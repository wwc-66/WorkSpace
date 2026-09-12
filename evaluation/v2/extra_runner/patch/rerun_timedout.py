# evaluation/v2/retry_failed_v2.py
import json
import os
import sys
import requests
from datetime import datetime

# 路径配置
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 导入模型路由（引用 V1 的）
from evaluation.v1.eval_runner_v1 import get_model_config

BASE_URL = "http://127.0.0.1:8000"
RESULTS_DIR = os.path.join(CURRENT_DIR, "results")
CASES_FILE = os.path.join(CURRENT_DIR, "eval_cases_v2.json")

# 定义要重跑的 Case（直接拷贝你报错的信息）
FAILED_CASES = {
    "deepseek-v4-flash": ["M01-1", "M01-2", "M01-3", "M02-2"],
    "qwen3.8:27b": ["M01-1"]
}
TIMEOUT = 180  # 放宽到 3 分钟

def call_generate(prompt, model):
    provider, api_key, base_url = get_model_config(model)
    payload = {
        "prompt": prompt,
        "model": model,
        "provider": provider,
        "api_key": api_key
    }
    if base_url:
        payload["base_url"] = base_url
    try:
        resp = requests.post(f"{BASE_URL}/generate", json=payload, timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "response": f"请求失败: {e}"}

def call_ask(prompt, model):
    provider, api_key, base_url = get_model_config(model)
    payload = {
        "question": prompt,
        "model": model,
        "provider": provider,
        "api_key": api_key
    }
    if base_url:
        payload["base_url"] = base_url
    try:
        resp = requests.post(f"{BASE_URL}/ask", json=payload, timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "answer": f"请求失败: {e}"}

def main():
    # 加载原始 cases
    with open(CASES_FILE, 'r', encoding='utf-8') as f:
        all_cases = json.load(f)
    
    # 构建 ID -> prompt 映射（并记录类别和类型）
    case_map = {}
    for category, cases in all_cases.items():
        for case in cases:
            case_id = case["id"]
            case_map[case_id] = {
                "prompt": case["prompt"],
                "category": category,
                "name": case["name"]
            }

    for model, case_ids in FAILED_CASES.items():
        print(f"\n🔁 正在重跑 {model} 的失败 Case...")
        safe_model = model.replace(":", "_").replace("/", "_")
        result_file = os.path.join(RESULTS_DIR, f"eval_results_{safe_model}_v2.json")
        
        # 读取已有的结果文件
        with open(result_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        
        # 遍历需要重跑的 Case
        for case_id in case_ids:
            print(f"   - 重跑 {case_id}...")
            case_info = case_map.get(case_id)
            if not case_info:
                print(f"      ⚠️ 未找到 Case ID: {case_id}")
                continue
            
            prompt = case_info["prompt"]
            category = case_info["category"]
            
            # 根据类别选择 API
            if "根据上面给的文章" in prompt or "根据文章" in prompt:
                resp = call_ask(prompt, model)
                actual = resp.get("answer", "")
            else:
                resp = call_generate(prompt, model)
                actual = resp.get("response", "")
            
            # 更新 existing_data 中对应 Case 的 actual 和 latency
            for cat in existing_data["details"]:
                for item in existing_data["details"][cat]:
                    if item["id"] == case_id:
                        item["actual"] = actual
                        item["latency_ms"] = resp.get("latency_ms", -1)
                        # 如果有错误信息，记录下来便于调试
                        if "error" in resp:
                            item["error"] = resp.get("error")
                        print(f"      ✅ 更新成功，长度: {len(actual)} 字符")
                        break
        
        # 写回文件
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        print(f"   ✅ {model} 重跑完成，结果已更新至 {result_file}")

if __name__ == "__main__":
    main()