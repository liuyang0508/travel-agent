/**
 * @file 消息气泡组件
 * @description 单条聊天消息的气泡展示组件。根据消息角色（用户/助手）
 *   区分布局方向、头像样式和内容渲染方式。助手消息支持 Markdown 渲染。
 */

import type { ChatMessage, StructuredCard } from '../types'
import ReactMarkdown from 'react-markdown'
import { User, Bot } from 'lucide-react'
import { CardRenderer } from './cards'

/**
 * MessageBubble 组件的 Props
 */
interface Props {
  /** 要展示的聊天消息对象 */
  message: ChatMessage
}

/**
 * 消息气泡组件
 * @description 根据消息角色渲染不同样式：
 *   - 用户消息：右对齐，品牌色头像，纯文本展示
 *   - 助手消息：左对齐，灰色头像，Markdown 富文本渲染
 * @param props - 组件属性
 * @param props.message - 聊天消息数据
 */
export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? 'bg-brand-600' : 'bg-gray-100'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-brand-600" />
        )}
      </div>
      <div className={isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}>
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <>
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            {message.metadata?.cards && (
              <div className="mt-3 space-y-4">
                {(message.metadata.cards as StructuredCard[]).map((card, i) => (
                  <CardRenderer key={i} card={card} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
