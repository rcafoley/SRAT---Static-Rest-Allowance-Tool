import numpy as np
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
    # Compare page: two independent RA + ET pairings
    'cmp1_ra_model': ROHMERT_1973,
    'cmp1_et_region': DEFAULT_ET_REGION,
    'cmp1_et_model': DEFAULT_ET_MODEL,
    'cmp2_ra_model': MILNER_1985,
    'cmp2_et_region': DEFAULT_ET_REGION,
    'cmp2_et_model': DEFAULT_ET_MODEL,
    # Compare page: optional piecewise (compound) function per slot
    'cmp1_pw': False, 'cmp1_pw_t': 35.0,
    'cmp1b_ra_model': ROSE_1992, 'cmp1b_et_region': DEFAULT_ET_REGION, 'cmp1b_et_model': DEFAULT_ET_MODEL,
    'cmp2_pw': False, 'cmp2_pw_t': 35.0,
    'cmp2b_ra_model': ROSE_1992, 'cmp2b_et_region': DEFAULT_ET_REGION, 'cmp2b_et_model': DEFAULT_ET_MODEL,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _copy_from_widget(key):
    st.session_state[key] = st.session_state[f"w_{key}"]


def _on_region_change(prefix=""):
    rk, mk = f"{prefix}et_region", f"{prefix}et_model"
    st.session_state[rk] = st.session_state[f"w_{rk}"]
    st.session_state[mk] = ET_MODEL_CATEGORIES[st.session_state[rk]][0]


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


def render_et_selector(enabled, disabled_reason="", prefix=""):
    """
    Region + ET model selectors, greyed out when the RA model does not use MHT.
    `prefix` keeps independent state per selector set (calculator: "", compare slots: "cmp1_", "cmp2_").
    """
    rk, mk = f"{prefix}et_region", f"{prefix}et_model"
    st.markdown("**Endurance Time (MHT) Model**")
    st.session_state[f"w_{rk}"] = st.session_state[rk]
    st.selectbox(
        "Body Region:",
        list(ET_MODEL_CATEGORIES.keys()),
        key=f"w_{rk}",
        on_change=_on_region_change,
        args=(prefix,),
        disabled=not enabled,
    )
    options = ET_MODEL_CATEGORIES[st.session_state[rk]]
    if st.session_state[mk] not in options:
        st.session_state[mk] = options[0]
    st.selectbox("ET Model:", options, disabled=not enabled, **_bind(mk))

    if enabled:
        info = get_equation_info().get(st.session_state[mk])
        if info:
            with st.expander("About this ET model"):
                st.markdown(f"**Muscle Group:** {info['muscle']}")
                st.markdown(f"**Valid Range:** {info['valid_range']}")
                st.markdown(f"**Notes:** {info['notes']}")
                st.markdown(f"**Citation:** {info['citation']}")
    else:
        st.caption(disabled_reason)
    return st.session_state[mk]


def render_ra_selector(prefix=""):
    """RA model selector with its equation card and 'About' expander. Returns the selected model."""
    key = f"{prefix}ra_model"
    st.markdown("**Rest Allowance Model**")
    st.selectbox("RA Model:", RA_MODEL_ORDER, **_bind(key))
    ra_model = st.session_state[key]
    st.markdown(f"""
    <div class="model-card">
        <b>{ra_model}</b><br>
        <code>{RA_MODEL_INFO[ra_model]['equation_text']}</code><br>
        <small>Inputs: {RA_MODEL_INFO[ra_model]['inputs']}</small>
    </div>
    """, unsafe_allow_html=True)
    render_ra_model_info(ra_model)
    return ra_model


def not_required_reason(ra_model):
    return f"Not required: {ra_model} uses %MVC only and does not consider MHT."


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


def result_card(res, accent=None, heading=None):
    if res.ok:
        rest = res.rest_s
        sub = f"({rest / 60:.2f} minutes) · RA = {res.ra_pct:,.1f}% of holding time"
        cls, value = "result-card", f"{rest:,.1f} sec"
    else:
        cls, value, sub = "result-card na", "N/A", short_status(res)
    mht_line = f"MHT from: {res.et_model}" if res.et_model else "MHT not used by this model"
    style = f' style="border-color:{accent}; border-width:3px;"' if (accent and res.ok) else ""
    head = (f'<div class="result-label" style="font-weight:bold; color:{accent or COLORS["future_blue"]};">'
            f'{heading}</div>') if heading else ""
    # Built as one line: blank or indented lines inside an HTML block make Markdown render it as a code block
    html = "".join([
        f'<div class="{cls}"{style}>',
        head,
        f'<div class="result-label">Rest Allowance Time for a {res.holding_s:g} s hold at {res.pct_mvc:g}% MVC</div>',
        f'<div class="result-value">{value}</div>',
        f'<div class="result-label">{sub}</div>',
        '<br>',
        f'<div class="result-label">RA Model: {res.model}<br>{mht_line}</div>',
        '</div>',
    ])
    st.markdown(html, unsafe_allow_html=True)


# ============================================================================
# PLOTS
# ============================================================================

AXIS_STYLE = dict(
    showline=False,                                               # no outer edge lines
    zeroline=True, zerolinecolor='black', zerolinewidth=2,        # bold x = 0 / y = 0 lines inside the plot
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


def _star(fig, x, y, text, color=STAR_GOLD, name='Current Task'):
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode='markers', name=name,
        marker=dict(color=color, size=20, symbol='star',
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
def heatmap_grid(model, et_model, hold_max, n_hold=100):
    intensities = np.arange(1, 101, 1.0)
    holds = np.linspace(hold_max / n_hold, hold_max, n_hold)
    z = np.full((len(holds), len(intensities)), np.nan)
    for i, h in enumerate(holds):
        for j, p in enumerate(intensities):
            z[i, j] = rest_time_seconds(model, p, h, et_model)
    return intensities, holds, z


def plot_heatmap(model, et_model, hold_max, current, show_star=True):
    xs, ys, z = heatmap_grid(model, et_model, hold_max)
    zc = np.log10(z + 1)  # +1 s so RA = 0 (no fatigue) stays on the scale
    ticks = [v for v in [0, 1, 10, 100, 1_000, 10_000, 100_000, 1_000_000]
             if v <= np.nanmax(z, initial=0) * 1.01 or v == 0]
    fig = go.Figure(go.Heatmap(
        x=xs, y=ys, z=zc, customdata=z, colorscale='Viridis',
        colorbar=dict(title="Rest (s)", tickvals=np.log10(np.array(ticks) + 1), ticktext=[f"{t:,}" for t in ticks]),
        hovertemplate="Intensity: %{x:.0f}% MVC<br>Holding: %{y:.1f} s<br>Rest: %{customdata:.1f} s<extra></extra>",
        hoverongaps=False,
    ))
    if show_star and current.ok and current.holding_s <= hold_max:
        _star(fig, current.pct_mvc, current.holding_s,
              f"<b>Current Task</b><br>{current.pct_mvc:g}% MVC, {current.holding_s:g} s hold<br>Rest: {current.rest_s:.1f} s")
    fig.update_layout(
        title=dict(text=f"Rest Time Heatmap: {model}" + (f" (MHT: {et_model})" if et_model else ""),
                   font=dict(size=18, color=COLORS['future_blue']), x=0.5),
        xaxis=dict(title="Intensity (% MVC)"), yaxis=dict(title="Holding Time (seconds)"),
        plot_bgcolor='white', height=550, showlegend=False,
    )
    return fig


# ============================================================================
# COMPARISON (two RA + ET pairings overlaid; each may be piecewise in intensity)
# ============================================================================

COMPARE_DASH = {1: None, 2: 'dash'}   # Model 1 solid, Model 2 dashed
SAME_MODEL_TINT = 0.45                # Model 2 lightened when both slots share a colour
PIECEWISE_DEFAULT_T = 35.0            # default transition intensity (% MVC)


def _lighten(hex_color, t):
    rgb = _mix(_hex_to_rgb(hex_color), (255, 255, 255), t)
    return '#%02x%02x%02x' % rgb


# --- piecewise model specs -----------------------------------------------------
#
# A comparison "model" is one RA + ET pairing (a part), or two parts joined at a
# transition intensity T: the primary part applies below T, the secondary at/above T.

def _part(prefix):
    ra = st.session_state[f"{prefix}ra_model"]
    return dict(ra=ra, et=st.session_state[f"{prefix}et_model"] if model_uses_mht(ra) else None)


def _part_label(part):
    return part['ra'] + (f" + {part['et']}" if part['et'] else "")


def part_at(spec, pct):
    """Part in force at this intensity: primary below the transition, secondary at or above it."""
    if spec['T'] is None or pct < spec['T']:
        return spec['parts'][0]
    return spec['parts'][1]


def spec_mht_all(spec):
    return all(p['et'] for p in spec['parts'])


def spec_mht_any(spec):
    return any(p['et'] for p in spec['parts'])


def piecewise_curve(spec, xs, f):
    """
    Evaluate f(part, x) along an intensity grid. For a piecewise spec, the primary segment runs up to T,
    then a gap (NaN), then the secondary segment from T, so the step between models is not drawn as a line.
    """
    xs = np.asarray(xs, float)
    if spec['T'] is None:
        p = spec['parts'][0]
        return xs, np.array([f(p, x) for x in xs], float)
    T = spec['T']
    xa = np.append(xs[xs < T], T)
    xb = xs[xs >= T]
    if not len(xb) or xb[0] != T:
        xb = np.insert(xb, 0, T)
    ya = [f(spec['parts'][0], x) for x in xa]
    yb = [f(spec['parts'][1], x) for x in xb]
    return np.concatenate([xa, [T], xb]), np.array(ya + [np.nan] + yb, float)


def _transition_marks(specs):
    """(T, label, colour, position) for each transition; a shared transition is drawn once, in black."""
    ts = [s for s in specs if s['T'] is not None]
    if len(ts) == 2 and ts[0]['T'] == ts[1]['T']:
        return [(ts[0]['T'], f"Transition {ts[0]['T']:g}% (both)", 'black', "bottom right")]
    return [(s['T'], f"{s['short']} transition {s['T']:g}%", s['color'],
             "bottom left" if s['slot'] == 1 else "bottom right") for s in ts]


def _add_transition_lines(fig, specs):
    for T, label, color, pos in _transition_marks(specs):
        fig.add_vline(x=T, line_dash="dashdot", line_color=color, opacity=0.9, annotation_text=label,
                      annotation_font_color=color, annotation_position=pos)


def build_compare_specs(pct_mvc, holding_s):
    """One spec per comparison slot: its part(s), transition, colour, dash, labels and task result."""
    specs = []
    for slot in (1, 2):
        parts = [_part(f"cmp{slot}_")]
        T = None
        if st.session_state.get(f"cmp{slot}_pw"):
            parts.append(_part(f"cmp{slot}b_"))
            T = float(st.session_state[f"cmp{slot}_pw_t"])
        spec = dict(slot=slot, parts=parts, T=T, dash=COMPARE_DASH[slot], short=f"M{slot}",
                    color=RA_COLORS[parts[0]['ra']])
        active = part_at(spec, pct_mvc)
        spec.update(ra=active['ra'], et=active['et'],
                    res=compute_rest_allowance(active['ra'], pct_mvc, holding_s, active['et']))
        if T is None:
            spec['name'] = f"Model {slot}: {_part_label(parts[0])}"
            spec['active_name'] = spec['name']
        else:
            spec['name'] = (f"Model {slot}: {_part_label(parts[0])} (<{T:g}%) | "
                            f"{_part_label(parts[1])} (≥{T:g}%)")
            spec['active_name'] = (f"Model {slot}: {_part_label(active)} "
                                   f"({'≥' if pct_mvc >= T else '<'}{T:g}% part)")
        specs.append(spec)
    if specs[0]['color'] == specs[1]['color']:
        specs[1]['color'] = _lighten(specs[1]['color'], SAME_MODEL_TINT)
    return specs


def specs_identical(s1, s2):
    return s1['parts'] == s2['parts'] and s1['T'] == s2['T']


def _spec_star(fig, s, x, y, extra=""):
    r = s['res']
    _star(fig, x, y,
          f"<b>Model {s['slot']}</b> ({r.model})<br>{r.pct_mvc:g}% MVC, {r.holding_s:g} s hold<br>"
          f"Rest: {r.rest_s:.1f} s{extra}",
          color=s['color'], name=f"Model {s['slot']} prediction")


# --- plots --------------------------------------------------------------------

def cmp_rest_vs_holding(specs, pct, hold, y_scale):
    """Fixed intensity, so each model uses the single part in force at the task intensity."""
    mhts = [mht_seconds(pct / 100, s['et']) for s in specs if s['et']]
    mhts = [m for m in mhts if np.isfinite(m)]
    x_max = hold * 2
    for m in mhts:
        x_max = max(x_max, min(m * 1.1, hold * 10))
    xs = np.linspace(x_max / 400, x_max, 400)
    xs = np.unique(np.append(xs, [m for m in mhts if m <= x_max]))

    fig = go.Figure()
    shown = []
    for s in specs:
        ys = np.array([rest_time_seconds(s['ra'], pct, x, s['et']) for x in xs])
        shown.extend(ys[np.isfinite(ys)].tolist())
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines', name=s['active_name'], line=dict(color=s['color'], width=3, dash=s['dash']),
            hovertemplate=f"<b>{s['short']}: {s['ra']}</b><br>Holding: %{{x:.1f}} s<br>Rest: %{{y:.1f}} s<extra></extra>"
        ))
    shared_mht = specs[0]['et'] and specs[0]['et'] == specs[1]['et']
    for s in specs:
        if s['et'] and not (shared_mht and s['slot'] == 2):
            m = mht_seconds(pct / 100, s['et'])
            if np.isfinite(m) and m <= x_max:
                fig.add_vline(x=m, line_dash="dot", opacity=0.8,
                              line_color=COLORS['simcoe_blue'] if shared_mht else s['color'],
                              annotation_text=(f"MHT = {m:.1f} s (both)" if shared_mht
                                               else f"{s['short']} MHT = {m:.1f} s"),
                              annotation_position="top left" if s['slot'] == 1 else "top right",
                              annotation_font_color=COLORS['simcoe_blue'] if shared_mht else s['color'])
    for s in specs:
        if s['res'].ok:
            _spec_star(fig, s, hold, s['res'].rest_s)
            shown.append(s['res'].rest_s)
    y_max = max(shown) * 1.1 if shown and max(shown) > 0 else None
    return _layout(fig, f"Rest Time vs Holding Time at {pct:g}% MVC", "Holding Time (seconds)",
                   "Rest Time (seconds)", y_scale, x_range=[0, x_max], y_range=[0, y_max] if y_max else None)


def cmp_rest_vs_intensity(specs, pct, hold, y_scale):
    grid = np.unique(np.append(np.arange(0.5, 100.01, 0.5), pct))
    fig = go.Figure()
    shown = []
    for s in specs:
        xs, ys = piecewise_curve(s, grid, lambda p, x: rest_time_seconds(p['ra'], x, hold, p['et']))
        shown.extend(ys[np.isfinite(ys)].tolist())
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines', name=s['name'], line=dict(color=s['color'], width=3, dash=s['dash']),
            hovertemplate=f"<b>{s['short']}</b><br>Intensity: %{{x:.1f}}% MVC<br>Rest: %{{y:.1f}} s<extra></extra>"
        ))
    fig.add_vline(x=15, line_dash="dot", line_color=COLORS['dark_grey'], opacity=0.6,
                  annotation_text="15% MVC", annotation_position="top right")
    _add_transition_lines(fig, specs)
    for s in specs:
        if s['res'].ok:
            _spec_star(fig, s, pct, s['res'].rest_s)
    y_max = max(shown) * 1.05 if shown and max(shown) > 0 else None
    return _layout(fig, f"Rest Time vs Intensity for a {hold:g} s Hold", "Intensity (% MVC)",
                   "Rest Time (seconds)", y_scale, x_range=[0, 100], y_range=[0, y_max] if y_max else None)


def cmp_work_rest_cycles(specs):
    labels = [f"<b>Model {s['slot']}</b>: {s['ra']}" for s in specs]
    holds = [s['res'].holding_s if s['res'].ok else 0 for s in specs]
    rests = [s['res'].rest_s if s['res'].ok else 0 for s in specs]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=holds, orientation='h', name='Hold (work)', marker_color=COLORS['cool_grey'],
        text=[f"{h:.1f} s" if h else "" for h in holds], textposition='inside',
        hovertemplate="Hold: %{x:.1f} s<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        y=labels, x=rests, orientation='h', name='Rest (model colour)',
        marker=dict(color=[s['color'] for s in specs], line=dict(color='black', width=1)),
        text=[f"{r:.1f} s" if r else "" for r in rests], textposition='outside', cliponaxis=False,
        textfont=dict(color='black'),
        hovertemplate="Rest: %{x:.1f} s<extra></extra>"
    ))
    for lab, s in zip(labels, specs):
        if not s['res'].ok:
            fig.add_annotation(y=lab, x=0, text=f"N/A: {short_status(s['res'])}", showarrow=False,
                               xanchor='left', font=dict(color=COLORS['simcoe_blue']))
    fig.update_layout(
        barmode='stack',
        title=dict(text="One Work–Rest Cycle per Model", font=dict(size=20, color=COLORS['future_blue']), x=0.5),
        xaxis=dict(title="Time (seconds)", gridcolor='lightgray',
                   range=[0, max([h + r for h, r in zip(holds, rests)] + [1]) * 1.15]),
        yaxis=dict(autorange='reversed', automargin=True),
        margin=dict(l=230), plot_bgcolor='white', height=320,
        legend=dict(orientation='h', yanchor='bottom', y=1.0, xanchor='right', x=1),
    )
    return fig


def cmp_et_curves(specs, pct, hold, y_scale):
    used = [s for s in specs if spec_mht_any(s)]
    if not used:
        return None
    grid = np.linspace(1, 100, 500)
    fig = go.Figure()
    refs = [hold]
    for s in used:
        xs, ys = piecewise_curve(s, grid, lambda p, x: mht_seconds(x / 100, p['et']) if p['et'] else np.nan)
        if s['T'] is None:
            name = f"{s['short']}: {s['parts'][0]['et']}"
        else:
            name = (f"{s['short']}: {s['parts'][0]['et'] or '—'} (<{s['T']:g}%) | "
                    f"{s['parts'][1]['et'] or '—'} (≥{s['T']:g}%)")
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines', name=name, line=dict(color=s['color'], width=3, dash=s['dash']),
            hovertemplate=f"<b>{s['short']}</b><br>Intensity: %{{x:.1f}}% MVC<br>MHT: %{{y:.1f}} s<extra></extra>"
        ))
    fig.add_hline(y=hold, line_dash="dash", line_color=COLORS['dark_grey'], opacity=0.8,
                  annotation_text=f"Holding time = {hold:g} s")
    fig.add_vline(x=pct, line_dash="dash", line_color=COLORS['dark_grey'], opacity=0.4)
    _add_transition_lines(fig, used)
    for s in used:
        if s['et']:
            m = mht_seconds(pct / 100, s['et'])
            if np.isfinite(m):
                refs.append(m)
                _star(fig, pct, m, f"<b>Model {s['slot']} MHT at {pct:g}% MVC</b><br>{s['et']}<br>"
                                   f"{m:.1f} s ({m / 60:.2f} min)",
                      color=s['color'], name=f"Model {s['slot']} MHT")
    _layout(fig, "Endurance Time Curves Supplying MHT", "Intensity (% MVC)", "Maximum Holding Time (seconds)",
            y_scale, x_range=[0, 100], y_range=[0, max(refs) * 3])
    fig.update_layout(legend=dict(xanchor="right", x=0.99))
    return fig


def cmp_auto_xmax(specs, holding_s):
    return max(overview_auto_xmax(p['ra'], p['et'], False, holding_s) for s in specs for p in s['parts'])


def _in_part(spec, side, pcts):
    pcts = np.asarray(pcts, float)
    if spec['T'] is None:
        return np.ones(pcts.shape, bool)
    return pcts < spec['T'] if side == 0 else pcts >= spec['T']


def cmp_overview(specs, hold_max, show_star, log_y, normalised):
    """10% MVC iso-intensity lines for both models: Model 1 solid, Model 2 dashed, each in its colour.
    For a piecewise model, each intensity line comes from the part in force at that intensity."""
    fig = go.Figure()
    xkey, ykey = ('fmht', 'ra') if normalised else ('hold', 'rest')
    all_y, ends = [], []
    for s in specs:
        first_line, first_bound, spec_ends = True, True, []
        for side, part in enumerate(s['parts']):
            if part['et'] and not normalised:
                bp, bx, by = exhaustion_boundary(part['ra'], part['et'], hold_max)
                keep = _in_part(s, side, bp) if len(bp) else np.array([], bool)
                if keep.any():
                    fig.add_trace(go.Scatter(
                        x=bx[keep], y=by[keep], mode='lines', name=f"{s['short']} exhaustion boundary",
                        legendgroup=f"m{s['slot']}b", showlegend=first_bound,
                        line=dict(color=s['color'], width=1, dash='dot'), opacity=0.7, customdata=bp[keep],
                        hovertemplate=f"<b>{s['short']} exhaustion boundary</b><br>%{{customdata:.1f}}% MVC<br>"
                                      "Hold = MHT = %{x:,.1f} s<br>Rest: %{y:,.1f} s<extra></extra>"
                    ))
                    first_bound = False
                    all_y.extend(by[keep].tolist())
            for c in overview_curves(part['ra'], part['et'], hold_max, False, normalised):
                if not _in_part(s, side, [c['p']])[0]:
                    continue
                xs, ys = c[xkey], c[ykey]
                if normalised:
                    hover = (f"<b>{s['short']}: {c['p']}% MVC</b> ({part['ra']})<br>fMHT: %{{x:.3f}}<br>"
                             f"RA: %{{y:,.1f}}%<br>Holding: %{{customdata[0]:,.1f}} s<br>"
                             f"Rest: %{{customdata[1]:,.1f}} s<extra></extra>")
                    cd = np.column_stack([c['hold'], c['rest']])
                else:
                    hover = (f"<b>{s['short']}: {c['p']}% MVC</b> ({part['ra']})<br>Holding: %{{x:,.1f}} s<br>"
                             f"Rest: %{{y:,.1f}} s<extra></extra>")
                    cd = None
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode='lines', name=s['name'], legendgroup=f"m{s['slot']}", showlegend=first_line,
                    line=dict(color=s['color'], width=2, dash=s['dash']), customdata=cd, hovertemplate=hover
                ))
                first_line = False
                finite = np.isfinite(ys)
                all_y.extend(ys[finite].tolist())
                if np.any(ys[finite] > 0):
                    i = np.where(finite)[0][-1]
                    spec_ends.append((c['p'], xs[i], ys[i]))
        for g in _group_end_labels(spec_ends):
            ends.append((s, min(g['ps']), g['x'], g['y'], g['text']))

    star_specs = []
    if show_star:
        for s in specs:
            r = s['res']
            if r.ok and (not normalised or np.isfinite(r.fmht)):
                star_specs.append(s)
                all_y.append(r.ra_pct if normalised else r.rest_s)
    pos = [v for v in all_y if v > 0]
    y_top = max(pos) if pos else 1.0
    y_floor = y_top / 10 ** LOG_DECADES

    def y_pos(v):
        return np.log10(max(v, y_floor)) if log_y else v

    # End labels, skipping overlaps across both models
    x_span = 1.0 if normalised else hold_max
    y_lo, y_hi = (np.log10(y_floor), np.log10(y_top)) if log_y else (0.0, y_top)
    placed = []
    for s, p, x, y, text in sorted(ends, key=lambda e: e[1]):
        gx, gy = x / x_span, (y_pos(y) - y_lo) / max(y_hi - y_lo, 1e-12)
        if any(abs(gx - px) < 0.06 and abs(gy - py) < 0.035 for px, py in placed):
            continue
        placed.append((gx, gy))
        fig.add_annotation(x=x, y=y_pos(y), text=text, showarrow=False, xanchor='left', xshift=4,
                           font=dict(size=11, color=s['color']))

    x_max = 1.0 if normalised else hold_max
    for s in star_specs:
        r = s['res']
        if normalised:
            _star(fig, r.fmht, r.ra_pct,
                  f"<b>Model {s['slot']}</b> ({r.model})<br>fMHT = {r.fmht:.3f}<br>"
                  f"RA: {r.ra_pct:.1f}% · Rest: {r.rest_s:.1f} s",
                  color=s['color'], name=f"Model {s['slot']} prediction")
        else:
            _spec_star(fig, s, r.holding_s, r.rest_s)
            x_max = max(x_max, r.holding_s)

    if normalised:
        title, xt, yt = "Model Overview, normalised to MHT", "fMHT (holding time ÷ MHT)", "Rest Allowance (% of holding time)"
    else:
        title, xt, yt = "Model Overview (10% MVC lines)", "Holding Time (seconds)", "Rest Time (seconds)"
    _layout(fig, title, xt, yt, 'log' if log_y else 'linear', x_range=[0, x_max * 1.07], height=680)
    if log_y:
        fig.update_yaxes(range=[np.log10(y_floor), np.log10(y_top * 1.5)], dtick=1)
    fig.update_layout(title=dict(font=dict(size=18)),
                      legend=dict(orientation='h', yanchor='top', y=-0.14, xanchor='left', x=0,
                                  bgcolor='rgba(255,255,255,0)'))
    return fig


def _symlog(v):
    return np.sign(v) * np.log10(1 + np.abs(v))


def spec_heatmap_grid(spec, hold_max):
    """Rest-time grid for a spec; piecewise specs take the secondary part's columns at/above T."""
    p0 = spec['parts'][0]
    xs, ys, z = heatmap_grid(p0['ra'], p0['et'], hold_max)
    if spec['T'] is not None:
        p1 = spec['parts'][1]
        _, _, zb = heatmap_grid(p1['ra'], p1['et'], hold_max)
        z = np.where(xs[None, :] < spec['T'], z, zb)
    return xs, ys, z


def cmp_difference_heatmap(specs, hold_max, current_pct, current_hold, show_star):
    s1, s2 = specs
    xs, ys, z1 = spec_heatmap_grid(s1, hold_max)
    _, _, z2 = spec_heatmap_grid(s2, hold_max)
    d = z2 - z1                                    # NaN wherever either model is undefined
    t = _symlog(d)
    zmax = float(np.nanmax(np.abs(t))) if np.any(np.isfinite(t)) else 1.0
    zmax = max(zmax, 0.5)
    mags = [v for v in [10, 100, 1_000, 10_000, 100_000, 1_000_000] if np.log10(1 + v) <= zmax * 1.01]
    tickvals = [-_symlog(v) for v in reversed(mags)] + [0] + [_symlog(v) for v in mags]
    ticktext = [f"−{v:,}" for v in reversed(mags)] + ["0"] + [f"+{v:,}" for v in mags]
    fig = go.Figure(go.Heatmap(
        x=xs, y=ys, z=t, zmid=0, zmin=-zmax, zmax=zmax, colorscale='RdBu_r',
        customdata=np.dstack([z1, z2, d]),
        colorbar=dict(title=dict(text="M2 − M1<br>rest (s)"), tickvals=tickvals, ticktext=ticktext),
        hovertemplate="Intensity: %{x:.0f}% MVC<br>Holding: %{y:.1f} s<br>"
                      "M1 rest: %{customdata[0]:,.1f} s<br>M2 rest: %{customdata[1]:,.1f} s<br>"
                      "<b>M2 − M1: %{customdata[2]:+,.1f} s</b><extra></extra>",
        hoverongaps=False,
    ))
    for T, label, _, pos in _transition_marks(specs):
        fig.add_vline(x=T, line_dash="dashdot", line_color='black', line_width=1.5, annotation_text=label,
                      annotation_font_color='black', annotation_position=pos.replace("bottom", "top"))
    if show_star and current_hold <= hold_max and (s1['res'].ok or s2['res'].ok):
        d_now = (s2['res'].rest_s - s1['res'].rest_s) if (s1['res'].ok and s2['res'].ok) else np.nan
        _star(fig, current_pct, current_hold,
              f"<b>Current Task</b><br>{current_pct:g}% MVC, {current_hold:g} s hold<br>"
              + (f"M2 − M1: {d_now:+.1f} s" if np.isfinite(d_now) else "Difference: N/A"))
    fig.update_layout(
        title=dict(text="Rest Time Difference Heatmap (Model 2 − Model 1)",
                   font=dict(size=18, color=COLORS['future_blue']), x=0.5),
        xaxis=dict(title="Intensity (% MVC)"), yaxis=dict(title="Holding Time (seconds)"),
        plot_bgcolor='white', height=560, showlegend=False,
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
        ra_model = render_ra_selector()
    with c2:
        uses_mht = model_uses_mht(ra_model)
        et_model = render_et_selector(uses_mht, disabled_reason=not_required_reason(ra_model))

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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Rest vs Holding Time", "Rest vs Intensity", "Work–Rest Cycle",
                                                  "Endurance Time (MHT)", "Model Overview", "Rest Time Heatmap"])
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
    with tab6:
        h1, h2 = st.columns([1, 1.4])
        with h1:
            hm_star = st.checkbox("Show current task (★)", value=True, key="hm_star")
        with h2:
            hm_user = st.number_input("Max holding time shown (s)", min_value=1.0, value=None,
                                      step=60.0, format="%.0f", placeholder="Auto", key="hm_ymax",
                                      help="Upper limit of the holding-time axis. Leave blank for automatic: "
                                           "the same range as the Model Overview (MHT at 20% MVC for the "
                                           f"selected ET model, up to {OVERVIEW_AUTO_CAP_S:,} s).")
        hm_max = float(hm_user) if hm_user else overview_auto_xmax(ra_model, et_model, True, holding_s)
        with st.spinner("Calculating heatmap..."):
            show_chart(plot_heatmap(ra_model, et_model if uses_mht else None, hm_max, res, hm_star), width="stretch")
        st.caption("Rest time for every combination of intensity (1–100% MVC) and holding time, for the selected "
                   "RA and ET models. "
                   + ("Blank cells are outside the model's valid domain (holding time > MHT, ET undefined"
                      + (", or Milner fMHT ≤ 0.01" if ra_model == MILNER_1985 else "") + "). "
                      if uses_mht else "")
                   + "Colour scale is logarithmic in rest seconds. Drag to zoom, double-click to reset.")
        if hm_star and not res.ok:
            st.warning(f"The current task can't be starred: {short_status(res).lower()}.")
        elif hm_star and res.holding_s > hm_max:
            st.warning("The current task's holding time is above the axis range; increase the max holding time to see it.")


# ============================================================================
# COMPARE PAGE
# ============================================================================
elif st.session_state.current_page == "Compare":
    st.title("Rest Allowance Model Comparison")
    st.markdown("*Compare two rest allowance + endurance time model pairings for the same task*")
    st.markdown("---")

    pct_mvc, holding_s = render_task_inputs()

    st.markdown("---")
    sel_cols = st.columns(2, gap="large")
    for slot, col in zip((1, 2), sel_cols):
        with col:
            st.markdown(f"### Model {slot} Selection")
            st.checkbox("Use compound/piecewise function",
                        help="Join two RA + ET pairings at a transition intensity: the primary model applies "
                             "below it and the secondary model at and above it.",
                        **_bind(f"cmp{slot}_pw"))
            piecewise = st.session_state[f"cmp{slot}_pw"]
            if piecewise:
                st.number_input("Transition intensity (% MVC)", min_value=1.0, max_value=99.0, step=1.0,
                                format="%.1f", **_bind(f"cmp{slot}_pw_t"))
                t_sel = st.session_state[f"cmp{slot}_pw_t"]
                st.markdown(f"#### Primary Model (< {t_sel:g}% MVC)")
            ra_sel = render_ra_selector(prefix=f"cmp{slot}_")
            render_et_selector(model_uses_mht(ra_sel), disabled_reason=not_required_reason(ra_sel),
                               prefix=f"cmp{slot}_")
            if piecewise:
                st.markdown(f"#### Secondary Model (≥ {t_sel:g}% MVC)")
                ra_b = render_ra_selector(prefix=f"cmp{slot}b_")
                render_et_selector(model_uses_mht(ra_b), disabled_reason=not_required_reason(ra_b),
                                   prefix=f"cmp{slot}b_")

    specs = build_compare_specs(pct_mvc, holding_s)
    s1, s2 = specs
    both_mht = spec_mht_all(s1) and spec_mht_all(s2)

    st.markdown("---")
    st.markdown("### Results")
    res_cols = st.columns(2, gap="large")
    for s, col in zip(specs, res_cols):
        with col:
            heading = f"Model {s['slot']}"
            if s['T'] is not None:
                heading += (f" · {'secondary' if pct_mvc >= s['T'] else 'primary'} model applies "
                            f"({pct_mvc:g}% {'≥' if pct_mvc >= s['T'] else '<'} {s['T']:g}% transition)")
            result_card(s['res'], accent=s['color'], heading=heading)
            if s['res'].status in ('infeasible', 'out_of_domain', 'et_undefined', 'invalid_input'):
                st.error(s['res'].message)
            elif s['res'].status == 'no_fatigue':
                st.info(s['res'].message)

    d1, d2, d3 = st.columns(3)
    if s1['res'].ok and s2['res'].ok:
        diff = s2['res'].rest_s - s1['res'].rest_s
        d1.metric("Difference (Model 2 − Model 1)", f"{diff:+,.1f} s")
        d2.metric("Ratio (Model 2 ÷ Model 1)", f"×{s2['res'].rest_s / s1['res'].rest_s:,.2f}"
                  if s1['res'].rest_s > 0 else "—")
        d3.metric("More rest predicted by",
                  "Equal" if np.isclose(diff, 0) else ("Model 2" if diff > 0 else "Model 1"))
    else:
        d1.metric("Difference (Model 2 − Model 1)", "—")
        d2.metric("Ratio (Model 2 ÷ Model 1)", "—")
        d3.metric("More rest predicted by", "—")
    if specs_identical(s1, s2):
        st.info("Model 1 and Model 2 are the same, so their curves overlap exactly.")

    st.markdown("---")
    st.markdown("### Interactive Plots")
    st.caption("Model 1 is drawn solid and Model 2 dashed, each in its RA model's colour (Model 2 is lightened "
               "when both use the same RA model). Stars mark each model's prediction for the current task.")
    c1t, c2t, c3t, c4t, c5t, c6t = st.tabs(["Rest vs Holding Time", "Rest vs Intensity", "Work–Rest Cycle",
                                            "Endurance Time (MHT)", "Model Overview",
                                            "Rest Time Difference Heatmap"])
    with c1t:
        show_chart(cmp_rest_vs_holding(specs, pct_mvc, holding_s, y_scale_val))
        st.caption("MHT-based curves end where holding time reaches that model's MHT (dotted line)."
                   + (" At a fixed intensity, a piecewise model uses whichever part is in force at the task "
                      "intensity, named in the legend." if (s1['T'] is not None or s2['T'] is not None) else ""))
    with c2t:
        show_chart(cmp_rest_vs_intensity(specs, pct_mvc, holding_s, y_scale_val))
        st.caption("MHT-based curves end at the intensity where MHT falls below the holding time."
                   + (" Piecewise models are drawn with a break at their transition (dash-dot line): the step "
                      "there comes from joining two models, not from physiology."
                      if (s1['T'] is not None or s2['T'] is not None) else ""))
    with c3t:
        show_chart(cmp_work_rest_cycles(specs))
    with c4t:
        et_fig = cmp_et_curves(specs, pct_mvc, holding_s, y_scale_val)
        if et_fig is None:
            st.info("Neither model uses MHT, so there is no endurance time curve to show.")
        else:
            show_chart(et_fig)
            if s1['T'] is None and s2['T'] is None and s1['et'] and s1['et'] == s2['et']:
                st.caption("Both models use the same ET model, so the curves overlap.")
            elif not (spec_mht_any(s1) and spec_mht_any(s2)):
                st.caption("Only one of the two models uses MHT.")
            if s1['T'] is not None or s2['T'] is not None:
                st.caption("Piecewise models switch ET model at their transition (dash-dot line); a gap in a "
                           "curve means that part's RA model does not use MHT.")
    with c5t:
        o1, o2, o3 = st.columns([1, 1, 1.4])
        with o1:
            cmp_ov_star = st.checkbox("Show model predictions (★)", value=True, key="cmp_ov_star")
            cmp_ov_log = st.checkbox("Log scale (y-axis)", value=(y_scale_val == 'log'), key="cmp_ov_log")
        with o2:
            cmp_ov_norm = st.checkbox(
                "Normalise to MHT (fMHT)", value=False, key="cmp_ov_norm", disabled=not both_mht,
                help="x = holding time ÷ MHT (0–1), y = rest allowance as % of holding time."
                     if both_mht else "Available when both models use MHT."
            )
            cmp_ov_norm = cmp_ov_norm and both_mht
        with o3:
            cmp_ov_user = st.number_input("Max holding time shown (s)", min_value=1.0, value=None, step=60.0,
                                          format="%.0f", placeholder="Auto", key="cmp_ov_xmax",
                                          disabled=cmp_ov_norm,
                                          help="Leave blank for automatic: the longer of the two models' "
                                               "default ranges.")
        cmp_ov_max = float(cmp_ov_user) if cmp_ov_user else cmp_auto_xmax(specs, holding_s)
        show_chart(cmp_overview(specs, cmp_ov_max, cmp_ov_star, cmp_ov_log, cmp_ov_norm))
        st.caption("Lines every 10% MVC for each model, labelled at their ends. "
                   + ("For a piecewise model, each line comes from the part in force at that intensity. "
                      if (s1['T'] is not None or s2['T'] is not None) else "")
                   + ("MHT-based lines end at MHT; the dotted lines are each model's exhaustion boundary. "
                      if not cmp_ov_norm else "")
                   + ("On the log scale, lines at RA = 0 are not shown. " if cmp_ov_log else "")
                   + "Drag to zoom, double-click to reset.")
    with c6t:
        h1, h2 = st.columns([1, 1.4])
        with h1:
            cmp_hm_star = st.checkbox("Show current task (★)", value=True, key="cmp_hm_star")
        with h2:
            cmp_hm_user = st.number_input("Max holding time shown (s)", min_value=1.0, value=None, step=60.0,
                                          format="%.0f", placeholder="Auto", key="cmp_hm_xmax",
                                          help="Leave blank for automatic: the longer of the two models' "
                                               "default ranges.")
        cmp_hm_max = float(cmp_hm_user) if cmp_hm_user else cmp_auto_xmax(specs, holding_s)
        with st.spinner("Calculating heatmap..."):
            show_chart(cmp_difference_heatmap(specs, cmp_hm_max, pct_mvc, holding_s, cmp_hm_star))
        st.caption("Red: Model 2 predicts more rest. Blue: Model 1 predicts more rest. White: they agree. "
                   + ("Dash-dot lines mark piecewise transitions. " if (s1['T'] is not None or s2['T'] is not None) else "")
                   +
                   "Blank cells are outside the valid domain of either model. Colour scale is logarithmic "
                   "in seconds of difference. Drag to zoom, double-click to reset.")
        if cmp_hm_star and holding_s > cmp_hm_max:
            st.warning("The current task's holding time is above the axis range; increase the max holding time to see it.")


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
