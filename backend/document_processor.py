def read_txt(file_path: str) -> str:
    """读取txt文件内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def chunk_text(text:str, chunk_size: int = 500, overlap:int = 50) -> list[str]:
    """
    将长文本切分成多个小块（chunk）
    - chunk_size：每块的最大字符数
    - overlap：块与块之间的重叠字符数，用于保持上下文连贯
    """
    #定义变量
    chunks = []
    start = 0
    text_length = len(text)
    #切分文本
    while start < text_length:
        #计算当前chunk的结束位置
        end = start + chunk_size
        #如果end超过文本长度，则切分到最后一块文本，直接取start直到末尾的文本
        if end >= text_length:
            chunks.append(text[start:])
        #将当前chunk添加到chunks
        chunks.append(text[start:end])
        #更新start位置，考虑重叠部分（overlap）
        start = end - overlap
    
    return chunks