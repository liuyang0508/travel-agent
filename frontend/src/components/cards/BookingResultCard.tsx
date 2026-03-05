import { CheckCircle, XCircle, Clock, Plane, Hotel, TrainFront } from 'lucide-react'
import clsx from 'clsx'
import type { BookingResultItem } from '../../types'

interface BookingResultCardProps {
  result: BookingResultItem
}

const statusConfig = {
  confirmed: {
    border: 'border-green-200',
    icon: CheckCircle,
    iconColor: 'text-green-500',
    label: '预订成功',
    bg: 'bg-green-50',
  },
  failed: {
    border: 'border-red-200',
    icon: XCircle,
    iconColor: 'text-red-500',
    label: '预订失败',
    bg: 'bg-red-50',
  },
  pending: {
    border: 'border-amber-200',
    icon: Clock,
    iconColor: 'text-amber-500',
    label: '处理中',
    bg: 'bg-amber-50',
  },
} as const

const bookingTypeIcon = {
  flight: Plane,
  hotel: Hotel,
  train: TrainFront,
} as const

function formatPrice(price: number): string {
  return `¥${price.toLocaleString('zh-CN')}`
}

export function BookingResultCard({ result }: BookingResultCardProps) {
  const config = statusConfig[result.status]
  const StatusIcon = config.icon
  const TypeIcon = bookingTypeIcon[result.bookingType]

  return (
    <div className={clsx(
      'animate-fadeInUp rounded-xl border p-4 transition-all bg-white',
      config.border
    )}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusIcon className={clsx('h-5 w-5', config.iconColor)} />
          <span className={clsx(
            'rounded-full px-2 py-0.5 text-xs font-medium',
            config.bg,
            config.iconColor
          )}>
            {config.label}
          </span>
        </div>
        <TypeIcon className="h-4 w-4 text-gray-400" />
      </div>

      <div className="mt-3">
        <p className="font-mono text-xs text-gray-400">订单号: {result.orderId}</p>
      </div>

      {Object.keys(result.details).length > 0 && (
        <div className="mt-2.5 space-y-1">
          {Object.entries(result.details).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-gray-500">{key}</span>
              <span className="text-gray-900">{value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3">
        <span className="text-sm text-gray-500">总价</span>
        <span className="text-xl font-bold tabular-nums text-gray-900">
          {formatPrice(result.totalPrice)}
        </span>
      </div>

      <p className="mt-2 text-xs text-gray-500">{result.message}</p>
    </div>
  )
}
