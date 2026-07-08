import argparse
import subprocess
import sys
from pathlib import Path


class VisualizePipelineResults:
    """Startet GraphOverviewVisualizer, WallPolygonVisualizer und PCSegmentVisualizer
    gleichzeitig mit denselben Datei-Pfaden (XML und JSON)."""

    SCRIPTS = [
        "GraphOverviewVisualizer.py",
        "WallPolygonVisualizer.py",
        "PCSegmentVisualizer.py",
    ]

    def __init__(self, path_xml, path_json, script_dir=None):
        self.path_xml = path_xml
        self.path_json = path_json
        self.script_dir = Path(script_dir) if script_dir else Path(__file__).resolve().parent
        self.processes = []

    def start(self):
        for script in self.SCRIPTS:
            script_path = self.script_dir / script
            process = subprocess.Popen([
                sys.executable, str(script_path),
                "--xml", self.path_xml,
                "--json", self.path_json,
            ])
            self.processes.append(process)
        return self.processes

    def wait(self):
        for process in self.processes:
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=VisualizePipelineResults.__doc__)
    parser.add_argument("--xml", dest="path_xml", default="../data/serialized-graph/GraphOfSyntheticWalls3.xml")
    parser.add_argument("--json", dest="path_json", default="../data/serialized-graph/GraphOfSyntheticWalls3_points.json")
    args = parser.parse_args()

    pipeline = VisualizePipelineResults(args.path_xml, args.path_json)
    pipeline.start()
    pipeline.wait()


if __name__ == "__main__":
    main()
