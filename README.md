智能简历匹配与分析 Agent (Resume-Matching-Agent)



基于 ReAct (Reasoning and Acting) 范式的单智能体应用。用户输入简历路径与目标城市，Agent 自动调用工具解析简历、联网搜索岗位需求，并输出多维度匹配分析报告。



核心技术与架构：



大语言模型：DeepSeek API (deepseek-chat)



Agent 架构：从零手写 ReAct 循环 (Thought-Action-Observation)



工具调用：Tavily 联网搜索 API、pdfplumber 文档解析



开发语言：Python



项目核心亮点：



不依赖 LangChain 等重型框架，深入理解并手写底层 Prompt 拼接与正则解析逻辑。



针对大模型输出不稳定的问题，设计了正则截断与异常处理防呆机制，保障系统稳定运行。



解决了复杂 PDF 中文编码解析乱码问题，大幅提升 Prompt 输入质量与最终报告准确度。



运行方式：



安装依赖包：pip install openai tavily-python pdfplumber



在 deep.py 中填入你自己的 API\_KEY 和 TAVILY\_API\_KEY。



修改 deep.py 中的 resume\_path 为你的本地简历路径。



运行代码：python deep.py



示例输出报告维度：



简历技能摘要



匹配度打分及理由



Top 3 匹配岗位



技能差距清单



提升建议

