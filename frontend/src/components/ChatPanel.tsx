/**
 * @file 聊天面板组件
 * @description 应用的核心交互区域，包含消息列表展示和用户输入框。
 *   支持快捷提示引导用户发起首次对话，消息列表会自动滚动到底部。
 */

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { useChatStore } from '../stores/chatStore'
import { useChat } from '../hooks/useChat'
import { MessageBubble } from './MessageBubble'

/**
 * 聊天面板组件
 * @description 左侧主面板，包含：
 *   - 空态引导：首次进入时展示欢迎语和快捷提示按钮
 *   - 消息列表：按时间顺序展示对话历史
 *   - 加载指示器：等待 AI 回复时显示
 *   - 输入区域：文本框 + 发送按钮，支持 Enter 键发送
 */
export function ChatPanel() {
  const [input, setInput] = useState('')
  const { messages, isLoading } = useChatStore()
  const { sendMessage } = useChat()
  /** 用于消息列表自动滚动到底部的锚点元素 */
  const bottomRef = useRef<HTMLDivElement>(null)

  // 每当消息列表变化时，自动平滑滚动到底部以展示最新消息
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /**
   * 处理消息发送
   * @description 校验输入非空且非加载态后，清空输入框并调用 sendMessage
   */
  const handleSend = () => {
    const text = input.trim()
    if (!text || isLoading) return
    setInput('')
    sendMessage(text)
  }

  return (
    <div className="flex flex-col h-full">
      {/* 消息列表区域 */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <p className="text-xl font-medium mb-2">欢迎使用 AI差旅通</p>
            <p className="text-sm">告诉我你的出差需求，我来帮你安排一切</p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              {[
                '我下周一需要去上海出差',
                '帮我查一下北京到深圳的机票',
                '我的出差申请审批到哪了？',
                '推荐杭州西湖附近的酒店',
              ].map((hint) => (
                <button
                  key={hint}
                  onClick={() => { if (!isLoading) sendMessage(hint); }}
                  className="text-left text-sm px-4 py-3 rounded-xl border border-gray-200 hover:border-brand-500 hover:bg-brand-50 transition-colors"
                >
                  {hint}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.messageId} message={msg} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <Loader2 className="w-4 h-4 animate-spin" />
            思考中...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 输入区域 */}
      <div className="border-t border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center gap-3 max-w-3xl mx-auto">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="输入你的差旅需求..."
            className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="bg-brand-600 hover:bg-brand-700 disabled:bg-gray-300 text-white rounded-xl p-2.5 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
