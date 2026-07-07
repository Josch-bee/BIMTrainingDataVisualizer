import plotly.express as px
import plotly.graph_objects as go

from WallGraph import WallGraph

PATH_XML = "../data/serialized-graph/GraphOfSyntheticWalls3.xml"
PATH_JSON = "../data/serialized-graph/GraphOfSyntheticWalls3_points.json"

graph = WallGraph(PATH_XML, PATH_JSON)
polygon_nodes = graph.nodes_of_type("WallPolygon")

# ---------------------------------------------------------------------------
# Zeigt alle WallPolygons gleichzeitig an, jedes als Fläche in einer eigenen
# Farbe.
# ---------------------------------------------------------------------------
COLORS = px.colors.qualitative.Alphabet

traces = []
for i, polygon_id in enumerate(polygon_nodes):
    color = COLORS[i % len(COLORS)]
    for face in graph.node_faces(polygon_id):
        mesh = graph.make_face_mesh(face, color, opacity=1, name=f"WallPolygon {polygon_id}", showlegend=True)
        if mesh is not None:
            traces.append(mesh)
        traces.append(graph.make_face_outline(face, color, opacity=1.0))

fig = go.Figure(
    data=traces,
    layout=go.Layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(aspectmode="data"),
        hoverlabel=dict(namelength=-1),
    ),
)
fig.show()
