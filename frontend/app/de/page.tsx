import { getDevices, getPricesDE, getMeta, buildDeviceRows } from '@/lib/data'
import PriceTable from '@/components/PriceTable'
import ScraperStatus from '@/components/ScraperStatus'

const DE_SOURCES = [
  { id: 'vodafone_de', label: 'Vodafone' },
  { id: 'telekom_de', label: 'Telekom' },
  { id: 'o2_de', label: 'O2' },
  { id: 'amazon_de', label: 'Amazon' },
  { id: 'mediamarkt_de', label: 'MediaMarkt' },
]

export default function DEPage() {
  const catalog = getDevices()
  const prices = getPricesDE()
  const meta = getMeta()
  const rows = buildDeviceRows(catalog, prices, 'vodafone_de')
  const hasData = Object.keys(prices.prices).length > 0

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🇩🇪 Germany Prices</h1>
          <p className="text-sm text-gray-500 mt-0.5">Vodafone vs Telekom, O2, Amazon &amp; MediaMarkt</p>
        </div>
        <a href="/uk" className="text-sm text-gray-400 hover:text-gray-700 transition-colors">
          Switch to UK →
        </a>
      </div>

      <ScraperStatus meta={meta} sources={DE_SOURCES} />

      {!hasData ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 p-16 text-center text-gray-400">
          <p className="text-lg font-medium mb-1">No data yet</p>
          <p className="text-sm">Run <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">python scrapers/run_all.py</code> to populate prices</p>
        </div>
      ) : (
        <PriceTable rows={rows} sources={DE_SOURCES} currency="EUR" />
      )}
    </div>
  )
}
