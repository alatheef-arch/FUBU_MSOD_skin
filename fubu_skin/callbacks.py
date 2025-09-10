# fubu_skin/callbacks.py
"""Defines callbacks for the Skin tab."""
from io import StringIO
import pandas as pd
from dash import html
from dash.dependencies import Input, Output

from app import app
from data_processing.data_transformer import (
    generate_merged_zone_styles,
    generate_zone_tooltips,
)

STRINGER_PITCH_COLUMN_ID = "Stringer Pitch (mm)"


@app.callback(
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
    all_stringers = df_raw[STRINGER_PITCH_COLUMN_ID].unique()
    pivoted = df_raw.pivot_table(
        index=STRINGER_PITCH_COLUMN_ID,
        columns="Frame Pitch (ID)",
        values="Skin Thickness (mm)",
        aggfunc="first",
        sort=False,
    )
    df_grid_display = pivoted.reindex(all_stringers).reset_index()

    columns = [
        {"name": "" if str(c) == STRINGER_PITCH_COLUMN_ID else str(c), "id": str(c)}
        for c in df_grid_display.columns
    ]

    grid_data_df = df_grid_display.copy()
    for col in grid_data_df.columns:
        if col != STRINGER_PITCH_COLUMN_ID:
            grid_data_df[col] = ""

    tooltips = generate_zone_tooltips(main_data_json, stored_panels)
    conditional_styles = []
    if stored_panels:
        for panel in stored_panels:
            for coord in panel.get("coords", []):
                conditional_styles.append(
                    {
                        "if": {
                            "row_index": coord["row"],
                            "column_id": coord["column_id"],
                        },
                        "backgroundColor": panel.get("color"),
                        "color": panel.get("text_color"),
                    }
                )

    border_styles = generate_merged_zone_styles(columns, stored_panels)
    final_styles = conditional_styles + border_styles
    grid_data_dict = grid_data_df.to_dict("records")

    return grid_data_dict, columns, final_styles, tooltips
