# OpenAvatarInterview

基于 LAM (Large Avatar Model) 3D 数字人的 AI 模拟面试系统。支持全双工语音交互、唇形同步、简历解析与多智能体面试工作流，提供面试后评估报告。

## 功能特性

- **全双工语音对话** -- 基于 Silero VAD + Smart Turn EOU + 语义轮次检测，支持随时打断
- **3D 数字人驱动** -- LAM Audio2Expression 实时音频驱动面部表情，高斯溅射渲染
- **简历驱动面试** -- 支持 PDF/DOCX/TXT/MD 简历上传，自动分析并生成定制化面试题
- **多智能体工作流** -- LangGraph 编排 6 个专业 Agent（简历分析、题目规划、面试官、对话分析、评估、报告生成）
- **面试评估报告** -- 自动生成包含评分、优势/风险分析和录用建议的 Markdown 报告
- **Web 搜索增强** -- 面试题目规划集成 DuckDuckGo / Tavily 搜索，获取相关面试话题
- **多传输协议** -- 支持 WebRTC、WebSocket 及混合模式

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Vue 3 + Electron)           │
│              gaussian-splat-renderer-for-lam             │
└────────────┬──────────────────────────┬─────────────────┘
             │ WebRTC / WebSocket       │ WebSocket
┌────────────▼──────────────────────────▼─────────────────┐
│              FastAPI + uvicorn (demo.py)                  │
├──────────────────────────────────────────────────────────┤
│                    ChatEngine                             │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────────┐  │
│  │  VAD    │ │  ASR    │ │   TTS    │ │  LLM Handler │  │
│  │ Silero  │ │SenseVoice│ │CosyVoice│ │ OpenAI-compat│  │
│  └─────────┘ └─────────┘ └──────────┘ └──────────────┘  │
│  ┌───────────────────┐  ┌──────────────────────────────┐ │
│  │  Avatar Handler   │  │    Interview Agent Handler   │ │
│  │  LAM Audio2Exp    │  │  LangGraph Multi-Agent       │ │
│  └───────────────────┘  └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 多智能体管线

| Agent                  | 职责                                     |
| ---------------------- | ---------------------------------------- |
| ResumeAnalyzerAgent    | 解析简历，提取技能、经历、项目亮点       |
| QuestionPlannerAgent   | 生成 3-4 道定制面试题，含类别和追问提示 |
| InterviewerAgent       | 实时面试对话，支持追问和结束判断         |
| DialogueAnalyzerAgent  | 话题覆盖、回答质量、技术深度评分 (1-5)  |
| EvaluationAgent        | 结构化评估：录用建议、优势、风险         |
| ReportGeneratorAgent   | 生成完整 Markdown 面试报告               |

## 快速开始

### 环境要求

- Python 3.11 (推荐使用 `uv` 管理)
- CUDA 12.8 + PyTorch 2.8
- Node.js (前端构建)

### 安装

```bash
# 1. 克隆项目
git clone <repo-url>
cd OpenAvatarInterview

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key：
#   DASHSCOPE_API_KEY=your_key    # 阿里云百炼（ASR/TTS/LLM）
#   OPENAI_API_KEY=your_key       # 可选，用于 OpenAI 兼容接口

# 3. 一键安装依赖
python install.py
```

### 启动服务

```bash
# 启动后端（默认端口 12777）
python src/demo.py --config config/interview_with_lam.yaml

# 启动前端开发服务器（可选）
cd src/service/frontend_service/frontend
npm install && npm run dev
```

### 访问

- 面试页面: `http://localhost:12777/interview`
- 健康检查: `http://localhost:12777/liveness`
- 版本信息: `http://localhost:12777/version`

## 项目结构

```
OpenAvatarInterview/
├── config/                     # YAML 配置文件
│   └── interview_with_lam.yaml # 主配置（Handler 管线）
├── docs/                       # 设计文档
├── lam_samples/                # LAM 数字人资产 (zip)
├── models/                     # 预训练模型权重
│   ├── iic/                    #   SenseVoice ASR
│   ├── LAM_audio2exp/          #   LAM 音频转表情
│   ├── smart_turn/             #   Smart Turn EOU (ONNX)
│   └── wav2vec2-base-960h/     #   Wav2Vec2 特征提取
├── src/
│   ├── demo.py                 # 主入口 (FastAPI + uvicorn)
│   ├── chat_engine/            # 核心引擎框架
│   │   ├── chat_engine.py      #   ChatEngine 会话管理
│   │   ├── common/             #   Handler 基类
│   │   ├── core/               #   Handler/Logic/Signal Manager
│   │   └── data_models/        #   数据类型定义
│   ├── handlers/               # 可插拔 Handler 模块
│   │   ├── asr/                #   语音识别 (SenseVoice, 百炼)
│   │   ├── avatar/             #   数字人驱动 (LAM)
│   │   ├── client/             #   客户端 (WebSocket, WebRTC)
│   │   ├── interview/          #   面试智能体系统
│   │   │   ├── agents/         #     6 个专业 Agent
│   │   │   ├── graph/          #     LangGraph 编排
│   │   │   ├── prompts/        #     Prompt 模板
│   │   │   └── services/       #     简历解析
│   │   ├── llm/                #   LLM 接口 (OpenAI-compat, Dify, Qwen)
│   │   ├── tts/                #   语音合成 (CosyVoice, EdgeTTS)
│   │   └── vad/                #   语音活动检测 (Silero, Smart Turn)
│   └── service/                # 服务层
│       └── frontend_service/   #   Vue 3 前端
├── tests/                      # 测试用例
├── install.py                  # 依赖安装脚本
└── pyproject.toml              # Python 项目配置
```

## 配置说明

主配置文件 `config/interview_with_lam.yaml` 定义了完整的 Handler 管线：

```yaml
service:
  host: "0.0.0.0"
  port: 12777

handler_search_paths:
  - "src/handlers"

handlers:
  - name: "SileroVad"
    type: "duplex_vad_handler"
    # ...
  - name: "SenseVoiceASR"
    type: "asr_handler_sensevoice"
    # ...
  - name: "CosyVoiceTTS"
    type: "tts_handler_cosyvoice_bailian"
    # ...
  - name: "InterviewAgent"
    type: "interview_agent_handler"
    # ...
  - name: "LAM_Driver"
    type: "avatar_handler_lam_audio2expression"
    # ...
```

## API 接口

| 方法   | 路径                                         | 说明             |
| ------ | -------------------------------------------- | ---------------- |
| GET    | `/interview`                                 | 面试页面         |
| POST   | `/openavatarinterview/sessions/{id}/resume`  | 上传简历         |
| GET    | `/openavatarinterview/sessions/{id}/status`  | 会话状态         |
| GET    | `/openavatarinterview/sessions/{id}/report`  | 下载面试报告     |
| GET    | `/openavatarinterview/sessions/{id}/questions` | 获取题目计划   |
| GET    | `/openavatarinterview/sessions/{id}/analysis`  | 获取对话分析   |
| GET    | `/version`                                   | 版本信息         |
| GET    | `/liveness`                                  | 健康检查         |
| GET    | `/readiness`                                 | 就绪检查         |

## 技术栈

| 层级     | 技术                                        |
| -------- | ------------------------------------------- |
| 后端     | Python 3.11, FastAPI, uvicorn               |
| 智能体   | LangGraph, OpenAI SDK (DashScope 兼容)      |
| ASR      | FunASR SenseVoice                           |
| TTS      | DashScope CosyVoice, Edge TTS               |
| VAD      | Silero VAD, Smart Turn EOU (ONNX)           |
| 数字人   | LAM Audio2Expression, Wav2Vec2              |
| 通信     | WebRTC (aiortc), WebSocket                  |
| 前端     | Vue 3, TypeScript, Vite, Electron           |
| UI       | Ant Design Vue, Element Plus                |
| 配置     | Dynaconf, Pydantic                          |
| 日志     | Loguru                                      |
| 包管理   | uv (Python), npm (Node.js)                  |

## 许可证

TBD
