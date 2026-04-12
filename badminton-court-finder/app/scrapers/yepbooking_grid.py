"""ASCII grid formatting for YepBooking-style court × time tables."""

from __future__ import annotations

from app.schemas.courts import CourtAvailability


def _effective_prices(
    courts: list[CourtAvailability],
    prices: dict[str, str] | None,
) -> dict[str, str]:
    if prices is not None:
        return prices
    out: dict[str, str] = {}
    for court in courts:
        for s in court.slots:
            if s.price:
                out.setdefault(s.start_time, s.price)
    return out


def format_yepbooking_grid(
    courts: list[CourtAvailability],
    prices: dict[str, str] | None = None,
) -> str:
    """Pretty-print courts × time slots; optional ``prices`` from raw schema parse.

    When ``prices`` is ``None``, per-slot ``CourtSlot.price`` is used for a price column.
    """
    if not courts:
        return "(no courts)\n"

    effective_prices = _effective_prices(courts, prices)

    slot_keys: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for court in courts:
        for s in court.slots:
            k = (s.start_time, s.end_time)
            if k not in seen:
                seen.add(k)
                slot_keys.append(k)
    slot_keys.sort(key=lambda t: t[0])

    headers = ["time"] + [c.court_name for c in courts]
    if effective_prices:
        headers.append("price")

    rows: list[list[str]] = []
    for st, en in slot_keys:
        row: list[str] = [f"{st}–{en}"]
        for court in courts:
            slot = next(
                (
                    s
                    for s in court.slots
                    if s.start_time == st and s.end_time == en
                ),
                None,
            )
            row.append(slot.status.value if slot else "—")
        if effective_prices:
            row.append(effective_prices.get(st, "—"))
        rows.append(row)

    all_rows = [headers, *rows]
    col_widths = [
        max(len(str(row[i])) for row in all_rows) for i in range(len(headers))
    ]

    def fmt_row(cells: list[str]) -> str:
        return " | ".join(str(c).ljust(w) for c, w in zip(cells, col_widths))

    sep = "-+-".join("-" * w for w in col_widths)
    lines = [fmt_row(headers), sep, *(fmt_row(r) for r in rows)]
    return "\n".join(lines) + "\n"
