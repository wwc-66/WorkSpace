def _replace_variables(text: str, context: dict) -> str:
    """将字符串中的 $变量名 替换为上下文中的实际值"""
    result = text
    for key, value in context.items():
        placeholder = f"${key}"
        if placeholder in result:
            result = result.replace(placeholder, str(value))
    return result

def execute_workflow(steps: list[dict]) -> dict:
    """
    执行一个工作流，返回最终上下文
    
    steps: 步骤列表，每个步骤包含：
        - name: 步骤名称
        - function: 要调用的函数
        - args: 参数字典
        - output_key: 输出结果的键名
    """
    context = {}
    
    for step in steps:
        # 1. 解析参数
        parsed_args = {}
        for key, value in step['args'].items():
            #检验参数是否为“$”开头的字符串，如果是，则从上下文中获取对应的值
            if isinstance(value, str):
                # 先检查是否以 $ 开头（整个值是占位符）
                if value.startswith('$'):
                    var_name = value[1:]
                    parsed_args[key] = context.get(var_name, value)
                else:
                    # 否则替换字符串内部的 $变量
                    parsed_args[key] = _replace_variables(value, context)
            else:
                parsed_args[key] = value
        
        # 2. 调用函数
        result = step['function'](**parsed_args)
        
        # 3. 存储结果
        context[step['output_key']] = result

    return context