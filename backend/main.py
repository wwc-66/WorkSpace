from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import UploadFile, File
import shutil
from pydantic import BaseModel
from backend.llm_client import LLMClient
from backend.vector_store import VectorStore
from backend.document_processor import read_txt, chunk_text, read_directory
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Workspace AI Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    prompt: str
    api_key: str = None
    model: str = None
    provider: str = None
    base_url: str = None

class AskRequest(BaseModel):
    question: str
    api_key: str = None
    model: str = None
    provider: str = None
    base_url: str = None

api_key = os.getenv("DASHSCOPE_API_KEY")
model = "qwen-plus"

llm_client = LLMClient()

# ===== 初始化向量存储 =====
# 读取测试文档并切分
# 替换原来直接写 chunk_size=500, overlap=50 的地方
chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
overlap = int(os.getenv("CHUNK_OVERLAP", "50"))

doc_path = os.getenv("DOCUMENT_PATH", "rag_data")
documents = read_directory(doc_path)

all_chunks = []
total_chars = 0
for doc in documents:
    chunks = chunk_text(doc["content"], chunk_size=chunk_size, overlap=overlap)
    total_chars += len(doc["content"])
    # 给每个 chunk 打上来源文件名标签
    for chunk in chunks:
        all_chunks.append(f"[来源: {doc['filename']}]\n{chunk}")
    logger.info(f"已加载文档: {doc['filename']}, 共 {len(doc['content'])} 字符, 切分为 {len(chunks)} 个块")

logger.info(f"全部文档: 共 {len(documents)} 个文件, {total_chars} 字符, 总计 {len(all_chunks)} 个块")
vector_store = VectorStore(api_key=api_key)
vector_store.add_chunks(all_chunks)
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
def generate(req: GenerateRequest):
    response = llm_client.generate(
        prompt=req.prompt,
        api_key=req.api_key,
        model=req.model,
        provider=req.provider,
        base_url=req.base_url
    )
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
        response = llm_client.generate(
            prompt=prompt,
            api_key=req.api_key,
            model=req.model,
            provider=req.provider,
            base_url=req.base_url
        )
        logger.info(f"生成回答，长度 {len(response)} 字符")
    except Exception as e:
        return {'error': f'模型调用失败: {str(e)}'}
    
    return {
        "answer": response,
        "sources": [chunk[:100] + "..." for chunk, _ in results]  # 附上来源摘要
    }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 确保目录存在
    os.makedirs("rag_data", exist_ok=True)
    file_path = os.path.join("rag_data", file.filename)

    # 保存文件
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 读取内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 切分并向量化
    from backend.document_processor import chunk_text
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    tagged_chunks = [f"[来源: {file.filename}]\n{chunk}" for chunk in chunks]
    vector_store.add_chunks(tagged_chunks)

    return {"status": "ok", "filename": file.filename, "chunks": len(chunks)}