import pandas as pd
from EnergyPrediction import solar_pipeline_nasa

if __name__ == "__main__":
    # Site details (you can change these)
    lat, lon = 28.218114039861177, 77.28043557859039  # Example: Faridabad region
    timezone = "Asia/Kolkata"

    # Date range (inclusive)
    start_date = "20250401"  # YYYYMMDD
    end_date = "20250731"

    # PV system details
    panel_area_m2 = 2.0
    panel_efficiency = 0.20
    num_panels = 1
    Pdc0 = 82800  # W (or adjust to your installed DC capacity)

    # Run the pipeline
    results = solar_pipeline_nasa(
        lat=lat,
        lon=lon,
        start_date=start_date,
        end_date=end_date,
        timezone=timezone,
        panel_area_m2=panel_area_m2,
        panel_efficiency=panel_efficiency,
        num_panels=num_panels,
        Pdc0=Pdc0,
        tilt=20.0,
        azimuth=180.0,
        print_sun=False,
        print_hourly=False,
        print_daily=False,
        print_weekly=False,
        print_monthly=False,
    )

    # Extract hourly generation (convert from W to kW)
    hourly_df = results["hourly"][["P_dc"]].copy()
    # Convert W → kWh per hour (since each record is for 1 hour)
    hourly_df["Energy (kWh)"] = hourly_df["P_dc"] / 1000.0

    # Keep only relevant column
    hourly_df = hourly_df[["Energy (kWh)"]]

    # Ensure timestamps are localized to IST
    hourly_df.index = hourly_df.index.tz_convert(timezone)

    # Prepare clean timestamp column
    hourly_df = hourly_df.reset_index().rename(columns={"index": "Timestamp"})
    hourly_df["Timestamp"] = hourly_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # --- Save to CSV ---
    output_file = "WikaRcc_predicted.csv"
    hourly_df.to_csv(output_file, index=False)

    print(f"\n✅ Hourly energy generation (kWh) saved to '{output_file}'")
    print(f"   Total hours: {len(hourly_df)}")
    print(hourly_df.head(10))
