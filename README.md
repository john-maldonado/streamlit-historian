# Streamlit Historian MVP

This repository contains a minimal historian trending client built with Streamlit and ECharts.
It can connect to a Snowflake-backed historian API or run in a self-contained demo mode with
synthetic data.

## Features

- Hierarchical tag browser with search, multi-select, and on-demand expansion.
- Multi-series time chart powered by `streamlit-echarts`, including zoom, pan, and brush.
- Time range presets (15m, 1h, 24h, 7d) plus configurable custom range in UTC.
- Aggregation selector and configurable maximum point count per query.
- CSV export for the most recent query result.
- Automatic fallback to synthetic demo data when no API base URL is configured.

## Getting Started

### Installation

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

If you prefer to install manually, the app depends on:

- `streamlit`
- `streamlit-echarts`
- `pandas`
- `requests`

### Configuration

By default the app runs in demo mode using synthetic historian data. To connect to a real API,
provide a base URL via Streamlit secrets (`.streamlit/secrets.toml`):

```toml
API_BASE = "https://your-api-host"
```

### Running the App

```bash
streamlit run app.py
```

Open the printed local URL in your browser. Select tags from the sidebar to visualize trends.

### Running with Docker

Build and run the app inside a container (port 8501) using either Docker directly or
`docker-compose`:

```bash
# Build the image
docker build -t streamlit-historian .

# Run the container
docker run --rm -p 8501:8501 streamlit-historian

# Or use docker-compose
docker compose up --build
```

When connecting to a real API, supply `API_BASE` via Streamlit secrets. One option is to mount a
`.streamlit/secrets.toml` file into the container:

```bash
docker run --rm -p 8501:8501 \
  -v $(pwd)/.streamlit/secrets.toml:/app/.streamlit/secrets.toml:ro \
  streamlit-historian
```

### CSV Export

The **Download CSV** button exports exactly the series shown in the latest chart query. Each row
includes the tag path, timestamp, value, and optional quality flag.

## Development Notes

- Modules are organized under `components/` and `utils/` for clarity.
- The demo API client generates deterministic, sinusoidal signals to mimic real historian data.
- Brush selections highlight the chosen time window and display it beneath the chart. (Auto-query
  on brush is planned for a future iteration.)

## Testing

Linting is provided via `ruff`:

```bash
ruff check .
```

Run this before submitting changes to ensure style and import checks pass.
