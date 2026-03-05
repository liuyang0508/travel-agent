/**
 * @file 任务卡片组件
 * @description 展示单个子任务的状态卡片，包含序号、状态图标、任务名称、描述和状态标签。
 *   根据任务当前状态动态切换图标、颜色和背景样式。
 */

import type { TaskNode } from '../types'
import { CheckCircle2, Circle, Loader2, AlertCircle, Clock, XCircle } from 'lucide-react'
import clsx from 'clsx'

/**
 * TaskCard 组件的 Props
 */
interface Props {
  /** 任务节点数据 */
  task: TaskNode
  /** 任务在列表中的序号（从 0 开始） */
  index: number
}

/**
 * 任务状态与视觉样式的映射配置
 * @description 为每种任务状态定义对应的图标组件、文字颜色、背景颜色和中文标签
 */
const statusConfig = {
  pending: { icon: Circle, color: 'text-gray-400', bg: 'bg-gray-50', label: '待执行' },
  running: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-50', label: '执行中' },
  waiting_user: { icon: Clock, color: 'text-amber-500', bg: 'bg-amber-50', label: '等待确认' },
  completed: { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50', label: '已完成' },
  failed: { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50', label: '失败' },
  cancelled: { icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-50', label: '已取消' },
}

/**
 * 任务卡片组件
 * @description 渲染单个任务的可视化卡片，包含：
 *   - 左侧：任务序号 + 状态图标（running 状态时图标带旋转动画）
 *   - 右侧：任务名称、描述文本（最多两行）、状态标签
 * @param props - 组件属性
 * @param props.task - 任务节点数据
 * @param props.index - 任务序号
 */
export function TaskCard({ task, index }: Props) {
  const config = statusConfig[task.status]
  const Icon = config.icon

  return (
    <div className={clsx('task-card', config.bg)}>
      <div className="flex items-start gap-3">
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-mono text-gray-400 w-5">{index + 1}</span>
          <Icon
            className={clsx('w-5 h-5', config.color, task.status === 'running' && 'animate-spin')}
          />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate">{task.name}</p>
          {task.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{task.description}</p>
          )}
          <span
            className={clsx(
              'inline-block text-xs mt-1.5 px-2 py-0.5 rounded-full',
              config.color,
              config.bg,
            )}
          >
            {config.label}
          </span>
        </div>
      </div>
    </div>
  )
}
