"""SVG plots of a scenario (no plotting library needed, renders on GitHub)."""

from __future__ import annotations

from html import escape

from .models import DoorState
from .scenarios import ScenarioResult
from .simulator import SimulatorConfig

FONT = "font-family='Helvetica, Arial, sans-serif'"
STATE_COLORS = {
    DoorState.CLOSED: "#9aa5b1",
    DoorState.OPENING: "#2e86de",
    DoorState.OPEN: "#27ae60",
    DoorState.CLOSING: "#74b9ff",
    DoorState.STOPPED: "#e67e22",
    DoorState.FAULT: "#c0392b",
}


def scenario_svg(result: ScenarioResult, config: SimulatorConfig | None = None, width: int = 1000) -> str:
    cfg = config or SimulatorConfig()
    h = result.history
    t_end = h[-1].timestamp_s or 1.0
    left, right = 90, 30
    pw = width - left - right
    panels = [
        ("Door position [%]", "position_pct", 0.0, 100.0, None),
        ("Motor current [A]", "motor_current_a", 0.0, 2.5, cfg.overcurrent_limit_a),
        ("Supply voltage [V]", "supply_voltage_v", 0.0, 30.0, cfg.undervoltage_threshold_v),
    ]
    ph, gap, top = 95, 28, 70
    digital_top = top + len(panels) * (ph + gap)
    height = digital_top + 4 * 22 + 70

    def px(t):
        return left + t / t_end * pw

    title = "Healthy open/close cycle" if result.fault is None else f"Injected fault: {result.fault.value}"
    det = ", ".join(f"{d.code} at {d.first_seen_s:.1f} s" for d in result.detections) or "no findings"
    out = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<rect width='100%' height='100%' fill='white'/>",
        f"<text x='{left}' y='26' {FONT} font-size='17' font-weight='bold'>{escape(title)}</text>",
        f"<text x='{left}' y='46' {FONT} font-size='12' fill='#52606d'>Measurement-based detection: {escape(det)} | final state {result.final_state.value}</text>",
    ]

    # command markers
    prev = None
    for t in h:
        if t.command != prev and t.command.value not in ("NONE",):
            x = px(t.timestamp_s)
            out.append(f"<line x1='{x:.1f}' y1='{top - 6}' x2='{x:.1f}' y2='{digital_top + 4 * 22}' stroke='#7b8794' stroke-dasharray='3,3'/>")
            out.append(f"<text x='{x + 4:.1f}' y='{top - 8}' {FONT} font-size='10' fill='#52606d'>cmd {t.command.value}</text>")
        prev = t.command

    for i, (label, attr, lo, hi, limit) in enumerate(panels):
        y0 = top + i * (ph + gap)

        def py(v, y0=y0, lo=lo, hi=hi):
            return y0 + ph - (v - lo) / (hi - lo) * ph

        out.append(f"<rect x='{left}' y='{y0}' width='{pw}' height='{ph}' fill='#f8fafc' stroke='#d9e2ec'/>")
        out.append(f"<text x='{left - 8}' y='{y0 + ph / 2 + 4}' {FONT} font-size='11' text-anchor='end'>{escape(label.split(' [')[0])}</text>")
        out.append(f"<text x='{left - 8}' y='{y0 + ph / 2 + 18}' {FONT} font-size='10' fill='#7b8794' text-anchor='end'>[{label.split('[')[1]}</text>")
        for v in (lo, hi):
            out.append(f"<text x='{left - 4 + pw}' y='{py(v) + (10 if v == hi else -3):.1f}' {FONT} font-size='9' fill='#9aa5b1' text-anchor='end'>{v:g}</text>")
        if limit is not None:
            out.append(f"<line x1='{left}' y1='{py(limit):.1f}' x2='{left + pw}' y2='{py(limit):.1f}' stroke='#c0392b' stroke-dasharray='6,4'/>")
            out.append(f"<text x='{left + pw - 4}' y='{py(limit) - 4:.1f}' {FONT} font-size='9' fill='#c0392b' text-anchor='end'>limit {limit:g}</text>")
        pts = " ".join(f"{px(t.timestamp_s):.1f},{py(getattr(t, attr)):.1f}" for t in h)
        out.append(f"<polyline points='{pts}' fill='none' stroke='#1f2933' stroke-width='2'/>")
        if attr == "motor_current_a":
            for trip in result.trips:
                if trip.unit == "A":
                    x, y = px(trip.timestamp_s), py(min(hi * 0.9, trip.measured))
                    out.append(f"<path d='M{x - 5:.1f},{y - 5:.1f} L{x + 5:.1f},{y + 5:.1f} M{x - 5:.1f},{y + 5:.1f} L{x + 5:.1f},{y - 5:.1f}' stroke='#c0392b' stroke-width='2.5'/>")
                    out.append(f"<text x='{x + 9:.1f}' y='{y + 4:.1f}' {FONT} font-size='10' fill='#c0392b'>trip {trip.measured:g} A</text>")

    # state band and digital signals
    rows = [
        ("State", None),
        ("Open sensor", "open_sensor"),
        ("Closed sensor", "closed_sensor"),
        ("Closed & locked", "closed_and_locked"),
    ]
    for r, (label, attr) in enumerate(rows):
        y = digital_top + r * 22
        out.append(f"<text x='{left - 8}' y='{y + 13}' {FONT} font-size='11' text-anchor='end'>{label}</text>")
        for a, b in zip(h, h[1:] + [h[-1]]):
            x0, x1 = px(a.timestamp_s), px(b.timestamp_s if b is not a else t_end)
            if attr is None:
                out.append(f"<rect x='{x0:.1f}' y='{y}' width='{max(0.5, x1 - x0):.1f}' height='16' fill='{STATE_COLORS[a.state]}'/>")
            elif getattr(a, attr):
                out.append(f"<rect x='{x0:.1f}' y='{y + 3}' width='{max(0.5, x1 - x0):.1f}' height='10' fill='#27ae60'/>")
        if attr is not None:
            out.append(f"<line x1='{left}' y1='{y + 13}' x2='{left + pw}' y2='{y + 13}' stroke='#d9e2ec'/>")

    # detection markers
    for d in result.detections:
        x = px(d.first_seen_s)
        out.append(f"<path d='M{x:.1f},{digital_top - 14} l-6,-10 l12,0 z' fill='#c0392b'><title>{escape(d.evidence)}</title></path>")
        out.append(f"<text x='{x + 8:.1f}' y='{digital_top - 16}' {FONT} font-size='11' font-weight='bold' fill='#c0392b'>{d.code}</text>")

    ay = digital_top + 4 * 22 + 14
    for s in range(0, int(t_end) + 1):
        out.append(f"<text x='{px(s):.1f}' y='{ay}' {FONT} font-size='10' text-anchor='middle' fill='#52606d'>{s}</text>")
    out.append(f"<text x='{left + pw / 2}' y='{ay + 18}' {FONT} font-size='11' text-anchor='middle'>time [s]</text>")
    lx = left
    for state, color in STATE_COLORS.items():
        out.append(f"<rect x='{lx}' y='{ay + 30}' width='12' height='10' fill='{color}'/>")
        out.append(f"<text x='{lx + 16}' y='{ay + 39}' {FONT} font-size='10'>{state.value}</text>")
        lx += 30 + 7 * len(state.value)
    out.append("</svg>")
    return "\n".join(out)
