"""Streamlit entry point for the historian MVP."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Dict, Iterable, List

import pandas as pd
import streamlit as st

from components.chart import render_time_series
from components.tag_tree import TagTree, render_tag_tree
from utils.api_client import DEFAULT_MAX_POINTS, get_api_client

st.set_page_config(page_title="Historian", layout="wide")

PRESETS = ["15m", "1h", "24h", "7d", "Custom"]
AGG_OPTIONS = ["raw", "1m", "5m", "1h"]


def init_session_state() -> None:
    now = datetime.now(tz=UTC)
    st.session_state.setdefault("selected_tags", [])
    st.session_state.setdefault("brush_range", None)
    st.session_state.setdefault("last_series_payload", [])
    st.session_state.setdefault("custom_start", now - timedelta(hours=1))
    st.session_state.setdefault("custom_end", now)


def compute_time_range(preset: str, custom_start: datetime, custom_end: datetime) -> tuple[datetime, datetime]:
    now = datetime.now(tz=UTC)
    presets = {
        "15m": now - timedelta(minutes=15),
        "1h": now - timedelta(hours=1),
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
    }
    if preset in presets:
        return presets[preset], now
    return custom_start, custom_end


def parse_brush_coordinate(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    if isinstance(value, str):
        sanitized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(sanitized)
    raise ValueError(f"Unsupported brush coordinate: {value!r}")


def main() -> None:
    init_session_state()
    client = get_api_client()

    st.sidebar.header("Tag Browser")
    with st.sidebar:
        search = st.text_input("Filter tags", placeholder="Search...")
        tags = client.fetch_tags()
        tag_tree = TagTree.from_paths(tags)
        filtered_tree = tag_tree.filtered(search)
        selected_tags = render_tag_tree(filtered_tree, st.session_state["selected_tags"])
        st.session_state["selected_tags"] = selected_tags

    st.title("Historian Trends")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        preset = st.selectbox("Time range", PRESETS, index=1)
    with col2:
        agg = st.selectbox("Aggregation", AGG_OPTIONS, index=0)
    with col3:
        max_points = st.number_input(
            "Max points",
            min_value=1000,
            max_value=50000,
            value=DEFAULT_MAX_POINTS,
            step=1000,
        )

    custom_start = st.session_state["custom_start"]
    custom_end = st.session_state["custom_end"]
    if preset == "Custom":
        st.subheader("Custom range (UTC)")
        start_col, end_col = st.columns(2)
        with start_col:
            start_date = st.date_input(
                "Start date",
                value=custom_start.date(),
                key="custom_start_date",
            )
            start_time = st.time_input(
                "Start time",
                value=custom_start.time(),
                key="custom_start_time",
            )
        with end_col:
            end_date = st.date_input(
                "End date",
                value=custom_end.date(),
                key="custom_end_date",
            )
            end_time = st.time_input(
                "End time",
                value=custom_end.time(),
                key="custom_end_time",
            )
        custom_start = datetime.combine(start_date, start_time).replace(tzinfo=UTC)
        custom_end = datetime.combine(end_date, end_time).replace(tzinfo=UTC)
        st.session_state["custom_start"] = custom_start
        st.session_state["custom_end"] = custom_end

    start, end = compute_time_range(preset, custom_start, custom_end)

    if start >= end:
        st.error("Start time must be before end time.")
        return

    st.write(f"Showing data from **{start.isoformat()}** to **{end.isoformat()}** (UTC)")

    if not selected_tags:
        st.info("Select one or more tags from the sidebar to view trends.")
        return

    with st.spinner("Loading series..."):
        series_payload = client.fetch_series(selected_tags, start, end, agg, int(max_points))
        st.session_state["last_series_payload"] = series_payload

    chart_events = render_time_series(series_payload, key="historian_chart")

    if chart_events and chart_events.get("areas"):
        try:
            area = chart_events["areas"][0]
            coord_range = area["coordRange"]
            st.session_state["brush_range"] = (
                parse_brush_coordinate(coord_range[0]),
                parse_brush_coordinate(coord_range[1]),
            )
        except Exception:  # pragma: no cover - defensive
            st.session_state["brush_range"] = None
    elif chart_events:
        st.session_state["brush_range"] = None

    if st.session_state["brush_range"]:
        start_brush, end_brush = st.session_state["brush_range"]
        st.caption(
            f"Brushed range: {start_brush.isoformat()} to {end_brush.isoformat()}"
        )

    if st.session_state["last_series_payload"]:
        csv_buffer = build_csv(st.session_state["last_series_payload"])
        st.download_button(
            "Download CSV",
            data=csv_buffer.getvalue(),
            file_name="historian_export.csv",
            mime="text/csv",
        )


def build_csv(series_payload: List[Dict[str, Iterable]]) -> StringIO:
    rows = []
    for series in series_payload:
        name = series.get("name")
        for point in series.get("points", []):
            timestamp = point[0]
            value = point[1]
            quality = point[2] if len(point) > 2 else None
            rows.append(
                {
                    "tag": name,
                    "timestamp": timestamp,
                    "value": value,
                    "quality": quality,
                }
            )
    buffer = StringIO()
    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(buffer, index=False)
    else:
        buffer.write("")
    buffer.seek(0)
    return buffer


if __name__ == "__main__":
    main()
