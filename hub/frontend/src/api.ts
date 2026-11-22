export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.method && options.method !== 'GET') headers.set('X-Fleetmuster-Request', '1')
  if (options.body) headers.set('Content-Type', 'application/json')
  const response = await fetch('/api/v1' + path, { ...options, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    throw new ApiError(response.status, typeof detail === 'string' ? detail
      : Array.isArray(detail) ? detail[0]?.msg ?? 'Check the submitted values'
      : 'The hub could not complete the request')
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const roles = ['admin', 'operator', 'viewer', 'guest'] as const
export type User = { id: number; username: string; role: typeof roles[number] }
export type Host = {
  id: string
  name: string
  kind: string
  observed_hostname: string | null
  status: 'online' | 'stale' | 'unavailable'
  last_contact: string | null
}

type NumberValue = number | null
type Memory = { total_bytes: NumberValue; used_bytes: NumberValue; usage_percent: NumberValue }
type Interface = {
  type: string
  is_up: boolean | null
  upload_bytes_per_second: NumberValue
  download_bytes_per_second: NumberValue
}
type DiskRate = { read_bytes_per_second: NumberValue; write_bytes_per_second: NumberValue }

export type Collectors = {
  cpu: { logical_cores: NumberValue; load_average: Record<string, NumberValue> } | null
  memory: { ram: Memory; swap: Memory } | null
  disk: {
    filesystems: (Memory & { mountpoint: string })[]
    io: Record<string, DiskRate> | null
  } | null
  network: { interfaces: Record<string, Interface> | null } | null
  temperature: Record<string, { label: string; current_celsius: NumberValue }[]> | null
  system: {
    distribution: string | null
    os: string | null
    kernel: string | null
    architecture: string | null
    uptime_seconds: NumberValue
    power_profile: { name: string } | null
  } | null
}
export type Collector = keyof Collectors
export type Snapshot = {
  host: Host
  summary: Record<string, NumberValue>
  collectors?: Collectors
  freshness: Record<Collector, {
    sampled_at?: string | null
    age_seconds: NumberValue
    status: 'current' | 'stale' | 'unavailable'
  }>
}
export type Point = [string, NumberValue]
export type History = { resolution: 'sample' | 'hour'; series: Record<string, Point[]> }
