/**
 * @file 应用根组件
 * @description AI 差旅通的顶层布局组件，定义了整体页面结构：
 *   顶部导航栏 + 左侧聊天面板 + 右侧任务面板的双栏布局（Manus 风格）。
 */

import { ChatPanel } from './components/ChatPanel'
import { TaskPanel } from './components/TaskPanel'
import { Plane } from 'lucide-react'

/**
 * 应用根组件
 * @description 采用全屏高度的 Flex 纵向布局：
 *   1. 顶部导航栏：品牌 Logo、应用名称和标签
 *   2. 主内容区：左侧弹性宽度的 ChatPanel + 右侧固定 420px 宽的 TaskPanel
 */
export default function App() {
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部导航栏 */}
      <header className="h-14 border-b border-gray-200 bg-white flex items-center px-6 shrink-0">
        <Plane className="w-6 h-6 text-brand-600 mr-2" />
        <h1 className="text-lg font-semibold text-gray-900">AI差旅通</h1>
        <span className="ml-2 text-xs bg-brand-50 text-brand-600 px-2 py-0.5 rounded-full">
          智能差旅助手
        </span>
      </header>

      {/* 主内容区：左侧聊天 + 右侧任务面板 */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 min-w-0">
          <ChatPanel />
        </div>
        <div className="w-[420px] border-l border-gray-200 bg-white shrink-0">
          <TaskPanel />
        </div>
      </div>
    </div>
  )
}
