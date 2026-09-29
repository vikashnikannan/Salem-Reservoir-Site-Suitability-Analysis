"""
Salem Reservoir Site Suitability - Decision Support Dashboard
Run locally:  streamlit run app.py
Deploy:       https://share.streamlit.io  (main file = app.py)
The dashboard only reads the small files in ./data produced by export_dashboard_data.py.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import lib
from lib import CLASS_COLORS, CLASS_NAMES, GROUP_COLORS, INK, WATER, SCREEN, stretch

st.set_page_config(page_title="Salem Reservoir Suitability", layout="wide")
lib.css()

META = lib.meta()
SUM = META.get("summary", {})
CAND = lib.bool_col(lib.csv("candidate_sites.csv"), ["all_ok", "Hyd_ok", "Geo_ok", "Eng_ok"])
RES = lib.csv("reservoirs.csv")
LAYOUT = dict(margin=dict(l=10, r=10, t=45, b=10), font=dict(family="Source Sans 3, sans-serif", size=16, color=INK),
              plot_bgcolor="white", paper_bgcolor="white")


def plot(fig, **kw):
    stretch(st.plotly_chart, fig, **kw)


# ------------------------------------------------------------------------------ map --
STYLES = {"carto-positron": "Light", "open-street-map": "Streets", "carto-darkmatter": "Dark"}
NOTES = {"dist_protected": "Hard-constraint mask only (not weighted).",
         "dist_reserve_forest": "Hard-constraint mask only (not weighted).",
         "dist_eco_sensitive": "Hard-constraint mask only (not weighted).",
         "existing_tanks": "Kept out of the model because it is circular with the existing-reservoir validation."}


def build_map(base="class", show_res=True, cand_mode="Hide", center=None, zoom=8.4, sel=None, height=600,
              style="carto-positron", image=None, bounds=None):
    """Plotly map: raster image + boundary + point layers, with an on-map legend for the points."""
    if image is None:
        image = {"class": "suitability_class.png", "rsi": "suitability_rsi.png"}.get(base)
        bounds = META.get("bounds", {}).get(base)
    layers = []
    uri = lib.image_uri(image) if image else None
    if uri and bounds:
        w, s_, e, n = bounds
        layers.append(dict(sourcetype="image", source=uri, coordinates=[[w, n], [e, n], [e, s_], [w, s_]],
                           opacity=0.85, below="traces"))
    bd = lib.boundary()
    if bd:
        layers.append(dict(sourcetype="geojson", source=bd, type="line", color=INK, line=dict(width=2),
                           below="traces"))
    c = center or META.get("center", [78.2, 11.6])
    fig = go.Figure()
    # Plotly only creates the map when at least one map trace exists; this invisible point guarantees it.
    fig.add_trace(go.Scattermap(lon=[c[0]], lat=[c[1]], mode="markers", marker=dict(size=1, opacity=0),
                                showlegend=False, hoverinfo="skip"))
    if len(CAND) and cand_mode != "Hide":
        C = CAND.copy()
        C["tip"] = ("Site " + C.site_id.astype(str) + ", rank " + C["rank"].astype(str) + ", " + C.cls.astype(str)
                    + ", RSI " + C.score.round(2).astype(str))
        if sel is not None:
            fig.add_trace(go.Scattermap(lon=[sel["lon"]], lat=[sel["lat"]], mode="markers", name="Selected site",
                                        marker=dict(size=32, color="#FFB800", opacity=0.55), hoverinfo="skip"))
        if cand_mode == "Passed and failed":
            F = C[~C.all_ok]
            fig.add_trace(go.Scattermap(lon=F.lon, lat=F.lat, mode="markers", name="Candidate: failed screening",
                                        marker=dict(size=9, color="#6e6e6e"), text=F.tip, hoverinfo="text"))
        P = C[C.all_ok]
        fig.add_trace(go.Scattermap(lon=P.lon, lat=P.lat, mode="markers", name="Candidate: passed screening",
                                    marker=dict(size=13, color="#D62828"), text=P.tip, hoverinfo="text"))
    if show_res and len(RES):
        fig.add_trace(go.Scattermap(lon=RES.lon, lat=RES.lat, mode="markers", name="Existing reservoir",
                                    marker=dict(size=10, color="#1455DC"), text=["Existing reservoir"] * len(RES),
                                    hoverinfo="text"))
    fig.update_layout(map=dict(style=style, center=dict(lon=c[0], lat=c[1]), zoom=zoom, layers=layers),
                      margin=dict(l=0, r=0, t=0, b=0), height=height, paper_bgcolor="white", showlegend=True,
                      font=dict(family="Source Sans 3, sans-serif", size=16, color=INK),
                      legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,.92)", bordercolor="#9FB2C4",
                                  borderwidth=1, font=dict(size=15)))
    plot(fig, config={"scrollZoom": True})


def legend(base="class"):
    """Colour key for the raster shown under the map (point layers have their own legend on the map)."""
    if base == "class":
        st.markdown(lib.key(list(zip(CLASS_COLORS, CLASS_NAMES)) + [("#8a8a8a", "Excluded (hard constraint)")]),
                    unsafe_allow_html=True)
    elif base == "rsi":
        lib.ramp_legend("low RSI", "high RSI", "Reservoir Suitability Index (1-5)")


def no_data() -> bool:
    if not META:
        lib.header("Salem Reservoir Site Suitability", "No data found.")
        st.warning("The ./data folder is empty. Run `python export_dashboard_data.py --base <pipeline folder>` "
                   "on the machine that holds the pipeline output, then commit the ./data folder.")
        return True
    return False


# -------------------------------------------------------------------------- overview --
def overview():
    if no_data():
        return
    lib.header("Salem Reservoir Site Suitability",
               "GIS-based hierarchical AHP weighted overlay with hard constraints, candidate-site screening and "
               "validation against existing reservoirs. Salem district, Tamil Nadu.")
    area = SUM.get("area_km2", {})
    salem = SUM.get("salem_km2", 0)
    hv = area.get("High", 0) + area.get("Very High", 0)
    val = lib.csv("07_validation.csv")
    auc = val.set_index("model").AUC.max() if len(val) else None
    n_ok = int(CAND.all_ok.sum()) if len(CAND) else 0
    k = st.columns(6)
    res_m = SUM.get("resolution_m")
    lib.figure(k[0], "District area", f"{salem:,.0f} km²", f"analysed at {res_m:g} m" if res_m else "")
    lib.figure(k[1], "High and Very High", f"{hv:,.0f} km²", f"{hv / salem:.1%} of district" if salem else "")
    lib.figure(k[2], "Excluded", f"{area.get('Excluded', 0):,.0f} km²", "hard constraints")
    lib.figure(k[3], "Candidate sites", f"{len(CAND):,}", f"{n_ok} pass all screening")
    lib.figure(k[4], "Existing reservoirs", f"{len(RES):,}", "used for validation")
    lib.figure(k[5], "Best model AUC", f"{auc:.3f}" if auc is not None else "n/a", "ROC-AUC, existing reservoirs")
    st.write("")
    a, b = st.columns([3, 2])
    with a:
        st.subheader("Suitability map")
        build_map(cand_mode="Passed only", height=560)
        legend()
    with b:
        st.subheader("Area by class")
        if area:
            names = ["Excluded"] + CLASS_NAMES
            d = pd.DataFrame({"class": names, "km2": [area.get(n, 0) for n in names]})
            d["share"] = d.km2 / salem * 100 if salem else 0
            fig = px.bar(d, y="class", x="km2", orientation="h", color="class",
                         color_discrete_map={**dict(zip(CLASS_NAMES, CLASS_COLORS)), "Excluded": "#8a8a8a"},
                         category_orders={"class": names[::-1]}, text=d.share.map(lambda v: f"{v:.1f}%"))
            fig.update_traces(marker_line_color="rgba(0,0,0,.35)", marker_line_width=1, textposition="outside")
            fig.update_layout(**LAYOUT, height=310, showlegend=False, xaxis_title="Area (km²)", yaxis_title="")
            plot(fig)
    lib.note("<b>Preliminary screening only.</b> The results show where detailed hydrological, geological, "
             "geophysical, seismic and foundation investigation is worth doing. They do not replace it.")


# ------------------------------------------------------------------------------- map --
def map_page():
    if no_data():
        return
    lib.header("Suitability Map", "Five-class suitability, the continuous Reservoir Suitability Index (RSI) and "
                                  "existing reservoirs. Scroll to zoom, drag to pan.")
    c1, c2, c3 = st.columns([3, 2, 1])
    base = c1.radio("Base layer", ["class", "rsi", "none"], horizontal=True,
                    format_func=lambda x: {"class": "5 classes", "rsi": "Continuous RSI", "none": "Basemap only"}[x])
    style = c2.selectbox("Basemap", list(STYLES), format_func=STYLES.get)
    res = c3.toggle("Existing reservoirs", True)
    legend(base)
    build_map(base, res, "Hide", height=720, style=style)
    if base == "rsi" and SUM.get("rsi_range"):
        lo, hi = SUM["rsi_range"]
        st.caption(f"RSI colour stretch: 2nd to 98th percentile, {lo:.2f} to {hi:.2f} on the 1-5 scale.")


# --------------------------------------------------------------------------- weights --
def model_page():
    if no_data():
        return
    lib.header("Model and Factor Weights", "Hierarchical AHP: criteria groups, then parameters within each group. "
                                           "Final weight = group weight x local weight.")
    W = lib.csv("05_ahp_weights.csv")
    if not lib.need(W, "05_ahp_weights.csv"):
        return
    a, b = st.columns(2)
    with a:
        g = W.groupby("group").final_w.sum().reset_index().sort_values("final_w")
        fig = px.bar(g, x="final_w", y="group", orientation="h", color="group", color_discrete_map=GROUP_COLORS,
                     title="Weight of each criteria group", text=g.final_w.map(lambda v: f"{v:.1%}"))
        fig.update_traces(textposition="outside")
        fig.update_layout(**LAYOUT, height=380, showlegend=False, xaxis_title="Share of total weight", yaxis_title="")
        plot(fig)
    with b:
        fig = px.treemap(W, path=["group", "key"], values="final_w", color="group",
                         color_discrete_map=GROUP_COLORS, title="Group and parameter hierarchy")
        fig.update_layout(**LAYOUT, height=380)
        plot(fig)
    top = W.sort_values("final_w").tail(20)
    fig = px.bar(top, x="final_w", y="key", color="group", orientation="h", color_discrete_map=GROUP_COLORS,
                 title="Top 20 parameters by final weight")
    fig.update_layout(**LAYOUT, height=580, xaxis_title="Final weight", yaxis_title="")
    plot(fig)
    st.subheader("Consistency of the pairwise judgements")
    cr = W.groupby("group").group_CR.first().reset_index().rename(columns={"group_CR": "CR"})
    cr["status"] = cr.CR.apply(lambda x: "acceptable (< 0.10)" if x < 0.10 else "revise (> 0.10)")
    stretch(st.dataframe, cr.round(3), hide_index=True)
    lib.note("The pairwise judgements in the pipeline are generated from importance scores set in the script. "
             "Replace them with literature or expert values before treating the weights as final.")
    reg = lib.csv("01_parameter_register.csv")
    if len(reg):
        with st.expander("Full parameter register and how each layer was standardised"):
            stretch(st.dataframe, reg.drop(columns=[c for c in ["group_CR"] if c in reg]).round(4), hide_index=True)
    st.download_button("Download weights (CSV)", W.to_csv(index=False), "salem_ahp_weights.csv", "text/csv")


# ------------------------------------------------------------------------- validation --
def validation_page():
    if no_data():
        return
    lib.header("Validation and Sensitivity", "How well does the model recover existing reservoirs, and how robust is "
                                             "it to the weights and to individual parameters?")
    V = lib.csv("07_validation.csv")
    if not lib.need(V, "07_validation.csv"):
        return
    cols = st.columns(len(V))
    for c, (_, r) in zip(cols, V.iterrows()):
        lib.figure(c, f"{r.model}: ROC-AUC", f"{r.AUC:.3f}",
                   f"{int(r.reservoirs)} reservoirs, {int(r.background)} background points")
    st.write("")
    with st.expander("All validation statistics"):
        stretch(st.dataframe, V.round(3).set_index("model").T)
    a, b = st.columns(2)
    FR = lib.csv("07_frequency_ratio.csv")
    if len(FR):
        with a:
            fig = px.bar(FR, x="cls", y="frequency_ratio", color="cls",
                         color_discrete_map=dict(zip(CLASS_NAMES, CLASS_COLORS)), category_orders={"cls": CLASS_NAMES},
                         title="Frequency ratio by class (above 1 = over-represented)")
            fig.update_traces(marker_line_color="rgba(0,0,0,.35)", marker_line_width=1)
            fig.add_hline(y=1, line_dash="dash", line_color="grey")
            fig.update_layout(**LAYOUT, showlegend=False, height=360, xaxis_title="", yaxis_title="Frequency ratio")
            plot(fig)
    B = lib.csv("07_auc_vs_background_buffer.csv")
    if len(B):
        with b:
            fig = px.line(B, x="background_buffer_m", y="AUC", markers=True, title="AUC against background separation")
            fig.update_traces(line_color=WATER)
            fig.update_layout(**LAYOUT, height=360, yaxis_range=[0.4, 1],
                              xaxis_title="Minimum distance of background points from reservoirs (m)")
            plot(fig)
    p = lib.figure_path("07_roc.png")
    if p:
        st.subheader("ROC curves")
        st.image(str(p), width=520)
    CM = lib.csv("06_class_method_comparison.csv")
    if len(CM):
        st.subheader("Effect of the classification method on class areas")
        mdl = st.radio("Model", CM.model.unique().tolist(), horizontal=True)
        d = CM[CM.model == mdl]
        fig = px.bar(d, x="cls", y="area_km2", color="method", barmode="group", category_orders={"cls": CLASS_NAMES},
                     color_discrete_sequence=[INK, WATER, "#C98A2C"])
        fig.update_layout(**LAYOUT, height=360, xaxis_title="", yaxis_title="Area (km²)")
        plot(fig)
        st.caption("Classes are presentation classes, not engineering thresholds. The bars show how much the "
                   "class areas change with the method.")
    J = lib.csv("08_jackknife.csv")
    if len(J):
        st.subheader("Jackknife: which parameters matter most?")
        J = J.sort_values("influence")
        fig = go.Figure()
        fig.add_bar(y=J.key, x=J.auc_alone, orientation="h", name="Only this parameter", marker_color="#2a9d8f")
        fig.add_bar(y=J.key, x=J.auc_without, orientation="h", name="Without this parameter", marker_color="#e76f51")
        fig.update_layout(**LAYOUT, barmode="group", height=max(520, 42 * len(J)), xaxis_range=[0.4, 1],
                          xaxis_title="ROC-AUC", legend=dict(orientation="h", y=1.03))
        plot(fig)
        fig = px.scatter(J, x="weight", y="influence", color="group", text="key", color_discrete_map=GROUP_COLORS,
                         title="Influence on the map against assigned weight")
        fig.update_traces(textposition="top center", marker_size=10)
        fig.update_layout(**LAYOUT, height=500, yaxis_title="Map change when removed (1 - Spearman rho)",
                          xaxis_title="Final AHP weight")
        plot(fig)
    S = lib.csv("08_group_sensitivity.csv")
    if len(S):
        st.subheader("Group-weight sensitivity (plus and minus 10 % and 20 %)")
        m = S.melt("scenario", ["spearman", "top20_jaccard"], var_name="metric")
        fig = px.bar(m, x="scenario", y="value", color="metric", barmode="group", color_discrete_sequence=[INK, WATER])
        fig.update_layout(**LAYOUT, height=400, yaxis_range=[0, 1.02], xaxis_tickangle=-45, xaxis_title="")
        plot(fig)
    st.caption("Existing reservoirs are historical decisions, not perfect ground truth. AUC is only indicative when "
               "few reservoir pixels are available.")


# ---------------------------------------------------------------------- raster layers --
def layers_page():
    if no_data():
        return
    lib.header("Raster Layers", "Every standardised input raster (scores 1-5) shown on the map with its legend.")
    L = META.get("layers", {})
    if not L:
        st.info("No layer images in ./data/layers. Re-run export_dashboard_data.py (see README).")
        return
    W, REG = lib.csv("05_ahp_weights.csv"), lib.csv("01_parameter_register.csv")
    grp = dict(zip(W.key, W.group)) if len(W) else {}
    wt = dict(zip(W.key, W.final_w)) if len(W) else {}
    groups = ["All"] + sorted({grp.get(k, "Not in model") for k in L})
    c1, c2, c3 = st.columns([1, 2, 1])
    g = c1.selectbox("Criteria group", groups)
    keys = [k for k in L if g == "All" or grp.get(k, "Not in model") == g]
    k = c2.selectbox("Layer", keys, format_func=lambda x: x.replace("_", " "))
    style = c3.selectbox("Basemap", list(STYLES), format_func=STYLES.get)
    left, right = st.columns([3, 1])
    with left:
        build_map(show_res=False, height=700, style=style, image=f"layers/{k}.png", bounds=L[k]["bounds"])
    with right:
        st.subheader(k.replace("_", " "))
        st.markdown(f"**Group:** {grp.get(k, 'not in the 31-factor model')}")
        if k in wt:
            st.markdown(f"**Final AHP weight:** {wt[k]:.3f}")
        if len(REG) and "key" in REG.columns and k in set(REG.key):
            r = REG[REG.key == k].iloc[0]
            for col, label in [("type", "Type"), ("direction", "Direction"), ("standardisation", "Standardisation")]:
                if col in r.index and pd.notna(r[col]):
                    st.markdown(f"**{label}:** {r[col]}")
        if k in NOTES:
            lib.note(NOTES[k])
        lib.ramp_legend("1 = least suitable", "5 = most suitable", "Standardised score")
        st.caption("Existing reservoirs are not drawn here so the raster stays readable.")


# --------------------------------------------------------------------------- outputs --
def outputs_page():
    if no_data():
        return
    lib.header("Pipeline Outputs", "The maps and charts written by the analysis script, shown as produced.")
    found = [(f, t, d) for f, (t, d) in lib.FIGURES.items() if lib.figure_path(f)]
    if not found:
        st.info("No figures in ./data/figures. Re-run export_dashboard_data.py to copy them.")
        return
    for i in range(0, len(found), 2):
        cs = st.columns(2)
        for c, (f, t, d) in zip(cs, found[i:i + 2]):
            with c:
                st.markdown(f"**{t}**")
                if d:
                    st.caption(d)
                stretch(st.image, str(lib.figure_path(f)))
    st.subheader("Downloads")
    for f, label in [("Reservoir_Suitability_5class.tif", "Suitability classes (GeoTIFF, UTM 44N)"),
                     ("Reservoir_Suitability_continuous.tif", "Continuous RSI (GeoTIFF, UTM 44N)")]:
        p = lib.DATA / "rasters" / f
        if p.exists():
            st.download_button(label, p.read_bytes(), f, "image/tiff", key=f"dl_{f}")
    for f in ["candidate_sites.csv", "05_ahp_weights.csv", "07_validation.csv", "08_jackknife.csv"]:
        df = lib.csv(f)
        if len(df):
            st.download_button(f, df.to_csv(index=False), f, "text/csv", key=f"dl_{f}")


# ------------------------------------------------------------------------- methodology --
def method_page():
    lib.header("Methodology and Limitations", "From raw rasters to a screened shortlist of candidate sites.")
    st.markdown("""
1. **Audit.** Every raster is checked for value range, declared NoData and zeros.
2. **Standardise.** Layers are resampled to one common grid, clipped to Salem and scaled to 1-5. Duplicates are removed.
3. **Hard constraints.** Protected areas, reserve forest, eco-sensitive zones, settlements and steep slopes are excluded, not weighted.
4. **Redundancy.** Spearman and Pearson correlation, VIF and PCA are used to select 31 primary factors.
5. **AHP.** Five criteria groups, then parameters within each group; consistency ratios are reported.
6. **Overlay.** AHP weighted linear combination (primary) with TOPSIS as a comparison gives the RSI and five classes.
7. **Validation.** Existing reservoirs against spatially separated background points: ROC-AUC and frequency ratio.
8. **Sensitivity.** Jackknife, group weights changed by 10 % and 20 %, and candidate rank stability.
9. **Candidates.** High and Very High pixels on the drainage network, existing reservoirs excluded, 1 km minimum spacing.
10. **Screening.** Hydrological, geological and engineering checks, plus DEM storage and inundation checks when a DEM is supplied.
""")
    st.subheader("Screening thresholds used")
    rows = [dict(domain=d, factor=k, minimum_score=t) for d, thr in SCREEN.items() for k, t in thr.items()]
    stretch(st.dataframe, pd.DataFrame(rows), hide_index=True)
    st.caption("Thresholds are documented assumptions in the pipeline script, not standards.")
    st.subheader("Limitations")
    st.markdown("""
- This is pre-feasibility screening. It does not replace hydrological (design flood), geological, geophysical, seismic or foundation investigation.
- Foundation permeability is a regional proxy derived from lithology. No structure or lineament layers were available.
- The AHP judgements come from importance scores and should be replaced with literature or expert values.
- Classes are presentation classes, not engineering thresholds.
- Existing reservoirs are reference locations from historical decisions, not perfect ground truth.
""")
    log = lib.text("run_log.txt")
    if log:
        with st.expander("Pipeline run log"):
            st.code(log, language=None)


# ---------------------------------------------------------------------------- navigation --
pages = [st.Page(overview, title="Overview", default=True),
         st.Page(map_page, title="Suitability Map", url_path="map"),
         st.Page(layers_page, title="Raster Layers", url_path="layers"),
         st.Page(model_page, title="Model and Weights", url_path="weights"),
         st.Page(validation_page, title="Validation", url_path="validation"),
         st.Page(outputs_page, title="Pipeline Outputs", url_path="outputs"),
         st.Page(method_page, title="Methodology", url_path="method")]
st.sidebar.markdown("### Salem Reservoir Suitability")
st.sidebar.caption("Preliminary site-suitability screening")
st.navigation(pages).run()
st.sidebar.markdown(f'<div class="credit">{lib.AUTHOR}<br>{lib.EVENT}</div>', unsafe_allow_html=True)
