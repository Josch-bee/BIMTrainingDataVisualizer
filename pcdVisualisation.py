import open3d as o3d
import sys

def visualize_pcd(file_path, downsampling):
    # Load the point cloud
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        print("Datei konnte nicht geladen werden.")
        return
    print(f"Loaded point cloud with {len(pcd.points)} points.")
    
    # Downsample the point cloud
    if len(pcd.points) > 1000000 and downsampling:  # Threshold for downsampling
        voxel_size = 0.5  # value in m Voxel)
        pcd = pcd.voxel_down_sample(voxel_size)
        print(f"Points after Downsampling: {len(pcd.points)}")

    # Visualize the point cloud
    o3d.visualization.draw_geometries_with_editing([pcd], 
                                      window_name="BIM GNN Visualizer",
                                      width=1280, height=720)

# PCD files can be loaded faster as binaries
def savePcAsciiToBinary(inputPath, outputPath):
    pcd = o3d.io.read_point_cloud(inputPath)
    if pcd.is_empty():
        print("Datei konnte nicht geladen werden.")
        return
    o3d.io.write_point_cloud(outputPath, pcd, write_ascii=False)

# Convert ply to pcd
def convertPlyToPcd(inputPath, outputPath):
    pcd = o3d.io.read_point_cloud(inputPath)
    if pcd.is_empty():
        print("Datei konnte nicht geladen werden.")
        return
    o3d.io.write_point_cloud(outputPath, pcd)

# savePcAsciiToBinary("data/pcd/LeRosaire.pcd", "data/pcd/LeRosaire_binary.pcd")
# convertPlyToPcd("data/pc-data/generated/SchlossWeizernMediumHighCropped.ply", "data/pc-data/generated/SchlossWeizernMediumHighCropped.pcd")
visualize_pcd("C:/Users/josch/Desktop/Joschua/Bachelorarbeit Lokal/data/pc-data/generated/SyntheticWalls1.pcd", False)