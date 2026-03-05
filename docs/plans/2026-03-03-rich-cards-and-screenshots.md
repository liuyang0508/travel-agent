# 结构化卡片 + 完整闭环截图 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 AI 差旅通增加结构化卡片组件和 TaskPanel 实时进度，使系统能展示完整的出差闭环流程，并替换 README 截图。

**Architecture:** 后端各 Agent 在 events 中追加 `structured_data` 和 `task_update` 事件，SSE 层转发给前端。前端 useChat 解析新事件类型，将卡片数据附加到消息 metadata，MessageBubble 渲染卡片组件。

**Tech Stack:** Python/FastAPI/LangGraph（后端）、React/TypeScript/TailwindCSS/Zustand（前端）、lucide-react（图标）

---

## Phase 1: 类型定义与 Mock 数据

### Task 1: 前端类型定义扩展

**Files:**
- Modify: `frontend/src/types/index.ts`

**Step 1: 新增结构化数据类型**

在 `types/index.ts` 末尾追加以下类型：

```typescript
export interface FlightItem {
  flightId: string
  airline: string
  flightNo: string
  origin: string
  destination: string
  departTime: string
  arriveTime: string
  price: number
  cabinClass: string
  remainingSeats: number
}

export interface HotelItem {
  hotelId: string
  name: string
  address: string
  pricePerNight: number
  rating: number
  stars: number
  amenities: string[]
  distanceToDestination: string
}

export interface TrainItem {
  trainId: string
  trainNo: string
  origin: string
  destination: string
  departTime: string
  arriveTime: string
  duration: string
  price: number
  seatType: string
  remainingSeats: number
}

export interface BookingResultItem {
  orderId: string
  bookingType: 'flight' | 'hotel' | 'train'
  status: 'confirmed' | 'failed' | 'pending'
  message: string
  totalPrice: number
  details: Record<string, string>
}

export interface ApprovalInfoItem {
  applyId: string
  status: 'pending' | 'approved' | 'rejected'
  applicant: string
  destination: string
  dateRange: string
  reason: string
  approver: string
  submittedAt: string
  approvedAt?: string
  timeline: Array<{ step: string; status: 'done' | 'current' | 'upcoming'; time?: string }>
}

export type StructuredCardType =
  | 'flight_list'
  | 'hotel_list'
  | 'train_list'
  | 'booking_result'
  | 'approval_status'

export interface StructuredCard {
  cardType: StructuredCardType
  items: FlightItem[] | HotelItem[] | TrainItem[] | BookingResultItem[] | ApprovalInfoItem[]
}
```

**Step 2: 扩展 ChatMessage 的 metadata 约定**

在 `ChatMessage` 接口的 metadata 注释中说明 `cards` 字段：

```typescript
export interface ChatMessage {
  messageId: string
  sessionId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  /** cards?: StructuredCard[] — 结构化卡片数据，由 useChat 从 structured_data 事件中收集 */
  metadata?: Record<string, unknown>
  timestamp: string
}
```

**Step 3: 验证** — 运行 `cd frontend && npx tsc --noEmit`，确认无类型错误。

---

### Task 2: 后端 Mock 数据增强

**Files:**
- Modify: `backend/app/mcp/tools/mock_data.py`

**Step 1: 增强航班 mock 数据**

替换 `_mock_flights` 函数，返回更丰富的数据：

```python
def _mock_flights(params: dict) -> list[dict]:
    origin = params.get("origin", "北京")
    destination = params.get("destination", "上海")
    date = params.get("date", "2026-03-10")
    return [
        {
            "flight_id": "FL001",
            "airline": "中国国航",
            "flight_no": "CA1501",
            "origin": origin,
            "destination": destination,
            "depart_time": f"{date} 07:30",
            "arrive_time": f"{date} 09:45",
            "price": 1280,
            "cabin_class": "经济舱",
            "remaining_seats": 23,
        },
        {
            "flight_id": "FL002",
            "airline": "东方航空",
            "flight_no": "MU5101",
            "origin": origin,
            "destination": destination,
            "depart_time": f"{date} 09:00",
            "arrive_time": f"{date} 11:15",
            "price": 1150,
            "cabin_class": "经济舱",
            "remaining_seats": 8,
        },
        {
            "flight_id": "FL003",
            "airline": "中国国航",
            "flight_no": "CA1505",
            "origin": origin,
            "destination": destination,
            "depart_time": f"{date} 14:00",
            "arrive_time": f"{date} 16:10",
            "price": 2580,
            "cabin_class": "商务舱",
            "remaining_seats": 4,
        },
    ]
```

**Step 2: 增强酒店 mock 数据**

替换 `_mock_hotels` / `_mock_hotel_list` 函数：

```python
def _mock_hotel_list(params: dict) -> list[dict]:
    city = params.get("city", "上海")
    return [
        {
            "hotel_id": "HT001",
            "name": f"{city}浦东丽思卡尔顿酒店",
            "address": f"{city}浦东新区世纪大道8号",
            "price_per_night": 1680,
            "rating": 4.8,
            "stars": 5,
            "amenities": ["WiFi", "早餐", "健身房", "泳池", "商务中心"],
            "distance_to_destination": "0.5km",
        },
        {
            "hotel_id": "HT002",
            "name": f"{city}外滩华尔道夫酒店",
            "address": f"{city}黄浦区中山东一路2号",
            "price_per_night": 1280,
            "rating": 4.6,
            "stars": 5,
            "amenities": ["WiFi", "早餐", "健身房", "SPA"],
            "distance_to_destination": "1.2km",
        },
        {
            "hotel_id": "HT003",
            "name": f"{city}虹桥全季酒店",
            "address": f"{city}闵行区申虹路9号",
            "price_per_night": 458,
            "rating": 4.3,
            "stars": 3,
            "amenities": ["WiFi", "早餐"],
            "distance_to_destination": "3.5km",
        },
    ]
```

**Step 3: 增强高铁 mock 数据**

替换 `_mock_trains` 函数：

```python
def _mock_trains(params: dict) -> list[dict]:
    origin = params.get("origin", "北京")
    destination = params.get("destination", "上海")
    date = params.get("date", "2026-03-10")
    return [
        {
            "train_id": "TR001",
            "train_no": "G1",
            "origin": f"{origin}南站",
            "destination": f"{destination}虹桥站",
            "depart_time": f"{date} 07:00",
            "arrive_time": f"{date} 11:28",
            "duration": "4小时28分",
            "price": 553,
            "seat_type": "二等座",
            "remaining_seats": 156,
        },
        {
            "train_id": "TR002",
            "train_no": "G3",
            "origin": f"{origin}南站",
            "destination": f"{destination}虹桥站",
            "depart_time": f"{date} 08:00",
            "arrive_time": f"{date} 12:23",
            "duration": "4小时23分",
            "price": 553,
            "seat_type": "二等座",
            "remaining_seats": 42,
        },
        {
            "train_id": "TR003",
            "train_no": "G5",
            "origin": f"{origin}南站",
            "destination": f"{destination}虹桥站",
            "depart_time": f"{date} 09:00",
            "arrive_time": f"{date} 13:28",
            "duration": "4小时28分",
            "price": 933,
            "seat_type": "一等座",
            "remaining_seats": 3,
        },
    ]
```

**Step 4: 增强预订结果 mock 数据**

替换 `_mock_book_flight` / `_mock_book_hotel` / `_mock_book_train`：

```python
def _mock_book_flight(params: dict) -> dict:
    return {
        "order_id": f"ORD-FL-{int(time.time())}",
        "status": "confirmed",
        "message": "航班预订成功",
        "booking_type": "flight",
        "total_price": 1280,
        "details": {
            "航班": "CA1501",
            "航空公司": "中国国航",
            "出发": "北京 → 上海",
            "时间": "2026-03-10 07:30",
        },
    }

def _mock_book_hotel(params: dict) -> dict:
    return {
        "order_id": f"ORD-HT-{int(time.time())}",
        "status": "confirmed",
        "message": "酒店预订成功",
        "booking_type": "hotel",
        "total_price": 3360,
        "details": {
            "酒店": "上海浦东丽思卡尔顿酒店",
            "入住": "2026-03-10",
            "离店": "2026-03-12",
            "房型": "豪华大床房",
        },
    }

def _mock_book_train(params: dict) -> dict:
    return {
        "order_id": f"ORD-TR-{int(time.time())}",
        "status": "confirmed",
        "message": "高铁票预订成功",
        "booking_type": "train",
        "total_price": 553,
        "details": {
            "车次": "G1",
            "区间": "北京南站 → 上海虹桥站",
            "时间": "2026-03-10 07:00",
            "座位": "二等座",
        },
    }
```

**Step 5: 增强审批状态 mock 数据**

替换 `_mock_travel_apply_status`：

```python
def _mock_travel_apply_status(params: dict) -> dict:
    apply_id = params.get("apply_id", "TA-20260303-001")
    return {
        "apply_id": apply_id,
        "status": "approved",
        "applicant": "刘洋",
        "destination": "上海",
        "date_range": "2026-03-10 ~ 2026-03-12",
        "reason": "客户拜访",
        "approver": "张经理",
        "submitted_at": "2026-03-03 10:30",
        "approved_at": "2026-03-03 14:15",
        "timeline": [
            {"step": "提交申请", "status": "done", "time": "03-03 10:30"},
            {"step": "部门审批", "status": "done", "time": "03-03 14:15"},
            {"step": "审批通过", "status": "done", "time": "03-03 14:15"},
        ],
    }
```

**Step 6: 增强出差申请提交 mock 数据**

替换 `_mock_travel_apply`：

```python
def _mock_travel_apply(params: dict) -> dict:
    return {
        "apply_id": f"TA-20260303-001",
        "status": "pending",
        "message": "出差申请已提交，等待审批",
        "applicant": params.get("user_id", "default_user"),
        "destination": params.get("destination", "上海"),
        "date_range": f"{params.get('start_date', '2026-03-10')} ~ {params.get('end_date', '2026-03-12')}",
        "reason": params.get("reason", "客户拜访"),
        "submitted_at": "2026-03-03 10:30",
        "timeline": [
            {"step": "提交申请", "status": "done", "time": "03-03 10:30"},
            {"step": "部门审批", "status": "current", "time": ""},
            {"step": "审批完成", "status": "upcoming", "time": ""},
        ],
    }
```

**Step 7: 验证** — 运行 `cd backend && python -c "from app.mcp.tools.mock_data import get_mock_response; print(get_mock_response('get_flights', {'origin':'北京','destination':'上海','date':'2026-03-10'}))"` 确认数据正确。

---

## Phase 2: 后端数据流改造

### Task 3: Orchestrator 推送 task_update

**Files:**
- Modify: `backend/app/agents/orchestrator.py`

**Step 1: 在 stream_agent_pipeline 中集成 TaskPlanner**

在 `stream_agent_pipeline` 函数中，进入 graph.astream 前：
1. 根据意图创建 TaskPlan
2. 推送初始 `task_update` 事件

在 astream 循环中：
1. 检测 `current_agent` 变化时推送 task 状态更新

具体改动要点：
- import `TaskPlanner` 和 `TaskPlan` 相关类
- 在 yield thinking 事件后，先做一次意图预判（或在 intent_recognition 完成后），调用 `TaskPlanner.create_plan(intent)` 生成计划
- 推送 `{"type": "task_update", "data": {"plan": plan.model_dump()}}`
- 在 astream 循环中，当检测到 agent 节点完成时，推送对应 task 的状态变更

**Step 2: 验证** — 启动后端，发送一条消息，检查 SSE 输出中是否包含 `task_update` 事件。

---

### Task 4: itinerary_agent 推送 structured_data

**Files:**
- Modify: `backend/app/agents/itinerary_agent.py`

**Step 1: 在 MCP 工具调用后追加 structured_data 事件**

在 itinerary_agent 函数中，当 `get_flights` / `get_hotel_list` / `get_trains` 返回数据后，除了保存到 `tool_results`，还在 `events` 中追加：

```python
events.append({
    "event_type": "structured_data",
    "agent_role": "itinerary",
    "content": "",
    "metadata": {
        "card_type": "flight_list",
        "items": flights_data,
    },
})
```

对 hotel_list 和 train_list 同理。

**Step 2: 验证** — 发送行程查询消息，检查 SSE 输出中是否包含 `structured_data` 事件。

---

### Task 5: travel_apply_agent 推送 structured_data

**Files:**
- Modify: `backend/app/agents/travel_apply_agent.py`

**Step 1: 在提交申请和查询状态后追加 structured_data 事件**

- `travel_apply` 调用后 → 追加 `card_type: "approval_status"` 事件
- `travel_apply_status` 调用后 → 追加 `card_type: "approval_status"` 事件

---

### Task 6: booking_agent 推送 structured_data

**Files:**
- Modify: `backend/app/agents/booking_agent.py`

**Step 1: 在预订成功后追加 structured_data 事件**

- `book_flight` / `book_hotel` / `book_train` 调用后 → 追加 `card_type: "booking_result"` 事件

---

### Task 7: SSE 层适配

**Files:**
- Modify: `backend/app/api/chat.py`

**Step 1: 在 SSE 流中识别并转发新事件类型**

在 `stream_chat` 端点的事件处理循环中，新增对 `structured_data` 和 `task_update` 的处理：

- `type == "agent_event"` 且 `data.event_type == "structured_data"` → 转为 `{"chunk_type": "structured_data", "data": data.metadata}`
- `type == "task_update"` → 转为 `{"chunk_type": "task_update", "data": ...}`

其他事件保持原样。

**Step 2: 验证** — 完整测试 SSE 流，确认前端能收到 `structured_data` 和 `task_update` 的 chunk。

---

## Phase 3: 前端卡片组件

### Task 8: FlightCard 组件

**Files:**
- Create: `frontend/src/components/cards/FlightCard.tsx`

**Step 1: 实现 FlightCard**

展示：航空公司+航班号 | 出发时间→到达时间 | 价格+舱位+余票。
商务舱金色标签，余票<5 红色提示。底部「选择此航班」按钮。

---

### Task 9: HotelCard 组件

**Files:**
- Create: `frontend/src/components/cards/HotelCard.tsx`

**Step 1: 实现 HotelCard**

展示：酒店名+星级图标 | 地址+距离 | 价格/晚+评分 | 设施标签行。
底部「预订此酒店」按钮。

---

### Task 10: TrainCard 组件

**Files:**
- Create: `frontend/src/components/cards/TrainCard.tsx`

**Step 1: 实现 TrainCard**

展示：车次 | 出发站→到达站+历时 | 座位类型+价格+余票。
余票<5 红色提示。底部「选择此车次」按钮。

---

### Task 11: BookingResultCard 组件

**Files:**
- Create: `frontend/src/components/cards/BookingResultCard.tsx`

**Step 1: 实现 BookingResultCard**

展示：订单号 | 预订类型图标 | 状态标签 | 详情键值对。
成功绿色边框+勾号，失败红色边框+叹号。

---

### Task 12: ApprovalStatusCard 组件

**Files:**
- Create: `frontend/src/components/cards/ApprovalStatusCard.tsx`

**Step 1: 实现 ApprovalStatusCard**

展示：申请ID | 状态标签 | 竖向审批时间线步骤条 | 审批人信息。
已通过时底部「开始规划行程」引导按钮。

---

### Task 13: CardRenderer + 导出

**Files:**
- Create: `frontend/src/components/cards/CardRenderer.tsx`
- Create: `frontend/src/components/cards/index.ts`

**Step 1: 实现 CardRenderer**

根据 `card.cardType` 分发到对应卡片组件。对 `_list` 类型渲染多个卡片。

**Step 2: 创建 barrel export**

`index.ts` 导出 CardRenderer 和所有卡片组件。

---

### Task 14: CSS 动画与视觉升级

**Files:**
- Modify: `frontend/src/styles/globals.css`

**Step 1: 添加 fadeIn 动画和卡片样式**

```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fadeIn {
  animation: fadeIn 0.3s ease-out;
}

.card-action-btn {
  @apply text-xs px-3 py-1.5 rounded-lg font-medium transition-all hover:scale-105 active:scale-95;
}
```

---

## Phase 4: 前端集成

### Task 15: useChat Hook 适配

**Files:**
- Modify: `frontend/src/hooks/useChat.ts`

**Step 1: 处理 structured_data chunk**

在 SSE 解析循环中新增：

```typescript
} else if (chunk.chunk_type === 'structured_data') {
  pendingCards.push({
    cardType: chunk.data.card_type,
    items: chunk.data.items,
  })
}
```

流结束后，将 `pendingCards` 附加到助手消息：

```typescript
if (assistantContent) {
  addMessage({
    ...
    metadata: pendingCards.length > 0 ? { cards: pendingCards } : undefined,
  })
}
```

**Step 2: 验证** — 发送行程查询，检查浏览器 console 中 addMessage 调用时 metadata 是否包含 cards。

---

### Task 16: MessageBubble 集成卡片渲染

**Files:**
- Modify: `frontend/src/components/MessageBubble.tsx`

**Step 1: 在助手消息中渲染卡片**

```typescript
import { CardRenderer } from './cards'
import type { StructuredCard } from '../types'

// 在助手消息的 Markdown 渲染之后：
{!isUser && message.metadata?.cards && (
  <div className="mt-3 space-y-3 animate-fadeIn">
    {(message.metadata.cards as StructuredCard[]).map((card, i) => (
      <CardRenderer key={i} card={card} />
    ))}
  </div>
)}
```

**Step 2: 验证** — 完整走通一次行程查询流程，确认卡片正确渲染在消息气泡中。

---

## Phase 5: 文档更新

### Task 17: README 截图区更新

**Files:**
- Modify: `README.md`

**Step 1: 更新截图展示区**

将现有 3 张截图区替换为 6 张，使用新的文件名和描述。旧截图文件保留（或运行系统后替换为新截图）。

---

## 执行顺序与依赖关系

```
Phase 1: Task 1 (前端类型) + Task 2 (Mock 数据) — 并行
    ↓
Phase 2: Task 3~7 (后端数据流) — 顺序执行
    ↓
Phase 3: Task 8~14 (前端卡片) — 可并行
    ↓
Phase 4: Task 15~16 (集成) — 顺序执行
    ↓
Phase 5: Task 17 (文档)
```

总计 17 个 Task，预计涉及 **新增 8 文件 + 改动 10 文件**。
