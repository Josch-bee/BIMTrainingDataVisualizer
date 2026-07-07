import xml.etree.ElementTree as ET
import json
import numpy as np
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ---------------------------------------------------------------------------
# 1. DATEIPFADE DEFINIEREN
# ---------------------------------------------------------------------------
PATH_XML = "../data/serialized-graph/GraphOfSyntheticWalls2.xml"
PATH_JSON = "../data/serialized-graph/GraphOfSyntheticWalls2_points.json"

NS = {"g": "http://graphml.graphdrawing.org/xmlns"}

SIDE_COLORS = {
    "Floor": "#8B5A2B",
    "Ceiling": "#4C72B0",
    "Inside": "#55A868",
    "Outside": "#DD8452",
    "Start": "#8172B2",
    "End": "#64B5CD",
}

# ---------------------------------------------------------------------------
# 2. GRAPHML + PUNKTWOLKEN EINLESEN
# ---------------------------------------------------------------------------
def load_graph(xml_path):
    """Liest Knoten und Kanten inkl. ihrer Attribute aus der GraphML-Datei."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    key_names = {key.get("id"): key.get("attr.name") for key in root.findall(".//g:key", NS)}

    nodes = {}
    for node in root.findall(".//g:node", NS):
        attrs = {"node_type": None, "point_pool": -1, "vertex_indices": "", "wall_id": ""}
        for data in node.findall("g:data", NS):
            name = key_names.get(data.get("key"))
            if name == "point_pool":
                attrs["point_pool"] = int(data.text) if data.text else -1
            elif name in attrs:
                attrs[name] = data.text or ""
        nodes[node.get("id")] = attrs

    edges = []
    for edge in root.findall(".//g:edge", NS):
        e = {
            "source": edge.get("source"),
            "target": edge.get("target"),
            "edge_type": None,
            "distance": None,
            "wall_polygon_side": None,
        }
        for data in edge.findall("g:data", NS):
            name = key_names.get(data.get("key"))
            if name == "distance":
                try:
                    e["distance"] = float(data.text)
                except (TypeError, ValueError):
                    e["distance"] = None
            elif name in e:
                e[name] = data.text
        edges.append(e)

    return nodes, edges


def load_points(json_path):
    """Lädt die Punktpools (point_pool -> Nx3 Punkte)."""
    with open(json_path, "r") as f:
        raw = json.load(f)
    return {k: np.array(v, dtype=float) for k, v in raw.items()}


nodes, edges = load_graph(PATH_XML)
points_by_pool = load_points(PATH_JSON)


def parse_vertex_indices(raw):
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def node_pool_points(node_id):
    pool = nodes[node_id]["point_pool"]
    if pool is None or pool < 0:
        return np.empty((0, 3))
    return points_by_pool.get(str(pool), np.empty((0, 3)))


def node_faces(node_id):
    """Liste von Faces (je ein (N,3) Array) für einen Knoten, gebildet aus vertex_indices."""
    pool_points = node_pool_points(node_id)
    if len(pool_points) == 0:
        return []
    parsed = parse_vertex_indices(nodes[node_id]["vertex_indices"])
    if not parsed:
        return [pool_points]

    face_index_lists = parsed if isinstance(parsed[0], list) else [parsed]
    faces = []
    for idxs in face_index_lists:
        valid = [i for i in idxs if 0 <= i < len(pool_points)]
        if valid:
            faces.append(pool_points[valid])
    return faces


def node_points(node_id):
    """Alle Punkte eines Knotens als eine flache (N,3) Punktwolke."""
    faces = node_faces(node_id)
    if not faces:
        return np.empty((0, 3))
    return np.vstack(faces)


def centroid(pts):
    if pts is None or len(pts) == 0:
        return np.array([0.0, 0.0, 0.0])
    return pts.mean(axis=0)


# ---------------------------------------------------------------------------
# 3. GRAPH-BEZIEHUNGEN AUFBAUEN
# ---------------------------------------------------------------------------
wall_nodes = [nid for nid, a in nodes.items() if a["node_type"] == "Wall"]
polygon_nodes = [nid for nid, a in nodes.items() if a["node_type"] == "WallPolygon"]
segment_nodes = [nid for nid, a in nodes.items() if a["node_type"] == "PCSegment"]

wall_to_polygons = {w: [] for w in wall_nodes}
polygon_to_segments = {p: [] for p in polygon_nodes}

for e in edges:
    if e["edge_type"] == "WallToWallPolygon" and e["source"] in wall_to_polygons:
        wall_to_polygons[e["source"]].append((e["target"], e["wall_polygon_side"]))
    elif e["edge_type"] == "PCSegmentToWallPolygon" and e["target"] in polygon_to_segments:
        polygon_to_segments[e["target"]].append((e["source"], e["distance"]))


def best_segment_for_polygon(polygon_id):
    """Das PCSegment mit der geringsten Distanz zu einem WallPolygon."""
    candidates = [c for c in polygon_to_segments.get(polygon_id, []) if c[1] is not None]
    if not candidates:
        return None, None
    return min(candidates, key=lambda c: c[1])


# ---------------------------------------------------------------------------
# 4. PLOTLY HILFSFUNKTIONEN
# ---------------------------------------------------------------------------
def make_face_mesh(face_points, color, opacity, name, showlegend):
    """Füllt ein Face (Fan-Triangulation) als Mesh3d."""
    n = len(face_points)
    if n < 3:
        return None
    i = [0] * (n - 2)
    j = list(range(1, n - 1))
    k = list(range(2, n))
    return go.Mesh3d(
        x=face_points[:, 0], y=face_points[:, 1], z=face_points[:, 2],
        i=i, j=j, k=k,
        color=color, opacity=opacity, name=name,
        showlegend=showlegend, flatshading=True, hoverinfo="name",
    )


def make_face_outline(face_points, color, opacity, width=3):
    """Zeichnet die geschlossene Kontur eines Face."""
    loop = np.vstack([face_points, face_points[:1]])
    return go.Scatter3d(
        x=loop[:, 0], y=loop[:, 1], z=loop[:, 2],
        mode="lines",
        line=dict(color=color, width=width),
        opacity=opacity, showlegend=False, hoverinfo="skip",
    )


def add_wall_traces(traces, wall_id, sides, colors_by_side, opacity, outline_opacity, legend_group_prefix, show_legend):
    """Fügt alle Faces der WallPolygon-Kinder einer Wand hinzu."""
    for polygon_id, side in sides:
        for face in node_faces(polygon_id):
            color = colors_by_side.get(side, "lightgrey") if colors_by_side else "lightgrey"
            mesh = make_face_mesh(face, color, opacity, f"{legend_group_prefix}{side} ({polygon_id})", show_legend)
            if mesh is not None:
                traces.append(mesh)
            traces.append(make_face_outline(face, color, outline_opacity))


# ---------------------------------------------------------------------------
# 5. DASH APP
# ---------------------------------------------------------------------------
app = Dash(__name__)

wall_options = sorted(
    (
        {"label": f"Wand {nodes[w]['wall_id'] or w}  ({w})", "value": w}
        for w in wall_nodes
    ),
    key=lambda o: o["label"],
)

app.layout = html.Div([
    html.Div([
        html.H2("Wandkomplex-Visualisierung", style={"fontFamily": "sans-serif"}),
        html.Label("Wähle einen Wandkomplex:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="wall-selector",
            options=wall_options,
            value=wall_options[0]["value"] if wall_options else None,
            clearable=False,
            style={"marginTop": "10px"},
        ),
        html.Div([
            html.H4("Legende:"),
            html.P("• Farbige Flächen: WallPolygons der gewählten Wand (nach Seite eingefärbt)"),
            html.P("• Rote Diamanten: Nächstgelegenes PCSegment je Fläche"),
            html.P("• Orange gestrichelt: Verbindung Fläche ↔ zugeordnetes Segment"),
            html.P("• Grau: Kontext (übrige Wände & Segmente)"),
        ], style={
            "marginTop": "20px",
            "padding": "15px",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "5px",
            "fontSize": "13px",
            "fontFamily": "sans-serif",
            "lineHeight": "1.6",
        }),
        html.Div(id="match-info", style={
            "marginTop": "20px",
            "padding": "15px",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "5px",
            "fontSize": "13px",
            "fontFamily": "sans-serif",
            "lineHeight": "1.6",
        }),
    ], style={"width": "25%", "float": "left", "padding": "20px", "boxSizing": "border-box"}),

    html.Div([
        dcc.Graph(id="3d-scatter-plot", style={"height": "92vh"})
    ], style={"width": "75%", "float": "right"}),
])


@app.callback(
    Output("3d-scatter-plot", "figure"),
    Output("match-info", "children"),
    Input("wall-selector", "value"),
)
def update_graph(selected_wall):
    if not selected_wall:
        return go.Figure(), "Bitte eine Wand auswählen."

    selected_sides = wall_to_polygons.get(selected_wall, [])
    best_matches = {}
    for polygon_id, side in selected_sides:
        seg_id, dist = best_segment_for_polygon(polygon_id)
        best_matches[polygon_id] = (seg_id, dist, side)
    matched_segment_ids = {seg for seg, _, _ in best_matches.values() if seg}

    traces = []

    # --- Kontext: alle übrigen Wände (ausgegraut) ---
    for w in wall_nodes:
        if w == selected_wall:
            continue
        add_wall_traces(
            traces, w, wall_to_polygons.get(w, []),
            colors_by_side=None, opacity=0.08, outline_opacity=0.15,
            legend_group_prefix="Kontext ", show_legend=False,
        )

    # --- Kontext: alle nicht zugeordneten PCSegments (ausgegraut) ---
    for s in segment_nodes:
        if s in matched_segment_ids:
            continue
        pts = node_points(s)
        if len(pts):
            traces.append(go.Scatter3d(
                x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
                mode="markers",
                marker=dict(size=2, color="darkgrey", opacity=0.15),
                name=f"Segment {s}", showlegend=False, hoverinfo="name",
            ))

    # --- Ausgewählte Wand: Faces nach Seite eingefärbt ---
    add_wall_traces(
        traces, selected_wall, selected_sides,
        colors_by_side=SIDE_COLORS, opacity=0.6, outline_opacity=0.9,
        legend_group_prefix="", show_legend=True,
    )

    # --- Bestpassende PCSegments + Verbindungslinien ---
    for polygon_id, (seg_id, dist, side) in best_matches.items():
        if seg_id is None:
            continue
        seg_pts = node_points(seg_id)
        if len(seg_pts):
            traces.append(go.Scatter3d(
                x=seg_pts[:, 0], y=seg_pts[:, 1], z=seg_pts[:, 2],
                mode="markers",
                marker=dict(size=4, color="red", symbol="diamond", opacity=0.9),
                name=f"Segment {seg_id} → {side}", showlegend=True, hoverinfo="name",
            ))

        poly_center = centroid(node_points(polygon_id))
        seg_center = centroid(seg_pts)
        traces.append(go.Scatter3d(
            x=[poly_center[0], seg_center[0]],
            y=[poly_center[1], seg_center[1]],
            z=[poly_center[2], seg_center[2]],
            mode="lines",
            line=dict(color="orange", width=4, dash="dash"),
            showlegend=False, hoverinfo="skip",
        ))

    layout = go.Layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(
            xaxis=dict(title="X (m)", gridcolor="white", backgroundcolor="rgb(240, 240, 240)"),
            yaxis=dict(title="Y (m)", gridcolor="white", backgroundcolor="rgb(240, 240, 240)"),
            zaxis=dict(title="Z (m)", gridcolor="white", backgroundcolor="rgb(240, 240, 240)"),
            aspectmode="data",
        ),
        legend=dict(yanchor="top", y=0.95, xanchor="left", x=0.01),
    )
    fig = go.Figure(data=traces, layout=layout)

    info = [html.H4("Zuordnungen:")]
    for polygon_id, (seg_id, dist, side) in sorted(best_matches.items(), key=lambda kv: kv[1][2] or ""):
        if seg_id is None:
            info.append(html.P(f"{side}: keine Zuordnung"))
        else:
            info.append(html.P(f"{side} ({polygon_id}) → Segment {seg_id}, Distanz {dist:.5f}"))

    return fig, info


if __name__ == "__main__":
    app.run(debug=True)
