/**
 * @file 应用入口文件
 * @description React 应用的启动入口，负责将根组件 App 挂载到 DOM 节点上。
 *   使用 React.StrictMode 包裹以在开发环境下启用额外的检查和警告。
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
