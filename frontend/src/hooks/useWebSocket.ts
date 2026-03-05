import { useEffect, useRef, useCallback, useState } from 'react'

interface WSOptions {
  onMessage: (data: Record<string, unknown>) => void
  onOpen?: () => void
  onClose?: () => void
}

export function useWebSocket(sessionId: string | null, options: WSOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  const connect = useCallback(() => {
    if (!sessionId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/chat/ws/${sessionId}`)

    ws.onopen = () => {
      setConnected(true)
      options.onOpen?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        options.onMessage(data)
      } catch {
        // skip
      }
    }

    ws.onclose = () => {
      setConnected(false)
      options.onClose?.()
    }

    wsRef.current = ws
  }, [sessionId, options])

  const send = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message }))
    }
  }, [])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setConnected(false)
  }, [])

  useEffect(() => {
    return () => {
      wsRef.current?.close()
    }
  }, [])

  return { connect, send, disconnect, connected }
}
