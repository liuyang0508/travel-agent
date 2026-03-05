/**
 * @file 聊天核心 Hook
 * @description 封装与后端聊天 API 的 SSE 流式通信逻辑。
 *   处理用户消息发送、流式响应解析，并将 token、Agent 事件、任务更新
 *   分发到对应的 Zustand Store 中。
 */

import { useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useTaskStore } from '../stores/taskStore'
import type { ChatMessage, StructuredCard } from '../types'

/** 后端聊天接口的基础路径 */
const API_BASE = '/api/chat'
/** 是否启用前端调试日志（仅开发环境） */
const ENABLE_DEBUG_LOG = import.meta.env.DEV

/**
 * 统一的前端日志输出方法。
 * @description 仅在开发环境输出，避免生产环境控制台噪音。
 */
function debugLog(message: string, payload?: unknown) {
  if (!ENABLE_DEBUG_LOG) return
  if (payload === undefined) {
    console.info(`[useChat] ${message}`)
    return
  }
  console.info(`[useChat] ${message}`, payload)
}

/**
 * 将下划线命名转换为驼峰命名
 * @description 后端使用 Python 风格的下划线命名，前端使用 TypeScript 风格的驼峰命名
 */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
}

/**
 * 递归转换对象的所有键为驼峰命名
 * @description 用于转换后端返回的数据结构，使其符合前端类型定义
 */
function convertKeysToCamel(obj: unknown): unknown {
  if (Array.isArray(obj)) {
    return obj.map(convertKeysToCamel)
  } else if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj as Record<string, unknown>).reduce((acc, key) => {
      const camelKey = toCamelCase(key)
      acc[camelKey] = convertKeysToCamel((obj as Record<string, unknown>)[key])
      return acc
    }, {} as Record<string, unknown>)
  }
  return obj
}

/**
 * 聊天通信 Hook
 * @description 提供 sendMessage 方法，内部完成以下流程：
 *   1. 将用户消息写入 Store 并展示
 *   2. 通过 SSE 流向后端发送请求
 *   3. 逐块解析响应：累积 token 拼成助手回复、分发 Agent 事件、更新任务状态
 *   4. 错误时自动生成错误提示消息
 * @returns {{ sendMessage: (content: string) => Promise<void> }} 发送消息的方法
 */
export function useChat() {
  const { sessionId, setSessionId, addMessage, setLoading, addAgentEvent, clearEvents } =
    useChatStore()
  const { setPlan, updateTask } = useTaskStore()

  /**
   * 发送用户消息并处理流式响应
   * @param content - 用户输入的消息文本
   */
  const sendMessage = useCallback(
    async (content: string) => {
      debugLog('开始发送消息', { contentPreview: content.slice(0, 30), sessionId })
      const userMsg: ChatMessage = {
        messageId: crypto.randomUUID(),
        sessionId: sessionId || '',
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      }
      addMessage(userMsg)
      setLoading(true)
      clearEvents()

      try {
        const resp = await fetch(`${API_BASE}/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            message: content,
          }),
        })

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
        debugLog('SSE 请求建立成功')

        const reader = resp.body?.getReader()
        if (!reader) throw new Error('No reader')

        const decoder = new TextDecoder()
        let buffer = ''
        let assistantContent = ''
        const pendingCards: StructuredCard[] = []

        // 持续读取 SSE 流，直到流结束
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          // 最后一个元素可能是不完整的行，保留到下次拼接
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const payload = line.slice(6).trim()
            if (payload === '[DONE]') break

            try {
              const chunk = JSON.parse(payload)
              if (chunk.chunk_type === 'token') {
                assistantContent += chunk.data.token || ''
              } else if (chunk.chunk_type === 'agent_event') {
                addAgentEvent(chunk.data)
              } else if (chunk.chunk_type === 'structured_data') {
                // 转换后端的下划线命名为前端的驼峰命名
                const convertedItems = convertKeysToCamel(chunk.data.items)
                pendingCards.push({
                  cardType: chunk.data.card_type,
                  items: convertedItems,
                } as StructuredCard)
                debugLog('收到 structured_data', { cardType: chunk.data.card_type, itemsCount: (chunk.data.items as unknown[])?.length })
              } else if (chunk.chunk_type === 'task_update') {
                if (chunk.data.plan) setPlan(chunk.data.plan)
                if (chunk.data.task_id) updateTask(chunk.data.task_id, chunk.data)
              }
              // 后端首次响应时会携带 session_id，用于后续请求关联同一会话
              if (chunk.data?.session_id) {
                setSessionId(chunk.data.session_id)
                debugLog('更新会话 ID', chunk.data.session_id)
              }
            } catch {
              // 跳过格式异常的数据块
            }
          }
        }

        if (assistantContent) {
          debugLog('助手响应拼接完成', { contentLength: assistantContent.length, cardsCount: pendingCards.length })
          addMessage({
            messageId: crypto.randomUUID(),
            sessionId: sessionId || '',
            role: 'assistant',
            content: assistantContent,
            metadata: pendingCards.length > 0 ? { cards: pendingCards } : undefined,
            timestamp: new Date().toISOString(),
          })
        }
      } catch (err) {
        debugLog('请求异常', err)
        addMessage({
          messageId: crypto.randomUUID(),
          sessionId: sessionId || '',
          role: 'assistant',
          content: `抱歉，请求出错了：${err instanceof Error ? err.message : '未知错误'}`,
          timestamp: new Date().toISOString(),
        })
      } finally {
        setLoading(false)
        debugLog('本轮消息处理结束')
      }
    },
    [sessionId, setSessionId, addMessage, setLoading, addAgentEvent, clearEvents, setPlan, updateTask],
  )

  return { sendMessage }
}
