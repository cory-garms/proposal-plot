"""
Seeds the three core capabilities into the DB.
Safe to run multiple times (INSERT OR IGNORE).

Usage:
    python -m backend.capabilities.seed_capabilities
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.database import init_db
from backend.db.crud import insert_capability, get_all_capabilities

CAPABILITIES = [
    {
        "name": "Remote Sensing",
        "description": (
            "Expertise in acquiring and processing data from airborne and spaceborne sensors, "
            "including synthetic aperture radar (SAR), electro-optical/infrared (EO/IR), "
            "hyperspectral imaging, and multispectral sensors. Applications include terrain "
            "mapping, change detection, target recognition, and environmental monitoring."
        ),
        "keywords": [
            "SAR", "synthetic aperture radar", "LiDAR", "hyperspectral", "multispectral",
            "satellite imagery", "EO/IR", "electro-optical", "infrared", "remote sensing",
            "aerial imaging", "radar", "spectral", "optical sensor", "geospatial",
            "earth observation", "UAV sensor", "drone imaging", "thermal imaging",
            "change detection", "target detection", "surveillance imagery",
        ],
    },
    {
        "name": "3D Point Clouds",
        "description": (
            "Deep expertise in 3D point cloud acquisition, processing, and analysis from "
            "LiDAR sensors and photogrammetric reconstruction. Includes mesh generation, "
            "surface reconstruction, volumetric analysis, SLAM-based localization, and "
            "machine learning methods for 3D scene understanding."
        ),
        "keywords": [
            "point cloud", "LiDAR", "photogrammetry", "mesh reconstruction", "voxelization",
            "SLAM", "3D reconstruction", "surface reconstruction", "3D mapping",
            "volumetric", "depth sensing", "structured light", "stereo vision",
            "3D scene understanding", "PointNet", "3D object detection", "terrain model",
            "digital elevation model", "DEM", "DSM", "ground segmentation",
        ],
    },
    {
        "name": "Edge Computing",
        "description": (
            "Experience deploying real-time machine learning and signal processing pipelines "
            "on resource-constrained hardware including FPGAs, embedded processors, and "
            "custom SoCs. Focus on low-latency inference, model compression, on-device AI, "
            "and power-efficient processing for field-deployable systems."
        ),
        "keywords": [
            "edge computing", "embedded systems", "FPGA", "low-latency", "on-device",
            "real-time processing", "edge AI", "edge inference", "IoT", "embedded AI",
            "model compression", "quantization", "pruning", "TensorRT", "OpenVINO",
            "Jetson", "microcontroller", "SoC", "power-efficient", "field-deployable",
            "resource-constrained", "autonomous system", "onboard processing",
        ],
    },
]


def seed() -> None:
    init_db()
    existing = {c["name"] for c in get_all_capabilities()}
    seeded = 0
    for cap in CAPABILITIES:
        if cap["name"] not in existing:
            insert_capability(cap["name"], cap["description"], json.dumps(cap["keywords"]))
            print(f"  Seeded: {cap['name']} ({len(cap['keywords'])} keywords)")
            seeded += 1
        else:
            print(f"  Skipped (exists): {cap['name']}")
    print(f"\nDone. {seeded} new capabilities seeded.")


if __name__ == "__main__":
    seed()
