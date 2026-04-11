export interface Device {
  normalized_id: string
  canonical_name: string
  brand: string
  model: string
  storage_gb: number | null
  aliases: string[]
}

export interface PriceEntry {
  upfront_price: number | null
  monthly_price: number | null
  contract_months: number | null
  total_cost: number | null
  url: string
  in_stock: boolean
  currency: string
  scraped_at: string
}

export interface PricesFile {
  scraped_at: string | null
  prices: Record<string, Record<string, PriceEntry>>
}

export interface MetaSource {
  status: 'ok' | 'error' | 'blocked'
  scraped_at: string
  device_count?: number
  error?: string
}

export interface MetaFile {
  last_full_scrape: string | null
  sources: Record<string, MetaSource>
}

export interface DeviceCatalog {
  devices: Device[]
}

// Merged view of one device across all sources
export interface DeviceRow {
  device: Device
  prices: Record<string, PriceEntry>
}
