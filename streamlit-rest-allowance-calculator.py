import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
import streamlit as st

from et_models import (
    CURVE_COLORS,
    DEFAULT_ET_MODEL,
    DEFAULT_ET_REGION,
    ET_MODEL_CATEGORIES,
    get_equation_info,
    mht_seconds,
)
from ra_models import (
    BYSTROM_1994,
    COMPILATION_CITATION,
    RA_COLORS,
    RA_MODEL_INFO,
    RA_MODEL_ORDER,
    MILNER_1985,
    ROHMERT_1973,
    ROSE_1992,
    compute_rest_allowance,
    model_uses_mht,
    rest_time_seconds,
)

"""
SRAT - Static Rest Allowance Tool
Companion to SETT (Static Endurance Time Tool). Uses SETT's ET models to supply
maximum holding time (MHT) to rest allowance models. All outputs in SECONDS.
Copyright Ryan C. A. Foley 2025
v1.0.0
"""

APP_VERSION = "1.0.0"

st.set_page_config(
    page_title="SRAT - Static Rest Allowance Tool",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ontario Tech University branding colors (shared with SETT)
COLORS = {
    'white': '#FFFFFF',
    'future_blue': '#003C71',
    'simcoe_blue': '#C00B2E',
    'tech_tangerine': '#E75D2A',
    'warm_grey': '#ACA39A',
    'cool_grey': '#A7A8AA',
    'dark_grey': '#5B6770',
    'spirit_navy': '#00283C'
}

st.markdown("""
<style>
    .main { padding: 1rem; }
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        border: 1px solid #003C71;
        background-color: white;
        color: #003C71;
        transition: all 0.3s;
    }
    .stButton > button:hover { background-color: #003C71; color: white; }
    .result-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 2px solid #003C71;
        text-align: center;
    }
    .result-card.na { border-color: #C00B2E; }
    .result-value { font-size: 2.5rem; font-weight: bold; color: #003C71; }
    .result-card.na .result-value { color: #C00B2E; }
    .result-label { font-size: 1rem; color: #5B6770; }
    h1 { color: #003C71; border-bottom: 3px solid #E75D2A; padding-bottom: 10px; }
    h2, h3 { color: #003C71; }
    .block-container { padding-top: 1rem; }
    .model-card {
        background-color: #f0f7ff;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #003C71;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SESSION STATE (inputs persist across pages)
# ============================================================================

DEFAULTS = {
    'current_page': 'Calculator',
    'pct_mvc': 40.0,
    'holding_s': 30.0,
    'ra_model': ROHMERT_1973,
    'et_region': DEFAULT_ET_REGION,
    'et_model': DEFAULT_ET_MODEL,
    'heatmap_model': ROHMERT_1973,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _copy_from_widget(key):
    st.session_state[key] = st.session_state[f"w_{key}"]


def _on_region_change():
    st.session_state.et_region = st.session_state.w_et_region
    st.session_state.et_model = ET_MODEL_CATEGORIES[st.session_state.et_region][0]


def _bind(key):
    """Restore a widget's value from its persistent key before rendering it."""
    st.session_state[f"w_{key}"] = st.session_state[key]
    return dict(key=f"w_{key}", on_change=_copy_from_widget, args=(key,))


# ============================================================================
# INPUT WIDGETS
# ============================================================================

def render_task_inputs():
    st.markdown("### Task Inputs")
    c1, c2 = st.columns(2)
    with c1:
        st.number_input(
            "Task Intensity (% MVC)",
            min_value=0.01, max_value=100.0, step=1.0, format="%.2f",
            help="Percentage of Maximum Voluntary Contraction",
            **_bind('pct_mvc')
        )
    with c2:
        st.number_input(
            "Holding Time / Task Duration (seconds)",
            min_value=0.1, max_value=36000.0, step=1.0, format="%.1f",
            help="Duration of the static exertion",
            **_bind('holding_s')
        )
    return st.session_state.pct_mvc, st.session_state.holding_s


def render_et_selector(enabled, disabled_reason=""):
    """Region + ET model selectors, greyed out when the RA model does not use MHT."""
    st.markdown("**Endurance Time (MHT) Model**")
    st.session_state.w_et_region = st.session_state.et_region
    st.selectbox(
        "Body Region:",
        list(ET_MODEL_CATEGORIES.keys()),
        key="w_et_region",
        on_change=_on_region_change,
        disabled=not enabled,
    )
    options = ET_MODEL_CATEGORIES[st.session_state.et_region]
    if st.session_state.et_model not in options:
        st.session_state.et_model = options[0]
    st.selectbox("ET Model:", options, disabled=not enabled, **_bind('et_model'))

    if enabled:
        info = get_equation_info().get(st.session_state.et_model)
        if info:
            with st.expander("About this ET model"):
                st.markdown(f"**Muscle Group:** {info['muscle']}")
                st.markdown(f"**Valid Range:** {info['valid_range']}")
                st.markdown(f"**Notes:** {info['notes']}")
                st.markdown(f"**Citation:** {info['citation']}")
    else:
        st.caption(disabled_reason)
    return st.session_state.et_model


def render_ra_model_info(model):
    info = RA_MODEL_INFO[model]
    with st.expander("About this rest allowance model"):
        st.latex(info['equation_latex'])
        st.markdown(f"**Inputs:** {info['inputs']}")
        st.markdown(f"**Valid domain:** {info['domain']}")
        st.markdown("**Main characteristics:**\n" + "\n".join(f"- {c}" for c in info['characteristics']))
        st.markdown(f"**Citation:** {info['citation']}")


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def fmt_s(x, nd=1):
    return f"{x:,.{nd}f} s" if np.isfinite(x) else "—"


def short_status(res):
    return {
        'ok': 'OK',
        'no_fatigue': 'No fatigue (≤15% MVC)',
        'infeasible': 'Holding time > MHT',
        'out_of_domain': 'Outside model domain',
        'et_undefined': 'ET model undefined',
        'invalid_input': 'Invalid input',
    }[res.status]


def result_card(res):
    if res.ok:
        rest = res.rest_s
        sub = f"({rest / 60:.2f} minutes) · RA = {res.ra_pct:,.1f}% of holding time"
        cls, value = "result-card", f"{rest:,.1f} sec"
    else:
        cls, value, sub = "result-card na", "N/A", short_status(res)
    mht_line = f"MHT from: {res.et_model}" if res.et_model else "MHT not used by this model"
    st.markdown(f"""
    <div class="{cls}">
        <div class="result-label">Rest Allowance Time for a {res.holding_s:g} s hold at {res.pct_mvc:g}% MVC</div>
        <div class="result-value">{value}</div>
        <div class="result-label">{sub}</div>
        <br>
        <div class="result-label">RA Model: {res.model}<br>{mht_line}</div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# PLOTS
# ============================================================================

AXIS_STYLE = dict(
    showline=True, linecolor='black', linewidth=1.5,              # edge lines stay visible when zoomed
    zeroline=True, zerolinecolor='black', zerolinewidth=1.5,      # x = 0 / y = 0 lines when in view
    ticks='outside', tickcolor='black',
)


def show_chart(fig, **kwargs):
    """Apply shared axis styling, then render. Every chart in the app goes through here."""
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    # Rest/time axes are never negative: start linear y-axes at 0 so the zero line sits on the axis
    fig.update_yaxes(rangemode='tozero', selector=dict(type='linear'))
    kwargs.setdefault('width', 'stretch')
    st.plotly_chart(fig, **kwargs)


def _layout(fig, title, xtitle, ytitle, y_scale, x_range=None, y_range=None, height=550):
    yaxis = dict(title=ytitle, type='log' if y_scale == 'log' else 'linear',
                 gridcolor='lightgray', showgrid=True)
    if y_range is not None and y_scale != 'log':
        yaxis['range'] = y_range
    xaxis = dict(title=xtitle, gridcolor='lightgray', showgrid=True)
    if x_range is not None:
        xaxis['range'] = x_range
    fig.update_layout(
        title=dict(text=title, font=dict(size=20, color=COLORS['future_blue']), x=0.5),
        xaxis=xaxis, yaxis=yaxis,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.85)"),
        hovermode='closest', plot_bgcolor='white', height=height,
    )
    return fig


def _line_style(model, selected):
    if model == selected:
        return dict(color=RA_COLORS[model], width=4)
    return dict(color=RA_COLORS[model], width=2, dash='dot')


STAR_GOLD = '#FFC72C'  # current-task marker: gold fill, black outline (neutral against every RA model colour)


def _star(fig, x, y, text):
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode='markers', name='Current Task',
        marker=dict(color=STAR_GOLD, size=20, symbol='star',
                    line=dict(color='black', width=2)),
        hovertemplate=text + "<extra></extra>"
    ))


def plot_rest_vs_holding(res, models, et_model, y_scale):
    pct, hold = res.pct_mvc, res.holding_s
    mht = mht_seconds(pct / 100, et_model) if et_model else np.nan
    x_max = hold * 2
    if np.isfinite(mht):
        x_max = max(x_max, min(mht * 1.1, hold * 10))
    xs = np.linspace(x_max / 400, x_max, 400)
    if np.isfinite(mht) and mht <= x_max:
        xs = np.unique(np.append(xs, mht))

    fig = go.Figure()
    shown = []
    for m in models:
        ys = np.array([rest_time_seconds(m, pct, x, et_model) for x in xs])
        if np.any(np.isfinite(ys)):
            shown.extend(ys[np.isfinite(ys)].tolist())
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode='lines', name=m, line=_line_style(m, res.model),
                hovertemplate=f"<b>{m}</b><br>Holding: %{{x:.1f}} s<br>Rest: %{{y:.1f}} s<extra></extra>"
            ))
    if np.isfinite(mht) and mht <= x_max and any(model_uses_mht(m) for m in models):
        fig.add_vline(x=mht, line_dash="dash", line_color=COLORS['simcoe_blue'], opacity=0.7,
                      annotation_text=f"MHT = {mht:.1f} s", annotation_position="top left")
    if res.ok:
        _star(fig, hold, res.rest_s, f"<b>Current Task</b><br>Holding: {hold:g} s<br>Rest: {res.rest_s:.1f} s")
        shown.append(res.rest_s)
    y_max = max(shown) * 1.1 if shown and max(shown) > 0 else None
    return _layout(fig, f"Rest Time vs Holding Time at {pct:g}% MVC",
                   "Holding Time (seconds)", "Rest Time (seconds)", y_scale,
                   x_range=[0, x_max], y_range=[0, y_max] if y_max else None)


def plot_rest_vs_intensity(res, models, et_model, y_scale):
    pct, hold = res.pct_mvc, res.holding_s
    xs = np.unique(np.append(np.arange(0.5, 100.01, 0.5), pct))
    fig = go.Figure()
    shown = []
    for m in models:
        ys = np.array([rest_time_seconds(m, x, hold, et_model) for x in xs])
        if np.any(np.isfinite(ys)):
            shown.extend(ys[np.isfinite(ys)].tolist())
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode='lines', name=m, line=_line_style(m, res.model),
                hovertemplate=f"<b>{m}</b><br>Intensity: %{{x:.1f}}% MVC<br>Rest: %{{y:.1f}} s<extra></extra>"
            ))
    fig.add_vline(x=15, line_dash="dot", line_color=COLORS['dark_grey'], opacity=0.6,
                  annotation_text="15% MVC", annotation_position="bottom right")
    if res.ok:
        _star(fig, pct, res.rest_s, f"<b>Current Task</b><br>Intensity: {pct:g}% MVC<br>Rest: {res.rest_s:.1f} s")
    y_max = max(shown) * 1.05 if shown and max(shown) > 0 else None
    return _layout(fig, f"Rest Time vs Intensity for a {hold:g} s Hold",
                   "Intensity (% MVC)", "Rest Time (seconds)", y_scale,
                   x_range=[0, 100], y_range=[0, y_max] if y_max else None)


def plot_work_rest_cycles(results, selected):
    labels, holds, rests, notes = [], [], [], []
    for r in results:
        label = f"<b>{r.model}</b>" if r.model == selected else r.model
        labels.append(label)
        holds.append(r.holding_s if r.ok else 0)
        rests.append(r.rest_s if r.ok else 0)
        notes.append("" if r.ok else f"N/A: {short_status(r)}")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=holds, orientation='h', name='Hold (work)',
        marker_color=COLORS['future_blue'],
        text=[f"{h:.1f} s" if h else "" for h in holds], textposition='inside',
        hovertemplate="Hold: %{x:.1f} s<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        y=labels, x=rests, orientation='h', name='Rest',
        marker_color=COLORS['tech_tangerine'],
        text=[f"{r:.1f} s" if r else "" for r in rests], textposition='inside',
        hovertemplate="Rest: %{x:.1f} s<extra></extra>"
    ))
    for lab, note in zip(labels, notes):
        if note:
            fig.add_annotation(y=lab, x=0, text=note, showarrow=False, xanchor='left',
                               font=dict(color=COLORS['simcoe_blue']))
    fig.update_layout(
        barmode='stack',
        title=dict(text="One Work–Rest Cycle per Model", font=dict(size=20, color=COLORS['future_blue']), x=0.5),
        xaxis=dict(title="Time (seconds)", gridcolor='lightgray'),
        yaxis=dict(autorange='reversed', automargin=True),
        margin=dict(l=230),
        plot_bgcolor='white', height=120 + 80 * len(results),
        legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='right', x=1),
    )
    return fig


def plot_et_curve(res, et_model, y_scale):
    pct, hold = res.pct_mvc, res.holding_s
    xs = np.linspace(1, 100, 500)
    ys = np.array([mht_seconds(x / 100, et_model) for x in xs])
    mht = mht_seconds(pct / 100, et_model)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode='lines', name=et_model,
        line=dict(color=CURVE_COLORS.get(et_model, COLORS['future_blue']), width=4),
        hovertemplate=f"<b>{et_model}</b><br>Intensity: %{{x:.1f}}% MVC<br>MHT: %{{y:.1f}} s<extra></extra>"
    ))
    fig.add_hline(y=hold, line_dash="dash", line_color=COLORS['tech_tangerine'], opacity=0.8,
                  annotation_text=f"Holding time = {hold:g} s")
    if np.isfinite(mht):
        _star(fig, pct, mht, f"<b>MHT at {pct:g}% MVC</b><br>{mht:.1f} s ({mht / 60:.2f} min)")
        fig.add_vline(x=pct, line_dash="dash", line_color=COLORS['tech_tangerine'], opacity=0.5)
    ref = max(hold, mht if np.isfinite(mht) else 0)
    _layout(fig, "Endurance Time Curve Supplying MHT", "Intensity (% MVC)",
            "Maximum Holding Time (seconds)", y_scale, x_range=[0, 100], y_range=[0, ref * 3])
    fig.update_layout(legend=dict(xanchor="right", x=0.99))
    return fig


OVERVIEW_AUTO_CAP_S = 12_000  # 200 min: upper limit for the automatic x-axis range
OVERVIEW_AUTO_MIN_PCT = 20    # auto x-range spans the MHT of the lowest line at/above this intensity
OVERVIEW_PCT_RANGE = (5, 100)  # intensity range mapped onto the colour gradient
BOUNDARY_COLOR = '#9AA0A6'
LOG_DECADES = 4               # log y-axis shows this many decades below the largest value


def overview_intensities(show_5):
    step = 5 if show_5 else 10
    return list(range(step, 101, step))


def overview_auto_xmax(ra_model, et_model, show_5, holding_s):
    """
    Longest finite MHT among the plotted intensities >= 20% MVC (capped), or a holding-based range
    if MHT is not used. Lines below 20% have very long MHTs (and are RA = 0 for Rohmert below 15%),
    so including them would compress the rest of the family; they are drawn but clipped at this range.
    """
    if not model_uses_mht(ra_model):
        return max(600.0, holding_s * 2)
    mhts = [mht_seconds(p / 100, et_model) for p in overview_intensities(show_5) if p >= OVERVIEW_AUTO_MIN_PCT]
    mhts = [m for m in mhts if np.isfinite(m) and m > 0]
    longest = max(mhts) if mhts else 600.0
    return float(min(max(longest, holding_s * 1.2), OVERVIEW_AUTO_CAP_S))


# --- colour gradient by intensity -------------------------------------------

OVERVIEW_TINT = 0.72  # how far the lowest intensity is blended toward white


def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(rgb, target, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(rgb, target))


def intensity_colorscale(ra_model):
    """
    Light-to-dark scale for intensity, anchored on the RA model's own line colour (RA_COLORS),
    so the overview matches the scenario plots: 100% MVC = the model colour, low intensity = a light tint.
    """
    base = _hex_to_rgb(RA_COLORS[ra_model])
    light = _mix(base, (255, 255, 255), OVERVIEW_TINT)
    return [[0.0, f"rgb{light}"], [1.0, f"rgb{base}"]]


def intensity_color(pct, scale):
    lo, hi = OVERVIEW_PCT_RANGE
    t = min(max((pct - lo) / (hi - lo), 0.0), 1.0)
    return sample_colorscale(scale, [t])[0]


# --- curve data ---------------------------------------------------------------

@st.cache_data(show_spinner=False)
def overview_curves(ra_model, et_model, hold_max, show_5, normalised, n_pts=300):
    """
    One curve per intensity. Each curve is a dict with p, hold, rest, fmht, ra (arrays).
    Seconds mode: holding time from 0 to MHT (or hold_max, whichever is shorter).
    Normalised mode: fMHT from 0 to 1 (MHT-based models only).
    """
    curves = []
    uses_mht = model_uses_mht(ra_model)
    for p in overview_intensities(show_5):
        mht = mht_seconds(p / 100, et_model) if uses_mht else np.nan
        mht_ok = np.isfinite(mht) and mht > 0
        if normalised:
            fm = np.linspace(0, 1, n_pts + 1)[1:]
            if mht_ok:
                holds = fm * mht
            elif ra_model == ROHMERT_1973 and p <= 15:   # RA = 0 regardless of MHT
                curves.append(dict(p=p, hold=np.full_like(fm, np.nan), rest=np.zeros_like(fm),
                                   fmht=fm, ra=np.zeros_like(fm)))
                continue
            else:
                continue
        else:
            end = min(mht, hold_max) if mht_ok else hold_max
            holds = np.linspace(0, end, n_pts + 1)[1:]
        rs = [compute_rest_allowance(ra_model, p, h, et_model) for h in holds]
        c = dict(p=p, hold=holds,
                 rest=np.array([r.rest_s for r in rs]),
                 fmht=holds / mht if mht_ok else np.full_like(holds, np.nan),
                 ra=np.array([r.ra_pct for r in rs]))
        if np.any(np.isfinite(c['rest'])) or np.any(np.isfinite(c['ra'])):
            curves.append(c)
    return curves


@st.cache_data(show_spinner=False)
def exhaustion_boundary(ra_model, et_model, hold_max):
    """Rest time for a hold that lasts exactly MHT (fMHT = 1), across intensities, within the x-range."""
    pcts, holds, rests = [], [], []
    for p in np.arange(1.0, 100.01, 0.5):
        mht = mht_seconds(p / 100, et_model)
        if not (np.isfinite(mht) and 0 < mht <= hold_max):
            continue
        r = compute_rest_allowance(ra_model, p, mht, et_model).rest_s
        if np.isfinite(r):
            pcts.append(p); holds.append(mht); rests.append(r)
    return np.array(pcts), np.array(holds), np.array(rests)


def _group_end_labels(ends):
    """Merge labels of lines that end at the same point (e.g., Milner normalised: all intensities coincide)."""
    groups = []
    for p, x, y in ends:
        for g in groups:
            if np.isclose(g['x'], x, rtol=1e-6) and np.isclose(g['y'], y, rtol=1e-6):
                g['ps'].append(p)
                break
        else:
            groups.append(dict(x=x, y=y, ps=[p]))
    for g in groups:
        g['text'] = f"{g['ps'][0]}%" if len(g['ps']) == 1 else f"{min(g['ps'])}–{max(g['ps'])}%"
    return groups


def plot_model_overview(res, ra_model, et_model, hold_max, show_5, show_star, log_y, normalised):
    uses_mht = model_uses_mht(ra_model)
    normalised = normalised and uses_mht
    et_for_model = et_model if uses_mht else None
    curves = overview_curves(ra_model, et_for_model, hold_max, show_5, normalised)
    scale = intensity_colorscale(ra_model)
    xkey, ykey = ('fmht', 'ra') if normalised else ('hold', 'rest')

    fig = go.Figure()
    all_y = []

    # Exhaustion boundary first so it sits behind the intensity lines
    if uses_mht and not normalised:
        bp, bx, by = exhaustion_boundary(ra_model, et_model, hold_max)
        if len(bx):
            fig.add_trace(go.Scatter(
                x=bx, y=by, mode='lines', name='Exhaustion boundary (hold = MHT)',
                line=dict(color=BOUNDARY_COLOR, width=1.2), customdata=bp,
                hovertemplate="<b>Exhaustion boundary</b><br>%{customdata:.1f}% MVC<br>"
                              "Hold = MHT = %{x:,.1f} s<br>Rest: %{y:,.1f} s<extra></extra>"
            ))
            all_y.extend(by.tolist())

    ends, zero_lines = [], []
    for c in curves:
        p, xs, ys = c['p'], c[xkey], c[ykey]
        solid = p % 10 == 0
        col = intensity_color(p, scale)
        if normalised:
            hover = (f"<b>{p}% MVC</b><br>fMHT: %{{x:.3f}}<br>RA: %{{y:,.1f}}%<br>"
                     f"Holding: %{{customdata[0]:,.1f}} s<br>Rest: %{{customdata[1]:,.1f}} s<extra></extra>")
            cd = np.column_stack([c['hold'], c['rest']])
        else:
            hover = f"<b>{p}% MVC</b><br>Holding: %{{x:,.1f}} s<br>Rest: %{{y:,.1f}} s<extra></extra>"
            cd = None
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines', name=f"{p}% MVC", showlegend=False, customdata=cd,
            line=dict(color=col, width=2.5 if solid else 1.6, dash=None if solid else 'dash'),
            hovertemplate=hover
        ))
        finite = np.isfinite(ys)
        all_y.extend(ys[finite].tolist())
        if np.all(ys[finite] == 0):
            zero_lines.append(p)
        elif solid:
            i = np.where(finite)[0][-1]
            ends.append((p, xs[i], ys[i]))

    # y-axis range (log needs an explicit floor: Rohmert/Milner approach 0 as holding time -> 0)
    pos = [v for v in all_y if v > 0]
    star_ok = show_star and res.ok and (not normalised or np.isfinite(res.fmht))
    if star_ok:
        sy = res.ra_pct if normalised else res.rest_s
        if sy > 0:
            pos.append(sy)
    y_top = max(pos) if pos else 1.0
    y_floor = y_top / 10 ** LOG_DECADES

    def y_pos(v):  # annotation y in axis units
        return np.log10(max(v, y_floor)) if log_y else v

    # End labels: skip any that would overlap one already placed (the colour bar is the full key)
    x_span = 1.0 if normalised else max(hold_max, res.holding_s if star_ok else 0)
    y_lo, y_hi = (np.log10(y_floor), np.log10(y_top)) if log_y else (0.0, y_top)
    placed = []
    for g in sorted(_group_end_labels(ends), key=lambda g: min(g['ps'])):
        gx, gy = g['x'] / x_span, (y_pos(g['y']) - y_lo) / max(y_hi - y_lo, 1e-12)
        if any(abs(gx - px) < 0.06 and abs(gy - py) < 0.035 for px, py in placed):
            continue
        placed.append((gx, gy))
        fig.add_annotation(x=g['x'], y=y_pos(g['y']), text=g['text'], showarrow=False, xanchor='left',
                           xshift=4, font=dict(size=11, color=intensity_color(max(g['ps']), scale)))
    if zero_lines and not log_y:
        x_lab = 1.0 if normalised else hold_max
        fig.add_annotation(x=x_lab, y=0, text=f"≤{max(zero_lines)}%: RA = 0", showarrow=False,
                           xanchor='right', yanchor='bottom', font=dict(size=11, color=COLORS['dark_grey']))

    # Colour bar keyed to intensity
    lo, hi = OVERVIEW_PCT_RANGE
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers', showlegend=False, hoverinfo='skip',
        marker=dict(colorscale=scale, cmin=lo, cmax=hi, color=[lo], showscale=True,
                    colorbar=dict(title=dict(text="% MVC"), thickness=12, len=0.7,
                                  tickvals=[10, 20, 40, 60, 80, 100]))
    ))

    if normalised:
        x_max = 1.0
        if star_ok:
            _star(fig, res.fmht, res.ra_pct,
                  f"<b>Current Task</b><br>{res.pct_mvc:g}% MVC, fMHT = {res.fmht:.3f}<br>"
                  f"RA: {res.ra_pct:.1f}% · Rest: {res.rest_s:.1f} s")
        title = f"Overview of {ra_model}, normalised to MHT"
        xt, yt = "fMHT (holding time ÷ MHT)", "Rest Allowance (% of holding time)"
    else:
        x_max = hold_max
        if star_ok:
            _star(fig, res.holding_s, res.rest_s,
                  f"<b>Current Task</b><br>{res.pct_mvc:g}% MVC, {res.holding_s:g} s hold<br>Rest: {res.rest_s:.1f} s")
            x_max = max(x_max, res.holding_s)
        title = f"Overview of {ra_model}" + (f" (MHT: {et_model})" if et_for_model else "")
        xt, yt = "Holding Time (seconds)", "Rest Time (seconds)"

    _layout(fig, title, xt, yt, 'log' if log_y else 'linear', x_range=[0, x_max * 1.07], height=600)
    if log_y:
        fig.update_yaxes(range=[np.log10(y_floor), np.log10(y_top * 1.5)], dtick=1)
    fig.update_layout(title=dict(font=dict(size=18)),
                      legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='left', x=0,
                                  bgcolor='rgba(255,255,255,0)'))
    return fig


@st.cache_data(show_spinner=False)
def heatmap_grid(model, et_model, hold_max, n_hold=60):
    intensities = np.arange(1, 101, 1.0)
    holds = np.linspace(hold_max / n_hold, hold_max, n_hold)
    z = np.full((len(holds), len(intensities)), np.nan)
    for i, h in enumerate(holds):
        for j, p in enumerate(intensities):
            z[i, j] = rest_time_seconds(model, p, h, et_model)
    return intensities, holds, z


def plot_heatmap(model, et_model, hold_max, current):
    xs, ys, z = heatmap_grid(model, et_model, hold_max)
    zc = np.log10(z + 1)  # +1 s so RA = 0 (no fatigue) stays on the scale
    ticks = [v for v in [0, 1, 10, 100, 1_000, 10_000, 100_000] if v <= np.nanmax(z, initial=0) * 1.01 or v == 0]
    fig = go.Figure(go.Heatmap(
        x=xs, y=ys, z=zc, customdata=z, colorscale='Viridis',
        colorbar=dict(title="Rest (s)", tickvals=np.log10(np.array(ticks) + 1), ticktext=[f"{t:,}" for t in ticks]),
        hovertemplate="Intensity: %{x:.0f}% MVC<br>Holding: %{y:.1f} s<br>Rest: %{customdata:.1f} s<extra></extra>",
        hoverongaps=False,
    ))
    if current.ok and current.holding_s <= hold_max:
        _star(fig, current.pct_mvc, current.holding_s,
              f"<b>Current Task</b><br>{current.pct_mvc:g}% MVC, {current.holding_s:g} s hold<br>Rest: {current.rest_s:.1f} s")
    fig.update_layout(
        title=dict(text=f"Rest Time Map: {model}", font=dict(size=20, color=COLORS['future_blue']), x=0.5),
        xaxis=dict(title="Intensity (% MVC)"), yaxis=dict(title="Holding Time (seconds)"),
        plot_bgcolor='white', height=550, showlegend=False,
    )
    return fig


# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://github.com/rcafoley.png", width=80)
    with col2:
        st.markdown("**Ryan C. A. Foley**")
        st.markdown("PhD Candidate, CSEP-CEP")
    st.markdown("[Website](https://rcafoley.github.io) | [GitHub](https://github.com/rcafoley)")
    st.markdown("[ryan.foley@ontariotechu.ca](mailto:ryan.foley@ontariotechu.ca)")
    st.markdown("---")

    st.markdown("### Navigation")
    for page, label in [("Calculator", "Calculator"), ("Compare", "Compare RA Models"), ("About", "About")]:
        if st.button(label, width="stretch",
                     type="primary" if st.session_state.current_page == page else "secondary"):
            st.session_state.current_page = page
            st.rerun()
    st.markdown("---")

    st.markdown("### Display Options")
    y_scale = st.radio("Y-Axis Scale", ["Linear", "Logarithmic"], index=0)
    y_scale_val = 'linear' if y_scale == "Linear" else 'log'
    st.markdown("---")

    st.markdown("### Quick Reference")
    st.info("""
    **RA (%)** = rest time ÷ holding time × 100

    **Rest time (s)** = RA ÷ 100 × holding time

    **fMHT** = holding time ÷ MHT

    MHT-based models are only valid for holding time ≤ MHT (fMHT ≤ 1).
    """)


# ============================================================================
# CALCULATOR PAGE
# ============================================================================
if st.session_state.current_page == "Calculator":
    st.title("SRAT - Static Rest Allowance Tool")
    st.markdown("*Estimate the rest needed after a static exertion, using endurance time (MHT) from SETT's ET models*")
    st.markdown("---")

    pct_mvc, holding_s = render_task_inputs()

    st.markdown("---")
    st.markdown("### Model Selection")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Rest Allowance Model**")
        st.selectbox("RA Model:", RA_MODEL_ORDER, **_bind('ra_model'))
        ra_model = st.session_state.ra_model
        st.markdown(f"""
        <div class="model-card">
            <b>{ra_model}</b><br>
            <code>{RA_MODEL_INFO[ra_model]['equation_text']}</code><br>
            <small>Inputs: {RA_MODEL_INFO[ra_model]['inputs']}</small>
        </div>
        """, unsafe_allow_html=True)
        render_ra_model_info(ra_model)
    with c2:
        uses_mht = model_uses_mht(ra_model)
        et_model = render_et_selector(
            uses_mht,
            disabled_reason=f"Not required: {ra_model} uses %MVC only and does not consider MHT."
        )

    res = compute_rest_allowance(ra_model, pct_mvc, holding_s, et_model if uses_mht else None)
    all_results = [compute_rest_allowance(m, pct_mvc, holding_s, et_model) for m in RA_MODEL_ORDER]

    st.markdown("---")
    st.markdown("### Result")
    rc1, rc2 = st.columns([1, 1])
    with rc1:
        result_card(res)
    with rc2:
        m1, m2 = st.columns(2)
        m1.metric("Maximum Holding Time", fmt_s(res.mht_s) if uses_mht else "Not used")
        m2.metric("fMHT (hold ÷ MHT)", f"{res.fmht:.3f}" if np.isfinite(res.fmht) else ("Not used" if not uses_mht else "—"))
        m3, m4 = st.columns(2)
        m3.metric("Work–Rest Cycle", fmt_s(res.cycle_s))
        m4.metric("Duty Cycle", f"{res.duty_cycle * 100:.1f}%" if np.isfinite(res.duty_cycle) else "—")
        if res.status in ('infeasible', 'out_of_domain', 'et_undefined', 'invalid_input'):
            st.error(res.message)
        elif res.status == 'no_fatigue':
            st.info(res.message)

    st.markdown("---")
    st.markdown("### Interactive Plots")
    overlay = st.checkbox("Overlay the other rest allowance models (using the same ET model for MHT)", value=True)
    plot_models = RA_MODEL_ORDER if overlay else [ra_model]
    plot_et = et_model if (uses_mht or overlay) else None

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Rest vs Holding Time", "Rest vs Intensity", "Work–Rest Cycle",
                                            "Endurance Time (MHT)", "Model Overview"])
    with tab1:
        show_chart(plot_rest_vs_holding(res, plot_models, plot_et, y_scale_val), width="stretch")
        st.caption("MHT-based curves end where holding time reaches MHT (fMHT = 1); beyond that the task cannot be sustained.")
    with tab2:
        show_chart(plot_rest_vs_intensity(res, plot_models, plot_et, y_scale_val), width="stretch")
        st.caption("MHT-based curves end at the intensity where MHT falls below the holding time.")
    with tab3:
        cyc = all_results if overlay else [res]
        show_chart(plot_work_rest_cycles(cyc, ra_model), width="stretch")
    with tab4:
        if uses_mht or overlay:
            show_chart(plot_et_curve(res, et_model, y_scale_val), width="stretch")
            st.caption("The task is feasible for MHT-based models when the curve sits above the holding-time line at the task intensity.")
        else:
            st.info(f"{ra_model} does not use MHT. Enable the overlay above to view the ET curve used by the other models.")
    with tab5:
        o1, o2, o3 = st.columns([1, 1, 1.4])
        with o1:
            show_star = st.checkbox("Show current task (★)", value=True, key="ov_star")
            show_5 = st.checkbox("Show 5% lines (dashed)", value=True, key="ov_5")
        with o2:
            log_y = st.checkbox("Log scale (y-axis)", value=(y_scale_val == 'log'), key="ov_log")
            normalised = st.checkbox(
                "Normalise to MHT (fMHT)", value=False, key="ov_norm", disabled=not uses_mht,
                help="x = holding time ÷ MHT (0–1), y = rest allowance as % of holding time. "
                     "Shows the RA model's own structure: every line ends at fMHT = 1."
                     if uses_mht else f"Not available: {ra_model} does not use MHT."
            )
            normalised = normalised and uses_mht
        with o3:
            x_user = st.number_input("Max holding time shown (s)", min_value=1.0, value=None,
                                     step=60.0, format="%.0f", placeholder="Auto", key="ov_xmax",
                                     disabled=normalised,
                                     help="Leave blank for automatic: MHT at 20% MVC for the selected ET "
                                          f"model (up to {OVERVIEW_AUTO_CAP_S:,} s). Enter a larger value "
                                          "to see more of the low-intensity lines.")
        hold_max = float(x_user) if x_user else overview_auto_xmax(ra_model, et_model, show_5, holding_s)
        show_chart(plot_model_overview(res, ra_model, et_model, hold_max, show_5, show_star, log_y, normalised),
                        width="stretch")
        if normalised:
            note = {
                ROHMERT_1973: "Rohmert (1973) RA % depends only on fMHT and %MVC, so this view is the same "
                              "for every ET model.",
                MILNER_1985: "Milner (1985) RA % depends only on fMHT, so all intensities collapse onto one "
                             "curve, and it is the same for every ET model.",
                ROSE_1992: "Rose et al. (1992) RA % depends only on MHT, so each intensity is a flat line "
                           "whose level is set by the ET model.",
            }.get(ra_model, "")
            st.caption("Each line is one contraction intensity (solid every 10% MVC, dashed at the 5% steps), "
                       "coloured light to dark by intensity. " + note + " Drag to zoom, double-click to reset.")
        else:
            st.caption("Each line is one contraction intensity (solid every 10% MVC, dashed at the 5% steps), "
                       "coloured light to dark by intensity. "
                       + ("Lines end at MHT for that intensity; the grey line joins those endpoints (exhaustion "
                          "boundary). Lines whose MHT is beyond the x-axis range are cut off at its edge. "
                          if uses_mht else "")
                       + ("On the log scale, lines at RA = 0 (≤15% MVC) are not shown. " if log_y else "")
                       + "Drag to zoom, double-click to reset.")
        if show_star and not res.ok:
            st.warning(f"The current task can't be starred: {short_status(res).lower()}.")
        elif show_star and normalised and not np.isfinite(res.fmht):
            st.warning("The current task can't be starred in the normalised view: MHT is undefined at this intensity.")


# ============================================================================
# COMPARE PAGE
# ============================================================================
elif st.session_state.current_page == "Compare":
    st.title("Rest Allowance Model Comparison")
    st.markdown("*Compare all four rest allowance models for the same task*")
    st.markdown("---")

    pct_mvc, holding_s = render_task_inputs()
    st.markdown("---")
    c1, _ = st.columns(2)
    with c1:
        et_model = render_et_selector(True)
        st.caption("Supplies MHT to Rohmert (1973), Milner (1985) and Rose et al. (1992).")

    results = [compute_rest_allowance(m, pct_mvc, holding_s, et_model) for m in RA_MODEL_ORDER]

    st.markdown("---")
    st.markdown("### Comparison Table")
    df = pd.DataFrame([{
        'RA Model': r.model,
        'Uses MHT': 'Yes' if model_uses_mht(r.model) else 'No',
        'MHT (s)': round(r.mht_s, 1) if np.isfinite(r.mht_s) else None,
        'fMHT': round(r.fmht, 3) if np.isfinite(r.fmht) else None,
        'RA (%)': round(r.ra_pct, 1) if np.isfinite(r.ra_pct) else None,
        'Rest Time (s)': round(r.rest_s, 1) if np.isfinite(r.rest_s) else None,
        'Cycle (s)': round(r.cycle_s, 1) if np.isfinite(r.cycle_s) else None,
        'Duty Cycle (%)': round(r.duty_cycle * 100, 1) if np.isfinite(r.duty_cycle) else None,
        'Status': short_status(r),
    } for r in results])
    st.dataframe(df, width="stretch", hide_index=True)
    for r in results:
        if r.status not in ('ok',) and r.message:
            st.caption(f"**{r.model}:** {r.message}")

    st.markdown("---")
    st.markdown("### Rest Time by Model")
    fig = go.Figure(go.Bar(
        x=[r.model for r in results],
        y=[r.rest_s if r.ok else 0 for r in results],
        marker_color=[RA_COLORS[r.model] for r in results],
        text=[f"{r.rest_s:.1f} s" if r.ok else "N/A" for r in results], textposition='outside',
        hovertemplate="%{x}<br>Rest: %{y:.1f} s<extra></extra>",
    ))
    _layout(fig, f"Rest Time for a {holding_s:g} s Hold at {pct_mvc:g}% MVC", "", "Rest Time (seconds)",
            y_scale_val, height=450)
    fig.update_layout(showlegend=False)
    show_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("### Rest Time Map (Intensity × Holding Time)")
    h1, h2 = st.columns(2)
    with h1:
        st.selectbox("RA Model:", RA_MODEL_ORDER, **_bind('heatmap_model'))
    with h2:
        hold_max = st.slider("Max Holding Time (s)", 10, 600, int(max(60, min(600, holding_s * 2))), step=10)
    hm_model = st.session_state.heatmap_model
    current = compute_rest_allowance(hm_model, pct_mvc, holding_s, et_model)
    show_chart(plot_heatmap(hm_model, et_model if model_uses_mht(hm_model) else None, hold_max, current),
                    width="stretch")
    st.caption("Blank cells are outside the model's valid domain (holding time > MHT, ET undefined, or "
               "Milner fMHT ≤ 0.01). Colour scale is logarithmic in rest seconds.")


# ============================================================================
# ABOUT PAGE
# ============================================================================
elif st.session_state.current_page == "About":
    st.title("About SRAT")
    st.markdown("---")
    st.markdown(f"""
    ## SRAT - Static Rest Allowance Tool

    **Version:** {APP_VERSION}
    **Author:** Ryan C. A. Foley, PhD Candidate, CSEP Clinical Exercise Physiologist
    **Laboratory:** Occupational Neuromechanics and Ergonomics (ONE) Laboratory – Dr. Nicholas La Delfa
    **Institution:** Ontario Tech University, Oshawa, Ontario, Canada

    ### Contact
    - **Academic Email:** ryan.foley@ontariotechu.ca
    - **Research Email:** ryan@afferentresearch.com
    - **GitHub:** [github.com/rcafoley](https://github.com/rcafoley)

    ---

    ### Purpose

    SRAT is a companion to SETT (Static Endurance Time Tool). It makes the most widely compared rest
    allowance (RA) models for static muscular work quickly accessible, and lets any of SETT's 31 endurance
    time models supply the maximum holding time (MHT) those RA models require.

    ### How it works

    Rest allowance models return RA as a percentage of holding time:

    *RA (%) = rest time ÷ holding time × 100*

    SRAT converts this to an absolute rest time:

    *Rest time (s) = RA ÷ 100 × holding time (s)*

    For models that need MHT, SRAT evaluates the selected ET model at the task intensity (ET models return
    minutes and are converted to seconds; Rose et al. 1992 takes MHT in minutes as published). All
    displayed times are in **seconds**.

    ---

    ### Domain handling

    - **Holding time > MHT (fMHT > 1):** reported as *N/A – holding time exceeds MHT*. The task cannot be
      sustained, and the MHT-based models are outside their valid domain, so no rest value is returned.
    - **≤15% MVC:** Rohmert (1973) and Byström & Fransson-Hall (1994) assume no fatigue, so RA = 0.
    - **Milner (1985):** the log term requires 100 − 1/fMHT > 0, so the model is undefined for fMHT ≤ 0.01.
    - **ET model undefined at the task intensity** (e.g., Rohmert 1960 below 15% MVC): MHT-based RA models
      return N/A.

    ---

    ### Rest Allowance Models

    Equations as compiled in El ahrache & Imbeau (2009), Table 1.
    """)

    for m in RA_MODEL_ORDER:
        info = RA_MODEL_INFO[m]
        st.markdown(f"#### {m}")
        st.latex(info['equation_latex'])
        st.markdown(
            f"- **Inputs:** {info['inputs']}\n"
            f"- **Valid domain:** {info['domain']}\n" +
            "\n".join(f"- {c}" for c in info['characteristics'])
        )

    st.markdown(f"""
    ---

    ### Limitations

    - RA models are built on **population averages**; individual recovery varies substantially
    - Models were developed for **static (isometric) exertions**; dynamic and highly intermittent work may differ
    - RA models were derived with specific MHT assumptions; pairing them with a different ET model is a
      deliberate modelling choice and will shift the result
    - The Milner (1985) form is very sensitive near fMHT = 1 to the rounded constant 4.61 (vs. ln 100 = 4.605)
    - Rose et al. (1992) does not consider holding time in RA %; rest time scales only through the
      RA × holding time conversion

    ---

    ### Key References

    **Model Compilation:**

    {COMPILATION_CITATION}

    **Rest Allowance Models:**

    {RA_MODEL_INFO[ROHMERT_1973]['citation']}

    {RA_MODEL_INFO['Milner 1985']['citation']}

    {RA_MODEL_INFO['Rose et al. 1992']['citation']}

    {RA_MODEL_INFO[BYSTROM_1994]['citation']}

    **Endurance Time:**

    Frey-Law, L.A. & Avin, K.G. (2010). Endurance time is joint-specific: A modelling and meta-analysis
    investigation. *Ergonomics*, 53(1), 109-129.

    El ahrache, K., Imbeau, D., & Farbos, B. (2006). Percentile values for determining maximum endurance
    times for static muscular work. *International Journal of Industrial Ergonomics*, 36, 99-108.

    ---
    *© 2025 Ryan Foley. All rights reserved.*
    """)


# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: {COLORS['dark_grey']};'>"
    f"SRAT v{APP_VERSION} | © 2025 Ryan Foley"
    f"</div>",
    unsafe_allow_html=True
)
