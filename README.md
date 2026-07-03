🎯 AI 智能面试官
一个基于 LangChain + RAG + Streamlit 的智能面试辅助系统。上传简历和岗位描述，AI 自动生成个性化面试题、模拟真实面试对话，并对回答进行量化评分与改进建议。

✨ 功能特点
简历解析：支持 PDF、Word、TXT 格式，自动提取候选人信息。

智能出题：基于 RAG 检索海量题库，结合简历技术栈生成针对性问题。

模拟面试：多轮对话，AI 扮演面试官，引导候选人回答问题。

自动评估：对每个回答给出 1‑10 分评分及详细改进建议。

轻量部署：基于 Streamlit，无需前端开发，开箱即用。

🛠️ 技术栈
组件	技术选型
前端界面	Streamlit
大语言模型	智谱 AI（glm-4 / embedding-2）
框架编排	LangChain（RAG、Chain、Prompt）
向量数据库	Chroma（本地持久化）
文档解析	pdfplumber、python-docx
编程语言	Python 3.9+
📦 快速开始
1. 克隆项目
bash
git clone https://github.com/your-username/ai-interviewer.git
cd ai-interviewer
2. 创建虚拟环境（推荐）
bash
conda create -n langchain1.2 python=3.9
conda activate langchain1.2
3. 安装依赖
bash
pip install -r requirements.txt
4. 配置环境变量
在项目根目录创建 .env 文件，填入你的智谱 AI API 信息：

env
ZHIPUAI_KEY=你的API密钥
ZHIPUAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
如果你使用其他兼容 OpenAI 的 API，可调整 model 和 base_url 参数。

5. 准备题库
将面试题库保存为 questions.JSON（格式见 data/ 示例）。

6. 启动应用
bash
streamlit run app.py
浏览器访问 http://localhost:8501 即可使用。

📁 项目结构
text
AIInterview/
├── app.py                 # 主程序（Streamlit 界面 + 逻辑）
├── questions.JSON         # 面试题库（问题、答案、分类等）
├── Chroma_db/             # 向量数据库持久化目录（自动生成）
├── requirements.txt       # Python 依赖
├── .env                   # 环境变量（API Key）
├── README.md              # 项目说明
└── .gitignore
🧠 核心流程
上传简历 → 解析文本。

点击“开始面试” → 初始化会话，清空历史。

后台 RAG 检索 → 根据岗位和简历关键词从题库中检索最相关的 3 道题。

AI 出题 → LangChain Chain 结合 Prompt 生成问题并展示。

用户回答 → 在输入框中作答。

AI 评估 → 根据标准答案和回答内容生成评分和改进建议。

循环进行 → 可继续下一题或结束面试。

📋 当前状态
✅ 环境配置 & 依赖安装

✅ 题库加载与向量化（Chroma）

✅ 简历解析（PDF / Word / TXT）

✅ Streamlit 界面（侧边栏、聊天框）

✅ RAG 检索链搭建（基础版）

⏳ 完整的对话流程（出题 → 回答 → 评估）正在实现中

⏳ 评估 Prompt 与输出格式化优化

当前点击“开始面试”后尚未触发后端逻辑，因为核心对话循环正在开发中。您可以基于已有框架自行扩展，或关注后续更新。

🚀 后续开发计划
完善 build_qa_chain 并集成到界面交互中

支持多轮对话与上下文记忆

添加“结束面试”并生成综合报告

支持更多题库格式（CSV、Excel）

增加用户自定义评分维度

部署到云端（Hugging Face Spaces / Streamlit Cloud）

