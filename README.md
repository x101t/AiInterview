# 🎯 AI 面试官

> 输入简历/岗位 → AI Agent 自动出题 → 模拟面试 → 追问深挖 → 结构化评估报告
>
> **Python + LangChain Agent + Chroma RAG + 智谱 GLM-4 + Streamlit**

[![CI](https://img.shields.io/badge/build-passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()

---

## 面试官会从这个项目看到什么

| 能力 | 体现 |
|------|------|
| **AI Agent 设计** | 4 个 Tool（题库检索、回答评估、难度调整、报告生成）+ ReAct 决策循环 |
| **RAG 工程化** | Chroma 向量数据库 + 智谱 Embedding API + `chunk_size=32` 分批处理 |
| **Prompt Engineering** | 5+ 版迭代，解决"不知道就跳过""评分不暴露""随机追问" |
| **LLM 温度分离** | 出题 0.7（创造性）、评估 0.1（稳定性）、报告 0.3 |
| **工程踩坑** | HuggingFace 被墙→转智谱 API、64 条限制→分批、Agent 面试节奏→反复调 Prompt |

---

## 快速开始

### Docker 一键启动（推荐）

```bash
cp .env.example .env          # 编辑填入智谱 API Key
docker-compose up -d           # 启动
open http://localhost:8501     # 访问
```

### 本地启动

```bash
# 1. 环境
conda create -n aiinterview python=3.11
conda activate aiinterview

# 2. 依赖
pip install -r requirements.txt

# 3. 配置
cp .env.example .env
# 编辑 .env 填入 ZHIPUAI_KEY

# 4. 启动
streamlit run app.py
```

---

## 架构

```
简历上传 → 解析（PDF/Word/TXT）
              ↓
     Chroma 向量检索（语义匹配 top-3）
              ↓
     LangChain Agent（ReAct 决策循环）
       ├── Tool 1: search_question_bank   → RAG 检索
       ├── Tool 2: evaluate_answer        → 内部评估（不暴露评分）
       ├── Tool 3: adjust_difficulty      → 难度自适应
       └── Tool 4: generate_final_report  → 结构化报告
              ↓
     Streamlit 聊天（实时对话 + 侧边栏进度）
```

## 项目结构

```
AIInterview/
├── app.py                 # 主程序（Agent + UI）
├── questions.JSON         # 题库（200 道）
├── requirements.txt       # Python 依赖
├── Dockerfile
├── docker-compose.yml
├── .env.example           # 环境变量模板
└── Chroma_db/             # 向量库（自动生成）
```

---

## 🎬 Demo 演示指南

### 录屏脚本（2 分钟）

| 时间 | 内容 |
|------|------|
| 0:00-0:20 | 展示项目结构 + README + 技术栈 |
| 0:20-0:45 | 上传简历 → 点击「开始面试」→ Agent 出第一题 |
| 0:45-1:20 | 回答几道题 → 展示追问 + "不知道就跳过" |
| 1:20-1:45 | 回答好 → Agent 随机追问或换题 |
| 1:45-2:00 | 面试结束 → 展示评估报告 |

### 录屏工具

- **Windows**：Win+G（自带）或 OBS Studio（免费）
- **分辨率**：1920×1080
- **输出格式**：MP4

---

## 简历描述模板

### 30 秒版（简历上的项目简介）

> "AI 面试官是我独立开发的 Agent 应用，使用 LangChain + Chroma RAG 架构。核心是 4 个 Tool 驱动的 ReAct Agent，能根据简历自动出题、评估回答、调整难度并生成结构化面试报告。在开发中解决了国内 HuggingFace 网络不可用、API 限流分批、Agent 面试节奏控制等实际工程问题。"

### 2 分钟版（面试口述）

> "这个项目的核心不是 RAG 本身——RAG 只是基础能力。真正的难点在 Agent 的面试节奏控制。最初 Agent 会在每次回答后直接亮评分，面试体验很差。后来我把 `evaluate_answer` 改成了纯内部决策工具，System Prompt 迭代了 5 版，最终实现了'不知道就跳过、回答好就深挖、结束给完整报告'的自然对话体验。技术上，我用 `temperature=0.1` 保证评分稳定性，用 `temperature=0.7` 出题保持多样性。最大的工程问题来自国内网络——HuggingFace 被墙，换成智谱 API 后遇到 64 条/次的限制，最终用 `chunk_size=32` 分批解决。"

---

## 已知问题 & TODO

- [ ] `adjust_difficulty` 闭环：评估结果未同步到下一次检索的难度参数
- [ ] `parse_resume` 边界处理：大文件/空文件/图片型 PDF 无保护
- [ ] Embedding API 调用无重试机制
- [ ] 面试记录持久化（当前丢失于 session 结束）

---

## 许可证

MIT
