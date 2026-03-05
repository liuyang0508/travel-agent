/**
 * @file 聊天状态管理 Store
 * @description 基于 Zustand 的全局聊天状态管理，维护当前会话 ID、消息列表、
 *   加载状态以及 Agent 实时事件队列。供聊天相关组件和 Hook 共享状态。
 */

import { create } from 'zustand'
import type { ChatMessage, AgentEvent } from '../types'

/**
 * 聊天状态接口
 * @description 定义聊天模块的全部状态字段和操作方法
 */
interface ChatState {
  /** 当前会话 ID，首次对话前为 null，由后端在首次响应时分配 */
  sessionId: string | null
  /** 当前会话的所有消息列表（按时间顺序） */
  messages: ChatMessage[]
  /** 是否正在等待 AI 回复 */
  isLoading: boolean
  /** Agent 执行过程中产生的实时事件列表 */
  agentEvents: AgentEvent[]
  /** 向消息列表追加一条新消息 */
  addMessage: (msg: ChatMessage) => void
  /** 设置加载状态 */
  setLoading: (loading: boolean) => void
  /** 向事件队列追加一个 Agent 事件 */
  addAgentEvent: (event: AgentEvent) => void
  /** 清空 Agent 事件队列（通常在发送新消息前调用） */
  clearEvents: () => void
  /** 设置当前会话 ID */
  setSessionId: (id: string) => void
}

/**
 * 聊天状态 Store 实例
 * @description 使用 Zustand create 创建的全局 Store，组件通过 useChatStore() 访问
 */
export const useChatStore = create<ChatState>((set) => ({
  sessionId: null,
  messages: [],
  isLoading: false,
  agentEvents: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setLoading: (loading) => set({ isLoading: loading }),
  addAgentEvent: (event) => set((s) => ({ agentEvents: [...s.agentEvents, event] })),
  clearEvents: () => set({ agentEvents: [] }),
  setSessionId: (id) => set({ sessionId: id }),
}))
