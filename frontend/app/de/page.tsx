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
  const rows = buildDeviceRows(catalog, prices)

  const hasData = Object.keys(prices.prices).length > 0

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-2xl font-bold">Germany — Device Prices</h1>
        <a href="/uk" className="text-sm text-gray-500 hover:underline">Switch to UK</a>
      </div>

      <ScraperStatus meta={meta} sources={DE_SOURCES} />

      {!hasData ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-gray-400">
          <p className="text-lg font-medium mb-2">No data yet</p>
          <p className="text-sm">Run the scraper to populate prices:<br />
            <code className="bg-gray-100 px-2 py-1 rounded text-xs">cd scrapers && python run_all.py</code>
          </p>
        </div>
      ) : (
        <PriceTable rows={rows} sources={DE_SOURCES} currency="EUR" />
      )}
    </div>
  )
}
