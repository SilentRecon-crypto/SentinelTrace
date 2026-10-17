# SentinelTrace — Frontend (SIH 2026)

Predictive cybercrime intelligence & cash-out risk analysis platform.
**Predict. Trace. Intervene.**

This is the **frontend-only** build. It runs entirely on a deterministic mock
data layer and is architected so the mock layer can be swapped for the real
SentinelTrace Python/FastAPI backend later without touching any UI code.

## Getting started

```bash
npm install
npm run dev       # http://localhost:5173
npm run build      # production build -> dist/
npm run preview    # serve the production build locally
```

## Architecture

```
src/
  components/
    ui/          Reusable primitives: RiskBadge, StatusBadge, KPICard,
                 DataTable, RiskMeter, Skeleton/Empty/Error states, PinButton
    layout/      Sidebar, Topbar, CommandPalette (Ctrl/Cmd+K), AlertCenter, brand mark
    charts/      RiskTrendChart (recharts)
    network/     NetworkGraphView -- interactive SVG transaction graph
    map/         IndiaMap -- stylized location risk map
  pages/         One component per route (Dashboard, Complaints, Accounts, ...)
  layouts/       AppShell (sidebar + topbar + routed content)
  data/          mockData.ts (deterministic generator), reference.ts (static
                 reference lists -- cities, Model A/B feature descriptions)
  services/      api.ts -- the ONLY place that touches mock data. Every
                 function returns a Promise and mirrors a planned FastAPI
                 endpoint (see comment header in the file).
  hooks/         useAsync (generic fetch/loading/error hook),
                 useWorkspace (Investigation Workspace pin state)
  types/         Shared TypeScript interfaces -- the frontend/backend contract
  utils/         Formatting (INR, dates, percentages) and a seeded PRNG
```

### Swapping in the real backend

Every page imports data exclusively from `src/services/api.ts`. To connect
the real backend, only that file needs to change -- replace each function
body with a `fetch()` call against the matching endpoint:

```
GET /api/complaints                 -> getComplaints()
GET /api/complaints/{id}            -> getComplaint(id)
GET /api/accounts                   -> getAccounts()
GET /api/accounts/{id}              -> getAccount(id)
GET /api/networks/{complaint_id}    -> getNetwork(complaintId)
GET /api/locations                  -> getLocations()
GET /api/locations/{id}             -> getLocation(id)
GET /api/predictions/{complaint_id} -> getPredictions(complaintId)
GET /api/model/metrics              -> getModelMetrics()
```

No component, hook, or page needs to change. Types in `src/types/index.ts`
already describe the expected response shapes.

## Notable pages

- **Dashboard** -- command-center KPIs, risk trend chart, live intelligence
  feed, top suspicious accounts, high-priority complaints.
- **Complaints / Complaint Intelligence** -- investigation table + per-case
  transaction-chain timeline, suspicious accounts, predicted locations.
- **Account Intelligence** -- risk profile, characteristics, Model A
  "Contributing Signals," linked complaints.
- **Transaction Networks** -- interactive SVG graph (pan/zoom/select/Trace
  Path) built from victim -> complaint -> account chain -> cash-out location.
- **Cash-Out Intelligence** -- stylized India map with risk-colored markers,
  ranked location list, location detail panel.
- **Predictions** -- dedicated ranked cash-out prediction screen per complaint.
- **Model Evaluation** -- real Model A metrics (Precision@1/@5, Recall@5, MRR)
  vs. baseline, evaluation context, feature transparency.
- **Investigation Workspace** -- pin complaints/accounts/locations into a
  working case board (session-local state via `useWorkspace`).
- **System Status** -- component health, explicitly labeled Demo Environment.

## Data

All data in `src/data/mockData.ts` is synthetic and deterministic (seeded
PRNG), so the same walkthrough reproduces identically across reloads. It
includes a coherent "hero" investigation story -- complaint `CMP-10482` ->
accounts `ACC-10482` -> `ACC-11037` -> `ACC-11842` -> predicted cash-out
`LOC-084` (New Delhi) -- matching the example figures in the product spec,
for a consistent live-demo walkthrough:

Dashboard -> Complaints -> suspicious accounts -> transaction network ->
trace chain -> highest-risk account -> cash-out intelligence -> ranked
locations -> model performance.

## Stack

React 19 + TypeScript + Vite + Tailwind CSS v4 + React Router + Recharts +
lucide-react. No backend calls, no secrets, no hard-coded credentials.
