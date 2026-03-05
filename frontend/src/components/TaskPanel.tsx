/**
 * @file 任务面板组件
 * @description 右侧任务规划面板，展示当前差旅请求的任务拆解和执行进度。
 *   包含任务计划头部（含完成进度）、任务卡片列表以及底部的 Agent 实时活动日志。
 */

import { useTaskStore } from '../stores/taskStore'
import { useChatStore } from '../stores/chatStore'
import { TaskCard } from './TaskCard'
import { AgentStatus } from './AgentStatus'
import { ListTodo, Activity } from 'lucide-react'

/**
 * 任务面板组件
 * @description 右侧侧边栏，由三个区域组成：
 *   1. 头部：显示"任务规划"标题和当前已完成/总任务数
 *   2. 任务列表：遍历渲染每个子任务的 TaskCard，空态时显示引导提示
 *   3. Agent 活动日志：展示最近 5 条 Agent 实时事件（思考、工具调用等）
 */
export function TaskPanel() {
  const { currentPlan } = useTaskStore()
  const { agentEvents } = useChatStore()

  return (
    <div className="flex flex-col h-full">
      {/* 任务计划头部 */}
      <div className="px-5 py-4 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <ListTodo className="w-5 h-5 text-brand-600" />
          <h2 className="font-semibold text-gray-900">任务规划</h2>
        </div>
        {currentPlan && (
          <p className="text-xs text-gray-500 mt-1">
            {currentPlan.tasks.filter((t) => t.status === 'completed').length} /{' '}
            {currentPlan.tasks.length} 已完成
          </p>
        )}
      </div>

      {/* 任务卡片列表 */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3 scrollbar-thin">
        {!currentPlan ? (
          <div className="text-center text-gray-400 text-sm mt-12">
            <ListTodo className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p>暂无任务计划</p>
            <p className="text-xs mt-1">发起差旅需求后将自动生成任务</p>
          </div>
        ) : (
          currentPlan.tasks.map((task, idx) => (
            <TaskCard key={task.taskId} task={task} index={idx} />
          ))
        )}
      </div>

      {/* Agent 实时活动日志，仅在有事件时显示，展示最近 5 条 */}
      {agentEvents.length > 0 && (
        <div className="border-t border-gray-200 px-5 py-3 max-h-48 overflow-y-auto">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-brand-600" />
            <span className="text-xs font-medium text-gray-600">Agent 活动</span>
          </div>
          <div className="space-y-1">
            {agentEvents.slice(-5).map((ev, i) => (
              <AgentStatus key={i} event={ev} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
