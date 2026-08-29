"""Build deterministic, dependency-free SVG assets from frozen research reports."""

# ruff: noqa: E501

from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F6_REPORT = ROOT / "artifacts/f6-final-ranking-robustness-report.json"
OUTPUT_DIR = ROOT / "docs/assets"

COLORS = {
    "ink": "#10243E",
    "muted": "#607089",
    "grid": "#DCE4EE",
    "blue": "#2563EB",
    "cyan": "#0891B2",
    "green": "#059669",
    "amber": "#D97706",
    "red": "#DC2626",
    "surface": "#F8FAFC",
    "white": "#FFFFFF",
}


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected an object: {path}")
    return payload


def _write(name: str, body: str, *, width: int = 1200, height: int = 675) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<rect width="100%" height="100%" fill="{COLORS['white']}"/>
<style>
  text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: {COLORS['ink']}; }}
  .title {{ font-size: 30px; font-weight: 700; }}
  .subtitle {{ font-size: 17px; fill: {COLORS['muted']}; }}
  .label {{ font-size: 16px; font-weight: 600; }}
  .small {{ font-size: 13px; fill: {COLORS['muted']}; }}
</style>
{body}
</svg>
"""
    (OUTPUT_DIR / name).write_text(svg, encoding="utf-8")


def build_model_comparison(report: dict[str, object]) -> None:
    models = report["model_summaries"]
    order = [
        ("normalized_move_persistence", "Persistence", COLORS["muted"]),
        ("ridge_regression", "Ridge", COLORS["blue"]),
        ("hist_gradient_boosting_regressor", "HGB", COLORS["cyan"]),
    ]
    body = [
        '<text x="64" y="62" class="title">Historical OOS model comparison</text>',
        '<text x="64" y="92" class="subtitle">Seven rolling-origin folds · frozen F5/F6 evidence · higher is better</text>',
    ]
    panels = [
        ("Mean Spearman rank correlation", "mean_spearman", 0.22, 76),
        ("Mean top-decile lift", "mean_top_decile_lift_ratio", 1.45, 638),
    ]
    for title, metric, maximum, panel_x in panels:
        body.append(
            f'<rect x="{panel_x}" y="132" width="486" height="430" rx="18" fill="{COLORS["surface"]}" stroke="{COLORS["grid"]}"/>'
        )
        body.append(f'<text x="{panel_x + 28}" y="176" class="label">{escape(title)}</text>')
        for index, (key, label, color) in enumerate(order):
            value = float(models[key][metric])
            y = 232 + index * 102
            baseline = 1.0 if metric == "mean_top_decile_lift_ratio" else 0.0
            span = maximum - baseline
            width = max(0.0, (value - baseline) / span) * 370
            body.extend(
                [
                    f'<text x="{panel_x + 28}" y="{y}" class="label">{label}</text>',
                    f'<rect x="{panel_x + 28}" y="{y + 18}" width="370" height="30" rx="8" fill="{COLORS["grid"]}"/>',
                    f'<rect x="{panel_x + 28}" y="{y + 18}" width="{width:.2f}" height="30" rx="8" fill="{color}"/>',
                    f'<text x="{panel_x + 414}" y="{y + 41}" text-anchor="end" class="label">{value:.4f}</text>',
                ]
            )
    body.extend(
        [
            '<rect x="76" y="590" width="1048" height="52" rx="12" fill="#EFF6FF"/>',
            '<text x="100" y="622" class="subtitle">Ridge selected by the predeclared practical-tie rule; this is ranking evidence, not direction or return prediction.</text>',
        ]
    )
    _write("track_a_model_comparison.svg", "\n".join(body))


def build_decile_chart(report: dict[str, object]) -> None:
    buckets = report["decile_analysis"]["ridge_regression"][
        "pooled_outer_assigned_deciles"
    ]["buckets"]
    values = [float(buckets[f"D{index}"]["mean_realized_target"]) for index in range(1, 11)]
    lower = [
        float(
            buckets[f"D{index}"]["bootstrap_95_interval_mean_realized_target"]["lower"]
        )
        for index in range(1, 11)
    ]
    upper = [
        float(
            buckets[f"D{index}"]["bootstrap_95_interval_mean_realized_target"]["upper"]
        )
        for index in range(1, 11)
    ]
    left, top, width, height = 100, 150, 1030, 400
    minimum, maximum = 0.4, 1.25

    def x(index: int) -> float:
        return left + index * width / 9

    def y(value: float) -> float:
        return top + (maximum - value) / (maximum - minimum) * height

    body = [
        '<text x="64" y="62" class="title">Ridge score deciles rank realized volatility surprise</text>',
        '<text x="64" y="92" class="subtitle">Pooled outer-fold assigned deciles · 20,637 historical OOS rows · 95% cluster-bootstrap intervals</text>',
    ]
    for tick in [0.4, 0.6, 0.8, 1.0, 1.2]:
        tick_y = y(tick)
        body.extend(
            [
                f'<line x1="{left}" y1="{tick_y:.2f}" x2="{left + width}" y2="{tick_y:.2f}" stroke="{COLORS["grid"]}"/>',
                f'<text x="{left - 18}" y="{tick_y + 5:.2f}" text-anchor="end" class="small">{tick:.1f}</text>',
            ]
        )
    points = " ".join(f"{x(i):.2f},{y(value):.2f}" for i, value in enumerate(values))
    body.append(
        f'<polyline points="{points}" fill="none" stroke="{COLORS["blue"]}" stroke-width="5" stroke-linejoin="round"/>'
    )
    for index, value in enumerate(values):
        point_x, point_y = x(index), y(value)
        body.extend(
            [
                f'<line x1="{point_x:.2f}" y1="{y(lower[index]):.2f}" x2="{point_x:.2f}" y2="{y(upper[index]):.2f}" stroke="{COLORS["cyan"]}" stroke-width="3"/>',
                f'<circle cx="{point_x:.2f}" cy="{point_y:.2f}" r="7" fill="{COLORS["blue"]}"/>',
                f'<text x="{point_x:.2f}" y="{top + height + 32}" text-anchor="middle" class="label">D{index + 1}</text>',
            ]
        )
    body.extend(
        [
            '<text x="64" y="620" class="subtitle">D1 = lowest predicted score · D10 = highest · pooled monotonic steps: 9/9</text>',
            '<text x="1136" y="620" text-anchor="end" class="subtitle">Not prospective validation</text>',
        ]
    )
    _write("track_a_ridge_deciles.svg", "\n".join(body))


def build_architecture() -> None:
    boxes = [
        (70, 170, 240, 118, "LINE / GAS", "Thin adapter\nRouting · reply · Flex", COLORS["green"]),
        (70, 360, 240, 118, "Streamlit", "Controlled offline fixture\nor loopback API", COLORS["cyan"]),
        (465, 245, 270, 150, "FastAPI", "Identity · portfolio rules\nTrack A/B contracts\nNo request-time providers", COLORS["blue"]),
        (890, 120, 255, 125, "Track A", "Frozen Ridge model\nVolatility-surprise rank", COLORS["blue"]),
        (890, 285, 255, 150, "Track B", "Event intelligence\nReaction magnitude signal\nChinese sentiment abstains", COLORS["amber"]),
        (890, 480, 255, 105, "Storage", "Versioned lineage\nPrivate/public boundary", COLORS["muted"]),
    ]
    body = [
        '<text x="64" y="62" class="title">Financial AI Assistant — system architecture</text>',
        '<text x="64" y="92" class="subtitle">Research-first contracts with explicit serving, privacy and abstention boundaries</text>',
    ]
    for x, y, width, height, title, subtitle, color in boxes:
        body.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{COLORS["white"]}" stroke="{color}" stroke-width="3"/>'
        )
        body.append(f'<text x="{x + 22}" y="{y + 35}" class="label">{escape(title)}</text>')
        for line_index, line in enumerate(subtitle.split("\n")):
            body.append(
                f'<text x="{x + 22}" y="{y + 68 + line_index * 22}" class="small">{escape(line)}</text>'
            )
    arrows = [
        (310, 229, 465, 295, COLORS["green"]),
        (310, 419, 465, 345, COLORS["cyan"]),
        (735, 285, 890, 185, COLORS["blue"]),
        (735, 325, 890, 355, COLORS["amber"]),
        (735, 365, 890, 530, COLORS["muted"]),
    ]
    for x1, y1, x2, y2, color in arrows:
        body.extend(
            [
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="3"/>',
                f'<circle cx="{x2}" cy="{y2}" r="5" fill="{color}"/>',
            ]
        )
    body.extend(
        [
            f'<rect x="360" y="520" width="420" height="80" rx="14" fill="#FEF2F2" stroke="{COLORS["red"]}" stroke-dasharray="8 6"/>',
            '<text x="382" y="551" class="label">Current-market serving: BLOCKED</text>',
            '<text x="382" y="578" class="small">F11B-2A exact feature parity 5/23 · controlled demo remains valid</text>',
        ]
    )
    _write("system_architecture.svg", "\n".join(body), width=1220, height=675)


def main() -> None:
    report = _load(F6_REPORT)
    build_model_comparison(report)
    build_decile_chart(report)
    build_architecture()
    print("built 3 deterministic portfolio SVG assets")


if __name__ == "__main__":
    main()
