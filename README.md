# Solar PV Energy Prediction & Error Analysis

This project provides an end-to-end workflow to:

1. Predict **solar DC energy** using hourly weather data from the **NASA POWER API**.
2. Compare those predictions with **actual plant data** in a notebook with error analysis and interactive plots.

---

## Project Structure

```text
.
├── Energy_prediction.py
│   └── solar_pipeline_nasa()   # Main prediction pipeline using NASA POWER
│
└── alpha_prediction and error analysis.ipynb
    ├── Reads Actual vs Predicted Excel
    ├── Computes daily/weekly aggregates & errors
    └── Generates interactive Plotly plots + HTML reports
````

---

## Setup

### Python

* Python 3.9+ recommended.

### Install Dependencies

```bash
pip install \
  numpy \
  pandas \
  requests \
  pytz \
  plotly \
  openpyxl \
  statsmodels
```

Optional (better irradiance & solar position):

```bash
pip install pvlib
```

For Jupyter:

```bash
pip install notebook  # or jupyterlab
```

---

## 1. Generating Predictions (`Energy_prediction.py`)

The script uses `solar_pipeline_nasa()` to:

* Fetch hourly GHI, DNI, temperature, wind from **NASA POWER**.
* Compute **solar position** and **plane-of-array (POA) irradiance**.
* Apply a simple **IAM** and **NOCT-based cell temperature** model.
* Compute **DC power** and aggregate to daily/weekly/monthly/annual kWh.

### Example Usage (as a Library)

```python
from Energy_prediction import solar_pipeline_nasa

results = solar_pipeline_nasa(
    lat=28.2181,
    lon=77.2804,
    start_date="20250901",       # 'YYYYMMDD'
    end_date="20250905",         # 'YYYYMMDD' (inclusive)
    timezone="Asia/Kolkata",

    # Either give Pdc0 directly:
    Pdc0=370350,                 # W (rated DC power at STC)

    # OR (if Pdc0 is None) compute it from panel geometry:
    # panel_area_m2=2.0,
    # panel_efficiency=0.20,
    # num_panels=1,

    tilt=20.0,                   # degrees (panel tilt)
    azimuth=180.0,               # degrees (180 = south)
    albedo=0.2,
    INOCT=45.0,                  # NOCT (°C)
    gamma=-0.004144,             # temp coeff (1/°C)

    # Optional console outputs
    print_sun=False,
    print_hourly=False,
    print_daily=False,
    print_weekly=True,
    print_monthly=True,
)

hourly = results["hourly"]       # DataFrame with GHI, DNI, POA, T_cell, P_dc, etc.
daily_kwh = results["daily_kwh"] # Series: daily energy (kWh)

hourly.to_csv("predictions_hourly.csv")
daily_kwh.to_csv("predictions_daily_kwh.csv")
```

### Function Signature (Key Arguments)

```python
solar_pipeline_nasa(
    lat, lon,
    start_date, end_date,        # 'YYYYMMDD' strings
    timezone="UTC",
    panel_area_m2=None,
    panel_efficiency=None,
    num_panels=None,
    Pdc0=None,                   # use this OR the three above
    tilt=20.0,
    azimuth=180.0,
    albedo=0.2,
    INOCT=45.0,
    gamma=-0.004144,
    print_sun=False,
    print_hourly=False,
    print_daily=False,
    print_weekly=False,
    print_monthly=False,
)
```

**Outputs (`dict`):**

* `hourly`      – `DataFrame` indexed by timestamp, includes `P_dc`.
* `daily_kwh`   – `Series` (kWh/day).
* `weekly_kwh`  – `Series` (kWh/week).
* `monthly_kwh` – `Series` (kWh/month).
* `annual_kwh`  – `Series` (kWh/year).

You can run the script directly as well:

```bash
python Energy_prediction.py
```

(The `__main__` block contains an example configuration.)

---

## 2. Error Analysis Notebook

`alpha_prediction and error analysis.ipynb` is used to:

* Combine **actual** plant data with **predicted** energy.
* Compute **daily/weekly errors** (signed, absolute, percentage).
* Generate **interactive Plotly plots**.
* Export **HTML reports**.

### Expected Input Excel

The notebook expects an Excel file (e.g. `alpha_prediction_metal.xlsx`) with at least:

* `Time`      – timestamp
* `Actual`    – actual energy (e.g. kWh)
* `Predicted` – predicted energy (e.g. kWh)

You may also have extra columns for different models (e.g. `Pred_L1`, `Pred_L3`).

Make sure these names match the variables you set at the top of the notebook:

```python
time_col   = "Time"
actual_col = "Actual"
pred_col   = "Predicted"  # or "Pred_L1", etc.
excel_path = "alpha_prediction_metal.xlsx"
sheet_name = 0            # or the sheet name
```

### What the Notebook Does

1. **Load & Clean**

   * Reads Excel via `pandas.read_excel`.
   * Parses `Time` as datetime, sorts, sets it as index.

2. **Aggregations**

   * Uses a helper like `daily_weekly_aggregates(...)` to:

     * Resample to daily / weekly totals.
     * Compute:

       * Error = `Predicted − Actual`
       * Absolute error
       * Percentage error

3. **Interactive Plots**

   * Daily & weekly:

     * Actual vs Predicted
     * Error and %Error trends
   * Plots are created using Plotly and shown inline.

4. **HTML Exports**

   * Individual HTML files for each plot.
   * Combined dashboards for all L1 or all L3 plots
     (e.g. `combined_L1_plots.html`, `combined_L3_plots.html`).

### How to Run the Notebook

1. Start Jupyter:

   ```bash
   jupyter notebook
   # or
   jupyter lab
   ```

2. Open `alpha_prediction and error analysis.ipynb`.

3. Update:

   * `excel_path`
   * `time_col`, `actual_col`, `pred_col`
   * Output folder for HTML plots (if needed).

4. Run all cells:

   * Plots will appear inline.
   * HTML files will be saved in the configured directory (e.g. `plots/`).

---

## 3. Typical Workflow

1. **Predict Energy**

   * Configure your site and system in `Energy_prediction.py`.
   * Run `solar_pipeline_nasa()` to generate hourly/daily predictions.
   * Save predictions (CSV/Excel).

2. **Prepare Actual vs Predicted File**

   * Merge actual plant data (meter logs) with model predictions.
   * Ensure an Excel file with `Time`, `Actual`, `Predicted` (and extra columns for L1/L3, etc.).

3. **Run Error Analysis**

   * Open the notebook.
   * Point it to your Excel file and column names.
   * Run cells to:

     * See daily/weekly comparison of Actual vs Predicted.
     * Inspect error trends and distributions.
     * Export interactive HTML reports for sharing.

```