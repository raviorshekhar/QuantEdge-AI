# QuantEdge AI

**Trading Intelligence & Research Platform**

QuantEdge AI is a personal trading intelligence project focused on building a structured, data-driven platform for market analysis, strategy research, backtesting, and paper trading.

The project combines financial market data engineering, rule-based trading strategies, quantitative analysis, and AI/LLM capabilities. It is being developed incrementally, with an emphasis on reliable foundations, modular architecture, and explainable trading decisions.

> **Current focus:** Building a reliable market data and paper-trading foundation for NIFTY Futures strategy research.

---

## Project Vision

The long-term vision is to develop an intelligent platform that helps users:

- Analyze market trends and trading opportunities.
- Generate rule-based trading signals.
- Evaluate strategies using historical market data.
- Backtest trading strategies before applying them.
- Simulate trades through paper trading.
- Understand the reasoning and evidence behind trading signals.
- Use AI-powered research and retrieval capabilities to support decision-making.

QuantEdge AI is intended to provide trading guidance and intelligence, not execute live broker orders.

## Initial Strategy Scope

The first strategy research phase focuses on:

| Component | Scope |
|---|---|
| Trading instrument | Individual NIFTY Futures expiry contracts |
| Market reference | NIFTY 50 Index |
| Strategy approach | Rule-based trend following |
| Technical indicators | EMA, RSI, ATR |
| Execution mode | Paper trading |
| Live broker execution | Out of scope |

The initial strategy will be deterministic and rule-based. ML-based prediction and advanced AI capabilities can be explored in later phases.

## Architecture

The project follows a **Modular Monolith** architecture, with clear separation of responsibilities and room for future extension.

```text
QuantEdge-AI/
│
├── src/
│   └── quantedge/
│       ├── market_data/
│       ├── instruments/
│       ├── paper_trading/
│       ├── strategies/
│       ├── backtesting/
│       ├── risk/
│       ├── analytics/
│       ├── api/
│       └── shared/
│
├── tests/
│   └── unit/
│
├── practice/
│
├── data/
│   ├── sample/
│   └── processed/
│
├── outputs/
│
├── pyproject.toml
└── README.md
```

*The directory structure represents the current project organization; some modules are placeholders for planned capabilities.*

## Implemented Foundation

The following components have been developed:

### 1. Instrument Management
- Instrument models for Index and Futures.
- Instrument validation.
- Instrument master registry.
- Underlying instrument relationship validation.
- Provider-to-instrument mapping.
- Mapping validity and overlap checks.

### 2. Market Data Engineering
- Immutable and validated market candle models.
- OHLC and volume validation.
- Timezone-aware timestamp handling.
- CSV market data ingestion.
- Parquet storage using PyArrow.
- CSV-to-Parquet processing pipeline.

### 3. Paper Trading Foundation
- Trading signal models.
- Signal acceptance and rejection decisions.
- Signal lifecycle management.
- Paper trade creation.
- Trade execution data model.

### 4. Application Configuration
- Environment-based settings.
- Pydantic Settings integration.
- Development, testing, and production environment support.

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python 3.12+ |
| Data validation | Pydantic |
| Configuration | Pydantic Settings |
| Data storage | Apache Parquet |
| Parquet engine | PyArrow |
| Testing | Pytest |
| Version control | Git and GitHub |

Additional technologies will be introduced when required by specific product capabilities.

## Getting Started

### Prerequisites

- Python 3.12 or later
- Git
- VS Code (recommended)

### 1. Clone the repository

```bash
git clone https://github.com/raviorshekhar/QuantEdge-AI.git
cd QuantEdge-AI
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
```

### 3. Activate the environment

**macOS / Linux**

```bash
source .venv/bin/activate
```

### 4. Install the project

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 5. Run the tests

```bash
pytest -v
```

## Development Roadmap

The project will evolve through incremental milestones.

- [x] Initial project structure and configuration
- [x] Instrument models and instrument master
- [x] Provider mapping validation
- [x] Market candle validation
- [x] CSV ingestion and Parquet storage
- [x] Initial paper trading models and signal lifecycle
- [ ] Instrument metadata and provider mapping resolution
- [ ] Market data quality and validation improvements
- [ ] Trade execution and exit lifecycle
- [ ] Technical indicator calculation
- [ ] Rule-based NIFTY Futures strategy engine
- [ ] Risk management framework
- [ ] Historical backtesting engine
- [ ] Performance analytics and trade reporting
- [ ] AI-powered research and RAG capabilities
- [ ] User-facing application

## Engineering Principles

- Modular and maintainable architecture.
- Data validation at system boundaries.
- Test-driven development wherever practical.
- Separation of strategy logic, market data, and trade lifecycle.
- Reproducible and explainable trading decisions.
- Paper trading before considering real-world execution.
- Incremental development without unnecessary architectural complexity.

## Disclaimer

QuantEdge AI is an independent software development and research project. Its outputs are intended for research, experimentation, and educational purposes. Trading involves financial risk, and no strategy or signal guarantees returns. The project does not execute live trades.

---

**QuantEdge AI — Research. Analyze. Validate. Improve.**