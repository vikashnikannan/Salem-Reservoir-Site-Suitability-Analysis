# Salem Reservoir Site Suitability - Decision Support Dashboard

Preliminary reservoir / dam site suitability screening for Salem district, Tamil Nadu.
GIS-based hierarchical AHP weighted overlay, hard constraints, candidate-site screening and validation
against existing reservoirs.

Author: Vikashni K - Centre for Water Resources Hackathon

## What is in this repository

| File | Purpose |
|---|---|
| `app.py`, `lib.py` | Streamlit dashboard |
| `export_dashboard_data.py` | Converts the pipeline output into small web files in `data/` |
| `data/` | Exported results read by the dashboard (commit this folder) |
| `requirements.txt` | Dashboard dependencies (streamlit, pandas, numpy, plotly) |
| `requirements_export.txt` | Extra dependencies for the export step only |

The dashboard never reads GeoTIFFs or shapefiles. Raw rasters and shapefiles stay on your machine.

## Step 1 - export the results (once, after the pipeline has run)

    pip install -r requirements_export.txt
    python export_dashboard_data.py --base "D:/internship/cwr- hacathon/final"

`--base` is the pipeline BASE folder (the one that contains `output/` and `shapefile/`).
This writes `data/` next to the script.

## Step 2 - run the dashboard locally

    pip install -r requirements.txt
    python -m streamlit run app.py

## Step 3 - push to GitHub

    git clone https://github.com/vikashnikannan/Salem-Reservoir-Site-Suitability-Analysis.git
    cd Salem-Reservoir-Site-Suitability-Analysis
    # copy every file of this folder in (including .streamlit/ and data/)
    git add .
    git commit -m "Add Streamlit decision-support dashboard"
    git push origin main

If your default branch is not `main`, use its name. If the repository already contains files with the same
names, review the differences before overwriting.

## Step 4 - deploy (optional)

1. Go to https://share.streamlit.io and sign in with GitHub.
2. Choose the repository, branch `main`, main file `app.py`.
3. Deploy.

## Troubleshooting (Windows)

- `streamlit` is not recognized: use `python -m streamlit run app.py`.
- `proj.db contains DATABASE.LAYOUT.VERSION.MINOR ...` during export: a PostgreSQL/PostGIS install has set
  `PROJ_LIB` or `PROJ_DATA`. The export script now ignores them. To clear them for the session:
  `$env:PROJ_LIB=$null; $env:PROJ_DATA=$null`
- `Ignoring invalid distribution ~yproj`: a broken leftover from an interrupted pyproj install. Delete the folder
  named `~yproj...` inside your Python `site-packages`, then run `pip install --force-reinstall pyproj`.

## Notes

- Screening thresholds on the Candidate Sites and Methodology pages are copied from the `SCREEN` dictionary in the
  pipeline script (`lib.py`). Keep them in sync if you change them.
- Every number shown comes from the exported files. Nothing is typed in by hand.
- The result is a pre-feasibility screening. It does not replace hydrological, geological, geophysical, seismic
  and foundation investigation.
