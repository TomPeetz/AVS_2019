#Lib

import subprocess
import tempfile
import atexit
import os
import io
import xml.etree.ElementTree as ET
from pathlib import Path
from ModMap import *

S_CONFIG = Path("sim.sumocfg")
NET_FILE = Path("sim.net.xml")
TRIPS_FILE = Path("sim.trips.xml")
LOG_FILE = Path("sim.log")
VTYPES_FILE = Path("vtypes.add.xml")

temp_dir = None

def finalize_worker():
    for f in temp_dir.iterdir():
        os.unlink(f)
    os.rmdir(temp_dir)

def initialize_worker(sumo_cfg_str, net_file_str, trips_file_str, vtypes_file_str):
    global temp_dir
    
    temp_dir = Path(tempfile.mkdtemp())
    
    with open(Path(temp_dir, NET_FILE), "w") as f:
        f.write(net_file_str)
        
    with open(Path(temp_dir, TRIPS_FILE), "w") as f:
        f.write(trips_file_str)
        
    with open(Path(temp_dir, VTYPES_FILE), "w") as f:
        f.write(vtypes_file_str)
    
    cfg_file = io.StringIO(sumo_cfg_str)
    sumo_cfg_tree = ET.parse(cfg_file)
    sumo_cfg_root = sumo_cfg_tree.getroot()

    sumo_cfg_root.find("input").find("net-file").attrib["value"] = NET_FILE.name
    sumo_cfg_root.find("input").find("route-files").attrib["value"] = TRIPS_FILE.name
    sumo_cfg_root.find("input").find("additional-files").attrib["value"] = VTYPES_FILE.name
    sumo_cfg_root.find("report").find("log").attrib["value"] = LOG_FILE.name
    
    sumo_cfg_tree.write(Path(temp_dir, S_CONFIG))
    
def prepare_simulation():
    pass
    
def execute_simulation():
    pass

def extract_results():
    pass

def evaluate_individual(individual):
    pass
    
    
