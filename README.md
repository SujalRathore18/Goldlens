# Goldlens

Goldlens is a systematic, data-first comparison workspace for gold contracts. The frontend is a React and Vite application and communicates with the FastAPI backend only through REST endpoints. Munimji is intentionally not implemented or modified.

## Setup

### Backend

```powershell
python -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python -m uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

```powershell
cd web
npm install
npm run dev
```

From the repository root, the equivalent commands are:

```powershell
npm run install:web
npm run dev
```

Or run both services with `docker compose up`.

## TinyFish integration

TinyFish is integrated server-side through `POST /api/tinyfish/run`. Configure it
with environment variables before starting the backend:

```powershell
$env:TINYFISH_API_KEY = "sk-tinyfish-your-key"
$env:TINYFISH_BASE_URL = "https://agent.tinyfish.ai"
```

The backend sends `url` and `goal` to TinyFish using the `X-API-Key` header.
The key is never sent to the browser, committed to the repository, or placed in
`.env.example`. The endpoint returns `503` when the key is not configured and
`502` when TinyFish cannot complete the request.

## Engine policy

- Contract fineness defaults are GOLDM 995, GOLDTEN 999, GOLDGUINEA 999, and GOLDPETAL 999. They are synthetic organizer-table metadata and remain unverified.
- Request dates use `DD/MM/YYYY`; response dates use `MM/DD/YYYY`; expiry values use `DDMMMYYYY` with case-insensitive months.
- Executable prices use `turnover / volume` when turnover is present. Otherwise they use the day-t Open. Signal inputs are restricted to data through the close of day t-1. The default slippage scenario is zero basis points and is recorded as `turnover_or_open` in a run manifest.
- Lifecycle windows are contract-specific and block simulated entries and exits outside the common window of both legs.
- Roll-down is `f(tau_t) - f(tau_t-1)` fit using data available through t-1; the residual change is the remainder and is the signal-driving component unless configured otherwise.
- Alerts are quiet by default: one per pair per day, no push, and no buy/sell wording. A failed gate returns a single reason code rather than an alert.

The sample CSV under `data/sample` is synthetic. It is not a market-data source and must not be used as evidence of live performance.

## Testing

```powershell
backend\.venv\Scripts\python -m pytest backend\tests
```

The CI workflow runs backend tests and the frontend type-check/build.

## Pages

The scaffold includes Desk, Intake, Tour, Verdict, Expiry, Basis, Alerts, and Lab routes. Privacy, terms, and favicon assets should be retained when supplied by the product shell.
