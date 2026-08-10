from fastapi import FastAPI
from pydantic import BaseModel
from backend.llm_client import LLMClient
from backend.vector_store import VectorStore
from backend.document_processor import read_txt, chunk_text
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Workspace AI Core")

class GenerateRequest(BaseModel):
    prompt: str

class AskRequest(BaseModel):
    question: str

api_key = os.getenv("DASHSCOPE_API_KEY")
model = "qwen-plus"

llm_client = LLMClient(api_key=api_key, model=model)

# ===== 初始化向量存储 =====
# 读取测试文档并切分
# 替换原来直接写 chunk_size=500, overlap=50 的地方
chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
overlap = int(os.getenv("CHUNK_OVERLAP", "50"))
doc_path = os.getenv("DOCUMENT_PATH", "test_data/sample.txt")

# 读取文档时使用 doc_path
doc_content = read_txt(doc_path)
chunks = chunk_text(doc_content, chunk_size=chunk_size, overlap=overlap)
logger.info(f"已加载文档: {doc_path}, 共 {len(doc_content)} 字符")
logger.info(f"切分为 {len(chunks)} 个块")

vector_store = VectorStore(api_key=api_key)
vector_store.add_chunks(chunks)
print(f"Workspace 已加载 {len(chunks)} 个文档块")
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate(req: GenerateRequest):
    response = llm_client.generate(req.prompt)
    return {"response": response}

@app.post("/ask")
def ask(req: AskRequest):
    # 1. 检查是否有文档
    if len(vector_store.chunks) == 0:
        return {'error': '请先上传文档'}
    
    # 2. 检索相关文档块
    results = vector_store.search(req.question, top_k=3)
    logger.info(f"检索到 {len(results)} 个相关块")

    # 3. 检查检索结果的相关度是否足够（阈值设为0.7）
    if results and results[0][1] < 0.7:
        return {'answer': '未找到足够相关的信息，请尝试换一种问法或上传更相关的文档。'}
    
    # 4. 构造 Prompt
    context = "\n\n".join([chunk for chunk, _ in results])
    prompt = f"""请基于以下资料回答用户的问题。如果资料中没有相关信息，请如实告知。
                资料：{context}

                用户问题：{req.question}

                请用简洁、准确的语言回答。"""
    
    # 5. 调用 LLM （带错误处理）
    try:
        response = llm_client.generate(prompt)
        logger.info(f"生成回答，长度 {len(response)} 字符")
    except Exception as e:
        return {'error': f'模型调用失败: {str(e)}'}
    
    return {
        "answer": response,
        "sources": [chunk[:100] + "..." for chunk, _ in results]  # 附上来源摘要
    }