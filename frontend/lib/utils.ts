import type { PriceEntry } from './types'

export function formatPrice(amount: number | null, currency: string): string {
  if (amount === null || amount === undefined) return '—'
  const locale = currency === 'EUR' ? 'de-DE' : 'en-GB'
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function cheapestTotal(
  prices: Record<string, { total_cost: number | null }>,
  sources: string[]
): number | null {
  const totals = sources
    .map((s) => prices[s]?.total_cost)
    .filter((v): v is number => v !== null && v !== undefined)
  return totals.length ? Math.min(...totals) : null
}
