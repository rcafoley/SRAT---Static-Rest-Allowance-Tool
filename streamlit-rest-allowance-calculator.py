import numpy as np
import pandas as pd
import plotly.graph_objects as go
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
    ROHMERT_1973,
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


def _star(fig, x, y, text):
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode='markers', name='Current Task',
        marker=dict(color=COLORS['tech_tangerine'], size=20, symbol='star',
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

    tab1, tab2, tab3, tab4 = st.tabs(["Rest vs Holding Time", "Rest vs Intensity", "Work–Rest Cycle", "Endurance Time (MHT)"])
    with tab1:
        st.plotly_chart(plot_rest_vs_holding(res, plot_models, plot_et, y_scale_val), width="stretch")
        st.caption("MHT-based curves end where holding time reaches MHT (fMHT = 1); beyond that the task cannot be sustained.")
    with tab2:
        st.plotly_chart(plot_rest_vs_intensity(res, plot_models, plot_et, y_scale_val), width="stretch")
        st.caption("MHT-based curves end at the intensity where MHT falls below the holding time.")
    with tab3:
        cyc = all_results if overlay else [res]
        st.plotly_chart(plot_work_rest_cycles(cyc, ra_model), width="stretch")
    with tab4:
        if uses_mht or overlay:
            st.plotly_chart(plot_et_curve(res, et_model, y_scale_val), width="stretch")
            st.caption("The task is feasible for MHT-based models when the curve sits above the holding-time line at the task intensity.")
        else:
            st.info(f"{ra_model} does not use MHT. Enable the overlay above to view the ET curve used by the other models.")


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
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.markdown("### Rest Time Map (Intensity × Holding Time)")
    h1, h2 = st.columns(2)
    with h1:
        st.selectbox("RA Model:", RA_MODEL_ORDER, **_bind('heatmap_model'))
    with h2:
        hold_max = st.slider("Max Holding Time (s)", 10, 600, int(max(60, min(600, holding_s * 2))), step=10)
    hm_model = st.session_state.heatmap_model
    current = compute_rest_allowance(hm_model, pct_mvc, holding_s, et_model)
    st.plotly_chart(plot_heatmap(hm_model, et_model if model_uses_mht(hm_model) else None, hold_max, current),
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
