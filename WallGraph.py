import xml.etree.ElementTree as ET
import json
import numpy as np
import plotly.graph_objects as go

NS = {"g": "http://graphml.graphdrawing.org/xmlns"}


class WallGraph:
    """Liest eine GraphML-Datei und die zugehörigen Punktwolken ein und
    stellt Hilfsfunktionen zur Face- und Plotly-Darstellung bereit."""

    def __init__(self, xml_path, json_path):
        self.nodes = self._load_nodes(xml_path)
        self.points_by_pool = self._load_points(json_path)

    @staticmethod
    def _load_nodes(xml_path):
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
        return nodes

    @staticmethod
    def _load_points(json_path):
        with open(json_path, "r") as f:
            raw = json.load(f)
        return {k: np.array(v, dtype=float) for k, v in raw.items()}

    def nodes_of_type(self, node_type):
        return [nid for nid, a in self.nodes.items() if a["node_type"] == node_type]

    @staticmethod
    def _parse_vertex_indices(raw):
        if not raw:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    def node_pool_points(self, node_id):
        pool = self.nodes[node_id]["point_pool"]
        if pool is None or pool < 0:
            return np.empty((0, 3))
        return self.points_by_pool.get(str(pool), np.empty((0, 3)))

    def node_faces(self, node_id):
        """Liste von Faces (je ein (N,3) Array) für einen Knoten, gebildet aus vertex_indices."""
        pool_points = self.node_pool_points(node_id)
        if len(pool_points) == 0:
            return []
        parsed = self._parse_vertex_indices(self.nodes[node_id]["vertex_indices"])
        if not parsed:
            return [pool_points]

        face_index_lists = parsed if isinstance(parsed[0], list) else [parsed]
        faces = []
        for idxs in face_index_lists:
            valid = [i for i in idxs if 0 <= i < len(pool_points)]
            if valid:
                faces.append(pool_points[valid])
        return faces

    @staticmethod
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

    @staticmethod
    def make_face_outline(face_points, color, opacity, width=3):
        """Zeichnet die geschlossene Kontur eines Face."""
        loop = np.vstack([face_points, face_points[:1]])
        return go.Scatter3d(
            x=loop[:, 0], y=loop[:, 1], z=loop[:, 2],
            mode="lines",
            line=dict(color=color, width=width),
            opacity=opacity, showlegend=False, hoverinfo="skip",
        )
