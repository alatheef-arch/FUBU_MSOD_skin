"""
Defines all callbacks for updating the skin tab of the Dash application.
"""

from io import StringIO

import dash
import pandas as pd  # type: ignore
from dash.dependencies import Input, Output, State

from app import app
from data_processing.helpers import format_value_for_csv


@app.callback(
    [Output("skin-csv-table", "data"), Output("skin-csv-table", "columns")],
    [Input("skin-data-store", "data")],
)
def update_skin_tab_table(skin_data_json):
    """Updates skin tab table dynamically"""
    if not skin_data_json:
        return [], []
    df_skin_final = pd.read_json(StringIO(skin_data_json), orient="split")
    if df_skin_final.empty:
        return [], []
    try:
        cols_to_drop = [
            "Frame Cross Section ",
            "Frame Density (g/cm³)",
            "Stringer Cross Section (mm²)",
            "Stringer Density (g/cm³)",
        ]
        df_for_display = df_skin_final.drop(columns=cols_to_drop, errors="ignore")
        df_formatted = df_for_display.copy()
        for col in df_formatted.columns:
            if pd.api.types.is_numeric_dtype(df_formatted[col]):
                df_formatted[col] = df_formatted[col].apply(format_value_for_csv)
        return (
            df_formatted.to_dict("records"),
            [{"name": i, "id": i} for i in df_formatted.columns],
        )
    # pylint: disable=broad-exception-caught
    except Exception as e:
        print(f"Error processing skin data for table: {e}")
        return [], []


# FIX: Disabled warnings related to the high number of arguments and variables,
# which is a common pattern for complex modal-saving callbacks in Dash.
# pylint: disable=too-many-arguments, too-many-positional-arguments, too-many-locals
@app.callback(
    [
        Output("custom-panels-store", "data", allow_duplicate=True),
        Output("main-data-store", "data", allow_duplicate=True),
        Output("skin-data-store", "data", allow_duplicate=True),
        Output("skin-properties-modal", "is_open", allow_duplicate=True),
    ],
    Input("skin-modal-save-button", "n_clicks"),
    [
        State("editing-zone-store", "data"),
        State("skin-modal-enable-thickness-checkbox", "value"),
        State("skin-modal-target-thickness-input", "value"),
        State("skin-modal-target-density-input", "value"),
        State("custom-panels-store", "data"),
        State("main-data-store", "data"),
        State("skin-data-store", "data"),
    ],
    prevent_initial_call=True,
)
def save_skin_properties(
    n_clicks,
    editing_zone,
    checkbox,
    thickness_val,
    density_val,
    stored_panels,
    main_data_json,
    skin_data_json,
):
    """Updates zone level skin properties for each cell in the zone"""
    if not n_clicks or not editing_zone:
        return dash.no_update, dash.no_update, dash.no_update, True

    try:
        apply_thickness = "APPLY_THICKNESS" in (checkbox or [])
        new_density = float(density_val)
        new_thickness = float(thickness_val) if apply_thickness else None
    except (ValueError, TypeError):
        return dash.no_update, dash.no_update, dash.no_update, True

    zone_to_edit = editing_zone["name"]
    df_raw = pd.read_json(StringIO(main_data_json), orient="split")
    df_skin_final = pd.read_json(StringIO(skin_data_json), orient="split")
    updated_panels = [p.copy() for p in stored_panels]
    panel_to_update = next(
        (p for p in updated_panels if p.get("name") == zone_to_edit), None
    )

    if not panel_to_update:
        return dash.no_update, dash.no_update, dash.no_update, True

    panel_to_update["target_density"] = new_density
    panel_to_update["target_thickness"] = new_thickness
    stringer_pitch_values = df_raw["Stringer Pitch (mm)"].unique()
    for coord in panel_to_update.get("coords", []):
        stringer_pitch = stringer_pitch_values[coord["row"]]
        frame_pitch = coord["column_id"]
        skin_mask = (
            (df_skin_final["Zone Name"] == zone_to_edit)
            & (df_skin_final["Row"] == stringer_pitch)
            & (df_skin_final["Column"] == frame_pitch)
        )
        if skin_mask.any():
            df_skin_final.loc[skin_mask, "Skin Density (g/cm³)"] = new_density
            if apply_thickness:
                final_thickness = new_thickness
            else:
                thickness_col = "Skin Thickness (mm)"
                skin_thickness_series = df_skin_final.loc[skin_mask, thickness_col]
                final_thickness = skin_thickness_series.iloc[0]
            str_len_cm = (
                df_skin_final.loc[skin_mask, "Stringer Length (mm)"].iloc[0] * 0.1
            )
            fr_len_cm = (
                df_skin_final.loc[skin_mask, "Frame Length(Pitch) (mm)"].iloc[0] * 0.1
            )
            thickness_cm = (final_thickness or 0) * 0.1
            new_weight = str_len_cm * fr_len_cm * thickness_cm * new_density
            df_skin_final.loc[skin_mask, "Weight (g)"] = new_weight
            panel_to_update["weight"][
                f"{coord['row']}-{coord['column_id']}"
            ] = new_weight

    return (
        updated_panels,
        df_raw.to_json(orient="split"),
        df_skin_final.to_json(orient="split"),
        False,
    )


@app.callback(
    [
        Output("zone-skin-weight-summary-table", "data"),
        Output("zone-skin-weight-summary-table", "columns"),
    ],
    [Input("skin-data-store", "data")],
)
def update_zone_weight_summary(skin_data_json):
    """Updates skin weight summary information for each zone"""
    if not skin_data_json:
        return [], []
    df_skin_final = pd.read_json(StringIO(skin_data_json), orient="split")
    if df_skin_final.empty:
        return [], []
    summary_df = df_skin_final.groupby("Zone Name")["Weight (g)"].sum().reset_index()
    summary_df["Weight (g)"] = summary_df["Weight (g)"] / 1000.0
    summary_df.rename(columns={"Weight (g)": "Total Skin Weight (kg)"}, inplace=True)
    summary_df["Total Skin Weight (kg)"] = summary_df["Total Skin Weight (kg)"].apply(
        format_value_for_csv
    )
    return (
        summary_df.to_dict("records"),
        [{"name": i, "id": i} for i in summary_df.columns],
    )


@app.callback(
    [
        Output("skin-properties-modal", "is_open", allow_duplicate=True),
        Output("editing-zone-store", "data", allow_duplicate=True),
        Output("skin-modal-enable-thickness-checkbox", "value"),
        Output("skin-modal-target-thickness-input", "value"),
        Output("skin-modal-target-density-input", "value"),
    ],
    [
        Input("final-zone-grid", "active_cell"),
        Input("skin-tab-final-zone-grid", "active_cell"),
    ],
    State("custom-panels-store", "data"),
    prevent_initial_call=True,
)
def open_skin_properties_modal(main_tab_cell, skin_tab_cell, stored_panels):
    """Opens the modal to edit skin properties when a zone is clicked."""
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return False, None, [], None, None

    panel_to_edit = _get_panel_for_active_cell(ctx.triggered[0]["value"], stored_panels)
    if not panel_to_edit:
        return False, None, [], None, None

    thickness = panel_to_edit.get("target_thickness")
    density = panel_to_edit.get("target_density")
    checkbox_val = ["APPLY_THICKNESS"] if thickness is not None else []
    return (True, {"name": panel_to_edit["name"]}, checkbox_val, thickness, density)


@app.callback(
    Output("skin-properties-modal", "is_open", allow_duplicate=True),
    Input("skin-modal-close-button", "n_clicks"),
    prevent_initial_call=True,
)
def close_skin_properties_modal(n_clicks):
    """Closes skin properties modal"""
    return False if n_clicks else dash.no_update




