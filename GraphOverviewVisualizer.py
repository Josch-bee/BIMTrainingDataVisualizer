import argparse

import plotly.graph_objects as go
import plotly.io as pio

from WallGraph import WallGraph

parser = argparse.ArgumentParser()
parser.add_argument("--xml", dest="path_xml", default="../data/serialized-graph/GraphOfSyntheticWalls3.xml")
parser.add_argument("--json", dest="path_json", default="../data/serialized-graph/GraphOfSyntheticWalls3_points.json")
args = parser.parse_args()

PATH_XML = args.path_xml
PATH_JSON = args.path_json

NODE_TYPES = ["Wall", "WallPolygon", "PCSegment"]
NODE_COLORS = {"Wall": "#4C72B0", "WallPolygon": "#55A868", "PCSegment": "#DD8452"}
EDGE_COLORS = {"WallToWallPolygon": "#8172B2", "PCSegmentToWallPolygon": "#64B5CD"}
SAMPLES_PER_EDGE = 25  # Zwischenpunkte je Kante, damit ein Klick entlang der ganzen Linie erkannt wird

graph = WallGraph(PATH_XML, PATH_JSON)

# ---------------------------------------------------------------------------
# Knotenpositionen: eine Spalte je Typ (Wall | WallPolygon | PCSegment),
# innerhalb der Spalte zentriert untereinander angeordnet.
# ---------------------------------------------------------------------------
positions = {}
for col, node_type in enumerate(NODE_TYPES):
    ids = graph.nodes_of_type(node_type)
    for i, node_id in enumerate(ids):
        positions[node_id] = (col, (len(ids) - 1) / 2 - i)

traces = []

# --- Kanten als anklickbare Linien ---
# --- Definition der Thresholds und Breiten ---
THRESHOLD_ANGLE = 2.0      # Maximaler Winkel
THRESHOLD_DISTANCE = 0.001   # Maximale Distanz
THRESHOLD_OVERLAP = 0.2     # Minimaler Overlap

WIDTH_THICK = 4.5           # Linienstärke wenn Bedingung erfüllt
WIDTH_NORMAL = 1          # Standard-Linienstärke

# --- Kanten als anklickbare Linien ---
for edge in graph.edges:
    if edge["source"] not in positions or edge["target"] not in positions:
        continue
    x0, y0 = positions[edge["source"]]
    x1, y1 = positions[edge["target"]]
    
    props = edge["properties"]
    edge_type = props.get("edge_type")
    color = EDGE_COLORS.get(edge_type, "lightgrey")
    info = "<br>".join(f"{key}: {value}" for key, value in props.items())

    # --- Dynamische Strichstärke berechnen ---
    line_width = WIDTH_NORMAL  # Standardwert
    
    if edge_type == "PCSegmentToWallPolygon":
        # Werte aus den Properties ziehen
        angle = float(props.get("angle", 0))
        distance = float(props.get("distance", 0))
        overlap = float(props.get("overlap", 0))
        
        # Bedingung prüfen: angle < threshold UND distance < threshold UND overlap > threshold
        if angle < THRESHOLD_ANGLE and distance < THRESHOLD_DISTANCE and overlap > THRESHOLD_OVERLAP:
            line_width = WIDTH_THICK

    # Zwischenpunkte berechnen
    xs = [x0 + (x1 - x0) * t / (SAMPLES_PER_EDGE - 1) for t in range(SAMPLES_PER_EDGE)]
    ys = [y0 + (y1 - y0) * t / (SAMPLES_PER_EDGE - 1) for t in range(SAMPLES_PER_EDGE)]

    traces.append(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        line=dict(color=color, width=line_width),  # <-- Hier wird die dynamische Breite gesetzt
        marker=dict(size=5, color=color),
        customdata=[info] * SAMPLES_PER_EDGE,
        hoverinfo="none",
        showlegend=False,
    ))

# --- Knoten je Typ als eigene Spur ---
TEXT_POSITIONS = {"Wall": "middle left", "WallPolygon": "top center", "PCSegment": "middle right"}

for node_type in NODE_TYPES:
    ids = graph.nodes_of_type(node_type)
    if not ids:
        continue
    labels = [f"{node_type} ({node_id})" for node_id in ids]
    traces.append(go.Scatter(
        x=[positions[n][0] for n in ids],
        y=[positions[n][1] for n in ids],
        mode="markers+text",
        marker=dict(size=16, color=NODE_COLORS[node_type], line=dict(color="white", width=1)),
        text=labels,
        textposition=TEXT_POSITIONS[node_type],
        textfont=dict(size=11),
        cliponaxis=False,
        hoverinfo="text",
        name=node_type,
    ))

fig = go.Figure(
    data=traces,
    layout=go.Layout(
        margin=dict(l=140, r=140, b=20, t=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        hoverdistance=40,  # großzügigere Trefftoleranz beim Klicken auf Kanten
    ),
)

# JS, das bei Klick auf eine Kante deren Eigenschaften in einer Box anzeigt
CLICK_SCRIPT = """
var gd = document.getElementById('{plot_id}');
var infoDiv = document.createElement('div');
infoDiv.id = 'edge-info';
infoDiv.style.position = 'fixed';
infoDiv.style.top = '20px';
infoDiv.style.right = '20px';
infoDiv.style.padding = '12px 16px';
infoDiv.style.background = '#f8f9fa';
infoDiv.style.border = '1px solid #ccc';
infoDiv.style.borderRadius = '6px';
infoDiv.style.fontFamily = 'sans-serif';
infoDiv.style.fontSize = '13px';
infoDiv.style.lineHeight = '1.6';
infoDiv.style.maxWidth = '260px';
infoDiv.innerHTML = 'Klicke auf eine Kante, um ihre Eigenschaften zu sehen.';
document.body.appendChild(infoDiv);
gd.on('plotly_click', function(data) {
    var pt = data.points[0];
    if (pt.customdata) {
        infoDiv.innerHTML = pt.customdata;
    }
});
"""

pio.renderers.default = "browser"
pio.renderers["browser"].post_script = CLICK_SCRIPT
fig.show()
