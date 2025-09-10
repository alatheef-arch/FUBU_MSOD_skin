import datetime
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

# --- PART 1: A Minimal Layout ---
def get_layout():
    """Creates a simple layout with just a button and a div."""
    return html.Div([
        html.H2("Callback Diagnostic Test"),
        html.Button("Click Me to Test Callback", id="test-button"),
        html.Hr(),
        html.H4("Callback Output:"),
        html.Pre(id="test-output", style={'border': '1px solid green', 'padding': '10px'}),
    ])

# --- PART 2: A Minimal Callback ---
def register_callbacks():
    """Registers a single, simple callback with no external dependencies."""
    @callback(
        Output("test-output", "children"),
        Input("test-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def simple_test_callback(n_clicks):
        if n_clicks is None:
            raise PreventUpdate
        # When the button is clicked, display the current time.
        return f"SUCCESS! The callback was triggered at: {datetime.datetime.now()}"
