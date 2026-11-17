import json
import os
import re
from openai import OpenAI
import requests
from tavily import TavilyClient
import pdfplumber  # 【修改点】换用强大的 pdfplumber 解决中文乱码

# ==========================================
# 1. 配置密钥与环境变量
# ==========================================
# 请替换为你自己的 DeepSeek API Key
API_KEY = "sk-*************"

# DeepSeek 官方接口地址
BASE_URL = "https://api.deepseek.com"

# 模型名称
MODEL_ID = "deepseek-chat"

# 替换为你自己的 Tavily 真实密钥
TAVILY_API_KEY = "tvly-*********************"
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY


# ==========================================
# 2. 定义工具函数 (Tools)
# ==========================================
def parse_resume(file_path: str) -> str:
    """读取本地 PDF 简历，提取纯文本。"""
    try:
        # 清理路径中可能多余的引号
        file_path = file_path.strip('"').strip("'")

        # 【修改点】使用 pdfplumber 读取，完美支持中文
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # 截断一下，防止简历太长超出模型上下文限制
        if len(text) > 3000:
            text = text[:3000] + "\n...(文本过长已截断)"

        if not text.strip():
            return "错误: 成功打开PDF，但未提取到文本（可能是图片格式简历）。"

        return text
    except FileNotFoundError:
        return f"错误: 找不到文件 '{file_path}'。请检查路径是否正确。"
    except Exception as e:
        return f"错误:解析简历失败 - {e}"


def search_jobs(skills: str, city: str) -> str:
    """根据技能关键词和目标城市，搜索相关岗位信息。"""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key or api_key == "tvly-xxxxxxxxxxxxxx":
        return "错误:未配置真实的 TAVILY_API_KEY 环境变量。"

    try:
        tavily = TavilyClient(api_key=api_key)
        # 优化搜索词，加上 "招聘要求" 可以让大模型更好对比
        query = f"{city} 招聘 {skills} 算法工程师 岗位要求"
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", [])[:5]:  # 取前5条即可
            formatted_results.append(f"- {result['title']}: {result['content'][:300]}")

        if not formatted_results:
            return "抱歉，没有找到相关的岗位推荐。"

        return "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"错误:执行Tavily搜索时出现问题 - {e}"


# 将所有可用工具注册到字典中
available_tools = {
    "parse_resume": parse_resume,
    "search_jobs": search_jobs,
}

# ==========================================
# 3. 定义 ReAct 系统提示词 (System Prompt)
# ==========================================
AGENT_SYSTEM_PROMPT = """你是一个专业的简历匹配助手。你可以使用以下工具：

parse_resume(file_path="简历路径"): 读取并提取简历中的核心内容。
search_jobs(skills="技能关键词", city="目标城市"): 搜索当前市面上的岗位需求。

请遵循以下工作流程：
1. 先调用 parse_resume 读取简历，提取出该求职者的核心技能栈（用逗号分隔）。
2. 然后调用 search_jobs，根据提取出的技能和目标城市搜索岗位信息。
3. 最后，对比简历内容和搜索到的岗位要求，输出一份分析报告。

报告必须包含以下内容，并使用 Markdown 格式排版：
- 【简历技能摘要】
- 【匹配度打分】（0-100分，并给出理由）
- 【Top 3 匹配岗位】
- 【技能差距清单】
- 【提升建议】

请按照以下严格格式进行思考和回答：

Thought: 思考下一步要做什么
Action: 工具名称(参数名="值")  # 或 Finish[最终答案]
Observation: 工具调用的返回结果（此步骤由系统填充，你不需要生成）

当你准备好最终答案时，使用：
Action: Finish[你的最终报告]
"""


# ==========================================
# 4. 封装 LLM 客户端类
# ==========================================
class OpenAICompatibleClient:
    """兼容 OpenAI 1.0+ SDK 的 LLM 客户端类"""

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用 LLM API 生成回答"""
        print("正在调用大语言模型...")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, stream=False
            )
            answer = response.choices[0].message.content
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误:调用语言模型服务时出错，请检查API_KEY余额或网络。"


# ==========================================
# 5. 主程序与 ReAct 循环
# ==========================================
if __name__ == "__main__":
    # 初始化客户端
    llm = OpenAICompatibleClient(
        model=MODEL_ID, api_key=API_KEY, base_url=BASE_URL
    )

    # 【修改点】确保文件名完全一致（注意你文件名里的空格）
    resume_path = r"C:\Users\10782\Desktop\简历\ltrcv .pdf"
    target_city = "北京"  # 或者 "上海"、"深圳"

    # 构造用户输入
    user_prompt = f"请帮我解析我的简历：{resume_path}，提取技能后，去搜索一下{target_city}的相关岗位，然后给我一份详细的匹配分析报告。"
    prompt_history = [f"用户请求: {user_prompt}"]

    print(f"用户输入: {user_prompt}\n" + "=" * 40)

    # 开始 Agent 轮询（最多允许交互 5 次）
    for i in range(5):
        print(f"--- 循环 {i + 1} ---\n")

        # 1. 拼接历史上下文传递给模型
        full_prompt = "\n".join(prompt_history)

        # 2. 调用 LLM 思考
        llm_output = llm.generate(
            full_prompt, system_prompt=AGENT_SYSTEM_PROMPT
        )

        # 防呆机制：如果模型一次性生成了多组 Thought-Action，使用正则截断多余输出
        match = re.search(
            r"(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)",
            llm_output,
            re.DOTALL,
        )
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")

        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        # 3. 解析模型输出的 Action
        action_match = re.search(r"Action:\s*(.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            prompt_history.append(observation_str)
            continue

        action_str = action_match.group(1).strip()

        # 4. 判断是否达到最终完成状态 (Finish)
        if action_str.startswith("Finish"):
            finish_match = re.match(r"Finish\[(.*)\]", action_str, re.DOTALL)
            if finish_match:
                final_answer = finish_match.group(1)
            else:
                final_answer = action_str  # 备用容错逻辑
            print(f"任务完成，最终答案:\n{final_answer}")
            break

        # 5. 正则提取调用的函数名称及参数字符串
        try:
            tool_name = re.search(r"(\w+)\(", action_str).group(1)
            args_str = re.search(r"\((.*)\)", action_str).group(1)

            # 解析参数为 Python 字典，如 city="北京" -> {'city': '北京'}
            kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))
        except Exception as parse_err:
            observation = f"错误: Action 参数格式解析失败 - {parse_err}"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            prompt_history.append(observation_str)
            continue

        # 6. 执行对应的函数工具
        if tool_name in available_tools:
            observation = available_tools[tool_name](**kwargs)
        else:
            observation = f"错误:未定义的工具 '{tool_name}'"

        # 7. 将 Observation 反馈注入历史记录
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)