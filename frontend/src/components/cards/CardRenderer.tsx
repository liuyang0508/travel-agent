import { Plane, Hotel, TrainFront } from 'lucide-react'
import type {
  StructuredCard,
  FlightItem,
  HotelItem,
  TrainItem,
  BookingResultItem,
  ApprovalInfoItem,
} from '../../types'
import { FlightCard } from './FlightCard'
import { HotelCard } from './HotelCard'
import { TrainCard } from './TrainCard'
import { BookingResultCard } from './BookingResultCard'
import { ApprovalStatusCard } from './ApprovalStatusCard'

interface CardRendererProps {
  card: StructuredCard
}

function SectionHeading({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
      {icon}
      <span>{label}</span>
    </div>
  )
}

export function CardRenderer({ card }: CardRendererProps) {
  switch (card.cardType) {
    case 'flight_list':
      return (
        <div>
          <SectionHeading icon={<Plane className="h-4 w-4" />} label="航班推荐" />
          <div className="space-y-3">
            {(card.items as FlightItem[]).map((flight) => (
              <FlightCard key={flight.flightId} flight={flight} />
            ))}
          </div>
        </div>
      )

    case 'hotel_list':
      return (
        <div>
          <SectionHeading icon={<Hotel className="h-4 w-4" />} label="酒店推荐" />
          <div className="space-y-3">
            {(card.items as HotelItem[]).map((hotel) => (
              <HotelCard key={hotel.hotelId} hotel={hotel} />
            ))}
          </div>
        </div>
      )

    case 'train_list':
      return (
        <div>
          <SectionHeading icon={<TrainFront className="h-4 w-4" />} label="高铁推荐" />
          <div className="space-y-3">
            {(card.items as TrainItem[]).map((train) => (
              <TrainCard key={train.trainId} train={train} />
            ))}
          </div>
        </div>
      )

    case 'booking_result':
      return (
        <div className="space-y-3">
          {(card.items as BookingResultItem[]).map((result) => (
            <BookingResultCard key={result.orderId} result={result} />
          ))}
        </div>
      )

    case 'approval_status':
      return (
        <div className="space-y-3">
          {(card.items as ApprovalInfoItem[]).map((approval) => (
            <ApprovalStatusCard key={approval.applyId} approval={approval} />
          ))}
        </div>
      )

    default:
      return null
  }
}
