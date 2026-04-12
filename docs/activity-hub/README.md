# Activity Hub

Simple web UI for browsing **sport venue time-slot availability** over the next week. It aggregates data from backend microservices (currently [Badminton Court Finder](../badminton-court-finder/README.md)) and shows **how many courts** have at least one **available** slot per time row and date — not individual court names.

**Source:** [`activity-hub/`](../../activity-hub/) (repository root).

## Documentation

| Document | Contents |
|----------|----------|
| [Development](development.md) | Prerequisites, quick start, environment variables |
| [Design and behavior](design-and-behavior.md) | Visual baseline, dates, performance notes |
| [Production](production.md) | Build, hosting, CORS with the court finder |
