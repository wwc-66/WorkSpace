# test_single_call.py
# 冒烟测试：验证所有待测模型能否正常响应（不依赖 eval_runner 的复杂逻辑）

import requests
import sys
import os

# 把当前目录加入 Python 路径，方便导入 eval_runner 里的配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接从 eval_runner 导入模型列表和路由函数，保证配置一致
from evaluation.v1.eval_runner_v1 import MODELS_TO_TEST, get_model_config

BASE_URL = "http://127.0.0.1:8000"

def test_single_model(model_name: str):
    """测试单个模型是否通"""
    print(f"\n🔍 正在测试模型: {model_name}")
    
    # 1. 从路由表获取配置
    provider, api_key, base_url = get_model_config(model_name)
    print(f"   路由 -> Provider: {provider}, BaseURL: {base_url}")
    
    # 2. 构造请求体（完全透传后端需要的字段）
    payload = {
        "prompt": "说一个字的回复：好",
        "model": model_name,
        "provider": provider,
        "api_key": api_key,
    }
    if base_url:
        payload["base_url"] = base_url
    
    # 3. 发请求
    try:
        resp = requests.post(f"{BASE_URL}/generate", json=payload, timeout=30)
        result = resp.json()
        
        if "response" in result and result["response"] == "好":
            print(f"   ✅ {model_name} 测试通过！回复: {result['response']}")
            return True
        elif "error" in result:
            print(f"   ❌ {model_name} 返回错误: {result['error']}")
            return False
        else:
            print(f"   ⚠️ {model_name} 返回异常结构: {result}")
            return False
    except Exception as e:
        print(f"   ❌ {model_name} 请求失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始全量冒烟测试...")
    print(f"待测模型列表: {MODELS_TO_TEST}")
    
    all_passed = True
    for model in MODELS_TO_TEST:
        if not test_single_model(model):
            all_passed = False
    
    print("\n" + "="*40)
    if all_passed:
        print("🎉 所有模型均测试通过！可以运行 python eval_runner.py")
    else:
        print("⚠️ 有模型测试失败，请检查 .env 配置或模型服务是否启动。")