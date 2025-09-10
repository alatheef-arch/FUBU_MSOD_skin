# fubu_skin/callbacks.py
"""Defines callbacks for the Skin component."""
from io import StringIO
import pandas as pd
from dash import callback
from dash.dependencies import Input, Output

from data_processing.data_transformer import generate_merged_zone_styles, generate_zone_tooltips

STRINGER_PITCH_COLUMN_ID = "Stringer Pitch (mm)"

@callback(
    [
        Output("skin-tab-final-zone-grid", "data", allow_duplicate=True),
        Output("skin-tab-final-zone-grid", "columns", allow_duplicate=True),
        Output("skin-tab-final-zone-grid", "style_data_conditional", allow_duplicate=True),
        Output("skin-tab-final-zone-grid", "tooltip_data", allow_duplicate=True),
    ],
    [Input("main-data-store", "data"), Input("custom-panels-store", "data")],
    prevent_initial_call=True
)
def update_skin_final_zone_grid(main_data_json, stored_panels):
    """Updates the Final Zone Grid on the Skin tab."""
    if not main_data_json:
        return [], [], [], []

    df_raw = pd.read_json(StringIO(main_data_json), orient="split")
    
    # Correctly pivot the data while preserving row order
    all_stringers = df_raw[STRINGER_PITCH_COLUMN_ID].unique()
    pivoted = df_raw.pivot_table(
        index=STRINGER_PITCH_COLUMN_ID,
        columns="Frame Pitch (ID)",
        values="Skin Thickness (mm)",
        aggfunc="first",
        sort=False,
    )
    df_grid_display = pivoted.reindex(all_stringers).reset_index()

    columns = [{"name": c if c != STRINGER_PITCH_COLUMN_ID else "", "id": c} for c in df_grid_display.columns]
    
    # --- FIX: Create a blank grid for the visual display ---
    # Instead of showing numbers, we show an empty grid that gets colored.
    grid_data_df = df_grid_display.copy()
    for col in grid_data_df.columns:
        if col != STRINGER_PITCH_COLUMN_ID:
            grid_data_df[col] = ""
            
    grid_data = grid_data_df.to_dict("records")
    tooltips = generate_zone_tooltips(main_data_json, stored_panels)
    styles = generate_merged_zone_styles(columns, stored_panels)

    # Add background colors for zones
    if stored_panels:
        for panel in stored_panels:
            for coord in panel.get("coords", []):
                styles.append(
                    {
                        "if": {
                            "row_index": coord["row"],
                            "column_id": coord["column_id"],
                        },
                        "backgroundColor": panel.get("color"),
                        "color": panel.get("text_color"),
                    }
                )

    return grid_data, columns, styles, tooltips

@callback(
    Output("skin-csv-table", "data"),
    Output("skin-csv-table", "columns"),
    Input("skin-data-store", "data")
)
def update_skin_data_view(skin_data_json):
    """Updates the skin data view table."""
    if not skin_data_json:
        return [], []
    df = pd.read_json(StringIO(skin_data_json), orient="split")
    columns = [{"name": i, "id": i} for i in df.columns]
    data = df.to_dict("records")
    return data, columns

@callback(
    Output("zone-skin-weight-summary-table", "data"),
    Output("zone-skin-weight-summary-table", "columns"),
    Input("skin-data-store", "data")
)
def update_skin_weight_summary(skin_data_json):
    """Updates the zone skin weight summary table."""
    if not skin_data_json:
        return [], []
    df = pd.read_json(StringIO(skin_data_json), orient="split")
    if df.empty or "Zone Name" not in df.columns:
        return [], []

    # Calculate weight in kg
    df["Skin Weight (kg)"] = pd.to_numeric(df["Weight (g)"], errors="coerce").fillna(0) / 1000.0
    
    summary = df.groupby("Zone Name")["Skin Weight (kg)"].sum().reset_index()
    columns = [{"name": i, "id": i} for i in summary.columns]
    data = summary.to_dict("records")
    return data, columns
