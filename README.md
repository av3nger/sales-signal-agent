# Sales Signal Research Agent

A FastAPI service that researches public web data to detect **sales signals** for a target company and produce an actionable outreach recommendation (`CONTACT`, `MONITOR`, or `AVOID`).

Given a company (and optionally an Ideal Customer Profile), the agent searches the web, extracts structured business events with an LLM, and applies a rule-based engine to score six categories of buying signals.

## How It Works

```
Request → Adapters (Tavily web search) → Evidence
        → EventExtractor (Claude) → Structured events
        → SignalEngine (rule-based) → Signals + Recommendation
```

1. **Adapters** (`app/adapters/`) — each adapter issues targeted web searches via [Tavily](https://tavily.com) for one signal category, deduplicates by URL, and returns `EvidenceItem`s.
2. **EventExtractor** (`app/extractor.py`) — sends each evidence snippet to Claude and parses a structured `ExtractedEvent` (event type, dates, amounts, seniority, etc.) with a simplified retry on JSON failures.
3. **SignalEngine** (`app/signal_engine.py`) — applies recency and relevance rules to events to compute each `Signal`'s status, direction, and confidence, then derives an overall recommendation.

### Signal Types

| Signal | Detects |
|---|---|
| `EXEC_MOVEMENT` | Leadership hires/departures in compliance, risk, security (or ICP-defined roles) |
| `REGULATORY_PRESSURE` | Fines, audits, enforcement actions, compliance deadlines |
| `FINANCIAL_TRENDS` | Funding, layoffs, revenue changes, M&A, budget cuts |
| `JOB_OPENINGS` | Active hiring and open positions |
| `TECH_TOOL_CHANGES` | Technology adoption and migrations |
| `BUDGET_TRENDS` | Budget allocation, spending increases/decreases |

An optional **ICP** (Ideal Customer Profile) lets you swap the default compliance/risk/security focus for your own target keywords, which steers both search queries and event relevance scoring.

## Requirements

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)
- A [Tavily API key](https://tavily.com)

## Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# then edit .env and fill in ANTHROPIC_API_KEY and TAVILY_API_KEY
```

### Configuration

Settings load from `.env` (see `app/config.py`). Required:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (required) |
| `TAVILY_API_KEY` | Tavily API key (required) |

Optional (with defaults):

| Variable | Default | Description |
|---|---|---|
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `MAX_EVIDENCE_PER_ADAPTER` | `10` | Max evidence items kept per adapter |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model used for event extraction |
| `LLM_MAX_TOKENS` | `1024` | Max tokens per extraction call |
| `EXEC_MOVEMENT_RECENCY_DAYS` | `90` | Recency window for exec movement |
| `REGULATORY_DEADLINE_DAYS` | `180` | Recency window for regulatory events |
| `JOB_OPENINGS_RECENCY_DAYS` | `30` | Recency window for job postings |
| `TECH_CHANGES_RECENCY_DAYS` | `90` | Recency window for tech changes |
| `BUDGET_TRENDS_RECENCY_DAYS` | `180` | Recency window for budget changes |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running

```bash
python run.py
```

The API starts on `http://0.0.0.0:8000` with auto-reload. Interactive docs are available at `http://localhost:8000/docs`.

## API

### `GET /health`

Health check.

```json
{ "status": "healthy" }
```

### `POST /analyze`

Analyze a company across all signal types (or a filtered subset).

**Request:**

```json
{
  "company": {
    "name": "Acme Corp",
    "domain": "acme.com",
    "country": "US",
    "industry": "fintech"
  },
  "signal_types": ["EXEC_MOVEMENT", "REGULATORY_PRESSURE"],
  "icp": {
    "keywords": ["data privacy", "security"],
    "description": "Teams responsible for data protection programs"
  }
}
```

- `company.name` and `company.domain` are required; `country`, `industry` are optional.
- `signal_types` is optional — omit to run all six signal types.
- `icp` is optional — provide it to retarget search and relevance scoring.

**Response:**

```json
{
  "company_domain": "acme.com",
  "analyzed_at": "2026-05-18T00:00:00Z",
  "signals": [
    {
      "type": "EXEC_MOVEMENT",
      "status": "POSITIVE",
      "direction": "GROWING",
      "confidence": 0.65,
      "summary": "Recent leadership activity: 1 hire(s) in data privacy, security roles.",
      "evidence": [
        {
          "source_type": "news",
          "title": "Acme names new Chief Privacy Officer",
          "url": "https://example.com/article",
          "published_at": "2026-04-01",
          "snippet": "..."
        }
      ]
    }
  ],
  "recommendation": "CONTACT",
  "recommendation_reasons": ["RECENT_EXEC_HIRE"]
}
```

### `POST /analyze/{signal_type}`

Analyze a single signal type (e.g. `POST /analyze/REGULATORY_PRESSURE`). Same request body as `/analyze` but without `signal_types`. Returns a single `signal` instead of a list.

**Example:**

```bash
curl -X POST http://localhost:8000/analyze/JOB_OPENINGS \
  -H "Content-Type: application/json" \
  -d '{"company": {"name": "Acme Corp", "domain": "acme.com"}}'
```

### Recommendation Logic

The engine maps positive/negative signals to reasons and resolves an overall recommendation:

- **`AVOID`** — negative signals outweigh positive (e.g. financial distress, budget cuts).
- **`CONTACT`** — two or more positive signals, or one positive with no negatives.
- **`MONITOR`** — no actionable signals, or mixed/insufficient evidence.

## Project Structure

```
app/
├── main.py            # FastAPI app and endpoints
├── config.py          # Settings loaded from .env
├── schemas.py         # Pydantic request/response/domain models
├── extractor.py       # LLM-based event extraction (Claude)
├── signal_engine.py   # Rule-based signal + recommendation computation
├── logging_config.py  # Logging setup
└── adapters/          # One web-search adapter per signal category
    ├── base.py        # Shared Tavily search + dedup logic
    ├── news.py        # EXEC_MOVEMENT
    ├── regulatory.py  # REGULATORY_PRESSURE
    ├── financial.py   # FINANCIAL_TRENDS
    ├── jobs.py        # JOB_OPENINGS
    ├── tech.py        # TECH_TOOL_CHANGES
    └── budget.py      # BUDGET_TRENDS
run.py                 # Uvicorn entry point
```

## Notes & Limitations

- Signal extraction depends on live web search results and LLM output; results are non-deterministic and best treated as research leads, not ground truth.
- The Anthropic client is called synchronously inside async handlers; for higher throughput, migrate to `anthropic.AsyncAnthropic` and process evidence concurrently.
- There is currently no automated test suite. Add `pytest` tests under a `tests/` directory before relying on this in production.
