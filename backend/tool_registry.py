from backend.tools import read_file, write_file, llm_generate, search_knowledge

# 工具注册表
TOOLS = [
    {
        "name": "read_file",
        "description": "读取指定路径的文件内容，返回文件内容字符串。如果文件不存在则报错。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"}
            },
            "required": ["path"]
        },
        "function": read_file
    },
    {
        "name": "write_file",
        "description": "将内容写入指定路径的文件。如果文件已存在则覆盖。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
                "content": {"type": "string", "description": "要写入的内容"}
            },
            "required": ["path", "content"]
        },
        "function": write_file
    },
    {
        "name": "llm_generate",
        "description": "调用大语言模型生成回答。适用于文本生成、总结、翻译等任务。",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "输入给模型的提示词"}
            },
            "required": ["prompt"]
        },
        "function": llm_generate
    },
    {
        "name": "search_knowledge",
        "description": "在向量知识库中搜索与查询最相关的文档片段。适用于需要从已有资料中查找信息的问题。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索查询语句"},
                "top_k": {"type": "integer", "description": "返回结果数量，默认为 3"}
            },
            "required": ["query"]
        },
        "function": search_knowledge
    }
]

def get_tools_description() -> str:
    lines = []
    for tool in TOOLS:
        lines.append(f"- {tool['name']}: {tool['description']}")
        lines.append(f"  参数: {tool['parameters']}")
    return "\n".join(lines)

def execute_tool_call(tool_name: str, arguments: dict):
    """根据工具名称和参数执行对应的函数"""
    for tool in TOOLS:
        if tool["name"] == tool_name:
            return tool["function"](**arguments)
    raise ValueError(f"未找到工具: {tool_name}")