import fs from 'fs'
import path from 'path'
import type { DeviceCatalog, PricesFile, MetaFile, DeviceRow } from './types'

const DATA_DIR = path.join(process.cwd(), '..', 'data')

function readJson<T>(filename: string): T {
  const raw = fs.readFileSync(path.join(DATA_DIR, filename), 'utf-8')
  return JSON.parse(raw) as T
}

export function getDevices(): DeviceCatalog {
  return readJson<DeviceCatalog>('devices.json')
}

export function getPricesUK(): PricesFile {
  return readJson<PricesFile>('prices_uk.json')
}

export function getPricesDE(): PricesFile {
  return readJson<PricesFile>('prices_de.json')
}

export function getMeta(): MetaFile {
  return readJson<MetaFile>('meta.json')
}

export function buildDeviceRows(
  catalog: DeviceCatalog,
  pricesFile: PricesFile,
): DeviceRow[] {
  return catalog.devices
    .map((device) => ({
      device,
      prices: pricesFile.prices[device.normalized_id] ?? {},
    }))
    .filter((row) => Object.keys(row.prices).length > 0)
    .sort((a, b) => a.device.canonical_name.localeCompare(b.device.canonical_name))
}
