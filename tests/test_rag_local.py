import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.vector_store import VectorStore
from backend.document_processor import chunk_text, read_directory
from backend.main import extract_source  # 如果你已经把它抽到单独模块，就从那里导入

import requests
import json

# 假设后端正在运行
BASE_URL = "http://127.0.0.1:8000"

# 准备测试数据
print("加载向量存储...")
api_key = os.getenv("DASHSCOPE_API_KEY")
vector_store = VectorStore(api_key=api_key)

# 加载文档（假设已经提前存入 rag_data）
doc_path = os.getenv("DOCUMENT_PATH", "rag_data")
documents = read_directory(doc_path)

all_chunks = []
for doc in documents:
    chunks = chunk_text(doc["content"], chunk_size=500, overlap=50)
    for chunk in chunks:
        all_chunks.append(f"[来源: {doc['filename']}]\n{chunk}")

vector_store.add_chunks(all_chunks)

# 测试问题列表
test_questions = [
    # RAG Case
    {"question": "Orion项目什么时候正式发布？", "expected": "2026年3月17日"},
    {"question": "哪个项目使用Cedar作为存储引擎？", "expected": "Orion"},
    {"question": "Atlas数据处理平台由哪个团队负责？", "expected": "Vega"},
    {"question": "Bluebell多久进行一次完整备份？", "expected": "每天一次，凌晨2:30"},
    {"question": "Orion项目的年度利润是多少？", "expected": "信息不足"},
]

for q in test_questions:
    try:
        resp = requests.post("http://127.0.0.1:8000/ask", json={"question": q["question"]})
        data = resp.json()
        print(f"✅ {q['question'][:20]}... -> {data.get('answer', '')[:50]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

for test_question in test_questions:
    print(f"\n测试问题: {test_question['question']}")

    results = vector_store.search(test_question['question'], top_k=3)
    print(f"\n检索到 {len(results)} 个结果:")

    for i, (chunk, score) in enumerate(results):
        print(f"\n--- 结果 {i+1} (相似度: {score:.4f}) ---")
        print(f"来源: {extract_source(chunk)}")
        print(f"内容: {chunk[:200]}...")