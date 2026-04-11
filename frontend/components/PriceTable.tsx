'use client'

import { useState, useMemo } from 'react'
import type { DeviceRow, PriceEntry } from '@/lib/types'
import { formatPrice, cheapestTotal } from '@/lib/utils'

interface Props {
  rows: DeviceRow[]
  sources: { id: string; label: string }[]
  currency: string
}

const SOURCE_COLORS: Record<string, string> = {
  vodafone_uk: 'bg-red-100 text-red-800',
  vodafone_de: 'bg-red-100 text-red-800',
  ee: 'bg-green-100 text-green-800',
  o2_uk: 'bg-blue-100 text-blue-800',
  o2_de: 'bg-blue-100 text-blue-800',
  three_uk: 'bg-purple-100 text-purple-800',
  telekom_de: 'bg-pink-100 text-pink-800',
  amazon_uk: 'bg-yellow-100 text-yellow-900',
  amazon_de: 'bg-yellow-100 text-yellow-900',
  currys: 'bg-indigo-100 text-indigo-800',
  mediamarkt_de: 'bg-orange-100 text-orange-800',
}

type SortKey = 'name' | 'vodafone' | 'cheapest'

export default function PriceTable({ rows, sources, currency }: Props) {
  const [search, setSearch] = useState('')
  const [brandFilter, setBrandFilter] = useState('All')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortAsc, setSortAsc] = useState(true)

  const brands = useMemo(() => {
    const set = new Set(rows.map((r) => r.device.brand))
    return ['All', ...Array.from(set).sort()]
  }, [rows])

  const sourceIds = sources.map((s) => s.id)
  const vodafoneSource = sourceIds.find((id) => id.startsWith('vodafone'))

  const filtered = useMemo(() => {
    let result = rows.filter((r) => {
      const matchSearch = r.device.canonical_name
        .toLowerCase()
        .includes(search.toLowerCase())
      const matchBrand = brandFilter === 'All' || r.device.brand === brandFilter
      return matchSearch && matchBrand
    })

    result = [...result].sort((a, b) => {
      let cmp = 0
      if (sortKey === 'name') {
        cmp = a.device.canonical_name.localeCompare(b.device.canonical_name)
      } else if (sortKey === 'vodafone' && vodafoneSource) {
        const aTotal = a.prices[vodafoneSource]?.total_cost ?? Infinity
        const bTotal = b.prices[vodafoneSource]?.total_cost ?? Infinity
        cmp = aTotal - bTotal
      } else if (sortKey === 'cheapest') {
        const aMin = cheapestTotal(a.prices, sourceIds) ?? Infinity
        const bMin = cheapestTotal(b.prices, sourceIds) ?? Infinity
        cmp = aMin - bMin
      }
      return sortAsc ? cmp : -cmp
    })

    return result
  }, [rows, search, brandFilter, sortKey, sortAsc, sourceIds, vodafoneSource])

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((v) => !v)
    else { setSortKey(key); setSortAsc(true) }
  }

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <span className="text-gray-300 ml-1">&#8597;</span>
    return <span className="ml-1">{sortAsc ? '▲' : '▼'}</span>
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="search"
          placeholder="Search devices..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-vodafone"
        />
        <select
          value={brandFilter}
          onChange={(e) => setBrandFilter(e.target.value)}
          className="border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-vodafone"
        >
          {brands.map((b) => <option key={b}>{b}</option>)}
        </select>
        <span className="text-sm text-gray-500 self-center">
          {filtered.length} devices
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="w-full text-sm border-collapse">
          <thead className="bg-gray-100 text-gray-700">
            <tr>
              <th
                className="text-left px-4 py-3 font-semibold cursor-pointer whitespace-nowrap"
                onClick={() => toggleSort('name')}
              >
                Device <SortIcon k="name" />
              </th>
              {sources.map((source) => (
                <th key={source.id} className="px-4 py-3 font-semibold whitespace-nowrap text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${SOURCE_COLORS[source.id] ?? 'bg-gray-200'}`}>
                    {source.label}
                  </span>
                </th>
              ))}
              <th
                className="px-4 py-3 font-semibold whitespace-nowrap text-center cursor-pointer"
                onClick={() => toggleSort('cheapest')}
              >
                Cheapest <SortIcon k="cheapest" />
              </th>
              <th className="px-4 py-3 font-semibold whitespace-nowrap text-center">
                vs Vodafone
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={sources.length + 3} className="px-4 py-8 text-center text-gray-400">
                  No devices found
                </td>
              </tr>
            )}
            {filtered.map(({ device, prices }) => {
              const minTotal = cheapestTotal(prices, sourceIds)
              const vodafoneTotal = vodafoneSource ? prices[vodafoneSource]?.total_cost ?? null : null
              const saving = vodafoneTotal !== null && minTotal !== null
                ? vodafoneTotal - minTotal
                : null

              return (
                <tr key={device.normalized_id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium whitespace-nowrap">
                    {device.canonical_name}
                  </td>
                  {sources.map((source) => {
                    const entry: PriceEntry | undefined = prices[source.id]
                    const isMin = entry?.total_cost !== null &&
                      entry?.total_cost !== undefined &&
                      entry.total_cost === minTotal
                    return (
                      <td
                        key={source.id}
                        className={`px-4 py-3 text-center whitespace-nowrap ${isMin ? 'bg-green-50' : ''}`}
                      >
                        {entry ? (
                          <a href={entry.url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                            <PriceCell entry={entry} currency={currency} isMin={isMin} />
                          </a>
                        ) : (
                          <span className="text-gray-300">—</span>
                        )}
                      </td>
                    )
                  })}
                  {/* Cheapest */}
                  <td className="px-4 py-3 text-center font-semibold text-green-700 whitespace-nowrap">
                    {minTotal !== null ? formatPrice(minTotal, currency) : '—'}
                  </td>
                  {/* vs Vodafone */}
                  <td className="px-4 py-3 text-center whitespace-nowrap">
                    {saving !== null && saving > 0 ? (
                      <span className="text-green-600 font-medium">Save {formatPrice(saving, currency)}</span>
                    ) : saving !== null && saving < 0 ? (
                      <span className="text-red-500 font-medium">+{formatPrice(Math.abs(saving), currency)}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function PriceCell({
  entry,
  currency,
  isMin,
}: {
  entry: PriceEntry
  currency: string
  isMin: boolean
}) {
  if (entry.monthly_price !== null && entry.contract_months !== null) {
    return (
      <span className={isMin ? 'font-bold text-green-700' : ''}>
        <span className="block">{formatPrice(entry.total_cost, currency)}</span>
        <span className="block text-xs text-gray-400">
          {formatPrice(entry.monthly_price, currency)}/mo × {entry.contract_months}mo
          {entry.upfront_price ? ` + ${formatPrice(entry.upfront_price, currency)} upfront` : ''}
        </span>
      </span>
    )
  }
  return (
    <span className={`block ${isMin ? 'font-bold text-green-700' : ''}`}>
      {formatPrice(entry.upfront_price, currency)}
    </span>
  )
}
