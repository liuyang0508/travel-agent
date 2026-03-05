import { Star, MapPin } from 'lucide-react'
import clsx from 'clsx'
import type { HotelItem } from '../../types'

interface HotelCardProps {
  hotel: HotelItem
  onSelect?: (hotelId: string) => void
}

function formatPrice(price: number): string {
  return `¥${price.toLocaleString('zh-CN')}`
}

export function HotelCard({ hotel, onSelect }: HotelCardProps) {
  return (
    <div className="animate-fadeInUp rounded-xl border border-gray-200 border-l-4 border-l-purple-300 p-4 hover:shadow-md transition-all bg-white">
      <div className="flex items-center justify-between">
        <span className="font-bold text-gray-900">{hotel.name}</span>
        <div className="flex items-center gap-0.5">
          {Array.from({ length: hotel.stars }).map((_, i) => (
            <Star key={i} className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
          ))}
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3 text-sm text-gray-500">
        <div className="flex items-center gap-1 truncate">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-gray-400" />
          <span className="truncate">{hotel.address}</span>
        </div>
        <span className="shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600">
          距目的地 {hotel.distanceToDestination}
        </span>
      </div>

      {hotel.amenities.length > 0 && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {hotel.amenities.map((amenity) => (
            <span
              key={amenity}
              className="rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-600"
            >
              {amenity}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        <div className="flex items-baseline gap-1">
          <span className="text-lg font-bold tabular-nums text-purple-600">
            {formatPrice(hotel.pricePerNight)}
          </span>
          <span className="text-xs text-gray-400">/晚</span>
        </div>
        <span className={clsx(
          'rounded-full px-2 py-0.5 text-xs font-medium',
          hotel.rating >= 4.5 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
        )}>
          {hotel.rating.toFixed(1)}分
        </span>
      </div>

      {onSelect && (
        <button
          type="button"
          onClick={() => onSelect(hotel.hotelId)}
          className="card-action-btn mt-3 w-full bg-purple-600 text-white hover:bg-purple-700"
        >
          预订此酒店
        </button>
      )}
    </div>
  )
}
