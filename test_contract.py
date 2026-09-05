# test_contract.py
# 这是一个“契约测试”，用于验证 LLMClient 的返回值结构是否符合 main.py 的预期
# 不发起真实网络请求，只做语法检查和属性验证

import sys
import os

# 把当前目录加入 Python 路径，确保能找到 backend 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_llm_response_contract():
    print("🧪 正在执行 MS-1 契约测试（无网络请求）...")
    
    # 1. 测试导入是否报错（检查语法和类定义）
    try:
        from backend.llm_client import LLMClient, LLMResponse
        print("✅ PASS: LLMClient 和 LLMResponse 导入成功")
    except Exception as e:
        print(f"❌ FAIL: 导入失败，请检查代码缩进或依赖包 - {e}")
        return False

    # 2. 测试 LLMResponse 数据类是否正常实例化（模拟真实返回数据）
    try:
        fake_result = LLMResponse(
            content="这是测试文本",
            model="test-model",
            provider="dashscope",
            latency_ms=123.45,
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            finish_reason="stop",
            error=None
        )
        # 核心验证：main.py 依赖的 .content 属性必须存在且是字符串
        assert hasattr(fake_result, "content"), ".content 属性缺失！"
        assert isinstance(fake_result.content, str), ".content 不是字符串类型！"
        assert fake_result.content == "这是测试文本", "content 值存储异常！"
        print("✅ PASS: LLMResponse 对象结构正确，.content 可正常访问")
    except Exception as e:
        print(f"❌ FAIL: LLMResponse 数据类异常 - {e}")
        return False

    # 3. 验证 LLMClient 的方法签名是否还在（只检查有没有这个方法，不真正调用）
    try:
        client = LLMClient()
        # 检查是否有 generate_with_messages 方法
        assert hasattr(client, "generate_with_messages"), "generate_with_messages 方法缺失！"
        # 这里只打印方法存在，不执行它（因为执行会触发网络请求）
        print("✅ PASS: generate_with_messages 方法存在")
    except Exception as e:
        print(f"❌ FAIL: LLMClient 实例化或方法检查失败 - {e}")
        return False

    print("\n🎉 所有契约测试通过！MS-1 代码无语法冲突，可以放心启动后端。")
    return True

if __name__ == "__main__":
    test_llm_response_contract()