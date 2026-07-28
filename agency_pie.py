import math
from io import StringIO

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="Agency Framework™ Visualizer", layout="wide")
st.title("Agency Framework™ Visualizer")
st.caption("Agency Framework™ – Oren Boxer, Ph.D.")
st.markdown(
    """
    <style>
    .stApp { background: #FAFAF8; }
    h1, h2, h3 { color: #2E4055; letter-spacing: -0.02em; }
    [data-testid="stSidebar"] { background: #F3F0E9; }
    [data-testid="stMetric"], [data-testid="stDataFrame"] {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Inputs
# -----------------------------
INPUT_DOMAINS = [
    "Reasoning", "Reading", "Math", "Writing",
    "Attention", "Planning", "Language",
    "Coordination", "Social", "Coping & Regulation"
]

MAIN_DOMAINS = [
    "Reasoning",
    "Academics",
    "Attention",
    "Planning",
    "Language",
    "Coordination",
    "Social",
    "Coping & Regulation",
]

ACADEMIC_SUBS = ["Math", "Writing", "Reading"]
ACADEMIC_SUB_ABBR = {"Math": "M", "Writing": "W", "Reading": "R"}
DISPLAY_LABELS = {
    "Coping & Regulation": "Coping &<br>Regulation",
}
LABEL_RADIUS_BY_DOMAIN = {
    "Reasoning": 1.03,
    "Academics": 1.10,
    "Attention": 1.08,
    "Planning": 1.03,
    "Language": 1.03,
    "Coordination": 1.07,
    "Social": 1.10,
    "Coping & Regulation": 1.02,
}
LABEL_FONT_SIZE_BY_DOMAIN = {
    "Reasoning": 16,
    "Academics": 15,
    "Attention": 17,
    "Planning": 17,
    "Language": 17,
    "Coordination": 16,
    "Social": 17,
    "Coping & Regulation": 15,
}

MAX_SCORE = 100
LABEL_RADIUS_FACTOR = 1.14
PLOT_MAX = int(MAX_SCORE * 1.24)

# Make the chart physically large (key for parent feedbacks + fullscreen readability)
CHART_HEIGHT = 880

# -----------------------------
# Color themes
# -----------------------------
THEMES = {
    "Agency Signature": {
        "Reasoning": "#304C6D",
        "Reading": "#D9A73E",
        "Math": "#E8BF63",
        "Writing": "#C98F38",
        "Attention": "#D16A5B",
        "Planning": "#6EA7A4",
        "Language": "#C98591",
        "Coordination": "#A97358",
        "Social": "#7D9B73",
        "Coping & Regulation": "#806A8F",
        "Academics": "#D9A73E",
    },
    "Original": {
        "Reasoning": "#4C78A8",
        "Reading": "#F58518",
        "Math": "#54A24B",
        "Writing": "#B279A2",
        "Attention": "#E45756",
        "Planning": "#72B7B2",
        "Language": "#FF9DA6",
        "Coordination": "#9D755D",
        "Social": "#BAB0AC",
        "Coping & Regulation": "#59A14F",
        "Academics": "#F58518",
    },
    "Muted Clinical": {
        "Reasoning": "#5B7C99",
        "Reading": "#D8A47F",
        "Math": "#6A9F58",
        "Writing": "#8C6FA8",
        "Attention": "#C25A5A",
        "Planning": "#5F9EA0",
        "Language": "#E8A0A8",
        "Coordination": "#8D6E63",
        "Social": "#9E9E9E",
        "Coping & Regulation": "#7DA453",
        "Academics": "#D8A47F",
    },
    "High Contrast": {
        "Reasoning": "#1F77B4",
        "Reading": "#FF7F0E",
        "Math": "#2CA02C",
        "Writing": "#9467BD",
        "Attention": "#D62728",
        "Planning": "#17BECF",
        "Language": "#FF69B4",
        "Coordination": "#8C564B",
        "Social": "#7F7F7F",
        "Coping & Regulation": "#32CD32",
        "Academics": "#FF7F0E",
    },
}

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Enter scores (0–100)")
theme_choice = st.sidebar.selectbox("Color Theme", list(THEMES.keys()))
COLOR_MAP = THEMES[theme_choice]

mode = st.sidebar.radio("Input method", ["Type values", "Paste CSV"])

values: list[int] = []

if mode == "Type values":
    for d in INPUT_DOMAINS:
        v = st.sidebar.number_input(d, min_value=0, max_value=100, value=50, step=1)
        values.append(int(v))
else:
    st.sidebar.write("Paste two-column CSV here (domain,value) OR just values in domain order.")
    sample = (
        "domain,value\n"
        "Reasoning,100\nReading,60\nMath,100\nWriting,90\nAttention,25\nPlanning,25\n"
        "Language,100\nCoordination,100\nSocial,100\nCoping & Regulation,50\n"
    )
    text = st.sidebar.text_area("Paste data", value=sample, height=220)

    try:
        df_in = pd.read_csv(StringIO(text))
        if "domain" not in df_in.columns or "value" not in df_in.columns:
            raise ValueError("CSV must have columns: domain,value")

        df_in["domain"] = df_in["domain"].astype(str)
        df_in["value"] = pd.to_numeric(df_in["value"], errors="coerce").fillna(0).astype(int)

        lookup_in = dict(zip(df_in["domain"], df_in["value"]))
        values = [int(lookup_in.get(d, 0)) for d in INPUT_DOMAINS]

    except Exception:
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        nums: list[int] = []
        for ln in lines:
            try:
                nums.append(int(float(ln)))
            except Exception:
                pass
        values = (nums + [0] * len(INPUT_DOMAINS))[: len(INPUT_DOMAINS)]

df_input = pd.DataFrame({"domain": INPUT_DOMAINS, "value": values})
lookup = dict(zip(df_input["domain"], df_input["value"]))

with st.expander("Review entered values"):
    st.dataframe(df_input, width="stretch", hide_index=True)

# -----------------------------
# Helpers
# -----------------------------
def clamp_int(x) -> int:
    try:
        v = int(float(x))
    except Exception:
        v = 0
    return max(0, min(MAX_SCORE, v))


def normalize_deg(deg: float) -> float:
    return float(deg % 360)


def boundary_lines(
    n: int,
    rotation_deg: float,
    max_r: int = MAX_SCORE,
    color: str = "rgba(0,0,0,0.12)",
    width: int = 1,
) -> list[dict]:
    lines = []
    rot = math.radians(rotation_deg)
    for k in range(n):
        theta = rot - (2 * math.pi * (k / n))  # clockwise
        x = max_r * math.cos(theta)
        y = max_r * math.sin(theta)
        lines.append(
            dict(
                type="line",
                x0=0, y0=0,
                x1=x, y1=y,
                xref="x", yref="y",
                line=dict(color=color, width=width),
                layer="below",
            )
        )
    return lines


def main_wedge_geometry(n_main: int):
    w_main = 360 / n_main
    rotation_deg = 90 - (180 / n_main)
    return w_main, rotation_deg


def common_layout(n_main: int) -> dict:
    half_slice = 180 / n_main
    rotation_deg = 90 - half_slice

    return dict(
        template="plotly_white",
        showlegend=False,
        height=CHART_HEIGHT,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Avenir Next, Avenir, Helvetica Neue, Arial, sans-serif"),
        polar=dict(
            barmode="overlay",
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, PLOT_MAX],
                showticklabels=False,
                ticks="",
                tickvals=[25, 50, 75, 100],
                gridcolor="rgba(48,76,109,0.10)",
                gridwidth=1,
                linecolor="#DDBB62",
                linewidth=2,
            ),
            angularaxis=dict(
                rotation=rotation_deg,
                direction="clockwise",
                showgrid=False,
                showticklabels=False,
                linecolor="#DDBB62",
                linewidth=2,
            ),
        ),
        xaxis=dict(visible=False, range=[-PLOT_MAX, PLOT_MAX]),
        yaxis=dict(visible=False, range=[-PLOT_MAX, PLOT_MAX], scaleanchor="x", scaleratio=1),
        shapes=[],
        margin=dict(l=145, r=145, t=125, b=145),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#D7C382",
            font=dict(color="#24384D", size=14),
        ),
    )


def add_labels(fig: go.Figure, labels: list[str], n_main: int) -> None:
    w_main, rotation_deg = main_wedge_geometry(n_main)
    centers = [normalize_deg(rotation_deg - (k + 0.5) * w_main) for k in range(n_main)]
    r_labels = [
        MAX_SCORE * LABEL_RADIUS_BY_DOMAIN.get(MAIN_DOMAINS[i], LABEL_RADIUS_FACTOR)
        for i in range(n_main)
    ]
    styled_labels = [f"<b>{label}</b>" for label in labels]
    label_sizes = [
        LABEL_FONT_SIZE_BY_DOMAIN.get(MAIN_DOMAINS[i], 17)
        for i in range(n_main)
    ]

    fig.add_trace(
        go.Scatterpolar(
            r=r_labels,
            theta=centers,
            mode="text",
            text=styled_labels,
            textfont=dict(
                family="Avenir Next, Avenir, Helvetica Neue, Arial, sans-serif",
                size=label_sizes,
                color="#2E4055",
                shadow="0 0 4px #FAFAF8, 0 0 8px #FAFAF8",
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )


def add_academics_sub_labels(fig: go.Figure, n_main: int) -> None:
    w_main, rotation_deg = main_wedge_geometry(n_main)
    acad_k = MAIN_DOMAINS.index("Academics")

    acad_edge_start = rotation_deg - acad_k * w_main
    w_mini = w_main / 3

    thetas = []
    texts = []
    for j, sub in enumerate(ACADEMIC_SUBS):
        theta_center = normalize_deg(acad_edge_start - (j + 0.5) * w_mini)
        thetas.append(theta_center)
        texts.append(f"<b>{sub.upper()}</b>")

    r_sub = MAX_SCORE * 0.95

    fig.add_trace(
        go.Scatterpolar(
            r=[r_sub] * len(thetas),
            theta=thetas,
            mode="text",
            text=texts,
            textfont=dict(
                family="Avenir Next, Avenir, Helvetica Neue, Arial, sans-serif",
                size=10,
                color="#5D523A",
                shadow="0 0 3px #FAFAF8, 0 0 6px #FAFAF8",
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )


# -----------------------------
# Trace builder
# -----------------------------
def build_traces(reveal_main_count: int) -> list:
    """
    reveal_main_count = number of MAIN_DOMAINS revealed (0..len(MAIN_DOMAINS))
    Academics counts as ONE reveal step (when it reveals, all 3 sub-slices appear).
    """
    n_main = len(MAIN_DOMAINS)
    w_main, rotation_deg = main_wedge_geometry(n_main)

    revealed = set(range(max(0, min(n_main, reveal_main_count))))

    traces = []

    # A complete, lightly tinted wheel remains visible behind the scores.
    # It represents the full set of capacities that can be strengthened.
    for k, name in enumerate(MAIN_DOMAINS):
        if name == "Academics":
            continue
        theta_center = normalize_deg(rotation_deg - (k + 0.5) * w_main)
        traces.append(
            go.Barpolar(
                r=[MAX_SCORE],
                theta=[theta_center],
                width=[w_main * 0.985],
                marker=dict(
                    color=COLOR_MAP.get(name, "#60758C"),
                    line=dict(color="#E1C46F", width=1.4),
                ),
                opacity=0.12,
                hoverinfo="skip",
            )
        )

    acad_k = MAIN_DOMAINS.index("Academics")
    acad_edge_start = rotation_deg - acad_k * w_main
    w_mini = w_main / 3
    for j, sub in enumerate(ACADEMIC_SUBS):
        theta_center = normalize_deg(acad_edge_start - (j + 0.5) * w_mini)
        traces.append(
            go.Barpolar(
                r=[MAX_SCORE],
                theta=[theta_center],
                width=[w_mini * 0.96],
                marker=dict(
                    color=COLOR_MAP.get(sub, "#D9A73E"),
                    line=dict(color="#E1C46F", width=1.2),
                ),
                opacity=0.13,
                hoverinfo="skip",
            )
        )

    # regular main wedges
    for k, name in enumerate(MAIN_DOMAINS):
        if name == "Academics":
            continue

        val = clamp_int(lookup.get(name, 0))
        if k not in revealed:
            val = 0

        theta_center = normalize_deg(rotation_deg - (k + 0.5) * w_main)

        traces.append(
            go.Barpolar(
                r=[val],
                theta=[theta_center],
                width=[w_main * 0.94],
                marker=dict(
                    color=COLOR_MAP.get(name, "#4C78A8"),
                    line=dict(color="rgba(255,255,255,0.92)", width=1.6),
                ),
                opacity=0.94,
                hovertemplate=f"{name}: {val}<extra></extra>",
            )
        )

    # Academics: subdivided inside ONE main wedge
    acad_revealed = acad_k in revealed

    for j, sub in enumerate(ACADEMIC_SUBS):
        val = clamp_int(lookup.get(sub, 0))
        if not acad_revealed:
            val = 0

        theta_center = normalize_deg(acad_edge_start - (j + 0.5) * w_mini)

        traces.append(
            go.Barpolar(
                r=[val],
                theta=[theta_center],
                width=[w_mini * 0.90],
                marker=dict(
                    color=COLOR_MAP.get(sub, "#999999"),
                    line=dict(color="rgba(255,255,255,0.94)", width=1.4),
                ),
                opacity=0.94,
                hovertemplate=f"Academics – {sub}: {val}<extra></extra>",
            )
        )

    return traces


# -----------------------------
# Client-side Stepper Figure (works in fullscreen modal)
# -----------------------------
def make_client_stepper_fig(initial_step: int) -> go.Figure:
    """
    Builds ALL steps as separate groups of traces, then uses a Plotly slider
    (method='update') to toggle which group's traces are visible.
    This works reliably in Streamlit's fullscreen chart modal.
    """
    n_main = len(MAIN_DOMAINS)

    # Build bar traces for each step
    per_step_traces: list[list] = []
    for step in range(n_main + 1):
        per_step_traces.append(build_traces(step))

    # Flatten bar traces
    flat_bars = []
    step_sizes = []
    for traces in per_step_traces:
        step_sizes.append(len(traces))
        flat_bars.extend(traces)

    fig = go.Figure(data=flat_bars)
    fig.update_layout(**common_layout(n_main))

    # Add labels ONCE at the end (always visible)
    add_labels(fig, [DISPLAY_LABELS.get(name, name) for name in MAIN_DOMAINS], n_main)
    add_academics_sub_labels(fig, n_main)

    total_bar_traces = len(flat_bars)
    label_trace_count = 2  # we add two Scatterpolar traces above

    # Precompute start indices for each step
    starts = []
    idx = 0
    for sz in step_sizes:
        starts.append(idx)
        idx += sz

    def visibility_for(step: int) -> list[bool]:
        vis = [False] * total_bar_traces
        start = starts[step]
        end = start + step_sizes[step]
        for i in range(start, end):
            vis[i] = True
        # labels always visible (last two traces)
        vis += [True] * label_trace_count
        return vis

    # Apply initial visibility
    initial_step = max(0, min(n_main, int(initial_step)))
    vis0 = visibility_for(initial_step)
    for i, v in enumerate(vis0):
        fig.data[i].visible = v

    # Slider labels
    step_labels = ["Start"] + [DISPLAY_LABELS.get(name, name) for name in MAIN_DOMAINS]

    slider_steps = []
    for step in range(n_main + 1):
        slider_steps.append(
            dict(
                method="update",
                args=[{"visible": visibility_for(step)}],
                label=step_labels[step],
            )
        )

    fig.update_layout(
        sliders=[
            dict(
                active=initial_step,
                currentvalue=dict(prefix="Reveal: ", font=dict(size=16)),
                pad=dict(t=40),
                steps=slider_steps,
            )
        ]
    )

    return fig


# -----------------------------
# Render (Streamlit Prev/Next + Fullscreen-safe Plotly slider)
# -----------------------------
st.subheader("Agency Profile")

n_main = len(MAIN_DOMAINS)

if "step" not in st.session_state:
    st.session_state.step = n_main

c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 2])

with c1:
    if st.button("⟵ Prev", use_container_width=True):
        st.session_state.step = max(0, st.session_state.step - 1)

with c2:
    if st.button("Next ⟶", use_container_width=True):
        st.session_state.step = min(n_main, st.session_state.step + 1)

with c3:
    if st.button("Reset", use_container_width=True):
        st.session_state.step = 0

with c4:
    if st.button("All", use_container_width=True):
        st.session_state.step = n_main

with c5:
    st.caption(f"Step: {st.session_state.step} / {n_main}")

# ONE chart element only (no duplicate-id errors). Big height for readability.
st.plotly_chart(
    make_client_stepper_fig(st.session_state.step),
    width="stretch",
    key="stepper_chart",
    config={
        "displayModeBar": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "agency-framework-profile",
            "height": 1400,
            "width": 1400,
            "scale": 2,
        },
    },
)

st.caption(
    "The complete outline represents the full set of capacities that can support "
    "agency. The colored areas reflect the capacities currently available to the child; "
    "areas with more room to grow help guide focused recommendations and support."
)
st.markdown("---")
st.caption("© Oren Boxer, Ph.D. All rights reserved.")
