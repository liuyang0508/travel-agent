import { Plane, ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import type { FlightItem } from '../../types'

interface FlightCardProps {
  flight: FlightItem
  onSelect?: (flightId: string) => void
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

export function FlightCard({ flight, onSelect }: FlightCardProps) {
  const cabinStyle = flight.cabinClass === '商务舱'
    ? 'bg-amber-100 text-amber-700'
    : 'bg-blue-100 text-blue-700'

  return (
    <div className="animate-fadeInUp rounded-xl border border-gray-200 p-4 hover:shadow-md transition-all bg-white">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Plane className="h-4 w-4 text-brand-500" />
          <span className="font-bold text-gray-900">{flight.airline}</span>
          <span className="font-mono text-sm text-gray-400">{flight.flightNo}</span>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="text-center">
          <p className="text-xl font-bold text-gray-900">{extractTime(flight.departTime)}</p>
          <p className="text-xs text-gray-500">{flight.origin}</p>
        </div>
        <div className="flex flex-col items-center px-4">
          <ArrowRight className="h-4 w-4 text-gray-300" />
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-gray-900">{extractTime(flight.arriveTime)}</p>
          <p className="text-xs text-gray-500">{flight.destination}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold tabular-nums text-brand-600">
            {formatPrice(flight.price)}
          </span>
          <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', cabinStyle)}>
            {flight.cabinClass}
          </span>
        </div>
        <span className={clsx(
          'text-xs',
          flight.remainingSeats < 5 ? 'font-medium text-red-500' : 'text-gray-400'
        )}>
          {flight.remainingSeats < 5 ? `仅剩${flight.remainingSeats}张` : `剩余${flight.remainingSeats}张`}
        </span>
      </div>

      {onSelect && (
        <button
          type="button"
          onClick={() => onSelect(flight.flightId)}
          className="card-action-btn mt-3 w-full bg-brand-600 text-white hover:bg-brand-700"
        >
          选择此航班
        </button>
      )}
    </div>
  )
}
