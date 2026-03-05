import { FileText, Check } from 'lucide-react'
import clsx from 'clsx'
import type { ApprovalInfoItem } from '../../types'
import { useChat } from '../../hooks/useChat'

interface ApprovalStatusCardProps {
  approval: ApprovalInfoItem
}

const statusBadge = {
  pending: { bg: 'bg-amber-100', text: 'text-amber-700', label: '审批中' },
  approved: { bg: 'bg-green-100', text: 'text-green-700', label: '已通过' },
  rejected: { bg: 'bg-red-100', text: 'text-red-700', label: '已驳回' },
} as const

export function ApprovalStatusCard({ approval }: ApprovalStatusCardProps) {
  const badge = statusBadge[approval.status]
  const { sendMessage } = useChat()

  const handlePlanTrip = () => {
    sendMessage(`帮我规划去${approval.destination}的行程，出差日期 ${approval.dateRange}`)
  }

  return (
    <div className="animate-fadeInUp rounded-xl border border-gray-200 bg-white p-4 hover:shadow-md transition-all">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-brand-500" />
          <span className="font-bold text-gray-900">出差申请</span>
          <span className="font-mono text-xs text-gray-400">{approval.applyId}</span>
        </div>
        <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', badge.bg, badge.text)}>
          {badge.label}
        </span>
      </div>

      {/* Info grid */}
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <div>
          <span className="text-gray-400">申请人</span>
          <p className="text-gray-900">{approval.applicant}</p>
        </div>
        <div>
          <span className="text-gray-400">目的地</span>
          <p className="text-gray-900">{approval.destination}</p>
        </div>
        <div>
          <span className="text-gray-400">出差日期</span>
          <p className="text-gray-900">{approval.dateRange}</p>
        </div>
        <div>
          <span className="text-gray-400">事由</span>
          <p className="text-gray-900">{approval.reason}</p>
        </div>
      </div>

      {/* Timeline */}
      {approval.timeline.length > 0 && (
        <div className="mt-4 space-y-0">
          {approval.timeline.map((item, idx) => {
            const isLast = idx === approval.timeline.length - 1
            return (
              <div key={idx} className="flex gap-3">
                {/* Indicator */}
                <div className="flex flex-col items-center">
                  {item.status === 'done' ? (
                    <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-500">
                      <Check className="h-3 w-3 text-white" />
                    </div>
                  ) : item.status === 'current' ? (
                    <div className="relative flex h-5 w-5 shrink-0 items-center justify-center">
                      <span className="absolute h-5 w-5 animate-ping rounded-full bg-brand-400 opacity-30" />
                      <span className="h-3 w-3 rounded-full bg-brand-500" />
                    </div>
                  ) : (
                    <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 bg-white" />
                  )}
                  {!isLast && (
                    <div
                      className={clsx(
                        'w-px flex-1 min-h-[20px]',
                        item.status === 'done' ? 'bg-green-300' : 'border-l border-dashed border-gray-300'
                      )}
                    />
                  )}
                </div>
                {/* Content */}
                <div className="pb-3">
                  <p className={clsx(
                    'text-sm font-medium',
                    item.status === 'done' ? 'text-gray-900' :
                    item.status === 'current' ? 'text-brand-600' : 'text-gray-400'
                  )}>
                    {item.step}
                  </p>
                  {item.time && (
                    <p className="text-xs text-gray-400">{item.time}</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Approver */}
      <div className="mt-2 text-sm text-gray-500">
        审批人: {approval.approver}
      </div>

      {/* Action button for approved status */}
      {approval.status === 'approved' && (
        <button
          type="button"
          onClick={handlePlanTrip}
          className="card-action-btn mt-3 w-full bg-brand-600 text-white hover:bg-brand-700"
        >
          开始规划行程
        </button>
      )}
    </div>
  )
}
