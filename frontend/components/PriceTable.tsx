'use client'

import { useState, useMemo } from 'react'
import type { DeviceRow, PriceEntry } from '@/lib/types'
import { formatPrice, cheapestTotal } from '@/lib/utils'

interface Props {
  rows: DeviceRow[]
  sources: { id: string; label: string }[]
  currency: string
}

const SOURCE_STYLES: Record<string, { dot: string; badge: string }> = {
  vodafone_uk:  { dot: 'bg-red-500',    badge: 'bg-red-50 text-red-700 border-red-200' },
  vodafone_de:  { dot: 'bg-red-500',    badge: 'bg-red-50 text-red-700 border-red-200' },
  ee:           { dot: 'bg-emerald-500',badge: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  o2_uk:        { dot: 'bg-blue-500',   badge: 'bg-blue-50 text-blue-700 border-blue-200' },
  o2_de:        { dot: 'bg-blue-500',   badge: 'bg-blue-50 text-blue-700 border-blue-200' },
  three_uk:     { dot: 'bg-purple-500', badge: 'bg-purple-50 text-purple-700 border-purple-200' },
  telekom_de:   { dot: 'bg-pink-500',   badge: 'bg-pink-50 text-pink-700 border-pink-200' },
  amazon_uk:    { dot: 'bg-amber-500',  badge: 'bg-amber-50 text-amber-700 border-amber-200' },
  amazon_de:    { dot: 'bg-amber-500',  badge: 'bg-amber-50 text-amber-700 border-amber-200' },
  currys:       { dot: 'bg-indigo-500', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  mediamarkt_de:{ dot: 'bg-orange-500', badge: 'bg-orange-50 text-orange-700 border-orange-200' },
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
      const matchSearch = r.device.canonical_name.toLowerCase().includes(search.toLowerCase())
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
    if (sortKey !== k) return <span className="text-gray-300 ml-1 text-xs">↕</span>
    return <span className="ml-1 text-xs">{sortAsc ? '↑' : '↓'}</span>
  }

  return (
    <div>
      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-5 items-center">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="search"
            placeholder="Search devices..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm w-56 focus:outline-none focus:ring-2 focus:ring-vodafone/30 focus:border-vodafone bg-white shadow-sm"
          />
        </div>
        <select
          value={brandFilter}
          onChange={(e) => setBrandFilter(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vodafone/30 focus:border-vodafone bg-white shadow-sm"
        >
          {brands.map((b) => <option key={b}>{b}</option>)}
        </select>
        <span className="text-sm text-gray-400 ml-1">
          {filtered.length} device{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm bg-white">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-100">
              <th
                className="text-left px-5 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer whitespace-nowrap bg-gray-50 rounded-tl-xl"
                onClick={() => toggleSort('name')}
              >
                Device <SortIcon k="name" />
              </th>
              {sources.map((source) => {
                const style = SOURCE_STYLES[source.id]
                return (
                  <th key={source.id} className="px-4 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap text-center bg-gray-50">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${style?.badge ?? 'bg-gray-100 text-gray-600 border-gray-200'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${style?.dot ?? 'bg-gray-400'}`} />
                      {source.label}
                    </span>
                  </th>
                )
              })}
              <th
                className="px-4 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap text-center bg-gray-50 cursor-pointer"
                onClick={() => toggleSort('cheapest')}
              >
                Cheapest <SortIcon k="cheapest" />
              </th>
              <th className="px-4 py-3.5 text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap text-center bg-gray-50 rounded-tr-xl">
                vs Vodafone
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={sources.length + 3} className="px-5 py-16 text-center text-gray-400">
                  <div className="flex flex-col items-center gap-2">
                    <svg className="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>No devices found</span>
                  </div>
                </td>
              </tr>
            )}
            {filtered.map(({ device, prices }, i) => {
              const minTotal = cheapestTotal(prices, sourceIds)
              const vodafoneTotal = vodafoneSource ? prices[vodafoneSource]?.total_cost ?? null : null
              const saving = vodafoneTotal !== null && minTotal !== null ? vodafoneTotal - minTotal : null

              return (
                <tr
                  key={device.normalized_id}
                  className={`border-t border-gray-50 hover:bg-gray-50/70 transition-colors ${i % 2 === 0 ? '' : 'bg-gray-50/30'}`}
                >
                  <td className="px-5 py-3.5">
                    <div className="font-semibold text-gray-900 whitespace-nowrap">{device.canonical_name}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{device.brand}</div>
                  </td>
                  {sources.map((source) => {
                    const entry: PriceEntry | undefined = prices[source.id]
                    const isMin = entry?.total_cost != null && entry.total_cost === minTotal
                    return (
                      <td key={source.id} className={`px-4 py-3.5 text-center whitespace-nowrap ${isMin ? 'bg-green-50/60' : ''}`}>
                        {entry ? (
                          <a href={entry.url} target="_blank" rel="noopener noreferrer" className="group inline-block">
                            <PriceCell entry={entry} currency={currency} isMin={isMin} />
                          </a>
                        ) : (
                          <span className="text-gray-200">—</span>
                        )}
                      </td>
                    )
                  })}
                  {/* Cheapest */}
                  <td className="px-4 py-3.5 text-center whitespace-nowrap">
                    {minTotal !== null ? (
                      <span className="font-bold text-gray-900">{formatPrice(minTotal, currency)}</span>
                    ) : <span className="text-gray-300">—</span>}
                  </td>
                  {/* vs Vodafone */}
                  <td className="px-4 py-3.5 text-center whitespace-nowrap">
                    {saving !== null && saving > 0.5 ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full text-xs font-semibold">
                        Save {formatPrice(saving, currency)}
                      </span>
                    ) : saving !== null && saving < -0.5 ? (
                      <span className="inline-flex items-center px-2.5 py-1 bg-red-50 text-red-600 border border-red-200 rounded-full text-xs font-semibold">
                        +{formatPrice(Math.abs(saving), currency)}
                      </span>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
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

function PriceCell({ entry, currency, isMin }: { entry: PriceEntry; currency: string; isMin: boolean }) {
  if (entry.monthly_price !== null && entry.contract_months !== null) {
    return (
      <span className="block">
        <span className={`block font-semibold group-hover:underline ${isMin ? 'text-green-700' : 'text-gray-900'}`}>
          {formatPrice(entry.total_cost, currency)}
        </span>
        <span className="block text-xs text-gray-400 mt-0.5">
          {formatPrice(entry.monthly_price, currency)}/mo × {entry.contract_months}mo
          {entry.upfront_price ? ` + ${formatPrice(entry.upfront_price, currency)}` : ''}
        </span>
      </span>
    )
  }
  return (
    <span className={`font-semibold group-hover:underline ${isMin ? 'text-green-700' : 'text-gray-900'}`}>
      {formatPrice(entry.upfront_price, currency)}
    </span>
  )
}
