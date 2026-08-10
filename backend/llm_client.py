from dashscope import Generation

class LLMClient:
    def __init__(self, api_key: str, model:str):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str):
        #1.调用dashscope的Generation.call方法
        #Generation.call是dashscope提供的同步调用接口
        #它接收一个prompt和model，返回一个响应对象
        response = Generation.call(
            model = self.model,     #指定使用哪个模型
            prompt = prompt,        #用户输入的文本（提示词）
            api_key = self.api_key  #用户的API Key
        )

        #2.从响应对象中提取文本
        #response.output.text是模型返回的文本内容
        #Generation返回的响应结构是固定的：output下有一个text字段
        return response.output.text

    def generate_with_messages(self, messages: list[dict]) -> str:
        """支持多轮对话的生成方法"""
        response = Generation.call(
            model=self.model,
            messages=messages,
            api_key=self.api_key
        )
        return response.output.text