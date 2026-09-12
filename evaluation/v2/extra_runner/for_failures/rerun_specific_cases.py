# evaluation/v2/rerun_specific_cases.py
import json
import os
import sys
import requests
from datetime import datetime
from collections import defaultdict

# 路径配置
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from evaluation.v1.eval_runner_v1 import get_model_config

BASE_URL = "http://127.0.0.1:8000"
RESULTS_DIR = os.path.join(CURRENT_DIR, "results")
CASES_FILE = os.path.join(CURRENT_DIR, "eval_cases_v2.json")
TIMEOUT = 180

# ============================================================
# 【配置区】按需修改
# ============================================================

# 任务 A：M01-3 修正后重跑（单次）
RERUN_SINGLE = {
    "M01-3": ["qwen-plus", "deepseek-flash", "qwen3.8:27b"]  # 修正后所有模型都重跑一次
}

# 任务 B：稳定性测试（多次重复）
STABILITY_TEST = {
    "M01-1": {"model": "deepseek-flash", "repeat": 5},
    "M01-2": {"model": "deepseek-flash", "repeat": 5},
}

# ============================================================

def load_cases():
    with open(CASES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    case_map = {}
    for category, cases in data.items():
        for case in cases:
            case_map[case["id"]] = {
                "prompt": case["prompt"],
                "category": category,
                "name": case["name"]
            }
    return case_map

def call_model(prompt, model):
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
        result = resp.json()
        return result.get("response", ""), result.get("error", None)
    except Exception as e:
        return "", str(e)

# ============== 任务 A: 单次重跑 M01-3 ==============
def run_rerun_single(case_map):
    print("\n" + "="*60)
    print("📌 任务 A: M01-3 修正后重跑")
    print("="*60)
    
    for case_id, models in RERUN_SINGLE.items():
        case_info = case_map.get(case_id)
        if not case_info:
            print(f"⚠️ 找不到 Case: {case_id}")
            continue
        
        prompt = case_info["prompt"]
        for model in models:
            print(f"\n🔁 重跑 {case_id} -> {model}")
            actual, error = call_model(prompt, model)
            
            # 更新对应模型的 result 文件
            safe_model = model.replace(":", "_").replace("/", "_")
            result_file = os.path.join(RESULTS_DIR, f"eval_results_{safe_model}_v2.json")
            
            if not os.path.exists(result_file):
                print(f"   ⚠️ 结果文件不存在: {result_file}")
                continue
            
            with open(result_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 找到对应 case 并更新
            updated = False
            for cat in data["details"]:
                for item in data["details"][cat]:
                    if item["id"] == case_id:
                        item["actual"] = actual
                        item["error"] = error
                        item["rerun_at"] = datetime.now().isoformat()
                        # 重置 passed 为 None，等待你重新人工审核
                        item["passed"] = None
                        updated = True
                        break
            
            if updated:
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"   ✅ 更新成功，回答长度: {len(actual)} 字符")
                print(f"   📄 前 200 字预览:\n{actual[:200]}...")
            else:
                print(f"   ⚠️ 未在文件中找到 {case_id}")

# ============== 任务 B: 稳定性测试 ==============
def run_stability_test(case_map):
    print("\n" + "="*60)
    print("📌 任务 B: 稳定性测试（多次重复）")
    print("="*60)
    
    results = defaultdict(list)
    
    for case_id, config in STABILITY_TEST.items():
        model = config["model"]
        repeat = config["repeat"]
        case_info = case_map.get(case_id)
        
        if not case_info:
            print(f"⚠️ 找不到 Case: {case_id}")
            continue
        
        print(f"\n🔁 稳定性测试: {case_id} -> {model} × {repeat} 次")
        prompt = case_info["prompt"]
        
        for i in range(repeat):
            print(f"   [{i+1}/{repeat}] 正在调用...", end=" ")
            actual, error = call_model(prompt, model)
            
            # 自动检查“3段×2句”格式（针对 M01 系列的硬约束）
            # 3段：用 \n\n 或两个以上连续换行切分
            # 2句/段：每段内的句号 + 问号数量 == 2
            segments = [s.strip() for s in actual.split("\n\n") if s.strip()]
            # 兼容模型可能用单个 \n 或 \n\n\n 分隔
            if len(segments) == 1:
                # 尝试用单个 \n 再切
                segments = [s.strip() for s in actual.split("\n") if s.strip()]
            
            num_segments = len(segments)
            sentences_per_segment = []
            for seg in segments:
                # 计算句末标点数量（。！？）
                import re
                count = len(re.findall(r'[。！？]', seg))
                sentences_per_segment.append(count)
            
            # 判定：3 段，每段 2 句
            format_ok = (num_segments == 3 and all(c == 2 for c in sentences_per_segment))
            
            results[case_id].append({
                "run_index": i + 1,
                "actual": actual,
                "error": error,
                "num_segments": num_segments,
                "sentences_per_segment": sentences_per_segment,
                "format_ok": format_ok
            })
            
            mark = "✅" if format_ok else "❌"
            print(f"{mark} 段数={num_segments}, 每段句数={sentences_per_segment}")
    
    # 输出稳定性报告
    print("\n" + "="*60)
    print("📊 稳定性测试汇总")
    print("="*60)
    report_lines = []
    for case_id, runs in results.items():
        ok_count = sum(1 for r in runs if r["format_ok"])
        total = len(runs)
        rate = ok_count / total * 100 if total > 0 else 0
        verdict = "系统性偏差" if rate < 40 else ("概率性失误" if rate < 80 else "基本稳定")
        line = f"{case_id}: {ok_count}/{total} 通过 ({rate:.1f}%) → {verdict}"
        print(line)
        report_lines.append(line)
    
    # 保存稳定性测试详情
    output_file = os.path.join(RESULTS_DIR, "stability_test_m01.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "config": STABILITY_TEST,
            "results": dict(results),
            "summary": report_lines
        }, f, ensure_ascii=False, indent=2)
    print(f"\n📄 稳定性测试详情已保存至: {output_file}")

# ============== 主入口 ==============
if __name__ == "__main__":
    case_map = load_cases()
    run_rerun_single(case_map)
    run_stability_test(case_map)
    print("\n🎉 所有任务完成。")