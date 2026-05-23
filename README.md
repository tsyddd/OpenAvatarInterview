# OpenAvatarInterview

基于 LAM (Large Avatar Model) 数字人的 AI 模拟面试系统。项目保留了 OpenAvatar 的低延迟语音链路，同时把面试能力拆成独立项目：支持简历驱动问答、LangGraph 多智能体工作流、实时情绪评估、面试报告生成，以及 LAM 数字人实时播报。

## 功能特性

- **低延迟全双工语音面试**：Silero VAD + Smart Turn EOU + Semantic Turn Detector，支持打断和连续追问
- **LAM 数字人播报**：TTS 音频驱动 LAM Audio2Expression，输出口型和面部表情
- **简历驱动题目规划**：支持 PDF / DOCX / TXT / MD 简历上传，自动分析背景并生成面试问题
- **LangGraph 多智能体编排**：面试官、简历分析、题目规划、对话分析、评估、报告生成协同工作
- **双路径情绪评估**：候选人每轮回答后先做低延迟规则评估，再异步做 LLM refine，指导后续追问策略
- **会话落盘与可追踪调试**：`runtime/sessions/<session_id>/session.json` 持久化题目、轮次、情绪状态、分析结果与报告状态
- **多格式报告**：自动生成 Markdown、HTML 预览和 PDF 报告
- **多传输模式**：支持 WebRTC、WebSocket 以及 LAM 前端页面

## 当前工作流

### 面试主流程

1. 前端创建 `session_id`，上传简历并轮询题目规划状态。
2. 用户进入 RTC / WS 面试页，与数字人面试官开始对话。
3. VAD 检测候选人发言结束后，ASR 输出文本给 `InterviewAgentHandler`。
4. `InterviewerAgent` 基于当前题目、最近对话、简历摘要和情绪上下文生成下一轮回复。
5. 回复文本进入 TTS，再驱动 LAM 数字人播报。
6. 面试结束后后台自动运行对话分析、综合评估和报告生成。

### Emotion 工作流

当前 emotion 模块只依赖候选人的文本回答，不使用摄像头或音频情绪特征。

1. 候选人本轮文本到达后，`InterviewGraph.fast_assess_emotion(...)` 立即执行规则评估。
2. 规则评估结果会立刻写入会话状态：
   - `latest_fast_emotion_assessment`
   - `latest_emotion_assessment`
   - `latest_interview_policy`
3. `InterviewerAgent` 在生成下一轮 prompt 时，会优先读取：
   - `latest_refined_emotion_assessment`
   - 否则回退到 `latest_fast_emotion_assessment`
   - 再回退到 `latest_emotion_assessment`
4. 面试官当前轮回复结束后，后台线程再触发一次 LLM refine：
   - 使用 `EmotionAgent.assess(...)`
   - 默认模型 `emotion_model_name = qwen-plus`
   - 结果写入 `latest_refined_emotion_assessment`
5. refine 后的 assessment 会继续覆盖后续 prompt 上下文和 `latest_interview_policy`。

Emotion 的目标不是临床判断，而是给面试官一个追问策略信号，例如：

- `confident`：可以继续深入
- `stable`：正常推进
- `anxious`：降难度、减压、先给台阶

## 系统架构

```text
Frontend (Vue 3)
  ├─ dashboard / interview pages
  ├─ WebRTC / WebSocket client
  └─ session_id persistence
            │
            ▼
FastAPI + ChatEngine (src/demo.py)
  ├─ Client Handler
  │   └─ LamClient / RTC
  ├─ Voice Pipeline
  │   ├─ SileroVad
  │   ├─ SenseVoice
  │   ├─ SemanticTurnDetector
  │   └─ CosyVoice
  ├─ Interview Pipeline
  │   ├─ InterviewAgentHandler
  │   ├─ InterviewGraph
  │   ├─ InterviewerAgent
  │   ├─ EmotionAgent
  │   ├─ DialogueAnalyzerAgent
  │   ├─ EvaluationAgent
  │   └─ ReportGeneratorAgent
  └─ Avatar Pipeline
      └─ LAM Audio2Expression
```

## 智能体职责

| Agent | 职责 |
| --- | --- |
| `ResumeAnalyzerAgent` | 解析简历，提取技能、经历、项目亮点 |
| `QuestionPlannerAgent` | 结合简历生成题目计划和追问方向 |
| `InterviewerAgent` | 负责实时面试问答、追问和结束判断 |
| `EmotionAgent` | 基于候选人回答输出交互状态和追问策略 |
| `DialogueAnalyzerAgent` | 面试结束后分析覆盖度、表达质量和技术深度 |
| `EvaluationAgent` | 输出结构化评估结果、风险和录用建议 |
| `ReportGeneratorAgent` | 生成 Markdown 报告，再派生 HTML/PDF |

## 快速开始

### 环境要求

- Python 3.11
- 推荐使用 `uv`
- CUDA 环境可用
- Node.js 仅在需要重建前端时使用

### 环境变量

至少需要：

```bash
export DASHSCOPE_API_KEY=your_key
```

如果使用兼容 OpenAI 的其他服务，也可以按需配置对应 `api_url` / `api_key`。

### 安装依赖

```bash
cd /media/liang/12T/han/OpenAvatarInterview
uv sync
```

### 启动服务

```bash
cd /media/liang/12T/han/OpenAvatarInterview
uv run python src/demo.py --config config/interview_with_lam.yaml
```

默认配置当前使用：

- 服务端口：`8382`
- LAM 资产：`lam_samples/chatting_avatar_20260519004403.zip`
- TTS：`cosyvoice-v2`
- Emotion refine 模型：`qwen-plus`

### 访问地址

- 根路径：`http://127.0.0.1:8382/`
- 面试 UI：`http://127.0.0.1:8382/ui/index.html`
- Dashboard：`http://127.0.0.1:8382/ui/dashboard.html`
- 健康检查：`http://127.0.0.1:8382/liveness`

## 项目结构

```text
OpenAvatarInterview/
├── config/
│   └── interview_with_lam.yaml
├── lam_samples/
│   └── *.zip                       # LAM 数字人资产
├── models/
│   ├── iic/                        # SenseVoice
│   ├── LAM_audio2exp/              # LAM Audio2Expression
│   ├── smart_turn/                 # Smart Turn EOU
│   └── wav2vec2-base-960h/         # LAM 音频特征
├── runtime/
│   └── sessions/<session_id>/      # 会话落盘、报告和中间文件
├── src/
│   ├── demo.py
│   ├── chat_engine/
│   ├── handlers/
│   │   ├── asr/
│   │   ├── avatar/
│   │   ├── client/
│   │   ├── interview/
│   │   │   ├── agents/             # 面试相关 Agent
│   │   │   ├── emotion/            # emotion_types / features / prompt / integration
│   │   │   ├── graph/              # InterviewGraph
│   │   │   ├── models/             # InterviewSessionState / InterviewTurn
│   │   │   ├── prompts/            # interviewer prompt 模板
│   │   │   ├── services/           # resume / report html / pdf
│   │   │   └── storage/            # session repository
│   │   ├── llm/
│   │   ├── logic/
│   │   ├── tts/
│   │   └── vad/
│   └── service/frontend_service/frontend/
├── tests/
└── pyproject.toml
```

## 配置说明

主配置文件是 `config/interview_with_lam.yaml`。当前结构是 `default.chat_engine.handler_configs`，不是旧版的 `handlers:` 列表格式。

示例：

```yaml
default:
  service:
    host: "0.0.0.0"
    port: 8382
  chat_engine:
    handler_search_path:
      - "src/handlers"
    handler_configs:
      SileroVad:
        module: vad/silerovad/duplex_vad_handler
      SenseVoice:
        module: asr/sensevoice/asr_handler_sensevoice
      SemanticTurnDetector:
        module: llm/semantic_turn_detector/semantic_turn_detector_handler
      CosyVoice:
        module: tts/bailian_tts/tts_handler_cosyvoice_bailian
      InterviewAgent:
        module: interview/interview_agent_handler
      LAM_Driver:
        module: avatar/lam/avatar_handler_lam_audio2expression
```

和 emotion 直接相关的配置在 `InterviewAgent` 对应的 `InterviewAgentConfig` 中：

- `model_name`
- `evaluator_model_name`
- `report_model_name`
- `resume_analyzer_model`
- `question_planner_model`
- `dialogue_analyzer_model`
- `emotion_model_name`

## 会话落盘字段

`runtime/sessions/<session_id>/session.json` 当前会包含以下 emotion 相关字段：

- `latest_fast_emotion_assessment`
- `latest_refined_emotion_assessment`
- `latest_emotion_assessment`
- `latest_interview_policy`
- `emotion_state_history`

普通对话轮记录在 `turns` 里，默认事件类型是：

```json
{"role": "candidate", "text": "你好", "event": "turn"}
```

这里的 `event: "turn"` 表示普通面试轮次，不是系统事件。

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/openavatarinterview/sessions/{session_id}` | 获取会话状态 |
| `POST` | `/openavatarinterview/sessions/{session_id}/resume` | 上传简历并触发后台分析 |
| `GET` | `/openavatarinterview/sessions/{session_id}/questions` | 获取题目计划 |
| `GET` | `/openavatarinterview/sessions/{session_id}/analysis` | 获取对话分析、评估和报告状态 |
| `GET` | `/openavatarinterview/sessions/{session_id}/report` | 下载 Markdown 报告 |
| `GET` | `/openavatarinterview/sessions/{session_id}/report/html` | 获取 HTML 报告预览 |
| `GET` | `/openavatarinterview/sessions/{session_id}/report/pdf` | 下载 PDF 报告 |

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11, FastAPI, uvicorn |
| 智能体 | LangGraph, OpenAI SDK 兼容调用 |
| ASR | FunASR SenseVoice |
| TTS | DashScope CosyVoice |
| VAD / 轮次检测 | Silero VAD, Smart Turn EOU, Semantic Turn Detector |
| 数字人 | LAM Audio2Expression, Wav2Vec2 |
| 通信 | WebRTC, WebSocket |
| 前端 | Vue 3, TypeScript, Vite |
| 报告 | Markdown + HTML Renderer + PDF Renderer |

## 许可证

待补充。
