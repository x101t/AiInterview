import json
import os
import streamlit as st
import pdfplumber
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from docx import Document as DocxDocument

# ============================================================
# 加载环境变量
# ============================================================
load_dotenv()


def load_qa_db():
    """读取题库 JSON 文件，返回 Document 列表"""
    with open("questions.JSON", "r", encoding="utf-8") as f:
        data = json.load(f)

    docs = []

    for item in data:
        content = f"问题:{item['question']}\n 答案:{item['answer']}\n 分类:{item['topic']}"
        meta = {
            "id": item["id"],
            "topic": item["topic"],
            "language": item["language"],
            "difficulty": item["difficulty"],
        }
        doc = Document(page_content=content, metadata=meta)
        docs.append(doc)

    return docs


def init_vectorstore():
    """
    加载题库文档并存入 Chroma，返回 vectorstore 实例。
    使用智谱 AI Embedding API（云端，无需下载模型）。
    """
    # 智谱 AI Embedding，API 兼容 OpenAI 格式
    # model: embedding-2（智谱 embedding 模型）
    # chunk_size=32: 智谱限制每次最多 64 条，分批发送避免 400 错误
    embeddings = OpenAIEmbeddings(
        model="embedding-2",
        api_key=os.getenv("ZHIPUAI_KEY"),
        base_url=os.getenv("ZHIPUAI_BASE_URL"),
        chunk_size=32,
    )

    # 如果已经建库了，直接加载
    if os.path.exists("./Chroma_db") and os.listdir("./Chroma_db"):
        return Chroma(
            persist_directory="./Chroma_db",
            embedding_function=embeddings,
        )

    # 第一次加载才插入
    docs = load_qa_db()
    return Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory="./Chroma_db",
    )

#简历解析函数
def parse_resume(file) -> str :
    """
    解析上传的简历文件(支持PDF/Word/TXT).返回纯文本
    """
    if file.type == "application/pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.type == "application/vnd.openxmlformats.wordprocessingml.document":
        doc = DocxDocument(file)
        return "\n".join(para.text  for para in doc.paragraphs)
    else:
        #TXT或其他文本文件
        return file.read().decode("utf-8")



#构建检索链
def get_llm():
    """初始化大模型"""
    return ChatOpenAI(
        model="glm-4-flash",
        api_key=os.getenv("ZHIPUAI_KEY"),
        base_url=os.getenv("ZHIPUAI_BASE_URL"),
        temperature=0.7
    )

def build_qa_chain():
    """构建 RAG 检索器 + 出题 Prompt + 评估 Prompt，返回给 run_app 使用"""
    vectorstore = init_vectorstore()

    # 检索 3 道相关题
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 出题 Prompt
    question_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位技术面试官。你的任务是根据候选人的简历和应聘岗位，从题库中挑选最合适的一道题进行提问。

要求：
1. 题目必须基于提供的题库内容，不要凭空捏造
2. 问题要针对简历中提到的技术栈
3. 语气专业但友好，直接提问即可
4. 只出一道题，绝对不要出多道"""),
        ("system", "候选人简历：{resume_text}"),
        ("system", "岗位描述：{job_desc}"),
        ("system", "候选题目（从题库检索）：\n{context}"),
        ("user", "请提问："),
    ])

    # 评估 Prompt
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位资深技术面试官。请评估候选人的回答，给出评分（1-10）和改进建议。

评分标准：
9-10分：回答全面、准确、有深度
7-8分：回答正确，但不够深入或不够流畅
5-6分：部分正确，有明显遗漏或错误
1-4分：回答不正确或完全不相关"""),
        ("system", "题目：{question}"),
        ("system", "标准答案要点：{answer_reference}"),
        ("system", "候选人回答：{user_answer}"),
        ("user", "请给出评分和具体改进建议："),
    ])

    return retriever, question_prompt, eval_prompt


# ============================================================
# Streamlit 界面
# ============================================================
def run_app():
    st.set_page_config(page_title="AI 面试官", layout="wide")
    st.title("AI 面试官")

    # 初始化 session_state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_question" not in st.session_state:
        st.session_state.current_question = None

    # ===================== 侧边栏 =====================
    with st.sidebar:
        st.header("求职者信息")
        upload_file = st.file_uploader("上传简历", type=["pdf", "docx", "txt"])
        job_desc = st.text_input("应聘岗位", placeholder="例如：Java 开发工程师")

        if st.button("开始面试"):
            if upload_file:
                resume_text = parse_resume(upload_file)
                st.session_state.resume_text = resume_text
                st.session_state.job_desc = job_desc
                st.session_state.messages = []
                st.session_state.current_question = None
                st.session_state.retrieved_docs = None
                st.rerun()
            else:
                st.warning("请先上传简历")

        # 自动出题：简历已就绪但还没出题
        if st.session_state.get("resume_text") and not st.session_state.get("current_question"):
            with st.spinner("面试官正在出题..."):
                retriever, question_prompt, _ = build_qa_chain()
                retrieved_docs = retriever.invoke(
                    st.session_state.resume_text + " " + st.session_state.get("job_desc", "")
                )
                context = "\n\n".join(doc.page_content for doc in retrieved_docs)

                llm = get_llm()
                prompt_text = question_prompt.format(
                    resume_text=st.session_state.resume_text,
                    job_desc=st.session_state.get("job_desc", ""),
                    context=context,
                )
                response = llm.invoke(prompt_text)

            st.session_state.current_question = response.content
            st.session_state.retrieved_docs = retrieved_docs
            st.session_state.messages.append({"role": "assistant", "content": response.content})
            st.rerun()

    # ===================== 主界面：聊天记录 =====================
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ===================== 用户输入框 =====================
    if prompt := st.chat_input("请输入你的回答..."):
        # 保存用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.pending_answer = prompt
        st.session_state.need_evaluate = True
        st.rerun()

    # ===================== 评估逻辑 =====================
    if st.session_state.get("need_evaluate"):
        st.session_state.need_evaluate = False
        user_answer = st.session_state.get("pending_answer", "")

        with st.chat_message("assistant"):
            with st.spinner("🤔 面试官正在评估你的回答..."):
                # 找到当前题目的标准答案
                current_q = st.session_state.get("current_question", "")
                reference = ""
                for doc in st.session_state.get("retrieved_docs", []):
                    if current_q[:10] in doc.page_content or any(
                        word in doc.page_content for word in current_q[:10]
                    ):
                        reference = doc.page_content
                        break

                # 调 LLM 评估
                _, _, eval_prompt = build_qa_chain()
                llm = get_llm()
                prompt_text = eval_prompt.format(
                    question=current_q,
                    answer_reference=reference,
                    user_answer=user_answer,
                )
                response = llm.invoke(prompt_text)
                st.markdown(response.content)

        # 保存评估结果
        st.session_state.messages.append({"role": "assistant", "content": response.content})

        # 清空当前题，下一轮自动出下一题
        st.session_state.current_question = None
        st.rerun()

if __name__ == "__main__":
    run_app()