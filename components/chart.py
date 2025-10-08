"""Chart utilities using ECharts for the historian app."""
from __future__ import annotations

from typing import Iterable, List

from streamlit_echarts import st_echarts


def build_chart_options(series: Iterable[dict], title: str | None = None) -> dict:
    """Build the ECharts option dictionary for the provided series."""

    x_axes = [
        {
            "type": "time",
            "boundaryGap": False,
        }
    ]
    y_axes = [
        {
            "type": "value",
            "scale": True,
        }
    ]

    echarts_series: List[dict] = []
    for idx, series_entry in enumerate(series):
        points = series_entry.get("points", [])
        data: List[list] = []
        for point in points:
            if len(point) >= 2:
                timestamp, value = point[0], point[1]
                quality = point[2] if len(point) > 2 else None
                data.append({
                    "value": [timestamp, value],
                    "quality": quality,
                })
        echarts_series.append(
            {
                "name": series_entry.get("name", f"Series {idx + 1}"),
                "type": "line",
                "showSymbol": False,
                "hoverAnimation": False,
                "sampling": "lttb",
                "data": data,
            }
        )

    options = {
        "title": {"text": title or ""},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "formatter": """
                function(params) {
                    const item = params[0];
                    const date = item.value[0];
                    let lines = [`${new Date(date).toISOString()}`];
                    params.forEach(p => {
                        const quality = p.data && p.data.quality;
                        const qualityText = quality === undefined ? '' : ` (q=${quality})`;
                        lines.push(`${p.seriesName}: ${p.value[1]}${qualityText}`);
                    });
                    return lines.join('<br/>');
                }
            """,
        },
        "legend": {"type": "scroll"},
        "xAxis": x_axes,
        "yAxis": y_axes,
        "grid": {"left": 40, "right": 20, "top": 40, "bottom": 60},
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0},
            {"type": "slider", "xAxisIndex": 0},
        ],
        "brush": {
            "toolbox": ["rect", "clear"],
            "xAxisIndex": "all",
        },
        "series": echarts_series,
        "animation": False,
    }
    return options


def render_time_series(series: Iterable[dict], height: int = 480, key: str | None = None):
    """Render the chart and return any interaction payload from ECharts."""

    options = build_chart_options(series)
    events = {"brushselected": "function(params) { return params; }"}
    return st_echarts(options=options, height=height, key=key, events=events)
