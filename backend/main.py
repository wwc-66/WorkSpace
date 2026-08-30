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
from backend.session_manager import SessionManager

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
    session_id: str = None
    api_key: str = None
    model: str = None
    provider: str = None
    base_url: str = None

class AskRequest(BaseModel):
    question: str
    session_id: str = None
    api_key: str = None
    model: str = None
    provider: str = None
    base_url: str = None

def extract_source(chunk: str) -> str:
    """从 chunk 文本中提取来源文件名"""
    if chunk.startswith("[来源:"):
        end = chunk.find("]")
        if end != -1:
            return chunk[4:end].strip()
    return "未知来源"

api_key = os.getenv("DASHSCOPE_API_KEY")
model = "qwen-plus"

llm_client = LLMClient()
session_manager = SessionManager()

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
    # 1. 获取或创建会话
    session_id = session_manager.get_or_create_session(req.session_id)[0]

    # 2. 将用户消息加入会话历史（记录当时使用的模型名）
    session_manager.add_message(session_id, "user", req.prompt, extra={"model": req.model})

    # 3. 获取完整上下文
    context = session_manager.get_full_context(session_id)

    # 4. 调用模型
    response = llm_client.generate_with_messages(
        messages=context,
        api_key=req.api_key,
        model=req.model,
        provider=req.provider,
        base_url=req.base_url
    )

    # 5. 将助手回复加入会话历史（记录当时使用的模型名）
    session_manager.add_message(session_id, "assistant", response, extra={"model": req.model})

    return {
        "response": response,
        "session_id": session_id
    }

@app.post("/ask")
def ask(req: AskRequest):
    # 1. 检查文档
    if len(vector_store.chunks) == 0:
        return {"error": "请先上传文档"}

    # 2. 检索相关文档块
    results = vector_store.search(req.question, top_k=3)
    #增加日志记录功能用于开发阶段的evaluation和retrieval分析
    import json
    from datetime import datetime

    def log_rag_query(question, results, filtered_results, answer, session_id):
        """记录一次 RAG 查询的完整信息"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "question": question,
            "top_k_results": [
                {
                    "chunk": chunk,
                    "score": score,
                    "source": extract_source(chunk)
                }
                for chunk, score in results
            ],
            "filtered_results": [
                {
                    "chunk": chunk,
                    "score": score,
                    "source": extract_source(chunk)
                }
                for chunk, score in filtered_results
            ],
            "final_answer": answer
        }
        with open("logs/rag_eval.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    # 在检索完成后，生成 sources
    sources = [chunk[:100] + "..." for chunk, _ in results]
    if results and results[0][1] < 0.7:
        # 只取第一个
        results = results[:1]
        #不直接以硬编码的形式返回错误，继续走后续流程，让模型判断，同时将sources设为相关度分数小于阈值但最高的文档
        sources = [chunk[:100] + "..." for chunk, _ in results]

    # 3. 构造上下文
    context = "\n\n".join([chunk for chunk, _ in results])

    # 4. 获取或创建会话
    session_id = session_manager.get_or_create_session(req.session_id)[0]

    # 5. 将用户消息（含检索上下文）加入会话历史
    # 注意：这里把检索结果作为用户消息的一部分存入，让模型能回顾
    session_manager.add_message(session_id, "user", f"[资料参考]\n{context}\n\n[用户问题]\n{req.question}", extra={"model": req.model})

    # 6. 获取完整上下文
    full_context = session_manager.get_full_context(session_id)

    # 7. 调用模型
    try:
        response = llm_client.generate_with_messages(
            messages=full_context,
            api_key=req.api_key,
            model=req.model,
            provider=req.provider,
            base_url=req.base_url
        )
    except Exception as e:
        # 会话已创建，返回 session_id 让前端保持同一会话
        return {"error": f"模型调用失败: {str(e)}", "session_id": session_id}

    # 8. 将助手回复加入会话历史（记录模型名与参考来源）
    session_manager.add_message(
        session_id,
        "assistant",
        response,
        extra={"sources": sources, "model": req.model}
    )

    # Evaluation阶段专用：生成日志
    threshold = 0.7  # 与现有阈值保持一致
    filtered_results = [(chunk, score) for chunk, score in results if score >= threshold]

    log_rag_query(
        question=req.question,
        results=results,
        filtered_results=filtered_results,
        answer=response,
        session_id=session_id
    )

    return {
        "answer": response,
        "session_id": session_id,
        "sources": sources
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

@app.get("/sessions")
def get_sessions():
    """获取所有会话的摘要列表（用于前端显示历史对话列表）"""
    return session_manager.get_all_sessions()

@app.get("/sessions/{session_id}")
def get_session_messages(session_id: str):
    """获取指定会话的完整消息历史（用于前端切换会话/刷新恢复）"""
    return {
        "session_id": session_id,
        "messages": session_manager.get_full_context(session_id)
    }

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """删除指定会话"""
    session_manager.delete_session(session_id)
    return {"status": "ok"}

@app.delete("/sessions")
def clear_all_sessions():
    """清空所有会话"""
    # 遍历并删除所有会话
    sessions = session_manager.get_all_sessions()
    for sid in sessions.keys():
        session_manager.delete_session(sid)
    return {"status": "ok"}