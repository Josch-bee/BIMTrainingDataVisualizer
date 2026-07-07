import json
import numpy as np
import open3d as o3d

def samplePlane(p0, p1, p2, p3, resolution):
    """
    Rastet ein beliebiges Viereck (inkl. Trapez) im 3D-Raum auf,
    indem alle 4 Eckpunkte (p0, p1, p2, p3) bilinear interpoliert werden.
    """
    # Schätze die Kantenlängen, um die Anzahl der Schritte zu bestimmen
    len_u = (np.linalg.norm(p1 - p0) + np.linalg.norm(p2 - p3)) / 2
    len_v = (np.linalg.norm(p3 - p0) + np.linalg.norm(p2 - p1)) / 2
    
    if len_u < 1e-5 or len_v < 1e-5:
        return np.empty((0, 3))
    
    # Normierte Schritte von 0.0 bis 1.0 berechnen
    u_steps = np.linspace(0, 1, max(2, int(len_u / resolution)))
    v_steps = np.linspace(0, 1, max(2, int(len_v / resolution)))
    
    grid_u, grid_v = np.meshgrid(u_steps, v_steps, indexing='ij')
    u_flat = grid_u.flatten()
    v_flat = grid_v.flatten()
    
    # Bilineare Interpolationsformel für alle 4 Punkte:
    # Kombiniert die Ecken gewichtet basierend auf der Position (u, v)
    points = (
        (1 - u_flat)[:, None] * (1 - v_flat)[:, None] * p0 +
        u_flat[:, None] * (1 - v_flat)[:, None] * p1 +
        u_flat[:, None] * v_flat[:, None] * p2 +
        (1 - u_flat)[:, None] * v_flat[:, None] * p3
    )
    
    return points

def generateWallSurfacePointCloud(geometryJson, resolution=0.05):
    # 1. Vertices laden
    vertices = np.array(geometryJson["geometry"]["vertices"])
    allPoints = []
    
    # 2. Wir nutzen die echten Polygone aus der JSON anstelle starrer Indizes!
    polygons = geometryJson["geometry"]["polygons"]
    
    for poly in polygons:
        # Extrahiere die Index-Liste für das aktuelle Polygon
        faceIndices = poly["convexPolygon"]["indices"]
        
        # Jedes Polygon bei einer Wand hat 4 Eckpunkte (Viereck)
        if len(faceIndices) == 4:
            p0 = vertices[faceIndices[0]]
            p1 = vertices[faceIndices[1]]
            p2 = vertices[faceIndices[2]]
            p3 = vertices[faceIndices[3]]
            
            # Fläche mit Punkten füllen
            facePoints = samplePlane(p0, p1, p2, p3, resolution)
            allPoints.append(facePoints)
            
    # 3. Alle Punkte zusammenfügen
    if not allPoints:
        return np.empty((0, 3))
        
    return np.vstack(allPoints)

def generatePointCloudFromBimJson(jsonPath, outputPcdPath, resolution=0.05):
    with open(jsonPath, "r") as file:
        wallGeometryData = json.load(file)

    allWallPoints = []
    
    for wall in wallGeometryData["walls"]:
        wallPoints = generateWallSurfacePointCloud(wall, resolution)
        allWallPoints.append(wallPoints)
        
    # 2. Alle Punkte effizient zu einem großen Array verbinden
    if not allWallPoints:
        print("Keine Wände in der JSON gefunden.")
        return None
        
    combinedPoints = np.vstack(allWallPoints)
    
    # 3. Erst jetzt EINMALIG das Open3D-Objekt erzeugen
    pcdWall = o3d.geometry.PointCloud()
    pcdWall.points = o3d.utility.Vector3dVector(combinedPoints)
    
    # 4. Speichern und zurückgeben
    o3d.io.write_point_cloud(outputPcdPath, pcdWall)
    return pcdWall

# --- Execution ---

pcdWall = generatePointCloudFromBimJson("data/bim-data/original/SyntheticWalls2.json", "data/pc-data/generated/SyntheticWalls2.pcd", resolution=0.05)

# Open preview of the generated point cloud
o3d.visualization.draw_geometries([pcdWall])