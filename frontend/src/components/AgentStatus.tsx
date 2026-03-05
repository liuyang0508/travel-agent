/**
 * @file Agent 状态组件
 * @description 展示单条 Agent 实时事件的行内组件，用于任务面板底部的活动日志区域。
 *   根据事件类型显示不同的图标（思考、工具调用、消息、错误等）。
 */

import type { AgentEvent } from '../types'
import { Brain, Wrench, MessageSquare, AlertTriangle } from 'lucide-react'

/**
 * AgentStatus 组件的 Props
 */
interface Props {
  /** 要展示的 Agent 事件对象 */
  event: AgentEvent
}

/**
 * 事件类型与图标的映射表
 * @description 将 Agent 事件类型映射为对应的 Lucide 图标组件
 */
const iconMap = {
  thinking: Brain,
  tool_call: Wrench,
  tool_result: Wrench,
  message: MessageSquare,
  error: AlertTriangle,
}

/**
 * Agent 状态展示组件
 * @description 单行展示一条 Agent 事件，包含事件类型图标、Agent 角色名和事件内容摘要。
 *   内容过长时自动截断（truncate）。
 * @param props - 组件属性
 * @param props.event - Agent 事件数据
 */
export function AgentStatus({ event }: Props) {
  const Icon = iconMap[event.eventType] || MessageSquare

  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <Icon className="w-3 h-3 shrink-0" />
      <span className="font-medium text-gray-600">[{event.agentRole}]</span>
      <span className="truncate">{event.content}</span>
    </div>
  )
}
