import { useEffect, useMemo, useState } from 'react'
import {
  fetchAvailabilityBatch,
  fetchSites,
  type AvailabilityResponse,
  type SiteInfo,
} from './api/badminton'
import {
  collectSlotKeys,
  countAvailableCourts,
  filterKeysByWindow,
} from './lib/aggregate'
import { nextSydneyDates, sydneyISODay } from './lib/dates'
import { parseSlotKey } from './lib/time'

const DATE_LABEL_TZ = 'Australia/Sydney'
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => i)

/** Calendar days from today (Sydney) to load and show. */
const DAY_SPAN_OPTIONS = [7, 14, 21] as const

/** ISO weekday 1 (Mon) … 7 (Sun), labels for multi-select. */
const WEEKDAY_FILTERS: { iso: number; label: string }[] = [
  { iso: 1, label: 'Mon' },
  { iso: 2, label: 'Tue' },
  { iso: 3, label: 'Wed' },
  { iso: 4, label: 'Thu' },
  { iso: 5, label: 'Fri' },
  { iso: 6, label: 'Sat' },
  { iso: 7, label: 'Sun' },
]

function atWholeHour(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}

type DayCell =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; data: AvailabilityResponse }
  | { status: 'err'; message: string }

type SiteGrid = Record<string, DayCell>

function formatDateHeading(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const utcNoon = new Date(Date.UTC(y, m - 1, d, 12))
  return utcNoon.toLocaleDateString('en-AU', {
    timeZone: DATE_LABEL_TZ,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

function venueLabel(siteKey: string, sites: SiteInfo[], grid: SiteGrid): string {
  const ok = Object.values(grid).find((c) => c.status === 'ok')
  if (ok && ok.status === 'ok') return ok.data.venue_name
  return sites.find((s) => s.key === siteKey)?.venue_name ?? siteKey
}

export default function App() {
  const [sites, setSites] = useState<SiteInfo[]>([])
  const [sitesError, setSitesError] = useState<string | null>(null)
  const [selectedSites, setSelectedSites] = useState<string[]>([])

  const [fromHour, setFromHour] = useState(6)
  const [toHour, setToHour] = useState(22)
  const timeFrom = atWholeHour(fromHour)
  const timeTo = atWholeHour(toHour)

  const [daySpan, setDaySpan] =
    useState<(typeof DAY_SPAN_OPTIONS)[number]>(7)

  /** Empty = all days; otherwise only these ISO weekdays (Sydney). */
  const [selectedWeekdays, setSelectedWeekdays] = useState<number[]>([])

  const [gridBySite, setGridBySite] = useState<Record<string, SiteGrid>>({})
  const [weekLoading, setWeekLoading] = useState(false)
  const [refreshNonce, setRefreshNonce] = useState(0)

  const dates = useMemo(() => nextSydneyDates(daySpan), [daySpan])

  const visibleDates = useMemo(() => {
    if (selectedWeekdays.length === 0) return dates
    const set = new Set(selectedWeekdays)
    return dates.filter((d) => set.has(sydneyISODay(d)))
  }, [dates, selectedWeekdays])

  const [filtersExpanded, setFiltersExpanded] = useState(false)

  const filtersSummary = useMemo(() => {
    const names = sites
      .filter((s) => selectedSites.includes(s.key))
      .map((s) => s.venue_name)
    const venues =
      names.length === 0
        ? 'No venues selected'
        : names.length <= 2
          ? names.join(' · ')
          : `${names.length} venues`
    const wk =
      selectedWeekdays.length === 0
        ? 'All days'
        : selectedWeekdays
            .map(
              (iso) => WEEKDAY_FILTERS.find((w) => w.iso === iso)?.label ?? '',
            )
            .filter(Boolean)
            .join(', ')
    return `${venues} · Next ${daySpan} days · ${wk} · ${timeFrom}–${timeTo}`
  }, [
    sites,
    selectedSites,
    daySpan,
    selectedWeekdays,
    timeFrom,
    timeTo,
  ])

  useEffect(() => {
    let cancelled = false
    fetchSites()
      .then((list) => {
        if (cancelled) return
        setSites(list)
        setSelectedSites((prev) => {
          if (prev.length > 0) return prev
          const botany = list.find((s) => s.key === 'botany')
          if (botany) return [botany.key]
          return list[0] ? [list[0].key] : []
        })
      })
      .catch((e) => {
        if (!cancelled) {
          setSitesError(e instanceof Error ? e.message : 'Failed to load sites')
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (selectedSites.length === 0) {
      return
    }

    /* eslint-disable react-hooks/set-state-in-effect -- loading flags before availability batch fetches */
    setWeekLoading(true)
    setGridBySite((prev) => {
      const next: Record<string, SiteGrid> = { ...prev }
      for (const site of selectedSites) {
        const row: SiteGrid = { ...(next[site] ?? {}) }
        for (const date of dates) {
          row[date] = { status: 'loading' }
        }
        next[site] = row
      }
      return next
    })
    /* eslint-enable react-hooks/set-state-in-effect */

    let cancelled = false

    void Promise.all(
      selectedSites.map(async (site) => {
        try {
          const batch = await fetchAvailabilityBatch(site, dates)
          if (cancelled) return
          setGridBySite((g) => {
            const row: SiteGrid = { ...g[site] }
            for (const day of batch.days) {
              if (day.ok && day.data) {
                row[day.date] = { status: 'ok', data: day.data }
              } else {
                row[day.date] = {
                  status: 'err',
                  message: day.error ?? 'Unknown error',
                }
              }
            }
            return { ...g, [site]: row }
          })
        } catch (e) {
          if (cancelled) return
          const message = e instanceof Error ? e.message : 'Unknown error'
          setGridBySite((g) => {
            const row: SiteGrid = { ...g[site] }
            for (const date of dates) {
              row[date] = { status: 'err', message }
            }
            return { ...g, [site]: row }
          })
        }
      }),
    ).finally(() => {
      if (!cancelled) setWeekLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [selectedSites, dates, refreshNonce])

  function toggleWeekday(iso: number) {
    setSelectedWeekdays((prev) => {
      const next = prev.includes(iso)
        ? prev.filter((x) => x !== iso)
        : [...prev, iso]
      return next.sort((a, b) => a - b)
    })
  }

  function toggleSite(key: string) {
    setSelectedSites((prev) => {
      const next = prev.includes(key)
        ? prev.filter((k) => k !== key)
        : [...prev, key].sort()
      if (next.length === 0) {
        setGridBySite({})
        setWeekLoading(false)
      }
      return next
    })
  }

  return (
    <div className="mx-auto min-h-svh max-w-6xl px-4 py-10 text-left">
      <header className="mb-10">
        <p className="text-sm font-medium text-[var(--color-accent)]">
          Katchup · Activity Hub
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[var(--color-ink)] sm:text-4xl">
          Court availability
        </h1>
        <p className="mt-3 max-w-2xl text-[var(--color-ink-muted)]">
          Rolling calendar days from today in Australia/Sydney (pick how many
          below). Each cell is the number of courts with at least one{' '}
          <span className="font-medium text-[var(--color-ink)]">available</span>{' '}
          slot for that time row. Data comes from badminton-court-finder.
        </p>
      </header>

      {sitesError && (
        <div
          className="mb-6 rounded-[var(--radius-card)] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {sitesError}
        </div>
      )}

      <section className="mb-8 rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-4 shadow-[var(--shadow-card)] sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <button
            type="button"
            onClick={() => setFiltersExpanded((v) => !v)}
            className="flex min-w-0 flex-1 items-start gap-2 rounded-[var(--radius-control)] text-left hover:bg-[var(--color-surface)] sm:gap-3 sm:px-1 sm:py-0.5"
            aria-expanded={filtersExpanded}
            aria-controls="filters-panel"
            id="filters-disclosure"
          >
            <span
              className={`mt-0.5 inline-flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-ink-muted)] transition-transform duration-200 ${
                filtersExpanded ? 'rotate-180' : ''
              }`}
              aria-hidden
            >
              <svg
                className="size-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
                  clipRule="evenodd"
                />
              </svg>
            </span>
            <span className="min-w-0">
              <span className="block text-lg font-semibold text-[var(--color-ink)]">
                Filters
              </span>
              {!filtersExpanded && (
                <span className="mt-1 block text-xs leading-snug text-[var(--color-ink-muted)]">
                  {filtersSummary}
                </span>
              )}
            </span>
          </button>
          <button
            type="button"
            onClick={() => setRefreshNonce((n) => n + 1)}
            disabled={weekLoading || selectedSites.length === 0}
            className="shrink-0 rounded-[var(--radius-control)] bg-[var(--color-accent)] px-4 py-2 text-sm font-medium text-white shadow-sm hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Refresh
          </button>
        </div>

        <div
          id="filters-panel"
          role="region"
          aria-labelledby="filters-disclosure"
          hidden={!filtersExpanded}
          className="mt-4 border-t border-[var(--color-border)] pt-4"
        >
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-ink-muted)]">
              Locations
            </p>
            {sites.length === 0 && !sitesError ? (
              <p className="text-sm text-[var(--color-ink-muted)]">
                Loading sites…
              </p>
            ) : (
              <div className="flex flex-wrap gap-x-4 gap-y-2">
                {sites.map((s) => (
                  <label
                    key={s.key}
                    className="flex cursor-pointer items-center gap-2 rounded-[var(--radius-control)] px-2 py-1 hover:bg-[var(--color-surface)]"
                  >
                    <input
                      type="checkbox"
                      className="size-4 shrink-0 rounded border-[var(--color-border)] text-[var(--color-accent)]"
                      checked={selectedSites.includes(s.key)}
                      onChange={() => toggleSite(s.key)}
                    />
                    <span className="text-sm font-medium text-[var(--color-ink)]">
                      {s.venue_name}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="mt-5 border-t border-[var(--color-border)] pt-5">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-ink-muted)]">
              Dates
            </p>
            <div className="flex flex-wrap items-center gap-3 gap-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm text-[var(--color-ink-muted)]">
                  Range
                </span>
                <select
                  value={daySpan}
                  onChange={(e) =>
                    setDaySpan(
                      Number(e.target.value) as (typeof DAY_SPAN_OPTIONS)[number],
                    )
                  }
                  className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-white px-3 py-2 text-sm"
                  aria-label="Number of days to load"
                >
                  {DAY_SPAN_OPTIONS.map((n) => (
                    <option key={n} value={n}>
                      Next {n} days
                    </option>
                  ))}
                </select>
              </div>
              <span
                className="hidden h-6 w-px bg-[var(--color-border)] sm:block"
                aria-hidden
              />
              <div
                className="flex min-w-0 flex-wrap items-center gap-2"
                role="group"
                aria-label="Filter by day of week"
              >
                <span className="text-sm text-[var(--color-ink-muted)]">
                  Days
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {WEEKDAY_FILTERS.map(({ iso, label }) => {
                    const on = selectedWeekdays.includes(iso)
                    return (
                      <button
                        key={iso}
                        type="button"
                        onClick={() => toggleWeekday(iso)}
                        className={
                          on
                            ? 'rounded-[var(--radius-control)] bg-[var(--color-accent)] px-2.5 py-1.5 text-xs font-semibold text-white shadow-sm sm:text-sm'
                            : 'rounded-[var(--radius-control)] border border-[var(--color-border)] bg-white px-2.5 py-1.5 text-xs font-medium text-[var(--color-ink)] hover:bg-[var(--color-surface)] sm:text-sm'
                        }
                        aria-pressed={on}
                      >
                        {label}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 border-t border-[var(--color-border)] pt-5">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--color-ink-muted)]">
              Time window (hours)
            </p>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-2">
              <span className="text-sm text-[var(--color-ink-muted)]">From</span>
              <select
                value={fromHour}
                onChange={(e) => setFromHour(Number(e.target.value))}
                className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-white px-3 py-2 text-sm tabular-nums"
                aria-label="From hour"
              >
                {HOUR_OPTIONS.map((h) => (
                  <option key={`fh-${h}`} value={h}>
                    {atWholeHour(h)}
                  </option>
                ))}
              </select>
              <span className="text-sm text-[var(--color-ink-muted)]">to</span>
              <select
                value={toHour}
                onChange={(e) => setToHour(Number(e.target.value))}
                className="rounded-[var(--radius-control)] border border-[var(--color-border)] bg-white px-3 py-2 text-sm tabular-nums"
                aria-label="To hour"
              >
                {HOUR_OPTIONS.map((h) => (
                  <option key={`th-${h}`} value={h}>
                    {atWholeHour(h)}
                  </option>
                ))}
              </select>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--color-ink-muted)]">
              Whole hours only; table rows are slot intervals that overlap this
              range. Loading more days issues more requests per venue; some
              sites only publish bookings a few weeks ahead.
            </p>
          </div>
        </div>
      </section>

      {selectedSites.length === 0 && sites.length > 0 && (
        <p className="text-sm text-[var(--color-ink-muted)]">
          Select at least one location to load availability.
        </p>
      )}

      {visibleDates.length === 0 && selectedWeekdays.length > 0 ? (
        <p className="text-sm text-[var(--color-ink-muted)]">
          No loaded days match your day selection. Clear day filters or pick
          different days.
        </p>
      ) : (
        <div className="flex flex-col gap-10">
          {selectedSites.map((siteKey) => (
            <SiteWeekTable
              key={siteKey}
              venueName={venueLabel(siteKey, sites, gridBySite[siteKey] ?? {})}
              dates={visibleDates}
              grid={gridBySite[siteKey] ?? {}}
              timeFrom={timeFrom}
              timeTo={timeTo}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function SiteWeekTable({
  venueName,
  dates,
  grid,
  timeFrom,
  timeTo,
}: {
  venueName: string
  dates: string[]
  grid: SiteGrid
  timeFrom: string
  timeTo: string
}) {
  const rowKeys = useMemo(() => {
    const okResponses = dates
      .map((d) => grid[d])
      .filter(
        (c): c is { status: 'ok'; data: AvailabilityResponse } =>
          c?.status === 'ok',
      )
      .map((c) => c.data)
    const all = collectSlotKeys(okResponses)
    return filterKeysByWindow(all, timeFrom, timeTo)
  }, [dates, grid, timeFrom, timeTo])

  const anyLoading = dates.some((d) => grid[d]?.status === 'loading')

  return (
    <section className="overflow-x-auto rounded-[var(--radius-card)] border border-[var(--color-border)] bg-[var(--color-surface-elevated)] shadow-[var(--shadow-card)]">
      <div className="border-b border-[var(--color-border)] px-5 py-4">
        <h2 className="text-lg font-semibold text-[var(--color-ink)]">
          {venueName}
        </h2>
      </div>
      {anyLoading && rowKeys.length === 0 ? (
        <p className="px-5 py-8 text-sm text-[var(--color-ink-muted)]">
          Loading availability…
        </p>
      ) : dates.length === 0 ? (
        <p className="px-5 py-8 text-sm text-[var(--color-ink-muted)]">
          No days to show for the current filters.
        </p>
      ) : rowKeys.length === 0 ? (
        <p className="px-5 py-8 text-sm text-[var(--color-ink-muted)]">
          No slot rows in this time window for the loaded days (or all requests
          failed).
        </p>
      ) : (
        <table className="w-full min-w-[640px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
              <th
                scope="col"
                className="sticky left-0 z-10 bg-[var(--color-surface)] px-4 py-3 text-left font-medium text-[var(--color-ink-muted)]"
              >
                Time
              </th>
              {dates.map((d) => (
                <th
                  key={d}
                  scope="col"
                  className="px-3 py-3 text-center font-medium text-[var(--color-ink-muted)]"
                >
                  {formatDateHeading(d)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowKeys.map((key) => {
              const { start, end } = parseSlotKey(key)
              return (
                <tr
                  key={key}
                  className="border-b border-[var(--color-border)] last:border-0"
                >
                  <th
                    scope="row"
                    className="sticky left-0 z-10 whitespace-nowrap bg-[var(--color-surface-elevated)] px-4 py-2.5 text-left font-mono text-xs font-medium text-[var(--color-ink)]"
                  >
                    {start}–{end}
                  </th>
                  {dates.map((d) => {
                    const cell = grid[d]
                    if (!cell || cell.status === 'idle')
                      return (
                        <td
                          key={d}
                          className="px-2 py-2 text-center text-[var(--color-ink-muted)]"
                        >
                          —
                        </td>
                      )
                    if (cell.status === 'loading')
                      return (
                        <td
                          key={d}
                          className="px-2 py-2 text-center text-[var(--color-ink-muted)]"
                        >
                          …
                        </td>
                      )
                    if (cell.status === 'err')
                      return (
                        <td
                          key={d}
                          className="px-2 py-2 text-center"
                          title={cell.message}
                        >
                          <span className="text-amber-700" aria-label={cell.message}>
                            !
                          </span>
                        </td>
                      )
                    const n = countAvailableCourts(cell.data, start, end)
                    return (
                      <td key={d} className="px-2 py-2 text-center">
                        <span
                          className={
                            n > 0
                              ? 'inline-flex min-w-[2rem] justify-center rounded-md bg-[var(--color-accent-muted)] px-2 py-1 text-sm font-semibold text-[var(--color-accent)]'
                              : 'text-[var(--color-ink-muted)]'
                          }
                        >
                          {n}
                        </span>
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}
