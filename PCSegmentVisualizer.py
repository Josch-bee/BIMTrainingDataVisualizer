import argparse

import plotly.express as px
import plotly.graph_objects as go

from WallGraph import WallGraph

parser = argparse.ArgumentParser()
parser.add_argument("--xml", dest="path_xml", default="../data/serialized-graph/GraphOfSyntheticWalls3.xml")
parser.add_argument("--json", dest="path_json", default="../data/serialized-graph/GraphOfSyntheticWalls3_points.json")
args = parser.parse_args()

PATH_XML = args.path_xml
PATH_JSON = args.path_json

graph = WallGraph(PATH_XML, PATH_JSON)
segment_nodes = graph.nodes_of_type("PCSegment")

# ---------------------------------------------------------------------------
# Zeigt alle PCSegments gleichzeitig an, jedes als konvexes Polygon (Fläche)
# in einer eigenen Farbe.
# ---------------------------------------------------------------------------
COLORS = px.colors.qualitative.Alphabet

traces = []
for i, seg_id in enumerate(segment_nodes):
    color = COLORS[i % len(COLORS)]
    for face in graph.node_faces(seg_id):
        mesh = graph.make_face_mesh(face, color, opacity=1, name=f"Segment {seg_id}", showlegend=True)
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
