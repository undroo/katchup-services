export type SlotStatus = 'available' | 'booked' | 'past'

export interface CourtSlot {
  start_time: string
  end_time: string
  status: SlotStatus
  price?: string | null
}

export interface CourtAvailability {
  court_name: string
  slots: CourtSlot[]
}

export interface AvailabilityResponse {
  site: string
  venue_name: string
  date: string
  courts: CourtAvailability[]
  scraped_at: string
}

export interface SiteInfo {
  key: string
  venue_name: string
  timezone: string
}

export interface SitesListResponse {
  sites: SiteInfo[]
}

export interface AvailabilityDayItem {
  date: string
  ok: boolean
  data?: AvailabilityResponse
  error?: string | null
}

export interface AvailabilityBatchResponse {
  site: string
  venue_name: string
  days: AvailabilityDayItem[]
}

export function getBadmintonBaseUrl(): string {
  const raw = import.meta.env.VITE_BADMINTON_BASE_URL as string | undefined
  return (raw?.replace(/\/$/, '') || '/api/badminton').replace(/\/$/, '')
}

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail != null) detail = JSON.stringify(body.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export async function fetchSites(): Promise<SiteInfo[]> {
  const base = getBadmintonBaseUrl()
  const res = await fetch(`${base}/v1/courts/sites`)
  const data = await parseJson<SitesListResponse>(res)
  return data.sites
}

export async function fetchAvailability(
  site: string,
  date: string,
): Promise<AvailabilityResponse> {
  const base = getBadmintonBaseUrl()
  const q = new URLSearchParams({ site, date })
  const res = await fetch(`${base}/v1/courts/availability?${q}`)
  return parseJson<AvailabilityResponse>(res)
}

export async function fetchAvailabilityBatch(
  site: string,
  dates: string[],
): Promise<AvailabilityBatchResponse> {
  const base = getBadmintonBaseUrl()
  const res = await fetch(`${base}/v1/courts/availability/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ site, dates }),
  })
  return parseJson<AvailabilityBatchResponse>(res)
}
