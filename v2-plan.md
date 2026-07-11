# AI 面试官 v2 — Agent + 追问 + 自适应难度 + 报告

## Context

当前 v1 是"RAG 检索 → 出题 → 一问一答评估"，缺少 Agent 的核心能力（Tool Use、多步推理、上下文）。v2 目标是把项目从"纯 RAG"升级为"RAG + Agent"，让面试官具备工具调用、追问上下文、自适应难度和结构化报告能力。

## 架构对比

```
v1（当前）:
  简历 → RAG检索 → LLM出题 → 用户回答 → LLM评估 → 下一题 → 循环
  问题: 没有记忆, 不会追问, 没有工具, 没有总结

v2（目标）:
  简历 → Agent(带工具) ⇄ 用户
           │
           ├── Tool: search_question_bank(query, difficulty) → RAG 检索题库
           ├── Tool: evaluate_answer(question, answer) → 评分+反馈（temp=0.1）
           └── Tool: generate_final_report() → 结构化面试报告
           
  Agent 自主决策: 出题? 追问? 下一题? 结束并出报告?
```

## 实施方案

### 修改文件
- `app.py` — 单文件，全部改动在此

### 新增 Session State

```python
st.session_state.interview_history = []   # [{round, question, answer, score, feedback, difficulty, follow_ups}]
st.session_state.current_difficulty = "medium"
st.session_state.question_count = 0
st.session_state.max_questions = 5
st.session_state.phase = "questioning"    # "questioning" | "summarizing" | "done"
st.session_state.current_question_ref = None  # 直接存引用文档,不用字符串匹配
```

### 新增 Agent Tools（4 个）

**Tool 1: `search_question_bank`**
```
输入: query(简历+岗位+已问过的题), difficulty
输出: 匹配的候选题目
实现: Chroma similarity_search + metadata 过滤 difficulty
```

**Tool 2: `evaluate_answer`**
```
输入: question, user_answer, reference_answer
输出: {score: 1-10, feedback: str, should_follow_up: bool}
实现: LLM temp=0.1, 专门评估 prompt
```

**Tool 3: `adjust_difficulty`**
```
输入: recent_scores[]
输出: new_difficulty ("easy"|"medium"|"hard")
规则: 均分>8 → 升难度, 均分<5 → 降难度
```

**Tool 4: `generate_final_report`**
```
输入: interview_history[]
输出: 结构化报告 (markdown)
维度: 技术深度、表达清晰度、知识广度、综合评分、录用建议
```

### Agent 设计

```
类型: Tool-calling Agent (ReAct)
模型: glm-4-flash (temp=0.7, 出题发散; eval 工具内部 temp=0.1)
System Prompt 核心指令:
  - 你是技术面试官
  - 先调用 search_question_bank 找题
  - 一次只问一道题
  - 候选人回答后, 调用 evaluate_answer 评分
  - 如果回答浅/有疑点 → 追问; 如果回答好 → 下一题
  - 问够 max_questions 道题 → 调用 generate_final_report
  - 根据 adjust_difficulty 结果调整难度
```

### UI 改动

- 侧边栏新增: 面试题数、当前难度、实时均分
- 主聊天区不变（Agent 消息自然展示追问）
- 评估结果以折叠面板显示（评分+反馈, 不那么占空间）
- 报告阶段显示结构化 markdown 卡片

### 修复现有问题

| 问题 | 修复方案 |
|------|---------|
| 评估匹配逻辑脆弱 (current_q[:10]) | `current_question_ref` 直接存检索到的 Document 对象 |
| 评估 temperature 太高 | `evaluate_answer` 工具内用独立 LLM temp=0.1 |
| 无对话上下文 | `interview_history` 存完整对话，Agent 每次都能看到 |
| 无面试总结 | `generate_final_report` 工具 |

## 代码结构（app.py 分节）

```
Section 1:  Imports + 环境变量
Section 2:  题库加载 + 向量库 (load_qa_db, init_vectorstore)  ← 不改
Section 3:  简历解析 (parse_resume)  ← 不改
Section 4:  LLM 工厂
              - get_llm(temperature=0.7)     ← Agent 主模型
              - get_eval_llm()               ← temp=0.1 评估专用
Section 5:  Agent Tools
              - search_question_bank
              - evaluate_answer
              - adjust_difficulty
              - generate_final_report
Section 6:  Agent 构建 (build_agent)         ← 替代 build_qa_chain
Section 7:  Streamlit UI (run_app)           ← 重写
```

## 验证方法

1. `streamlit run app.py`
2. 上传简历 → 点击开始面试 → Agent 出第一道题
3. 回答后 Agent 决定追问还是下一题
4. 观察侧边栏难度变化
5. 答完 5 题后 Agent 自动生成报告
