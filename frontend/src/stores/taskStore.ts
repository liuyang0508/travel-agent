/**
 * @file 任务状态管理 Store
 * @description 基于 Zustand 的全局任务状态管理，维护当前任务计划及其子任务的实时状态。
 *   当后端通过 SSE 推送任务更新时，组件通过此 Store 同步展示最新进度。
 */

import { create } from 'zustand'
import type { TaskNode, TaskPlan } from '../types'

/**
 * 任务状态接口
 * @description 定义任务模块的全部状态字段和操作方法
 */
interface TaskState {
  /** 当前任务计划，为 null 表示尚未生成计划 */
  currentPlan: TaskPlan | null
  /** 设置（替换）当前任务计划 */
  setPlan: (plan: TaskPlan) => void
  /** 根据任务 ID 局部更新某个子任务的字段（如状态变更） */
  updateTask: (taskId: string, updates: Partial<TaskNode>) => void
  /** 清空当前任务计划 */
  clearPlan: () => void
}

/**
 * 任务状态 Store 实例
 * @description 使用 Zustand create 创建的全局 Store，组件通过 useTaskStore() 访问
 */
export const useTaskStore = create<TaskState>((set) => ({
  currentPlan: null,
  setPlan: (plan) => set({ currentPlan: plan }),
  updateTask: (taskId, updates) =>
    set((s) => {
      if (!s.currentPlan) return s
      return {
        currentPlan: {
          ...s.currentPlan,
          tasks: s.currentPlan.tasks.map((t) =>
            t.taskId === taskId ? { ...t, ...updates } : t,
          ),
        },
      }
    }),
  clearPlan: () => set({ currentPlan: null }),
}))
