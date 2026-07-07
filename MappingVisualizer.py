import xml.etree.ElementTree as ET
import json
import numpy as np
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

# ---------------------------------------------------------------------------
# 1. DATEIPFADE DEFINIEREN
# ---------------------------------------------------------------------------
PATH_XML = "data/mapping-results/generated/MappedSyntheticWalls1.xml"
PATH_JSON = "data/mapping-results/generated/MappedSyntheticWalls1.json"

# ---------------------------------------------------------------------------
# 2. DATEN EINLESEN FUNCTIONS
# ---------------------------------------------------------------------------
def load_graph_edges(xml_path):
    """Parst die GraphML-Datei und extrahiert alle Quell- und Zielknoten (Edges)."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Namespace aus dem Root-Element extrahieren falls vorhanden
        ns = {'graphml': 'http://graphml.graphdrawing.org/xmlns'}
        
        edges = []
        for edge in root.findall('.//graphml:edge', ns):
            edges.append((edge.get('source'), edge.get('target')))
        
        if not edges:
            # Fallback falls kein Namespace-Präfix genutzt wurde
            for edge in root.findall('.//edge'):
                edges.append((edge.get('source'), edge.get('target')))
                
        return edges
    except Exception as e:
        print(f"Fehler beim Laden der XML: {e}")
        return []

def load_mapping_json(json_path):
    """Lädt die JSON-Datei mit den Punktwolken- und BIM-Daten."""
    try:
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Fehler beim Laden der JSON: {e}")
        return {"pc_nodes": {}, "bim_nodes": {}}

# Daten real laden
demo_edges = load_graph_edges(PATH_XML)
mapping_data = load_mapping_json(PATH_JSON)

# Dropdown-Optionen basierend auf den echten Kanten generieren
dropdown_options = [
    {"label": f"Cluster {src} ➔ BIM {tgt[:8]}...", "value": f"{src};{tgt}"}
    for src, tgt in demo_edges
]

# ---------------------------------------------------------------------------
# 3. DASH WEB OBERFLÄCHE AUFBAUEN
# ---------------------------------------------------------------------------
app = Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.H2("Bipartites Mapping", style={'fontFamily': 'sans-serif'}),
        html.Label("Wähle ein gemapptes Paar aus:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='mapping-selector',
            options=dropdown_options,
            value=dropdown_options[0]['value'] if dropdown_options else None,
            clearable=False,
            style={'marginTop': '10px'}
        ),
        html.Div([
            html.H4("Legende / Infos:"),
            html.P("• Farbige Punkte: Aktuell selektiertes Paar"),
            html.P("• Graue Punkte: Restliche Szene (Kontext)"),
            html.P("• Blaue Diamanten: PC Zentroiden"),
            html.P("• Rote Quadrate: BIM Zentroiden (gemittelt)"),
            html.P("• Orange Linie: Zuordnung (Mapping)")
        ], style={
            'marginTop': '30px', 
            'padding': '15px', 
            'backgroundColor': '#f8f9fa', 
            'borderRadius': '5px',
            'fontSize': '13px',
            'fontFamily': 'sans-serif',
            'lineHeight': '1.6'
        })
    ], style={'width': '25%', 'float': 'left', 'padding': '20px', 'boxSizing': 'border-box'}),
    
    html.Div([
        dcc.Graph(id='3d-scatter-plot', style={'height': '92vh'})
    ], style={'width': '75%', 'float': 'right'})
])

# ---------------------------------------------------------------------------
# 4. INTERAKTIVE LOGIK (CALLBACK) - KORRIGIERTE VERSION
# ---------------------------------------------------------------------------
@app.callback(
    Output('3d-scatter-plot', 'figure'),
    Input('mapping-selector', 'value')
)
def update_graph(selected_mapping):
    if not selected_mapping:
        return go.Figure()

    selected_pc, selected_bim = selected_mapping.split(';')
    data_traces = []
    
    # Schleife über alle Kanten aus der XML
    for src, tgt in demo_edges:
        # Prüfen, ob die Knoten überhaupt in den JSON-Daten existieren
        if src not in mapping_data["pc_nodes"] or tgt not in mapping_data["bim_nodes"]:
            continue
            
        is_selected = (src == selected_pc and tgt == selected_bim)
        
        # Visuelle Parameter setzen (Hervorhebung vs. Transparenz)
        opacity_points = 0.8 if is_selected else 0.05
        opacity_centroid = 1.0 if is_selected else 0.15
        
        pc_color = 'cyan' if is_selected else 'lightgrey'
        bim_color = 'magenta' if is_selected else 'darkgrey'
        
        # --- A. PUNKTWOLKEN CLUSTER (PC) PLOTTEN ---
        pc_node = mapping_data["pc_nodes"][src]
        pc_pts = np.array(pc_node["points"])
        
        # Sicherer Zugriff auf das verschachtelte "centroids"-Array [[x, y, z]]
        pc_centroids_list = pc_node.get("centroids", [])
        if pc_centroids_list and len(pc_centroids_list) > 0:
            pc_ctr = pc_centroids_list[0] # Greift auf das innere [x, y, z] zu
        else:
            pc_ctr = [0.0, 0.0, 0.0] # Fallback falls leer
        
        if pc_pts.size > 0:
            data_traces.append(go.Scatter3d(
                x=pc_pts[:,0], y=pc_pts[:,1], z=pc_pts[:,2],
                mode='markers',
                marker=dict(size=1.5, color=pc_color, opacity=opacity_points),
                name=f"Cluster {src} Punkte",
                showlegend=is_selected
            ))
            
        # PC Zentroid Marker
        data_traces.append(go.Scatter3d(
            x=[pc_ctr[0]], y=[pc_ctr[1]], z=[pc_ctr[2]],
            mode='markers',
            marker=dict(size=7, color='blue', opacity=opacity_centroid, symbol='diamond'),
            name=f"Zentroid PC {src}",
            showlegend=is_selected
        ))
        
        # --- B. BIM OBJEKT PLOTTEN ---
        bim_node = mapping_data["bim_nodes"][tgt]
        bim_pts = np.array(bim_node["points"])
        
        # Sicherer Zugriff auf die BIM Zentroiden
        bim_centroids_list = bim_node.get("centroids", [])
        if bim_centroids_list:
            bim_centroids = np.array(bim_centroids_list)
            # Wenn 2 (oder mehr) Zentroiden drin sind, nimm den Mittelpunkt davon
            if bim_centroids.ndim == 2 and len(bim_centroids) >= 2:
                bim_ctr = np.mean(bim_centroids, axis=0)
            elif bim_centroids.ndim == 2 and len(bim_centroids) == 1:
                bim_ctr = bim_centroids[0]
            else:
                bim_ctr = bim_centroids
        else:
            bim_ctr = [0.0, 0.0, 0.0]

        if bim_pts.size > 0:
            data_traces.append(go.Scatter3d(
                x=bim_pts[:,0], y=bim_pts[:,1], z=bim_pts[:,2],
                mode='markers',
                marker=dict(size=1.5, color=bim_color, opacity=opacity_points),
                name=f"BIM {tgt[:5]}... Punkte",
                showlegend=is_selected
            ))
            
        # BIM Zentroid Marker
        data_traces.append(go.Scatter3d(
            x=[bim_ctr[0]], y=[bim_ctr[1]], z=[bim_ctr[2]],
            mode='markers',
            marker=dict(size=7, color='red', opacity=opacity_centroid, symbol='square'),
            name=f"Zentroid BIM {tgt[:5]}...",
            showlegend=is_selected
        ))
        
        # --- C. VERBINDUNGSLINIE (NUR FÜR SELEKTIERTES PAAR) ---
        if is_selected:
            data_traces.append(go.Scatter3d(
                x=[pc_ctr[0], bim_ctr[0]],
                y=[pc_ctr[1], bim_ctr[1]],
                z=[pc_ctr[2], bim_ctr[2]],
                mode='lines',
                line=dict(color='orange', width=5),
                name="Aktiviertes Mapping"
            ))

    # Layout Einstellungen
    layout = go.Layout(
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(
            xaxis=dict(title='X (m)', gridcolor='white', backgroundcolor='rgb(240, 240, 240)'),
            yaxis=dict(title='Y (m)', gridcolor='white', backgroundcolor='rgb(240, 240, 240)'),
            zaxis=dict(title='Z (m)', gridcolor='white', backgroundcolor='rgb(240, 240, 240)'),
            aspectmode='data'
        ),
        legend=dict(yanchor="top", y=0.95, xanchor="left", x=0.01)
    )
    
    return go.Figure(data=data_traces, layout=layout)

if __name__ == '__main__':
    # Startet den Server
    app.run(debug=True)