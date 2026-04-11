import { getDevices, getPricesUK, getMeta, buildDeviceRows } from '@/lib/data'
import PriceTable from '@/components/PriceTable'
import ScraperStatus from '@/components/ScraperStatus'

const UK_SOURCES = [
  { id: 'vodafone_uk', label: 'Vodafone' },
  { id: 'ee', label: 'EE' },
  { id: 'o2_uk', label: 'O2' },
  { id: 'three_uk', label: 'Three' },
  { id: 'amazon_uk', label: 'Amazon' },
  { id: 'currys', label: 'Currys' },
]

export default function UKPage() {
  const catalog = getDevices()
  const prices = getPricesUK()
  const meta = getMeta()
  const rows = buildDeviceRows(catalog, prices, 'vodafone_uk')
  const hasData = Object.keys(prices.prices).length > 0

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🇬🇧 UK Prices</h1>
          <p className="text-sm text-gray-500 mt-0.5">Vodafone vs EE, Three, O2, Amazon &amp; Currys</p>
        </div>
        <a href="/de" className="text-sm text-gray-400 hover:text-gray-700 transition-colors">
          Switch to Germany →
        </a>
      </div>

      <ScraperStatus meta={meta} sources={UK_SOURCES} />

      {!hasData ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 p-16 text-center text-gray-400">
          <p className="text-lg font-medium mb-1">No data yet</p>
          <p className="text-sm">Run <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">python scrapers/run_all.py</code> to populate prices</p>
        </div>
      ) : (
        <PriceTable rows={rows} sources={UK_SOURCES} currency="GBP" />
      )}
    </div>
  )
}
