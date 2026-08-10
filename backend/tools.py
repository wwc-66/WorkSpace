import os
from backend.llm_client import LLMClient
from backend.vector_store import VectorStore
from backend.document_processor import read_txt, chunk_text
from dotenv import load_dotenv

load_dotenv()

# 初始化 LLM Client
api_key = os.getenv("DASHSCOPE_API_KEY")
model = os.getenv("LLM_MODEL", "qwen-plus")
llm_client = LLMClient(api_key=api_key, model=model)

# 初始化 Vector Store（使用你已有的文档）
doc_path = os.getenv("DOCUMENT_PATH", "test_data/sample.txt")
doc_content = read_txt(doc_path)
chunks = chunk_text(doc_content, chunk_size=500, overlap=50)
vector_store = VectorStore(api_key=api_key)
vector_store.add_chunks(chunks)

def read_file(path: str) -> str:
    """读取文件内容。如果文件不存在，尝试在 test_data/ 目录下查找"""
    # 先尝试原路径
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    
    # 如果原路径不存在，尝试在 test_data/ 下拼接
    alt_path = os.path.join("test_data", path)
    if os.path.exists(alt_path):
        with open(alt_path, "r", encoding="utf-8") as f:
            return f.read()
    
    # 如果都不存在，抛出明确的错误
    raise FileNotFoundError(f"文件不存在: {path}（已尝试在 test_data/ 下查找）")

def write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def llm_generate(prompt: str) -> str:
    return llm_client.generate(prompt)

def search_knowledge(query: str, top_k: int = 3) -> list[str]:
    results = vector_store.search(query, top_k=top_k)
    return [chunk for chunk, _ in results]