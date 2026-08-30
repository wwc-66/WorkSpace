#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import time
import requests
from datetime import datetime
from typing import Dict, List, Any

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ========== 配置 ==========
BASE_URL = "http://127.0.0.1:8000"
EVAL_CASES_FILE = "eval_cases.json"
OUTPUT_FILE = "eval_results.json"

# ========== 读取 eval cases ==========
with open(EVAL_CASES_FILE, "r", encoding="utf-8") as f:
    eval_cases = json.load(f)

# ========== 工具函数 ==========
def call_ask(question: str, session_id: str = None) -> Dict[str, Any]:
    """调用 /ask 接口"""
    payload = {"question": question}
    if session_id:
        payload["session_id"] = session_id
    try:
        resp = requests.post(f"{BASE_URL}/ask", json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "answer": f"请求失败: {e}"}

def call_generate(prompt: str, session_id: str = None) -> Dict[str, Any]:
    """调用 /generate 接口"""
    payload = {"prompt": prompt}
    if session_id:
        payload["session_id"] = session_id
    try:
        resp = requests.post(f"{BASE_URL}/generate", json=payload, timeout=30)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "response": f"请求失败: {e}"}

def check_exact_match(actual: str, expected: str) -> bool:
    """精确匹配，自动剥离对话中的常见前缀/后缀"""
    actual = actual.strip()
    expected = expected.strip()
    # 直接匹配
    if actual == expected:
        return True
    # 如果 expected 是短字符串（如测试代码），检查 actual 是否包含它
    if len(expected) <= 20 and expected in actual:
        return True
    return False

def check_exact_count(actual: str, expected_count: int) -> bool:
    """检查是否包含指定数量的要点（按换行或序号分割）"""
    import re
    # 按换行、序号等分割
    items = re.split(r'\n\s*|•\s*|\d+\.\s*', actual)
    items = [i.strip() for i in items if i.strip()]
    return len(items) == expected_count

def check_json_match(actual: str, expected: str) -> bool:
    """检查是否匹配 JSON 结构（忽略格式差异）"""
    try:
        actual_json = json.loads(actual)
        expected_json = json.loads(expected)
        return actual_json == expected_json
    except:
        return False

def check_answer_accuracy(actual: str, expected: str) -> bool:
    """检查答案是否包含预期内容，忽略格式和修饰词差异"""
    import re
    
    actual = actual.strip()
    expected = expected.strip()
    
    # 1. 直接包含检查（归一化后）
    def normalize(text):
        # 去除多余空格、标点
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('，', ',').replace('。', '.').replace('、', ',').replace('：', ':')
        # 去除开头结尾的标点
        text = text.strip('，。.,:：')
        return text
    
    actual_norm = normalize(actual)
    expected_norm = normalize(expected)
    
    # 如果归一化后直接包含或相等，通过
    if expected_norm in actual_norm or actual_norm == expected_norm:
        return True
    
    # 2. 提取核心关键词（去除常见修饰词）
    def extract_key(text):
        # 去除常见修饰词
        text = re.sub(r'大约|约|左右|大概|可能|也许|主要|正式', '', text)
        # 去除“每天一次”中的“一次”
        text = re.sub(r'一次', '', text)
        return text
    
    expected_core = extract_key(expected_norm)
    actual_core = extract_key(actual_norm)
    
    # 如果核心关键词在回答中出现，通过
    if expected_core and expected_core in actual_core:
        return True
    
    # 3. 对于“信息不足”类回答，检查是否包含“无法”“没有”“找不到”等否定词
    if "信息不足" in expected:
        negative_words = ["无法", "没有", "找不到", "不确定", "不存在", "未提供", "未找到"]
        if any(word in actual for word in negative_words):
            return True
    
    return False

def check_retrieval_hit(actual: dict, expected_file: str) -> bool:
    """检查检索结果中是否包含预期的来源文件"""
    sources = actual.get("sources", [])
    for source in sources:
        if expected_file in source:
            return True
    # 也检查 answer 中是否包含来源信息
    answer = actual.get("answer", "")
    if expected_file in answer:
        return True
    return False

# ========== 运行测试 ==========
def run_eval():
    results = {
        "timestamp": datetime.now().isoformat(),
        "summary": {},
        "details": {}
    }

    # 临时 session_id 用于会话测试
    session_id = None

    # ---------- 1. Conversation Context ----------
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

        # 执行多轮对话
        last_response = ""
        for step in case["steps"]:
            if step["role"] == "user":
                # 发送用户消息
                resp = call_generate(step["content"], session_id=session_id)
                if "session_id" in resp:
                    session_id = resp["session_id"]
                last_response = resp.get("response", "")
                case_result["actual"] = last_response
            # assistant 的 content 留空，我们只关心用户消息后的响应

        # 最后一轮响应就是我们要检查的
        if case["metric"] == "exact_match":
            case_result["passed"] = check_exact_match(last_response, case["expected"])

        conv_results.append(case_result)

    results["details"]["conversation_context"] = conv_results

    # ---------- 2. RAG ----------
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

        resp = call_ask(case["question"])
        case_result["actual_answer"] = resp.get("answer", "")
        case_result["sources"] = resp.get("sources", [])

        if "expected_evidence_file" in case and case["expected_evidence_file"]:
            case_result["retrieval_hit"] = check_retrieval_hit(resp, case["expected_evidence_file"])

        case_result["answer_accuracy"] = check_answer_accuracy(
            case_result["actual_answer"],
            case_result["expected_answer"]
        )

        case_result["passed"] = case_result["retrieval_hit"] and case_result["answer_accuracy"]

        rag_results.append(case_result)

    results["details"]["rag"] = rag_results

    # ---------- 3. Instruction Following ----------
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

        resp = call_generate(case["prompt"])
        actual = resp.get("response", "")
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

    # ---------- 4. 汇总 ----------
    total = 0
    passed = 0
    for category, items in results["details"].items():
        for item in items:
            total += 1
            if item.get("passed", False):
                passed += 1

    results["summary"] = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total * 100, 2) if total > 0 else 0
    }

    # 写入结果文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n===== Eval 完成 =====")
    print(f"总计: {total} 个用例")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {results['summary']['pass_rate']}%")
    print(f"结果已保存到: {OUTPUT_FILE}")

    return results

if __name__ == "__main__":
    run_eval()