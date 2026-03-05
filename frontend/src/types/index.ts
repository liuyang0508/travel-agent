/**
 * @file 全局类型定义
 * @description 定义前端应用中所有核心数据结构的 TypeScript 类型，
 *   包括聊天消息、任务节点、任务计划、Agent 事件以及流式数据块。
 */

/**
 * 聊天消息
 * @description 表示一条用户与 AI 助手之间的对话消息
 */
export interface ChatMessage {
  /** 消息唯一标识 */
  messageId: string
  /** 所属会话的唯一标识 */
  sessionId: string
  /** 消息角色：用户 / AI 助手 / 系统 */
  role: 'user' | 'assistant' | 'system'
  /** 消息文本内容 */
  content: string
  /** 可选的扩展元数据，用于携带前后端约定的附加信息 */
  metadata?: Record<string, unknown>
  /** 消息创建时间（ISO 8601 格式） */
  timestamp: string
}

/**
 * 任务节点
 * @description 表示任务计划中的一个可执行子任务，由特定 Agent 角色负责
 */
export interface TaskNode {
  /** 任务唯一标识 */
  taskId: string
  /** 任务名称（简短描述） */
  name: string
  /** 任务详细描述 */
  description: string
  /** 负责执行此任务的 Agent 角色名称 */
  agentRole: string
  /** 任务当前状态 */
  status: 'pending' | 'running' | 'waiting_user' | 'completed' | 'failed' | 'cancelled'
  /** 前置依赖的任务 ID 列表，当前任务需等待这些任务完成后才能开始 */
  dependencies: string[]
  /** 任务开始执行的时间（ISO 8601 格式） */
  startedAt?: string
  /** 任务完成的时间（ISO 8601 格式） */
  completedAt?: string
}

/**
 * 任务计划
 * @description 由 Orchestrator Agent 生成的完整任务拆解方案，包含多个有序的子任务
 */
export interface TaskPlan {
  /** 计划唯一标识 */
  planId: string
  /** 所属会话的唯一标识 */
  sessionId: string
  /** 计划包含的子任务列表 */
  tasks: TaskNode[]
  /** 计划创建时间（ISO 8601 格式） */
  createdAt: string
}

/**
 * Agent 事件
 * @description 后端 Agent 在执行过程中产生的实时事件，用于向前端推送 Agent 的工作动态
 */
export interface AgentEvent {
  /** 事件类型：思考 / 工具调用 / 工具返回 / 消息输出 / 错误 */
  eventType: 'thinking' | 'tool_call' | 'tool_result' | 'message' | 'error'
  /** 产生事件的 Agent 角色名称 */
  agentRole: string
  /** 关联的任务 ID（如果事件与特定任务相关） */
  taskId?: string
  /** 事件的文本内容 */
  content: string
  /** 可选的扩展元数据 */
  metadata?: Record<string, unknown>
  /** 事件产生时间（ISO 8601 格式） */
  timestamp: string
}

/**
 * 流式数据块
 * @description SSE 流中单条数据的结构，前端通过 chunk_type 分发到不同的处理逻辑
 */
export interface StreamChunk {
  /** 数据块类型：文本 token / Agent 事件 / 任务状态更新 / 流结束 / 错误 */
  chunkType: 'token' | 'agent_event' | 'task_update' | 'done' | 'error'
  /** 数据块的载荷，具体结构取决于 chunkType */
  data: Record<string, unknown>
}

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
