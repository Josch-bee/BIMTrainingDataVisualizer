import plotly.express as px
import plotly.graph_objects as go

from WallComplexVisualizer import polygon_nodes, node_faces, make_face_mesh, make_face_outline

# ---------------------------------------------------------------------------
# Zeigt alle WallPolygons gleichzeitig an, jedes als Fläche in einer eigenen
# Farbe.
# ---------------------------------------------------------------------------
COLORS = px.colors.qualitative.Alphabet

traces = []
for i, polygon_id in enumerate(polygon_nodes):
    color = COLORS[i % len(COLORS)]
    for face in node_faces(polygon_id):
        mesh = make_face_mesh(face, color, opacity=0.7, name=f"WallPolygon {polygon_id}", showlegend=True)
        if mesh is not None:
            traces.append(mesh)
        traces.append(make_face_outline(face, color, opacity=1.0))

fig = go.Figure(
    data=traces,
    layout=go.Layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(aspectmode="data"),
    ),
)
fig.show()
