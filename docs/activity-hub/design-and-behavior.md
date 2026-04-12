# Activity Hub — design and behavior

## Design

Visual baseline is the [TapTap Design System](https://www.freefigmatemplates.com/gallery/taptap-design-system) (Figma). There is no npm package; spacing, radii, and neutrals are approximated in Tailwind / `src/index.css`.

## Notes

- Dates use the **`Australia/Sydney`** calendar (aligned with configured venues).
- Fetching many locations × 7 days hits the scraper repeatedly; expect slow loads.
