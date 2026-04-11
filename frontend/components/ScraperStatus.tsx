import type { MetaFile } from '@/lib/types'

interface Props {
  meta: MetaFile
  sources: { id: string; label: string }[]
}

export default function ScraperStatus({ meta, sources }: Props) {
  const lastScrape = meta.last_full_scrape
    ? new Date(meta.last_full_scrape).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
    : 'Never'

  const failed = sources.filter((s) => meta.sources[s.id]?.status !== 'ok')

  return (
    <div className="flex flex-wrap items-center gap-3 mb-6 text-sm">
      <span className="text-gray-400">
        Updated <span className="text-gray-700 font-medium">{lastScrape}</span>
      </span>
      <span className="text-gray-300">·</span>
      <div className="flex gap-1.5 flex-wrap">
        {sources.map((s) => {
          const st = meta.sources[s.id]
          const ok = st?.status === 'ok'
          return (
            <span
              key={s.id}
              title={ok ? `${st?.device_count} devices` : (st?.error ?? 'No data')}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                ok
                  ? 'bg-green-50 text-green-700 border-green-200'
                  : 'bg-red-50 text-red-600 border-red-200'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-green-500' : 'bg-red-400'}`} />
              {s.label}
              {ok && st?.device_count ? ` ${st.device_count}` : ''}
            </span>
          )
        })}
      </div>
      {failed.length > 0 && (
        <span className="text-amber-600 text-xs">
          {failed.map((s) => s.label).join(', ')} unavailable
        </span>
      )}
    </div>
  )
}
