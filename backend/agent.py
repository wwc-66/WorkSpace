import json
from backend.tool_registry import TOOLS, execute_tool_call, get_tools_description
from backend.llm_client import LLMClient
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")
model = os.getenv("LLM_MODEL", "qwen-plus")
llm_client = LLMClient(api_key=api_key, model=model)

def get_system_prompt() -> str:
    """生成包含工具描述的系统提示词"""
    tools_desc = get_tools_description()
    return f"""你是一个可以帮助用户执行任务的 AI 助手。你可以调用以下工具来完成用户请求：

{tools_desc}

如果用户的任务需要调用工具，请返回一个 JSON 对象，格式如下：
{{
    "tool": "工具名称",
    "arguments": {{
        "参数名1": "参数值1",
        "参数名2": "参数值2"
    }}
}}

如果不需要调用工具，直接返回普通文本回答。

重要规则：
- 每次只调用一个工具
- 调用完工具后，根据返回结果决定是否继续调用其他工具
- 如果工具返回的结果已经足够回答用户问题，直接输出最终回答
- 如果任务已全部完成，输出最终回答，不要再调用工具
- 最多调用 5 次工具，超过后自动停止
"""

def run_agent(user_input: str) -> str:
    """
    多轮 Agent：循环调用工具，直到任务完成或达到最大轮数
    """
    max_iterations = 5  # 防止无限循环
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_input}
    ]
    
    for _ in range(max_iterations):
        # 调用模型
        response = llm_client.generate_with_messages(messages)
        messages.append({"role": "assistant", "content": response})
        
        # 尝试解析工具调用
        try:
            tool_call = json.loads(response)
            if "tool" in tool_call and "arguments" in tool_call:
                # 执行工具
                result = execute_tool_call(tool_call["tool"], tool_call["arguments"])
                messages.append({"role": "tool", "content": json.dumps(result)})
                continue  # 继续循环，让模型决定下一步
        except json.JSONDecodeError:
            # 不是 JSON，当作最终回答返回
            return response
    
    return "任务未完成，已达到最大尝试次数"