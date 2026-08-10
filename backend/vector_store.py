import os
import numpy as np
from dashscope import TextEmbedding

class VectorStore:
    def __init__(self, api_key:str, model:str = "text-embedding-v3"):
        self.api_key = api_key
        self.model = model
        #存储原始文本块
        self.chunks = []
        #存储对应向量
        self.vectors = []

    def add_chunks(self, texts:list[str]) -> None:
        '''将多个文本块向量化并存入内存'''
        #调用 Embedding API（一次可传入多个文本）
        response = TextEmbedding.call(
            model = self.model,
            input = texts,
            api_key = self.api_key
        )

        #提取向量并存储
        for item in response['output']['embeddings']:
            index = item['text_index']
            vector = item['embedding']
            self.chunks.append(texts[index])
            self.vectors.append(vector)

        print(f"已存储{len(self.chunks)}个文本块")

    def search(self, query:str, top_k:int = 3) -> list[tuple[str, float]]:
        '''搜索与查询最相关的top_k个文本块，返回：[(文本块，相似度分数), ...]'''
        #1.把用户问题转成向量
        response = TextEmbedding.call(
            model = self.model,
            input = [query],
            api_key = self.api_key
        )
        query_vector = response['output']['embeddings'][0]['embedding']

        #2.计算余弦相似度
        similarities = []
        for vec in self.vectors:
            sim = self._cosine_similarity(query_vector, vec)
            similarities.append(sim)

        #3.按相似度排序，取top_k
        paired = list(zip(self.chunks, similarities))
        paired.sort(key=lambda x: x[1], reverse=True)
        return paired[:top_k]

    def _cosine_similarity(self, a:list[float], b:list[float]) -> float:
        '''计算两个向量的余弦相似度'''
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))