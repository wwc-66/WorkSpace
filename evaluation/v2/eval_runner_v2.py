# evaluation/v2/eval_runner_v2.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict, List, Any

# ============================================================
# 【路径自动修复】无论从哪里运行，都能找到项目根目录
# ============================================================
# 获取当前文件所在目录（evaluation/v2/）
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 项目根目录：往上两级（v2 -> evaluation -> 根目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
# 将项目根目录加入 Python 路径，确保能 import backend
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# 切换工作目录到项目根目录，保证相对路径（如 .env）能正常读取
os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

# ============================================================
# 配置（所有路径相对于项目根目录）
# ============================================================
BASE_URL = "http://127.0.0.1:8000"
EVAL_CASES_FILE = os.path.join(CURRENT_DIR, "eval_cases_v2.json")
OUTPUT_DIR = os.path.join(CURRENT_DIR, "results")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 导入模型路由配置（沿用之前 v1 的 get_model_config）
from evaluation.v1.eval_runner_v1 import MODELS_TO_TEST, get_model_config, BASE_URL

# ============================================================
# 模型池
# ============================================================
MODELS_TO_TEST = ["deepseek-flash"]

# ============================================================
# 工具函数（call_ask / call_generate）
# ============================================================
def call_ask(question: str, session_id: str = None, model: str = None) -> Dict[str, Any]:
    payload = {"question": question}
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
        resp = requests.post(f"{BASE_URL}/ask", json=payload, timeout=60)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "answer": f"请求失败: {e}"}

def call_generate(prompt: str, session_id: str = None, model: str = None) -> Dict[str, Any]:
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

# ============================================================
# 判定函数（与 V1 保持一致，可复用）
# ============================================================
def check_answer_accuracy(actual: str, expected: str) -> bool:
    import re
    actual = actual.strip()
    expected = expected.strip()
    def normalize(text):
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('，', ',').replace('。', '.').replace('、', ',').replace('：', ':')
        return text.strip('，。.,:：')
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

# ============================================================
# 单模型运行函数（适配 V2 的 5 类结构）
# ============================================================
def run_single_model_eval(model_name: str, eval_cases: dict) -> Dict[str, Any]:
    print(f"\n正在测试 V2 模型: {model_name}")
    results = {
        "model": model_name,
        "version": "v2",
        "timestamp": datetime.now().isoformat(),
        "details": {},
        "summary": {}
    }

    total = 0
    passed = 0
    detail_summary = {}

    # 遍历 V2 的 5 个类别
    for category, cases in eval_cases.items():
        category_results = []
        for case in cases:
            case_id = case["id"]
            prompt = case["prompt"]
            expected = case["expected"]
            metric = case.get("metric", "human_review")
            
            # 根据类别判断用 ask 还是 generate（目前 V2 全部是单轮，我们统一用 generate，但 Evidence 和 RAG 类建议用 ask）
            # 为了通用，判断 prompt 里是否包含“根据上面给的文章”这类关键词，简单识别
            if "根据上面给的文章" in prompt or "根据文章" in prompt:
                # 这类通常需要 RAG 检索，走 /ask
                resp = call_ask(prompt, session_id=None, model=model_name)
                actual = resp.get("answer", "")
            else:
                # 纯指令遵循，走 /generate
                resp = call_generate(prompt, session_id=None, model=model_name)
                actual = resp.get("response", "")
            
            # 简易判分（V2 主要依赖人工审核，但我们先粗略给一个基于 key 的 flag）
            # 这里我们只记录 actual，不自动判 Pass/Fail，由你在 review 时对照 expected 人工判断
            # 但为了方便，我们暂时标记为 "pending_review"
            case_result = {
                "id": case_id,
                "name": case["name"],
                "difficulty": case.get("difficulty", 0),
                "actual": actual,
                "expected_checklist": expected,
                "passed": None,  # 人工填
                "latency_ms": resp.get("latency_ms", -1)
            }
            category_results.append(case_result)
            total += 1
        
        results["details"][category] = category_results
        detail_summary[category] = {"total": len(category_results), "passed": 0}  # 占位

    results["summary"] = {
        "total": total,
        "passed": None,  # 人工填写
        "pass_rate": None,
        "categories": detail_summary
    }

    # 保存该模型的详细 JSON（文件名包含 _v2）
    safe_model_name = model_name.replace(":", "_").replace("/", "_")
    output_file = os.path.join(OUTPUT_DIR, f"eval_results_{safe_model_name}_v2.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"   {model_name} V2 测试完成，结果已保存至 {output_file}")
    return results

# ============================================================
# 生成 V2 对比报告
# ============================================================
def generate_v2_markdown_report(all_results: List[Dict[str, Any]]):
    lines = []
    lines.append("# V2 模型基准测试对比报告 (Model Benchmark v2)")
    lines.append(f"\n**生成时间**: {datetime.now().isoformat()}")
    lines.append("\n## 综合对比表")
    lines.append("| 模型 | 总 Case 数 | 备注 |")
    lines.append("| :--- | :--- | :--- |")
    for res in all_results:
        model = res["model"]
        total = res["summary"]["total"]
        lines.append(f"| {model} | {total} | 需人工审核 expected_checklist |")
    lines.append("\n> V2 评估采用 `human_review` 指标，请打开各模型的 JSON 文件，对照 `expected_checklist` 逐项审核。")

    output_file = os.path.join(OUTPUT_DIR, "benchmark_comparison_v2.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nV2 Markdown 报告已生成: {output_file}")

# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    # 加载 V2 eval cases
    with open(EVAL_CASES_FILE, "r", encoding="utf-8") as f:
        eval_cases = json.load(f)

    all_model_results = []
    for model in MODELS_TO_TEST:
        result = run_single_model_eval(model, eval_cases)
        all_model_results.append(result)

    generate_v2_markdown_report(all_model_results)

    print("\n===== V2 全部模型基准测试完成 =====")
    for res in all_model_results:
        print(f"  {res['model']}: 共 {res['summary']['total']} 个 Case，结果已保存。")