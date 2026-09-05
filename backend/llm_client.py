import os
import requests
import json
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional
import time

load_dotenv()

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    latency_ms: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None

class LLMClient:
    def __init__(self):
        self.default_api_key = os.getenv("DASHSCOPE_API_KEY")
        self.default_model = os.getenv("LLM_MODEL", "qwen-plus")
        self.default_provider = os.getenv("LLM_PROVIDER", "dashscope")
        self.default_base_url = os.getenv("LLM_BASE_URL", None)

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
    def generate_with_messages(self, messages: list[dict], api_key: str = None, model: str = None, provider: str = None, base_url: str = None) -> LLMResponse:
        _api_key = api_key or self.default_api_key
        _model = model or self.default_model
        _provider = provider or self.default_provider
        _base_url = base_url or self.default_base_url

        # 在调用前，确保 messages 中包含 system 消息
        system_message = {"role": "system", "content": f"你是 {_model}，一个由用户配置的 AI 助手。"}
        # 只保留 role/content 字段，避免把存储的展示字段（model、sources 等）传给模型 API
        _messages = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages]
        # 如果 messages 中没有 system 消息，插入到开头
        if not _messages or _messages[0].get("role") != "system":
            _messages = [system_message] + _messages

        if _provider == "dashscope":
            return self._call_dashscope_messages(_messages, _api_key, _model)
        elif _provider == "openai_compatible":
            return self._call_openai_compatible_messages(_messages, _api_key, _model, _base_url)
        else:
            raise ValueError(f"不支持的 provider: {_provider}")

    def _call_dashscope_messages(self, messages: list[dict], api_key: str, model: str) -> LLMResponse:
        from dashscope import Generation
        start_time  = time.perf_counter()
        try:
            response = Generation.call(
                model=model,
                messages=messages,
                api_key=api_key
            )
            latency_ms = (time.perf_counter() - start_time) * 1000

            #提取token用量
            usage = getattr(response, 'usage', None)
            input_tokens = getattr(usage, 'input_tokens', None) if usage else None
            output_tokens = getattr(usage, 'output_tokens', None) if usage else None
            total_tokens = getattr(usage, 'total_tokens', None) if usage else None

            #提取 finish_reason
            finish_reason = None
            if hasattr(response, 'output') and hasattr(response.output, 'choices') and response.output.choices:
                finish_reason = response.output.choices[0].get('finish_reason', None)

            return LLMResponse(
                content=response.output.text,
                model=model,
                provider="dashscope",
                latency_ms=round(latency_ms, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider="dashscope",
                latency_ms=0,
                error=str(e)
            )

    def _call_openai_compatible_messages(self, messages: list[dict], api_key: str, model: str, base_url: str = None) -> LLMResponse:
        import openai
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1"
        )
        start_time = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content,
                model=model,
                provider="openai_compatible",
                latency_ms=round(latency_ms, 2),
                input_tokens=getattr(response.usage, 'prompt_tokens', None),
                output_tokens=getattr(response.usage, 'completion_tokens', None),
                total_tokens=getattr(response.usage, 'total_tokens', None),
                finish_reason=getattr(choice, 'finish_reason', None)
            )
        except Exception as e:
            return LLMResponse(
                content="",
                model=model,
                provider="openai_compatible",
                latency_ms=0,
                error=str(e)
            )