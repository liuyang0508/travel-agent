import { TrainFront, ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import type { TrainItem } from '../../types'

interface TrainCardProps {
  train: TrainItem
  onSelect?: (trainId: string) => void
}

function extractTime(datetime: string): string {
  const date = new Date(datetime)
  if (isNaN(date.getTime())) {
    const match = datetime.match(/(\d{2}:\d{2})/)
    return match ? match[1] : datetime
  }
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function formatPrice(price: number): string {
  return `¥${price.toLocaleString('zh-CN')}`
}

export function TrainCard({ train, onSelect }: TrainCardProps) {
  return (
    <div className="animate-fadeInUp rounded-xl border border-gray-200 p-4 hover:shadow-md transition-all bg-white">
      <div className="flex items-center gap-2">
        <span className="flex items-center gap-1.5 rounded-full bg-brand-100 px-2.5 py-0.5 text-xs font-bold text-brand-700">
          <TrainFront className="h-3.5 w-3.5" />
          {train.trainNo}
        </span>
        <span className="text-sm text-gray-500">{train.seatType}</span>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="text-center">
          <p className="text-xl font-bold text-gray-900">{extractTime(train.departTime)}</p>
          <p className="text-xs text-gray-500">{train.origin}</p>
        </div>
        <div className="flex flex-col items-center px-3">
          <span className="text-xs text-gray-400">{train.duration}</span>
          <div className="flex items-center gap-1">
            <span className="h-px w-6 bg-gray-300" />
            <ArrowRight className="h-3 w-3 text-gray-300" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-gray-900">{extractTime(train.arriveTime)}</p>
          <p className="text-xs text-gray-500">{train.destination}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <span className="text-lg font-bold tabular-nums text-brand-600">
          {formatPrice(train.price)}
        </span>
        <span className={clsx(
          'text-xs',
          train.remainingSeats < 5 ? 'font-medium text-red-500' : 'text-gray-400'
        )}>
          {train.remainingSeats < 5 ? `仅剩${train.remainingSeats}张` : `剩余${train.remainingSeats}张`}
        </span>
      </div>

      {onSelect && (
        <button
          type="button"
          onClick={() => onSelect(train.trainId)}
          className="card-action-btn mt-3 w-full bg-brand-600 text-white hover:bg-brand-700"
        >
          选择此车次
        </button>
      )}
    </div>
  )
}
