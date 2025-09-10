# /layouts/tabs/tab_skin.py
"""Defines the layout for the skin tab"""
import dash_bootstrap_components as dbc  # type: ignore
from dash import dash_table, html

from layouts.components import (
    create_data_table,
    create_final_zone_grid,
    create_image_and_grid_layout,
    create_tab_content_layout,
)
from layouts.styles import (
    datatable_style_cell,
    datatable_style_header,
    grid_title_style,
)


def get_layout():
    """Creates and returns the layout for the skin tab."""
    return dbc.Tab(
        label="Skin",
        tab_id="tab-1",
        children=[
            create_tab_content_layout(
                children=[
                    *create_image_and_grid_layout(
                        image_src="/assets/skin.jpg",
                        image_max_width="80%",
                        grid_id="skin-tab-final-zone-grid",
                        cell_selectable=True,
                    ),
                    html.H3("Skin Data View", style=grid_title_style),
                    create_data_table(
                        table_id="skin-csv-table",
                    ),
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


