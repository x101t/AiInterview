import json
import os
import streamlit as st
import pdfplumber
from dotenv import load_dotenv
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains.retrieval import create_retrieval_chain
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
    docs = load_qa_db()

    # 智谱 AI Embedding，API 兼容 OpenAI 格式
    # model: embedding-2（智谱 embedding 模型）
    # chunk_size=32: 智谱限制每次最多 64 条，分批发送避免 400 错误
    embeddings = OpenAIEmbeddings(
        model="embedding-2",
        api_key=os.getenv("ZHIPUAI_KEY"),
        base_url=os.getenv("ZHIPUAI_BASE_URL"),
        chunk_size=32,
    )

    # 创建/加载向量数据库（持久化到本地，第二次运行直接加载）
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory="./Chroma_db",
    )
    return vectorstore

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
    """构建RAG检索+出题链"""
    vectorstore = init_vectorstore()
    #检索3道相关题
    retrieve =vectorstore.as_retriever(search_kwargs = {"k": 3})

    #出题Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system","""你是因为自身技术面试官.你的任务是根据候选人的简历和应聘岗位,从题库中挑选最合适的一道题进行提问
        
          要求:
          1.题目必须基于提供的题库内容,不要凭空捏造
          2.问题要针对简历中提到的技术栈
          3.语气专业但友好,直接提问即可
        """),
        ("system","候选人简历:{resume_text}"),
        ("system", "岗位描述:{job_desc}"),
        ("system", "候选题目(从题库检索):\n{context}"),
        ("user", "请提问:"),
    ])

    #评估 Prompt
    eval_prompt = ChatPromptTemplate.from_messages([
        ("system","""你是一位资深技术面试官.请评估候选人的回答,给出评分(1-10)和改进建议
        
        评分标准：
        9-10分：回答全面、准确、有深度
        7-8分：回答正确，但不够深入或不够流畅
        5-6分：部分正确，有明显遗漏或错误
        1-4分：回答不正确或完全不相关"""),
        ("system", "题目：{question}"),
        ("system", "标准答案要点：{answer_reference}"),
        ("system", "候选人回答：{user_answer}"),
        ("user", "请给出评分和具体改进建议：")
    ])

    #组装链(先检索,再调用大模型)
    question_chain = create_stuff_documents_chain(get_llm(),prompt)
    retrieve_chain = create_retrieval_chain(retrieve,question_chain)


#界面设计
def run_app():
    st.set_page_config(page_title="AI 面试官",layout="wide")
    st.title("AI 面试官")

    #侧边栏:上传简历+岗位
    with st.sidebar:
        st.header("求职者信息")
        upload_file = st.file_uploader("上传简历",type = ["pdf","docx","txt"])
        job_desc = st.text_input("应聘岗位",placeholder = "例如: Java开发工程师")
        if st.button("开始面试"):
            if upload_file :
                resume_text = parse_resume(upload_file)
                st.session_state.resume_text = resume_text
                st.session_state.job_desc = job_desc
                st.session_state.messages = [] #清空历史
                st.session_state.current_question = None
                st.session_state.retrieved_docs = None
                st.rerun()
        #如果简历已上传但还没出题,自动生成第一道题
        if st.session_state.get("resume_text") and not st.session_state.get("current_question"):
            #检索题库
            vectorstore = init_vectorstore()
            retriever = vectorstore.as_retriever(search_kwargs = {"k": 3})
            retrieved_docs = retriever.invoke(st.session_state.resume_text+" "+ st.session_state.job_desc)

            #拼接
            context = "\n\n".join(doc.page_content for doc in retrieved_docs)

            #调LLM出题
            llm = get_llm()
            prompt_text = f"""你是一位技术面试官,根据候选人信息生成一道面试题.

                           候选人简历:{st.session_state.resume_text}
                           应聘岗位:{st.session_state.job_desc}
                           题库参考:{context}
            要求:题目必须基于题库内容,针对简历中的技术栈,直接问,不要加额外说明."""
            response = llm.invoke(prompt_text)

            #保持状态
            st.session_state.current_question = response.content
            st.session_state.retrieved_docs = retrieved_docs
            st.session_state.messages.append({"role": "assistant", "content": response.content})
            st.rerun()

    #主界面:聊天记录
    for msg  in st.session_state.get("messages",[]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    #输入框(用户回答)
    if prompt := st.chat_input("请输入你的回答..."):
        #把用户回答加入聊天记录
       st.session_state.messages.append({"role":"user","content":prompt})
       #找到当前题目的标准答案
       current_q = st.session_state.get("current_question","")
       reference = ""
       for doc in st.session_state.get("retrieved_docs",[]):
         if current_q in doc.page_content or any(word in doc.page_content for word in current_q[:10]):
                reference = doc.page_content
                break
       #调LLM评估
       llm =get_llm()
       eval_prompt = f"""你是一位资深技术面试官。请评估候选人的回答。

        题目：{st.session_state.current_question}
        标准答案参考：{reference}
        候选人回答：{prompt}

        请给出：
        1. 评分（1-10分）
        2. 优点
        3. 不足之处
        4. 改进建议
        5. 参考要点"""

       response = llm.invoke(eval_prompt)
       st.session_state.messages.append({"role": "assistant", "content": response.content})

       # 4. 清空当前题，下一轮自动出下一题
       st.session_state.current_question = None
       st.rerun()

if __name__ == "__main__":
    run_app()