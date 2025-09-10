# callbacks/callbacks_dynamic.py
from dash import dcc, html, Input, Output, State, dash_table, no_update, dash
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from app import app
from backend_service import get_layout_from_repo, find_package_directory
import traceback
import pandas as pd
import uuid
from io import StringIO
import json

# Import all local helper functions and objects that the remote code will need to execute successfully.
# Using '*' is acceptable here as this module's purpose is to create a comprehensive execution scope.
from layouts.components import *
from layouts.styles import *
from data_processing.data_loader import parse_upload_content
from data_processing.helpers import *
from data_processing.data_transformer import *
from callbacks.callbacks_interactive import _get_panel_for_active_cell
from callbacks.callbacks_display import STRINGER_PITCH_COLUMN_ID


# --- Callback to load the layout from the repository ---
@app.callback(
    [
        Output("dynamic-layout-container", "children"),
        Output("dynamic-layout-trigger-store", "data"),
    ],
    Input("load-repo-button", "n_clicks"),
    [
        State("github-repo-url", "value"),
        State("github-token", "value"),
        # The data stores are needed to pass to the exec scope, but are not outputs here.
        State("main-data-store", "data"),
        State("skin-data-store", "data"),
        State("custom-panels-store", "data"),
    ],
    prevent_initial_call=True,
)
def update_layout_from_github(
    n_clicks, repo_url, token, main_data, skin_data, custom_panels_data
):
    if not n_clicks or not repo_url or not token:
        raise PreventUpdate

    # Step 1: Package the data from the main application into a single, reliable dictionary.
    packaged_data = {
        "main_data": main_data,
        "skin_data": skin_data,
        "custom_panels": custom_panels_data,
    }

    # Step 2: Find the package directory and fetch the single consolidated remote file.
    package_name = find_package_directory(repo_url, token)
    if not package_name:
        error_layout = html.Div("Could not find a package directory in the repository.", style={"color": "red"})
        return error_layout, no_update

    layout_path = f"{package_name}/layout.py"
    remote_content = get_layout_from_repo(repo_url, token, layout_path)

    if not remote_content:
        error_layout = html.Div(f"Could not fetch remote file: {layout_path}", style={"color": "red"})
        return error_layout, no_update

    try:
        # Step 3: Prepare a comprehensive dictionary of all helpers the remote code needs to run.
        # CRITICAL CHANGE: Add 'packaged_data' to the helpers dictionary. This makes it
        # available as a global variable within the executed remote script's scope.
        helpers = {
            # Core Dash objects
            "Input": Input, "Output": Output, "State": State, "html": html, "dcc": dcc,
            "dbc": dbc, "dash_table": dash_table, "no_update": no_update, "PreventUpdate": PreventUpdate,
            "callback": app.callback, "dash": dash,
            # Core Python libraries
            "pd": pd, "StringIO": StringIO,
            # All local helper functions from your project
            "create_data_table": create_data_table, "create_image_and_grid_layout": create_image_and_grid_layout,
            "create_tab_content_layout": create_tab_content_layout, "datatable_style_cell": datatable_style_cell,
            "datatable_style_header": datatable_style_header, "grid_title_style": grid_title_style,
            "parse_upload_content": parse_upload_content, "format_value_for_csv": format_value_for_csv,
            "generate_merged_zone_styles": generate_merged_zone_styles, "generate_zone_tooltips": generate_zone_tooltips,
            "_get_panel_for_active_cell": _get_panel_for_active_cell,
            "STRINGER_PITCH_COLUMN_ID": STRINGER_PITCH_COLUMN_ID,
            # The packaged data from the main app is now available to the remote layout.
            "packaged_data": packaged_data,
        }

        # Step 4: Execute the remote code in a controlled scope.
        remote_scope = {}
        exec(remote_content, helpers, remote_scope)

        # Step 5: Explicitly call the registration and layout functions from the remote code.
        if 'register_callbacks' in remote_scope and callable(remote_scope['register_callbacks']):
            remote_scope['register_callbacks']()
        else:
            raise NameError("The remote layout.py must contain a 'register_callbacks' function.")

        if 'get_layout' in remote_scope and callable(remote_scope['get_layout']):
            layout = remote_scope['get_layout']()
        else:
            raise NameError("The remote layout.py must contain a 'get_layout' function.")

        # Step 6: Return the layout and the data pipeline contents to the front end.
        trigger_value = str(uuid.uuid4())
        return layout, trigger_value

    except Exception:
        # On any failure, display a detailed error message.
        tb = traceback.format_exc()
        error_layout = html.Div([html.H4("Error Executing Remote Code:", style={"color": "red"}), html.Pre(tb)])
        return error_layout, no_update
    
# --- Callback to transfer the data once the layout is ready ---
@app.callback(
    Output("dynamic-data-input-store", "data", allow_duplicate=True),
    Input("dynamic-layout-trigger-store", "data"),
    [
        State("main-data-store", "data"),
        State("skin-data-store", "data"),
        State("custom-panels-store", "data"),
    ],
    prevent_initial_call=True,
)
def transfer_data_to_dynamic_store(trigger_value, main_data, skin_data, custom_panels_data):
    if not trigger_value:
        raise PreventUpdate
    
    # Package the data and send it to the dynamic-data-input-store
    packaged_data = {
        "main_data": main_data,
        "skin_data": skin_data,
        "custom_panels": custom_panels_data,
    }
    return packaged_data
