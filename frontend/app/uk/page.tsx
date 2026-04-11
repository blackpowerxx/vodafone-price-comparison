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
  const rows = buildDeviceRows(catalog, prices)

  const hasData = Object.keys(prices.prices).length > 0

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-2xl font-bold">UK — Device Prices</h1>
        <a href="/de" className="text-sm text-gray-500 hover:underline">Switch to Germany</a>
      </div>

      <ScraperStatus meta={meta} sources={UK_SOURCES} />

      {!hasData ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-gray-400">
          <p className="text-lg font-medium mb-2">No data yet</p>
          <p className="text-sm">Run the scraper to populate prices:<br />
            <code className="bg-gray-100 px-2 py-1 rounded text-xs">cd scrapers && python run_all.py</code>
          </p>
        </div>
      ) : (
        <PriceTable rows={rows} sources={UK_SOURCES} currency="GBP" />
      )}
    </div>
  )
}
