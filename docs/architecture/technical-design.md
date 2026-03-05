# AI差旅通技术方案文档

本文档用于说明 AI 差旅通（travel-agent）的总体技术方案、核心架构与关键设计决策。  
架构图与时序图请参考：

- [架构图文档](./architecture.md)
- [时序图文档](./sequence-diagrams.md)
- [流程图文档](./flow-charts.md)

## 1. 项目目标

AI 差旅通的目标是把「出差申请—审批跟踪—行程规划—预订执行」串成完整闭环，并通过多智能体协作降低人工操作成本。

核心目标：

1. 用自然语言驱动差旅流程。
2. 将复杂任务拆解为可编排的多 Agent 协作流程。
3. 对接 MCP 网关，统一调用钉钉差旅能力。
4. 支持流式交互、任务可视化与上下文记忆。

## 2. 技术选型与决策理由

### 2.1 为什么选择 LangGraph（而非 AutoGen / CrewAI）

- **状态图建模能力强**：当前业务是“识别意图→按条件路由→执行子流程”的典型有向图流程，LangGraph 在状态流转与条件边上更贴近需求。
- **可控性高**：相比更开放的对话式多 Agent 框架，LangGraph 更适合企业流程型场景，便于做稳定性和可观测性控制。
- **与 LangChain 生态兼容**：Prompt、模型、工具调用可复用，降低整体工程复杂度。

### 2.2 为什么采用双模型路由（GLM + Qwen）

- **按任务特性分配模型**：意图识别和闲聊更关注速度与成本；规划类任务更关注推理和稳定输出。
- **可降级与可替换**：模型路由层与业务层解耦，后续可扩展更多模型提供商。
- **成本优化**：不把所有请求都交给同一高成本模型，控制单位请求成本。

### 2.3 为什么通过 Higress MCP 集成钉钉

- **统一工具调用协议**：MCP 提供标准化工具调用接口，减少业务层适配成本。
- **网关治理能力**：Higress 可承载鉴权、限流、观测等治理能力。
- **易于 Mock 与联调**：开发态可本地模拟工具返回，提高研发效率。

## 3. 系统分层架构

系统按职责分为六层：

1. **前端展示层**：React + Zustand，负责对话、任务进度、事件可视化。
2. **API 接入层**：FastAPI 提供 HTTP/SSE/WebSocket 接口。
3. **Agent 编排层**：LangGraph Orchestrator + 子 Agent。
4. **引擎能力层**：TaskPlanner / Memory / Context / ModelRouter / SkillRegistry。
5. **外部集成层**：MCP Client 对接 Higress 与钉钉差旅服务。
6. **存储层**：当前以内存为主，设计上支持 Redis / PostgreSQL。

详细图示见 `docs/architecture.md`。

## 4. 核心模块设计

### 4.1 Orchestrator（编排器）

- 文件：`backend/app/agents/orchestrator.py`
- 职责：构建 StateGraph，执行意图路由，串联子 Agent。
- 输入：`AgentState`
- 输出：最终回复 + 元数据（intent/confidence/current_agent）

### 4.2 Intent Agent（意图识别）

- 文件：`backend/app/agents/intent_agent.py`
- 职责：识别用户意图、提取实体并给出置信度。
- 关键设计：解析失败自动降级 `general_chat`，保证流程可继续。

### 4.3 Query Rewriter（查询改写）

- 文件：`backend/app/agents/query_rewriter.py`
- 职责：对模糊查询做补全，并合并实体到 `TravelContext`。

### 4.4 Travel Apply / Itinerary / Booking Agent

- `travel_apply_agent.py`：收集字段、提交申请、查询审批状态
- `itinerary_agent.py`：并行查询酒店/机票/高铁并生成推荐
- `booking_agent.py`：执行具体预订操作

### 4.5 引擎模块

- `task_planner.py`：DAG 拆解与拓扑执行
- `skill_registry.py`：技能注册与参数校验
- `memory_manager.py`：短期/长期/工作记忆三层模型
- `context_manager.py`：Token 预算与上下文压缩
- `model_router.py`：按任务路由模型

## 5. 数据模型设计

### 5.1 AgentState

核心字段：

- `messages`：最近对话消息
- `user_input`：当前用户输入
- `intent / intent_confidence / intent_entities`
- `travel_context`：当前差旅实体上下文
- `events`：用于前端展示的过程事件
- `response`：最终回复

### 5.2 TravelContext

典型字段：

- `origin / destination`
- `start_date / end_date`
- `reason`
- `apply_id / apply_status`

### 5.3 TaskPlan / TaskNode

- `TaskPlan`：计划级信息（plan_id、session_id、tasks）
- `TaskNode`：任务级信息（name、status、dependencies、output）

## 6. 异常处理策略

1. **LLM 解析异常降级**：JSON 解析失败回退到可用默认值。
2. **工具调用异常兜底**：单个工具失败不阻断整体流程（如 itinerary 并发查询）。
3. **API 异常友好返回**：对前端返回可读错误信息，避免静默失败。
4. **日志分级**：
   - `info`：关键业务节点
   - `debug`：中间状态
   - `warning`：可恢复异常
   - `error`：失败路径 + 堆栈

## 7. 性能优化策略

1. **上下文窗口控制**：仅截取最近 N 轮消息，减少 token 消耗。
2. **Token 预算治理**：超预算时自动触发上下文压缩。
3. **并行工具查询**：酒店/机票/高铁并发请求，降低总等待时间。
4. **模型按需路由**：不同任务使用不同模型，平衡效果和成本。

## 8. 安全设计

1. **网关鉴权**：MCP 调用通过令牌认证。
2. **配置隔离**：敏感信息通过 `.env` 管理，不写入代码。
3. **输入校验**：FastAPI + Pydantic 进行请求参数校验。
4. **错误最小暴露**：对外只返回必要错误信息，详细堆栈写入日志。

## 9. 部署架构

基于 Docker Compose：

- `backend`：FastAPI + Agent 核心
- `frontend`：Vite + React
- `redis`：会话与缓存
- `postgres`：持久化存储

详见 `docker-compose.yml` 以及 `docs/architecture.md` 的部署图。

## 10. 未来规划

1. 会话与任务状态从内存迁移到 Redis/PostgreSQL。
2. 构建统一观测面板（日志、链路、指标）。
3. 完善评测体系（意图准确率、响应时延、工具成功率）。
4. 增加审批提醒、费用合规、差旅政策校验等企业能力。
