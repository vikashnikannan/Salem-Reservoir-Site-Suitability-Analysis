"""Shared data loading, palette and styling for the Salem Reservoir Site Suitability dashboard."""
import base64
import inspect
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"

# ---- edit these two lines if the names need correcting --------------------------------
AUTHOR = "Vikashni K"
EVENT = "Centre for Water Resources Hackathon"
# ----------------------------------------------------------------------------------------

CLASS_NAMES = ["Very Low", "Low", "Moderate", "High", "Very High"]
CLASS_COLORS = ["#d7191c", "#fdae61", "#ffffbf", "#a6d96a", "#1a9641"]
GROUP_COLORS = {"Topography": "#8C6D46", "Hydrology": "#0B6E99", "Geology": "#7A5C99",
                "Soil": "#C98A2C", "Socio_Env": "#2E8B57"}
INK, WATER, SAND = "#14263A", "#0B6E99", "#F1F5F8"
# matplotlib RdYlGn at 0, .25, .5, .75, 1 (same colormap the export script uses for layers and RSI)
RAMP = ["#a50026", "#f98e52", "#feffbe", "#84ca66", "#006837"]

# Screening thresholds - COPIED from the SCREEN dictionary in the pipeline script.
# If you change them in the pipeline, change them here too.
SCREEN = {
    "Hydrological": {"catchment_area": 3.0, "streamflow": 3.0, "dependable_yield": 3.0, "runoff": 3.0},
    "Geological": {"lithology": 3.0, "foundation_perm": 3.0, "geomorphology": 2.5, "seismic": 2.0},
    "Engineering": {"valley_width": 3.5, "valley_depth": 3.0, "slope": 3.0, "relief": 3.0,
                    "settlement": 2.0, "roads": 2.0},
}

# Pipeline figures shown on the Outputs page: file -> (title, what it shows)
FIGURES = {
    "06_suitability_5class.png": ("Suitability classes with existing reservoirs",
                                  "Five presentation classes from the primary model; grey = hard-constraint exclusion."),
    "06_suitability_continuous.png": ("Continuous Reservoir Suitability Index",
                                      "The RSI before classification."),
    "06_topsis.png": ("TOPSIS closeness coefficient",
                      "Comparison model, unconstrained."),
    "02_constraint_mask.png": ("Hard-constraint mask", "1 = eligible, 0 = excluded."),
    "04_correlation_matrix.png": ("Correlation between model parameters",
                                  "Spearman correlation among the 31 selected factors."),
    "07_roc.png": ("ROC curves", "Existing reservoirs against spatially separated background points."),
    "08_jackknife_auc.png": ("Jackknife: AUC alone and without each parameter", ""),
    "08_jackknife_influence_vs_weight.png": ("Jackknife: influence against assigned weight", ""),
    "10_candidate_sites.png": ("Candidate dam sites", "Sites that passed and failed screening."),
}


# ---------------------------------------------------------------------------- loaders --
@st.cache_data
def csv(name: str) -> pd.DataFrame:
    p = DATA / name
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


@st.cache_data
def meta() -> dict:
    p = DATA / "meta.json"
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data
def boundary():
    p = DATA / "salem_boundary.geojson"
    return json.loads(p.read_text()) if p.exists() else None


@st.cache_data
def image_uri(name: str):
    p = DATA / name
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode() if p.exists() else None


@st.cache_data
def text(name: str) -> str:
    p = DATA / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def figure_path(name: str):
    p = DATA / "figures" / name
    return p if p.exists() else None


# ------------------------------------------------------------------------- helpers --
def stretch(fn, *args, **kw):
    """Full-width widgets on old and new Streamlit (use_container_width -> width='stretch')."""
    params = inspect.signature(fn).parameters
    if "use_container_width" in params:
        return fn(*args, use_container_width=True, **kw)
    return fn(*args, width="stretch", **kw)


def need(df, what: str) -> bool:
    if df is None or len(df) == 0:
        st.info(f"{what} was not found in ./data. Run export_dashboard_data.py first (see README).")
        return False
    return True


def bool_col(df: pd.DataFrame, cols) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().isin(["true", "1", "1.0"])
    return df


# --------------------------------------------------------------------------- styling --
def css():
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&family=Source+Serif+4:wght@600;700&display=swap');
html {{font-size:18px;}}
html, body, [class*="css"], .stMarkdown, .stDataFrame {{font-family:'Source Sans 3',sans-serif;}}
.stMarkdown p, .stMarkdown li {{font-size:1.05rem; line-height:1.55;}}
[data-testid="stSidebarNav"] a span {{font-size:1.05rem;}}
label, [data-testid="stWidgetLabel"] p {{font-size:1rem !important; font-weight:600;}}
.block-container {{padding-top:1.6rem; max-width:1320px;}}
[data-testid="stSidebar"] {{background:{INK};}}
[data-testid="stSidebar"] * {{color:#DCE6EF !important;}}
[data-testid="stSidebarNav"] a {{border-radius:6px; padding:.3rem .7rem;}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{background:#1F3E5E;}}
.pagehead {{border-bottom:2px solid {INK}; padding-bottom:.7rem; margin-bottom:1.3rem;}}
.pagehead h1 {{font-family:'Source Serif 4',serif; font-weight:700; font-size:2.4rem; color:{INK}; margin:0; padding:0;}}
.pagehead p {{color:#4A5B6C; margin:.35rem 0 0 0; max-width:900px; font-size:1.15rem;}}
.fig {{border-left:3px solid {WATER}; padding:.1rem 0 .1rem .8rem; margin-bottom:.4rem;}}
.fig .v {{font-family:'Source Serif 4',serif; font-size:2.2rem; font-weight:700; color:{INK}; line-height:1.1;}}
.fig .l {{font-size:1rem; color:#3B4C5D; font-weight:600;}}
.fig .s {{font-size:.9rem; color:#6B7B8A;}}
.tag {{display:inline-block; padding:.12rem .6rem; border-radius:4px; font-size:.95rem; font-weight:600; margin:.1rem .3rem .1rem 0;}}
.pass {{background:#E1F1E6; color:#1B6B3A;}} .fail {{background:#F8E1DE; color:#9C2A20;}} .na {{background:#ECEFF2; color:#5B6B7A;}}
.key {{display:inline-flex; align-items:center; margin:.2rem 1rem .2rem 0; font-size:1rem; color:#3B4C5D;}}
.key i {{display:inline-block; width:1.1rem; height:1.1rem; border-radius:2px; margin-right:.4rem; border:1px solid rgba(0,0,0,.25);}}
.note {{background:{SAND}; border-left:4px solid {WATER}; padding:.7rem 1rem; border-radius:4px; font-size:1.02rem; color:{INK};}}
.credit {{font-size:.95rem; color:#9FB2C4; line-height:1.4;}}
</style>""", unsafe_allow_html=True)


def header(title: str, sub: str):
    st.markdown(f'<div class="pagehead"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def figure(col, label: str, value: str, sub: str = ""):
    col.markdown(f'<div class="fig"><div class="v">{value}</div><div class="l">{label}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)


def tag(ok, label: str) -> str:
    if ok in (None, -1):
        return f'<span class="tag na">{label}: not assessed</span>'
    return f'<span class="tag {"pass" if bool(ok) else "fail"}">{label}: {"pass" if bool(ok) else "fail"}</span>'


def key(items) -> str:
    """items: list of (colour, label)"""
    return "".join(f'<span class="key"><i style="background:{c}"></i>{t}</span>' for c, t in items)


def note(md: str):
    st.markdown(f'<div class="note">{md}</div>', unsafe_allow_html=True)


def ramp_legend(low: str, high: str, title: str = ""):
    """Horizontal colour bar 1-5 for continuous / score rasters."""
    grad = ", ".join(RAMP)
    ticks = "".join(f'<span>{i}</span>' for i in range(1, 6))
    st.markdown(
        f'<div style="max-width:520px;margin:.3rem 0 .8rem 0;">'
        f'<div style="font-weight:600;margin-bottom:.25rem;">{title}</div>'
        f'<div style="height:1.1rem;border-radius:3px;border:1px solid rgba(0,0,0,.25);'
        f'background:linear-gradient(90deg,{grad});"></div>'
        f'<div style="display:flex;justify-content:space-between;font-size:.95rem;color:#3B4C5D;">{ticks}</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:.95rem;color:#3B4C5D;">'
        f'<span>{low}</span><span>{high}</span></div></div>', unsafe_allow_html=True)
