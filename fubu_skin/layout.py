# fubu_skin

from io import StringIO
import dash
import pandas as pd
from dash import callback, dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

# Note: All Dash objects (dbc, html, etc.) and helper functions are 
# provided by the main app's execution scope.

STRINGER_PITCH_COLUMN_ID = "Stringer Pitch (mm)"


# --- PART 1: The Layout Definition ---
def get_layout():
    """
    Creates and returns the layout for the skin tab.
    """
    return dbc.Tab(
        label="Skin",
        tab_id="tab-1",
        children=[
            # This store will hold the data from the main application.
            dcc.Store(id='skin-data-bridge-store'),
            
            create_tab_content_layout(
                children=[
                    *create_image_and_grid_layout(
                        image_src="/assets/skin.jpg",
                        image_max_width="80%",
                        grid_id="skin-tab-final-zone-grid",
                        cell_selectable=True,
                    ),
                    html.H3("Skin Data View", style=grid_title_style),
                    create_data_table(table_id="skin-csv-table"),
                    html.H3("Zone Skin Weight Summary", style=grid_title_style),
                    dash_table.DataTable(
                        id="zone-skin-weight-summary-table",
                        style_cell={**datatable_style_cell, "minWidth": "150px"},
                        style_header=datatable_style_header,
                        style_table={"marginBottom": "50px"},
                        sort_action="native",
                    ),
                ],
            )
        ],
    )


# --- PART 2: The Callback Registration ---
def register_callbacks():
    """This function contains and registers all the callbacks for the skin tab."""

    # This callback acts as a bridge, transferring data from the main app's store
    # to a local store within the dynamic layout. The callback now triggers
    # whenever the main data store is updated, preventing the race condition.
    @callback(
        Output("skin-data-bridge-store", "data"),
        Input("dynamic-data-input-store", "data"),
        prevent_initial_call=True,
    )
    def transfer_data_to_local_store(packaged_data):
        if packaged_data is None:
            raise PreventUpdate
        return packaged_data

    @callback(
        [
            Output("skin-tab-final-zone-grid", "data", allow_duplicate=True),
            Output("skin-tab-final-zone-grid", "columns", allow_duplicate=True),
            Output("skin-tab-final-zone-grid", "style_data_conditional", allow_duplicate=True),
            Output("skin-tab-final-zone-grid", "tooltip_data", allow_duplicate=True),
        ],
        Input("skin-data-bridge-store", "data"),
        prevent_initial_call=True,
    )
    def update_skin_final_zone_grid(packaged_data):
        if packaged_data is None or not packaged_data.get("main_data"):
            raise PreventUpdate

        main_data_json = packaged_data.get("main_data")
        stored_panels = packaged_data.get("custom_panels")

        df_raw = pd.read_json(StringIO(main_data_json), orient="split")
        all_stringers = df_raw[STRINGER_PITCH_COLUMN_ID].unique()
        pivoted = df_raw.pivot_table(index=STRINGER_PITCH_COLUMN_ID, columns="Frame Pitch (ID)",
                                     values="Skin Thickness (mm)", aggfunc="first", sort=False)
        df_grid_display = pivoted.reindex(all_stringers).reset_index()
        columns = [{"name": "" if str(c) == STRINGER_PITCH_COLUMN_ID else str(c), "id": str(c)} for c in
                   df_grid_display.columns]
        grid_data_df = df_grid_display.copy()
        for col in grid_data_df.columns:
            if col != STRINGER_PITCH_COLUMN_ID:
                grid_data_df[col] = ""
        tooltips = generate_zone_tooltips(main_data_json, stored_panels)
        conditional_styles = []
        if stored_panels:
            for panel in stored_panels:
                for coord in panel.get("coords", []):
                    conditional_styles.append({"if": {"row_index": coord["row"], "column_id": coord["column_id"]},
                                               "backgroundColor": panel.get("color"), "color": panel.get("text_color")})
        border_styles = generate_merged_zone_styles(columns, stored_panels)
        final_styles = conditional_styles + border_styles
        grid_data_dict = grid_data_df.to_dict("records")
        return grid_data_dict, columns, final_styles, tooltips

    @callback(
        [Output("skin-csv-table", "data"), Output("skin-csv-table", "columns")],
        Input("skin-data-bridge-store", "data"),
        prevent_initial_call=True,
    )
    def update_skin_tab_table(packaged_data):
        if packaged_data is None or not packaged_data.get("skin_data"):
            raise PreventUpdate
        skin_data_json = packaged_data.get("skin_data")
        
        df_skin_final = pd.read_json(StringIO(skin_data_json), orient="split")
        if df_skin_final.empty:
            return [], []
        cols_to_drop = ["Frame Cross Section ", "Frame Density (g/cm³)", "Stringer Cross Section (mm²)",
                        "Stringer Density (g/cm³)"]
        df_for_display = df_skin_final.drop(columns=cols_to_drop, errors="ignore")
        df_formatted = df_for_display.copy()
        for col in df_formatted.columns:
            if pd.api.types.is_numeric_dtype(df_formatted[col]):
                df_formatted[col] = df_formatted[col].apply(format_value_for_csv)
        return (df_formatted.to_dict("records"), [{"name": i, "id": i} for i in df_formatted.columns])

    @callback(
        [
            Output("zone-skin-weight-summary-table", "data"),
            Output("zone-skin-weight-summary-table", "columns"),
        ],
        Input("skin-data-bridge-store", "data"),
        prevent_initial_call=True,
    )
    def update_zone_weight_summary(packaged_data):
        if packaged_data is None or not packaged_data.get("skin_data"):
            raise PreventUpdate
        skin_data_json = packaged_data.get("skin_data")

        df_skin_final = pd.read_json(StringIO(skin_data_json), orient="split")
        if df_skin_final.empty:
            return [], []
        summary_df = df_skin_final.groupby("Zone Name")["Weight (g)"].sum().reset_index()
        summary_df["Weight (g)"] = summary_df["Weight (g)"] / 1000.0
        summary_df.rename(columns={"Weight (g)": "Total Skin Weight (kg)"}, inplace=True)
        summary_df["Total Skin Weight (kg)"] = summary_df["Total Skin Weight (kg)"].apply(format_value_for_csv)
        return (summary_df.to_dict("records"), [{"name": i, "id": i} for i in summary_df.columns])

    @callback(
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
        n_clicks, editing_zone, checkbox, thickness_val, density_val,
        stored_panels, main_data_json, skin_data_json
    ):
        if not n_clicks or not editing_zone: raise PreventUpdate
        try:
            apply_thickness = "APPLY_THICKNESS" in (checkbox or [])
            new_density = float(density_val)
            new_thickness = float(thickness_val) if apply_thickness else None
        except (ValueError, TypeError):
            raise PreventUpdate
        zone_to_edit = editing_zone["name"]
        df_raw = pd.read_json(StringIO(main_data_json), orient="split")
        df_skin_final = pd.read_json(StringIO(skin_data_json), orient="split")
        updated_panels = [p.copy() for p in stored_panels]
        panel_to_update = next((p for p in updated_panels if p.get("name") == zone_to_edit), None)
        if not panel_to_update: raise PreventUpdate
        panel_to_update["target_density"] = new_density
        panel_to_update["target_thickness"] = new_thickness
        stringer_pitch_values = df_raw["Stringer Pitch (mm)"].unique()
        for coord in panel_to_update.get("coords", []):
            stringer_pitch = stringer_pitch_values[coord["row"]]
            frame_pitch = coord["column_id"]
            skin_mask = ((df_skin_final["Zone Name"] == zone_to_edit) & (df_skin_final["Row"] == stringer_pitch) & (
                df_skin_final["Column"] == frame_pitch))
            if skin_mask.any():
                df_skin_final.loc[skin_mask, "Skin Density (g/cm³)"] = new_density
                if apply_thickness:
                    final_thickness = new_thickness
                else:
                    final_thickness = df_skin_final.loc[skin_mask, "Skin Thickness (mm)"].iloc[0]
                str_len_cm = (df_skin_final.loc[skin_mask, "Stringer Length (mm)"].iloc[0] * 0.1)
                fr_len_cm = (df_skin_final.loc[skin_mask, "Frame Length(Pitch) (mm)"].iloc[0] * 0.1)
                thickness_cm = (final_thickness or 0) * 0.1
                new_weight = str_len_cm * fr_len_cm * thickness_cm * new_density
                df_skin_final.loc[skin_mask, "Weight (g)"] = new_weight
                panel_to_update["weight"][f"{coord['row']}-{coord['column_id']}"] = new_weight
        return (updated_panels, df_raw.to_json(orient="split"), df_skin_final.to_json(orient="split"), False)

    @callback(
        [
            Output("skin-properties-modal", "is_open", allow_duplicate=True),
            Output("editing-zone-store", "data", allow_duplicate=True),
            Output("skin-modal-enable-thickness-checkbox", "value"),
            Output("skin-modal-target-thickness-input", "value"),
            Output("skin-modal-target-density-input", "value"),
        ],
        Input("skin-tab-final-zone-grid", "active_cell"),
        State("custom-panels-store", "data"),
        prevent_initial_call=True,
    )
    def open_skin_properties_modal(skin_tab_cell, stored_panels):
        ctx = dash.callback_context
        if not ctx.triggered or not ctx.triggered[0]["value"]: raise PreventUpdate
        panel_to_edit = _get_panel_for_active_cell(ctx.triggered[0]["value"], stored_panels)
        if not panel_to_edit: raise PreventUpdate
        thickness = panel_to_edit.get("target_thickness")
        density = panel_to_edit.get("target_density")
        checkbox_val = ["APPLY_THICKNESS"] if thickness is not None else []
        return (True, {"name": panel_to_edit["name"]}, checkbox_val, thickness, density)

    @callback(
        Output("skin-properties-modal", "is_open", allow_duplicate=True),
        Input("skin-modal-close-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_skin_properties_modal(n_clicks):
        if not n_clicks: raise PreventUpdate
        return False
