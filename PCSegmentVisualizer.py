import plotly.express as px
import plotly.graph_objects as go

from WallComplexVisualizer import segment_nodes, node_points

# ---------------------------------------------------------------------------
# Zeigt alle PCSegments gleichzeitig an, jedes in einer eigenen Farbe.
# ---------------------------------------------------------------------------
COLORS = px.colors.qualitative.Alphabet

traces = []
for i, seg_id in enumerate(segment_nodes):
    pts = node_points(seg_id)
    if len(pts) == 0:
        continue
    traces.append(go.Scatter3d(
        x=pts[:, 0], y=pts[:, 1], z=pts[:, 2],
        mode="markers",
        marker=dict(size=2, color=COLORS[i % len(COLORS)]),
        name=f"Segment {seg_id}",
    ))

fig = go.Figure(
    data=traces,
    layout=go.Layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(aspectmode="data"),
    ),
)
fig.show()
