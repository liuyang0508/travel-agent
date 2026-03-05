# AI差旅通架构图

本文档给出系统级、模块级和部署级的 Mermaid 架构图。  
设计细节请参考 [技术方案文档](./technical-design.md)。

## 1. 系统架构图（分层）

```mermaid
flowchart TD
    subgraph L1["前端层"]
        FE1["ChatPanel 聊天面板"]
        FE2["TaskPanel 任务面板"]
        FE3["Zustand 状态管理"]
    end

    subgraph L2["API 接入层（FastAPI）"]
        API1["/health"]
        API2["/api/chat/send"]
        API3["/api/chat/stream (SSE)"]
        API4["/api/chat/ws/{session_id}"]
        API5["/api/tasks/*"]
    end

    subgraph L3["Agent 编排层（LangGraph）"]
        ORC["Orchestrator"]
        IA["Intent Agent"]
        QR["Query Rewriter"]
        TA["Travel Apply Agent"]
        IT["Itinerary Agent"]
        BK["Booking Agent"]
    end

    subgraph L4["引擎能力层"]
        TP["TaskPlanner (DAG)"]
        SR["SkillRegistry"]
        MM["MemoryManager"]
        CM["ContextManager"]
        MR["ModelRouter"]
        PE["PromptEngine"]
    end

    subgraph L5["集成层"]
        MCP["MCP Client"]
        HG["Higress MCP 网关"]
        DD["钉钉差旅 API"]
    end

    subgraph L6["存储层"]
        RD["Redis"]
        PG["PostgreSQL"]
        MEM["内存会话/任务缓存（当前）"]
    end

    FE1 --> API2
    FE1 --> API3
    FE1 --> API4
    FE2 --> API5

    API2 --> ORC
    API3 --> ORC
    API4 --> ORC
    API5 --> TP

    ORC --> IA
    IA --> QR
    IA --> TA
    IA --> IT
    IA --> BK

    ORC --> MM
    ORC --> CM
    ORC --> MR
    ORC --> PE
    ORC --> TP
    TP --> SR

    TA --> MCP
    IT --> MCP
    BK --> MCP
    MCP --> HG --> DD

    MM --> RD
    TP --> PG
    API2 --> MEM
    API5 --> MEM
```

## 2. 核心模块依赖图

```mermaid
flowchart LR
    ORC["orchestrator.py"] --> IA["intent_agent.py"]
    ORC --> QR["query_rewriter.py"]
    ORC --> TA["travel_apply_agent.py"]
    ORC --> IT["itinerary_agent.py"]
    ORC --> BK["booking_agent.py"]
    ORC --> STATE["state.py"]
    ORC --> MR["model_router.py"]

    IA --> PE["prompt_engine.py"]
    IA --> MR
    QR --> PE
    QR --> MR
    TA --> MR
    IT --> MR
    IT --> PE

    TA --> MCP["mcp/client.py"]
    IT --> MCP
    BK --> MCP
    MCP --> MOCK["mcp/tools/mock_data.py"]

    TP["task_planner.py"] --> SR["skill_registry.py"]
    TP --> MR
    ORC --> TP
    ORC --> MM["memory_manager.py"]
    ORC --> CM["context_manager.py"]
```

## 3. 部署架构图（Docker Compose）

```mermaid
flowchart TD
    USER["浏览器用户"] --> FE["frontend 容器 :3000"]
    FE --> BE["backend 容器 :8000"]

    BE --> REDIS["redis:7-alpine :6379"]
    BE --> POSTGRES["postgres:16-alpine :5432"]
    BE --> HIG["Higress MCP 网关"]
    HIG --> DING["钉钉差旅 API"]

    subgraph NET["Docker Compose 网络"]
        FE
        BE
        REDIS
        POSTGRES
    end
```

---

更多交互流程请参考 [时序图文档](./sequence-diagrams.md) 与 [流程图文档](./flow-charts.md)。
