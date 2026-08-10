from backend.agent import run_agent

result = run_agent("读取 sample.txt，统计文件字数，然后保存到 word_count.txt")
print(result)