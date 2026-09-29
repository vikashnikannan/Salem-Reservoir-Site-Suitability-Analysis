"""
Convert the OUTPUT of the Salem suitability pipeline into small web-friendly files in ./data
(the dashboard never reads GeoTIFFs or shapefiles directly).

Run once after the pipeline, on the machine that has the output folder:
    python export_dashboard_data.py --base "D:/internship/cwr- hacathon/final"

--base is the pipeline BASE folder (it contains output/ and shapefile/).
Files are written to ./data next to this script unless --out is given.
"""
import os

# A PostgreSQL/PostGIS install can leave PROJ_LIB / PROJ_DATA pointing at an older proj.db, which breaks
# rasterio and pyproj. Removing them lets each library use its own bundled data. Must run BEFORE the imports below.
for _v in ("PROJ_LIB", "PROJ_DATA"):
    os.environ.pop(_v, None)

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.transform import array_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject
import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
from matplotlib import colormaps

CLASS_RGB = [(215, 25, 28), (253, 174, 97), (255, 255, 191), (166, 217, 106), (26, 150, 65)]
TABLES = ["05_ahp_weights.csv", "01_parameter_register.csv", "07_validation.csv", "07_frequency_ratio.csv",
          "07_auc_vs_background_buffer.csv", "08_jackknife.csv", "08_group_sensitivity.csv",
          "06_class_method_comparison.csv"]
FIGURES = ["06_suitability_5class.png", "06_suitability_continuous.png", "06_topsis.png", "02_constraint_mask.png",
           "04_correlation_matrix.png", "07_roc.png", "08_jackknife_auc.png",
           "08_jackknife_influence_vs_weight.png", "10_candidate_sites.png"]
CLASS_LABELS = ["Excluded", "Very Low", "Low", "Moderate", "High", "Very High"]


def warp4326(tif, resampling, max_px=1800):
    """Reproject a raster to EPSG:4326, limited to max_px on the long side. Returns array and [W, S, E, N]."""
    with rasterio.open(tif) as src:
        args = (src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
        t, w, h = calculate_default_transform(*args)
        f = max_px / max(w, h)
        if f < 1:
            t, w, h = calculate_default_transform(*args, dst_width=int(w * f), dst_height=int(h * f))
        dst = np.full((h, w), np.nan, "float32")
        reproject(rasterio.band(src, 1), dst, src_transform=src.transform, src_crs=src.crs,
                  src_nodata=src.nodata, dst_transform=t, dst_crs="EPSG:4326", dst_nodata=np.nan,
                  resampling=resampling)
    return dst, list(array_bounds(h, w, t))


def export_layers(o, out, meta):
    """Every standardised 1-5 raster -> small coloured PNG (RdYlGn, same as the RSI) for the Raster Layers page."""
    d = o / "rasters" / "standardized"
    (out / "layers").mkdir(parents=True, exist_ok=True)
    layers = {}
    for tif in sorted(d.glob("*.tif")):
        arr, b = warp4326(tif, Resampling.nearest, max_px=900)
        rgba = (colormaps["RdYlGn"](np.clip((arr - 1) / 4.0, 0, 1)) * 255).astype("uint8")
        rgba[..., 3] = np.where(np.isfinite(arr), 215, 0)
        mpimg.imsave(out / "layers" / f"{tif.stem}.png", rgba)
        layers[tif.stem] = {"bounds": b}
    if not layers:
        print("no standardised rasters found in", d)
    meta["layers"] = layers
    print(f"exported {len(layers)} layer images")


def copy_geotiffs(o, out):
    """Small GeoTIFFs offered as downloads (pipeline CRS and resolution)."""
    (out / "rasters").mkdir(parents=True, exist_ok=True)
    for f in ["Reservoir_Suitability_5class.tif", "Reservoir_Suitability_continuous.tif"]:
        src = o / "rasters" / f
        if src.exists():
            mb = src.stat().st_size / 1e6
            if mb > 40:
                print(f"skipped {f}: {mb:.0f} MB is too large to commit to GitHub comfortably")
                continue
            shutil.copy(src, out / "rasters" / f)
            print(f"copied {f} ({mb:.1f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="pipeline BASE folder (contains output/ and shapefile/)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "data"))
    a = ap.parse_args()
    base, out = Path(a.base), Path(a.out)
    o = base / "output"
    if not o.exists():
        raise SystemExit(f"Not found: {o}. Check --base.")
    (out / "figures").mkdir(parents=True, exist_ok=True)
    meta = {"bounds": {}, "summary": {}, "generated": date.today().isoformat()}

    # 1. class raster -> coloured PNG + area statistics
    cls_tif = o / "rasters" / "Reservoir_Suitability_5class.tif"
    arr, b = warp4326(cls_tif, Resampling.nearest)
    rgba = np.zeros(arr.shape + (4,), "uint8")
    rgba[arr == 0] = (90, 90, 90, 110)
    for i, rgb in enumerate(CLASS_RGB, 1):
        rgba[arr == i] = (*rgb, 205)
    mpimg.imsave(out / "suitability_class.png", rgba)
    meta["bounds"]["class"] = b
    with rasterio.open(cls_tif) as src:
        raw = src.read(1)
        px_km2 = abs(src.res[0] * src.res[1]) / 1e6
        meta["summary"]["resolution_m"] = float(abs(src.res[0]))
    cnt = np.bincount(raw[raw != 255].ravel(), minlength=6)[:6]
    meta["summary"]["area_km2"] = {n: float(c * px_km2) for n, c in zip(CLASS_LABELS, cnt)}
    meta["summary"]["salem_km2"] = float(cnt.sum() * px_km2)

    # 2. continuous RSI -> PNG
    rsi, b2 = warp4326(o / "rasters" / "Reservoir_Suitability_continuous.tif", Resampling.bilinear)
    lo, hi = np.nanpercentile(rsi, [2, 98])
    img = (colormaps["RdYlGn"](np.clip((rsi - lo) / (hi - lo), 0, 1)) * 255).astype("uint8")
    img[..., 3] = np.where(np.isfinite(rsi), 205, 0)
    mpimg.imsave(out / "suitability_rsi.png", img)
    meta["bounds"]["rsi"] = b2
    meta["summary"]["rsi_range"] = [float(lo), float(hi)]

    # 3. vectors
    bnd = gpd.read_file(base / "shapefile" / "salem_projected.shp")
    crs = bnd.crs
    bw = bnd.to_crs(4326)
    bw["geometry"] = bw.geometry.simplify(0.0005)
    bw[["geometry"]].to_file(out / "salem_boundary.geojson", driver="GeoJSON")
    minx, miny, maxx, maxy = bw.total_bounds
    meta["center"] = [float((minx + maxx) / 2), float((miny + maxy) / 2)]

    res = gpd.read_file(o / "vectors" / "Reservoirs_Salem.shp").to_crs(4326)
    pts = res.geometry.apply(lambda g: g if g.geom_type == "Point" else g.representative_point())
    keep = [c for c in res.columns if c != "geometry"][:3]
    R = pd.DataFrame(res[keep]).assign(lon=pts.x.values, lat=pts.y.values)
    R.to_csv(out / "reservoirs.csv", index=False)

    # 4. candidate sites (x, y are in the pipeline CRS -> lon/lat)
    D = pd.read_csv(o / "tables" / "10_candidate_sites_screened.csv")
    g = gpd.GeoDataFrame(D, geometry=gpd.points_from_xy(D.x, D.y), crs=crs).to_crs(4326)
    D["lon"], D["lat"] = g.geometry.x.values, g.geometry.y.values
    D.to_csv(out / "candidate_sites.csv", index=False)

    # 5. tables, figures, run log (copied unchanged)
    for t in TABLES:
        if (o / "tables" / t).exists():
            shutil.copy(o / "tables" / t, out / t)
        else:
            print("missing (skipped):", t)
    for f in FIGURES:
        if (o / "figures" / f).exists():
            shutil.copy(o / "figures" / f, out / "figures" / f)
        else:
            print("missing figure (skipped):", f)
    if (o / "run_log.txt").exists():
        shutil.copy(o / "run_log.txt", out / "run_log.txt")
    export_layers(o, out, meta)
    copy_geotiffs(o, out)
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print("Done ->", out)


if __name__ == "__main__":
    main()
