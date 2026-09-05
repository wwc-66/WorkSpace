#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ========== 配置 ==========
BASE_URL = "http://127.0.0.1:8000"
EVAL_CASES_FILE = "eval_cases.json"

# ==============================================
# 【手敲清单 第1条 修复版】精确路由映射表
# 原则：先匹配精确的云端模型名，其余全部视为本地 Ollama
# ==============================================

def get_model_config(model_name: str):
    """
    根据模型名称返回 (provider, api_key, base_url)
    采用显式映射表，避免 'qwen' 关键字误伤本地模型
    """
    # 1. 定义云端模型映射表（精确匹配）
    cloud_models = {
        "qwen-plus": {
            "provider": "dashscope",
            "api_key": os.getenv("DASHSCOPE_API_KEY"),
            "base_url": None
        },
        "deepseek-v4-flash": {
            "provider": "openai_compatible",
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "base_url": "https://api.deepseek.com/v1"
        },
        # 如果你以后想加 GPT-4o-mini，可以在这里追加
        # "gpt-4o-mini": {
        #     "provider": "openai_compatible",
        #     "api_key": os.getenv("OPENAI_API_KEY"),
        #     "base_url": None
        # }
    }

    # 2. 精确匹配：如果在云端映射表中，直接返回
    if model_name in cloud_models:
        config = cloud_models[model_name]
        return config["provider"], config["api_key"], config["base_url"]

    # 3. 兜底策略：凡是不在上述映射表中的，一律视为本地 Ollama 模型
    # 包括 qwen2.5:7b, llama3.1:8b, mistral 等
    return "openai_compatible", "ollama", "http://localhost:11434/v1"

# 你要测试的模型列表（按需增删）
# 注意：Ollama 里的模型名要和你 `ollama list` 里的一模一样
MODELS_TO_TEST = [
    "qwen-plus",           # 阿里云通义千问 Plus
    "deepseek-v4-flash",   # DeepSeek V4 Flash（需配置 DEEPSEEK_API_KEY）
    "qwen3.8:27b",         # Ollama本地通义千问 3.8
]

# ==============================================
# 【手敲清单 第2条】定义哪些 Case 属于“模型敏感类”
# 只有这些 Case 会参与模型质量排名，系统类 Case（C组）只做回归验证
# ==============================================
MODEL_SENSITIVE_IDS = {
    "R01", "R02", "R03", "R04", "R05",  # RAG 组全部依赖模型理解能力
    "I01", "I02", "I03", "I04", "I05"   # 指令遵循组全部依赖模型推理
}
# 不在上述集合中的，默认归类为 System Test（如 C01~C05）

# ========== 工具函数 ==========
def call_ask(question: str, session_id: str = None, model: str = None) -> Dict[str, Any]:
    """调用 /ask 接口，自动根据模型名配置 provider/api_key/base_url"""
    payload = {"question": question}
    if session_id:
        payload["session_id"] = session_id
    
    if model:
        # 【关键】根据模型名动态获取配置
        provider, api_key, base_url = get_model_config(model)
        payload["model"] = model
        payload["provider"] = provider
        payload["api_key"] = api_key
        if base_url:
            payload["base_url"] = base_url
    
    try:
        resp = requests.post(f"{BASE_URL}/ask", json=payload, timeout=60)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "answer": f"请求失败: {e}"}

def call_generate(prompt: str, session_id: str = None, model: str = None) -> Dict[str, Any]:
    """调用 /generate 接口，自动根据模型名配置 provider/api_key/base_url"""
    payload = {"prompt": prompt}
    if session_id:
        payload["session_id"] = session_id
    
    if model:
        provider, api_key, base_url = get_model_config(model)
        payload["model"] = model
        payload["provider"] = provider
        payload["api_key"] = api_key
        if base_url:
            payload["base_url"] = base_url
    
    try:
        resp = requests.post(f"{BASE_URL}/generate", json=payload, timeout=60)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "response": f"请求失败: {e}"}

# ---------- 以下判定函数与之前保持一致 ----------
def check_exact_match(actual: str, expected: str) -> bool:
    actual = actual.strip()
    expected = expected.strip()
    if actual == expected:
        return True
    if len(expected) <= 20 and expected in actual:
        return True
    return False

def check_exact_count(actual: str, expected_count: int) -> bool:
    import re
    items = re.split(r'\n\s*|•\s*|\d+\.\s*', actual)
    items = [i.strip() for i in items if i.strip()]
    return len(items) == expected_count

def check_json_match(actual: str, expected: str) -> bool:
    try:
        actual_json = json.loads(actual)
        expected_json = json.loads(expected)
        return actual_json == expected_json
    except:
        return False

def check_answer_accuracy(actual: str, expected: str) -> bool:
    import re
    actual = actual.strip()
    expected = expected.strip()
    def normalize(text):
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('，', ',').replace('。', '.').replace('、', ',').replace('：', ':')
        text = text.strip('，。.,:：')
        return text
    actual_norm = normalize(actual)
    expected_norm = normalize(expected)
    if expected_norm in actual_norm or actual_norm == expected_norm:
        return True
    def extract_key(text):
        text = re.sub(r'大约|约|左右|大概|可能|也许|主要|正式', '', text)
        text = re.sub(r'一次', '', text)
        return text
    expected_core = extract_key(expected_norm)
    actual_core = extract_key(actual_norm)
    if expected_core and expected_core in actual_core:
        return True
    if "信息不足" in expected:
        negative_words = ["无法", "没有", "找不到", "不确定", "不存在", "未提供", "未找到"]
        if any(word in actual for word in negative_words):
            return True
    return False

def check_retrieval_hit(actual: dict, expected_file: str) -> bool:
    sources = actual.get("sources", [])
    for source in sources:
        if expected_file in source:
            return True
    answer = actual.get("answer", "")
    if expected_file in answer:
        return True
    return False

# ==============================================
# 【手敲清单 第3条】单模型运行函数（核心逻辑）
# 这个函数接受一个 model_name，跑完所有 Cases，返回结构化结果
# ==============================================
def run_single_model_eval(model_name: str) -> Dict[str, Any]:
    print(f"\n🚀 正在测试模型: {model_name}")
    session_id = None
    results = {
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "details": {
            "conversation_context": [],
            "rag": [],
            "instruction_following": []
        },
        "summary": {}
    }

    # ---------- 1. Conversation Context (C组) ----------
    conv_results = []
    for case in eval_cases.get("conversation_context", []):
        case_result = {
            "id": case["id"],
            "name": case["name"],
            "passed": False,
            "actual": None,
            "expected": case["expected"],
            "note": case.get("note", "")
        }
        last_response = ""
        for step in case["steps"]:
            if step["role"] == "user":
                # 【关键】传入 model=model_name
                resp = call_generate(step["content"], session_id=session_id, model=model_name)
                if "session_id" in resp:
                    session_id = resp["session_id"]
                last_response = resp.get("response", "")
                case_result["actual"] = last_response
        if case["metric"] == "exact_match":
            case_result["passed"] = check_exact_match(last_response, case["expected"])
        conv_results.append(case_result)
    results["details"]["conversation_context"] = conv_results

    # ---------- 2. RAG (R组) ----------
    rag_results = []
    for case in eval_cases.get("rag", []):
        case_result = {
            "id": case["id"],
            "name": case["name"],
            "passed": False,
            "actual_answer": None,
            "expected_answer": case["expected_answer"],
            "retrieval_hit": False,
            "answer_accuracy": False,
            "sources": []
        }
        # 【关键】传入 model=model_name
        resp = call_ask(case["question"], session_id=None, model=model_name)
        case_result["actual_answer"] = resp.get("answer", "")
        case_result["latency_ms"] = resp.get("latency_ms", -1)
        case_result["sources"] = resp.get("sources", [])

        if "expected_evidence_file" in case and case["expected_evidence_file"]:
            case_result["retrieval_hit"] = check_retrieval_hit(resp, case["expected_evidence_file"])
        case_result["answer_accuracy"] = check_answer_accuracy(
            case_result["actual_answer"],
            case_result["expected_answer"]
        )
        # 注意：对于 R05（信息不足），我们允许 retrieval_hit=False 但 answer_accuracy=True 仍算通过
        if case["id"] == "R05":
            case_result["passed"] = case_result["answer_accuracy"]
        else:
            case_result["passed"] = case_result["retrieval_hit"] and case_result["answer_accuracy"]
        rag_results.append(case_result)
    results["details"]["rag"] = rag_results

    # ---------- 3. Instruction Following (I组) ----------
    inst_results = []
    for case in eval_cases.get("instruction_following", []):
        case_result = {
            "id": case["id"],
            "name": case["name"],
            "passed": False,
            "actual": None,
            "expected": case["expected"],
            "metric": case["metric"]
        }
        # 【关键】传入 model=model_name
        resp = call_generate(case["prompt"], session_id=None, model=model_name)
        actual = resp.get("response", "")
        case_result["latency_ms"] = resp.get("latency_ms", -1)
        case_result["actual"] = actual

        if case["metric"] == "exact_match":
            case_result["passed"] = check_exact_match(actual, case["expected"])
        elif case["metric"] == "exact_count":
            case_result["passed"] = check_exact_count(actual, case.get("expected_count", 3))
        elif case["metric"] == "json_match":
            case_result["passed"] = check_json_match(actual, case["expected"])
        elif case["metric"] == "answer_accuracy":
            case_result["passed"] = check_answer_accuracy(actual, case["expected"])
        inst_results.append(case_result)
    results["details"]["instruction_following"] = inst_results

    # ---------- 汇总统计 ----------
    total = 0
    passed = 0
    model_sensitive_total = 0
    model_sensitive_passed = 0
    system_total = 0
    system_passed = 0

    for category, items in results["details"].items():
        for item in items:
            total += 1
            if item.get("passed", False):
                passed += 1
            # 判断是否属于模型敏感类
            if item["id"] in MODEL_SENSITIVE_IDS:
                model_sensitive_total += 1
                if item.get("passed", False):
                    model_sensitive_passed += 1
            else:
                system_total += 1
                if item.get("passed", False):
                    system_passed += 1

    results["summary"] = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 2) if total > 0 else 0,
        "model_sensitive": {
            "total": model_sensitive_total,
            "passed": model_sensitive_passed,
            "pass_rate": round(model_sensitive_passed / model_sensitive_total * 100, 2) if model_sensitive_total > 0 else 0
        },
        "system": {
            "total": system_total,
            "passed": system_passed,
            "pass_rate": round(system_passed / system_total * 100, 2) if system_total > 0 else 0
        }
    }

    # 保存该模型的详细 JSON
    safe_model_name = model_name.replace(":", "_").replace("/", "_")
    output_file = f"eval_results_{safe_model_name}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"   ✅ {model_name} 完成，通过率: {results['summary']['pass_rate']}% (模型敏感: {results['summary']['model_sensitive']['pass_rate']}%)")
    return results

# ==============================================
# 【手敲清单 第4条】生成 Markdown 对比报告
# ==============================================
def generate_markdown_report(all_results: List[Dict[str, Any]]):
    lines = []
    lines.append("# 🧪 模型基准测试对比报告 (Model Benchmark v1)")
    lines.append(f"\n**生成时间**: {datetime.now().isoformat()}")
    lines.append("\n## 📊 综合对比表")
    lines.append("| 模型 | 总通过率 | 模型敏感通过率 | 系统通过率 | 备注 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")

    for res in all_results:
        model = res["model"]
        s = res["summary"]
        total_rate = f"{s['pass_rate']}%"
        ms_rate = f"{s['model_sensitive']['pass_rate']}%"
        sys_rate = f"{s['system']['pass_rate']}%"
        lines.append(f"| {model} | {total_rate} | {ms_rate} | {sys_rate} | - |")

    lines.append("\n## 📈 详细延迟与 Token 消耗")
    lines.append("| 模型 | 平均延迟 (ms) | 平均输出 Token |")
    lines.append("| :--- | :--- | :--- |")
    # 注意：延迟和 Token 数据保存在 eval_results_{model}.json 里，但 main.py 目前没有把 latency 返回到 /ask 接口体里。
    # 虽然我们存到了 session_manager，但 eval_runner 目前拿不到，这里先占位，提示后续优化方向。
    lines.append("| *待扩展* | *待扩展* | *待扩展* |")
    lines.append("\n> ⚠️ 提示：延迟与 Token 数据已记录在会话历史中，当前报告版本未从 /ask 接口透传，后续可升级 API 返回体包含 metrics。")

    with open("benchmark_comparison.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n📝 Markdown 报告已生成: benchmark_comparison.md")

# ========== 主入口 ==========
if __name__ == "__main__":
    # 快速路由测试（不发起网络请求）
    print(get_model_config("qwen-plus"))        # 预期: ('dashscope', 'sk-...', None)
    print(get_model_config("deepseek-v4-flash"))  # 预期: ('openai_compatible', 'sk-...', 'https://api.deepseek.com/v1')
    print(get_model_config("qwen3.8:27b"))       # 预期: ('openai_compatible', 'ollama', 'http://localhost:11434/v1')
    
    # 确认无误后，可以注释掉这几行，再跑真正的 Benchmark
    # 或者保留，不影响主流程


    # 加载 eval cases
    global eval_cases
    with open(EVAL_CASES_FILE, "r", encoding="utf-8") as f:
        eval_cases = json.load(f)

    all_model_results = []
    for model in MODELS_TO_TEST:
        # 判断一下 provider，如果模型名包含 "gpt" 则自动切换 provider，否则默认 dashscope
        # 这里为了演示，只做简单判断，你可以手动调整
        result = run_single_model_eval(model)
        all_model_results.append(result)

    # 生成对比报告
    generate_markdown_report(all_model_results)

    print("\n===== 🎉 全部模型基准测试完成 =====")
    for res in all_model_results:
        s = res["summary"]
        print(f"  {res['model']}: 总通过 {s['passed']}/{s['total']} ({s['pass_rate']}%), 模型敏感 {s['model_sensitive']['passed']}/{s['model_sensitive']['total']} ({s['model_sensitive']['pass_rate']}%)")