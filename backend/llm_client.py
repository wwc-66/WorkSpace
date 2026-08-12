import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self):
        self.default_api_key = os.getenv("DASHSCOPE_API_KEY")
        self.default_model = os.getenv("LLM_MODEL", "qwen-plus")
        self.default_provider = os.getenv("LLM_PROVIDER", "dashscope")  # 新增：默认 provider
        self.default_base_url = os.getenv("LLM_BASE_URL", None)  # 新增：自定义 API 地址

    def generate(self, prompt: str, api_key: str = None, model: str = None, provider: str = None, base_url: str = None) -> str:
        _api_key = api_key or self.default_api_key
        _model = model or self.default_model
        _provider = provider or self.default_provider
        _base_url = base_url or self.default_base_url

        if _provider == "dashscope":
            return self._call_dashscope(prompt, _api_key, _model)
        elif _provider == "openai_compatible":
            return self._call_openai_compatible(prompt, _api_key, _model, _base_url)
        else:
            raise ValueError(f"不支持的 provider: {_provider}")

    def _call_dashscope(self, prompt: str, api_key: str, model: str) -> str:
        from dashscope import Generation
        response = Generation.call(
            model=model,
            prompt=prompt,
            api_key=api_key
        )
        return response.output.text

    def _call_openai_compatible(self, prompt: str, api_key: str, model: str, base_url: str = None) -> str:
        import openai
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1"
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    # 保留 generate_with_messages 的多轮对话版本，类似修改
    def generate_with_messages(self, messages: list[dict], api_key: str = None, model: str = None, provider: str = None, base_url: str = None) -> str:
        _api_key = api_key or self.default_api_key
        _model = model or self.default_model
        _provider = provider or self.default_provider
        _base_url = base_url or self.default_base_url

        if _provider == "dashscope":
            return self._call_dashscope_messages(messages, _api_key, _model)
        elif _provider == "openai_compatible":
            return self._call_openai_compatible_messages(messages, _api_key, _model, _base_url)
        else:
            raise ValueError(f"不支持的 provider: {_provider}")

    def _call_dashscope_messages(self, messages: list[dict], api_key: str, model: str) -> str:
        from dashscope import Generation
        response = Generation.call(
            model=model,
            messages=messages,
            api_key=api_key
        )
        return response.output.text

    def _call_openai_compatible_messages(self, messages: list[dict], api_key: str, model: str, base_url: str = None) -> str:
        import openai
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1"
        )
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content