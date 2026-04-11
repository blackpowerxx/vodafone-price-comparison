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
    <div className="flex flex-wrap items-center gap-4 mb-5 text-sm text-gray-600">
      <span>Last updated: <strong>{lastScrape}</strong></span>
      {failed.length > 0 && (
        <span className="text-amber-600">
          {failed.length} source{failed.length > 1 ? 's' : ''} unavailable:{' '}
          {failed.map((s) => s.label).join(', ')}
        </span>
      )}
      <div className="flex gap-2 flex-wrap">
        {sources.map((s) => {
          const st = meta.sources[s.id]
          const ok = st?.status === 'ok'
          return (
            <span
              key={s.id}
              title={ok ? `${st?.device_count} devices` : (st?.error ?? 'No data')}
              className={`px-2 py-0.5 rounded text-xs font-medium ${
                ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}
            >
              {s.label} {ok ? `(${st?.device_count})` : 'N/A'}
            </span>
          )
        })}
      </div>
    </div>
  )
}
