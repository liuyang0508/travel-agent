# 结构化卡片组件 + 完整闭环截图设计

> 日期：2026-03-03
> 状态：已确认
> 目标受众：客户/老板演示

---

## 1. 背景与问题

当前 README 的 3 张截图只展示了欢迎页和简单对话，没有体现系统的核心能力：

- TaskPanel 始终为空（后端未推送 `task_update`）
- 行程推荐结果只以纯文本/Markdown 显示，无结构化卡片
- 无预订结果、审批状态等专用展示组件
- 截图无法展示"意图识别 → 出差申请 → 审批 → 行程规划 → 预订"的完整闭环

## 2. 方案概述

**后端 Mock + 前端全套组件**：

- 后端各 Agent 增加 `structured_data` 事件推送 + `task_update` 推送
- 前端新增 5 类结构化卡片组件 + TaskPanel 实时进度
- Mock 数据层增强，支持在 LLM 可用但钉钉 API 不通时完整演示
- 截图从 3 张扩展为 6 张，覆盖完整闭环

## 3. 数据流架构

### 3.1 新增 SSE chunk 类型

| chunk_type | data 结构 | 用途 |
|---|---|---|
| `structured_data` | `{card_type, items}` | 结构化卡片数据 |
| `task_update` | `{plan}` 或 `{task_id, status, ...}` | 任务进度 |

### 3.2 改进后的数据流

```
Agent → MCP tool_results → 同时：
  1. LLM 消化成文本 → token 推送 → Markdown 渲染
  2. structured_data 推送 → 卡片组件渲染（嵌入消息气泡下方）
```

前端消费方式：`structured_data` 事件将卡片数据附加到当前助手消息的 `metadata.cards` 中，`MessageBubble` 在 Markdown 之后渲染 `CardRenderer`。

## 4. 后端改动

### 4.1 Orchestrator — task_update 推送

- 进入 Agent 前：`TaskPlanner.create_plan()` → 推送完整 `TaskPlan`
- Agent 节点完成后：推送 task 状态更新（`running` → `completed`）
- 异常时：推送 task 状态 `failed`

涉及文件：`orchestrator.py`

### 4.2 各 Agent — structured_data 推送

| Agent | card_type |
|---|---|
| `itinerary_agent` | `flight_list` / `hotel_list` / `train_list` |
| `booking_agent` | `booking_result` |
| `travel_apply_agent` | `approval_status` |

每个 Agent 在 MCP 调用后，往 `events` 追加 `structured_data` 事件。

涉及文件：`itinerary_agent.py`、`booking_agent.py`、`travel_apply_agent.py`

### 4.3 Mock 数据增强

- 航班：航空公司、航班号、经停、舱位等级
- 酒店：星级、评分、设施标签、距离
- 高铁：车次、历时、座位类型、余票
- 预订结果：订单号、确认时间、总价
- 审批状态：审批人、审批链、时间线

涉及文件：`mcp/tools/mock_data.py`

### 4.4 SSE 层适配

`api/chat.py` 识别并转发 `structured_data` 和 `task_update` 事件。

涉及文件：`api/chat.py`

## 5. 前端新增组件

### 5.1 结构化卡片（src/components/cards/）

| 组件 | 展示内容 | 视觉特色 |
|---|---|---|
| `FlightCard` | 航空公司+航班号、出发→到达时间、价格+舱位 | 蓝色系，经济舱/商务舱颜色编码 |
| `HotelCard` | 酒店名+星级、地址+距离、价格/晚+评分、设施标签 | 紫色系，星级图标 |
| `TrainCard` | 车次、出发站→到达站+历时、座位+价格+余票 | 蓝色系，余票<5红色提示 |
| `BookingResultCard` | 订单号、类型图标、状态、详情 | 成功绿色/失败红色边框 |
| `ApprovalStatusCard` | 申请ID、状态、审批时间线（竖向步骤条） | 步骤条，已通过显示引导按钮 |

### 5.2 CardRenderer 分发组件

根据 `card_type` 分发到对应卡片组件。

### 5.3 MessageBubble 改造

助手消息：先 Markdown → 再检查 `metadata.cards` 渲染 CardRenderer。

### 5.4 useChat Hook 改造

处理 `structured_data` chunk：累积到 `pendingCards`，流结束时附加到助手消息 `metadata.cards`。

### 5.5 视觉升级

- `lucide-react` 图标
- 卡片进入 `animate-fadeIn` 动画
- 按钮 hover 微缩放
- 价格 `tabular-nums` 等宽数字
- 颜色编码：交通蓝、酒店紫、成功绿、失败红、等待琥珀

### 5.6 类型定义扩展

新增：`FlightItem`、`HotelItem`、`TrainItem`、`BookingResult`、`ApprovalInfo`、`StructuredCard`。

## 6. 截图规划

6 张截图，覆盖完整闭环：

| 序号 | 文件名 | 场景 | 关键展示 |
|---|---|---|---|
| 1 | `01-welcome.png` | 欢迎页 | 品牌首屏 + 快捷入口 |
| 2 | `02-intent-and-apply.png` | 意图识别 + 出差申请 | 对话 + TaskPanel 3个任务 + Agent活动 |
| 3 | `03-approval-status.png` | 审批状态 | ApprovalStatusCard + TaskPanel进度 |
| 4 | `04-itinerary-plan.png` | 行程规划 | FlightCard + HotelCard + TrainCard |
| 5 | `05-booking-result.png` | 预订执行 | BookingResultCard + TaskPanel全部完成 |
| 6 | `06-task-complete.png` | 全流程完成 | 行程总结 + TaskPanel 全绿 |

## 7. 文件改动清单

### 后端（6 文件）

- `backend/app/agents/orchestrator.py` — task_update 推送
- `backend/app/agents/itinerary_agent.py` — structured_data 推送
- `backend/app/agents/booking_agent.py` — structured_data 推送
- `backend/app/agents/travel_apply_agent.py` — structured_data 推送
- `backend/app/mcp/tools/mock_data.py` — 数据增强
- `backend/app/api/chat.py` — SSE 层适配

### 前端（新增 8 文件 + 改动 4 文件）

新增：
- `frontend/src/components/cards/FlightCard.tsx`
- `frontend/src/components/cards/HotelCard.tsx`
- `frontend/src/components/cards/TrainCard.tsx`
- `frontend/src/components/cards/BookingResultCard.tsx`
- `frontend/src/components/cards/ApprovalStatusCard.tsx`
- `frontend/src/components/cards/CardRenderer.tsx`
- `frontend/src/components/cards/index.ts`

改动：
- `frontend/src/components/MessageBubble.tsx`
- `frontend/src/hooks/useChat.ts`
- `frontend/src/types/index.ts`
- `frontend/src/styles/globals.css`

### 文档（1 文件）

- `README.md` — 截图区更新为 6 张
