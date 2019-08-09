#Lib

import subprocess
import tempfile
import atexit
import os
import io
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from ModMap import *
import GenEvoConstants

if 'SUMO_HOME' in os.environ:
    sumo_bin = os.path.join(os.environ['SUMO_HOME'], 'bin')
    sys.path.append(sumo_bin)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")
import sumolib


S_CONFIG = Path("sim.sumocfg")
TRIPS_FILE = Path("sim.trips.xml")
NET_FILE = Path("sim.net.xml")
LOG_FILE = Path("sim.log")
VTYPES_FILE = Path("vtypes.add.xml")

WORKER_PLAIN_FILES =  { "con" : Path("plain.con.xml"),
                        "edg" : Path("plain.edg.xml"),
                        "nod" : Path("plain.nod.xml"),
                        "tll" : Path("plain.tll.xml"),
                        "typ" : Path("plain.typ.xml") }

plain_con = None
plain_edg = None
plain_nod = None
plain_tll = None
plain_typ = None
sumo_cfg = None
trips = None
vtypes = None

v_glb = False

netcnvt = False
sumo_bin = False

def initialize_worker(sumo_cfg_str, trips_file_str, vtypes_file_str, plain_con_str, plain_edg_str, plain_nod_str, plain_tll_str, plain_typ_str, verbose):
    global sumo_cfg
    global trips
    global vtypes
    global plain_con
    global plain_edg
    global plain_nod
    global plain_tll
    global plain_typ
    
    global v_glb
    v_glb = verbose
    
    global netcnvt
    netcnvt = load_netconvert_binary()
    
    global sumo_bin
    sumo_bin = sumolib.checkBinary("sumo")
    
    if v_glb:
        print("Worker {} initializing.".format(os.getpid()))
    
    plain_con = plain_con_str
    plain_edg = plain_edg_str
    plain_nod = plain_nod_str
    plain_tll = plain_tll_str
    plain_typ = plain_typ_str
    
    trips = trips_file_str
    vtypes = vtypes_file_str
    
    cfg_file = io.StringIO(sumo_cfg_str)
    sumo_cfg_tree = ET.parse(cfg_file)
    sumo_cfg_root = sumo_cfg_tree.getroot()
    sumo_cfg_root.find("input").find("net-file").attrib["value"] = NET_FILE.name
    sumo_cfg_root.find("input").find("route-files").attrib["value"] = TRIPS_FILE.name
    sumo_cfg_root.find("input").find("additional-files").attrib["value"] = VTYPES_FILE.name
    sumo_cfg_root.find("report").find("log").attrib["value"] = LOG_FILE.name

    tmpd = Path(tempfile.mkdtemp())
    tmp_cnf_path = Path(tmpd, S_CONFIG)
    sumo_cfg_tree.write(tmp_cnf_path)
    with open(tmp_cnf_path, "r") as f:
        sumo_cfg = f.read()
    for f in tmpd.iterdir():
        os.unlink(f)
    os.rmdir(tmpd)
    
    if v_glb:
        print("Worker {} ready.".format(os.getpid()))
        

def populate_tmpd():
    
    tmpd = Path(tempfile.mkdtemp())
    plain_files = {}
    
    for key, path in WORKER_PLAIN_FILES.items():
        plain_files[key] = Path(tmpd, path)
        
    with open(plain_files["con"], "w") as f:
        f.write(plain_con)
    with open(plain_files["edg"], "w") as f:
        f.write(plain_edg)
    with open(plain_files["nod"], "w") as f:
        f.write(plain_nod)
    with open(plain_files["tll"], "w") as f:
        f.write(plain_tll)
    with open(plain_files["typ"], "w") as f:
        f.write(plain_typ)
        
    # ~ pprint("constants:")
    # ~ pprint(hashlib.sha1((plain_con+plain_edg+plain_nod+plain_tll+plain_typ+sumo_cfg+trips+vtypes).encode("UTF-8")).hexdigest())
    
    s_config = Path(tmpd, S_CONFIG)
    trips_file = Path(tmpd, TRIPS_FILE)
    vtypes_file = Path(tmpd, VTYPES_FILE)
    
    with open(s_config, "w") as f:
        f.write(sumo_cfg)
    with open(trips_file, "w") as f:
        f.write(trips)
    with open(vtypes_file, "w") as f:
        f.write(vtypes)
    
    net_file = Path(tmpd, NET_FILE)
    log_file = Path(tmpd, LOG_FILE)
    
    nr = Net_Repr(plain_files)
    
    return nr, tmpd, plain_files, s_config, net_file, log_file
    
def modify_net(individual, nr, plain_files, net_file):
    _, dna = individual
    
    for g_type, g_id, g_mod in dna:
        if g_type == GenEvoConstants.INTER_NODE:
            op, *_ = g_mod
            if op == GenEvoConstants.DO_NOTHING:
                pass
            elif op == GenEvoConstants.RIGHT_BEFORE_LEFT:
                change_intersection_to_right_before_left(g_id, nr)
            elif op == GenEvoConstants.TRAFFIC_LIGHT:
                change_intersection_to_traffic_light_right_on_red(g_id, nr)
            elif op == GenEvoConstants.TRAFFIC_LIGHT_RIGHT_ON_RED:
                change_intersection_to_traffic_light(g_id, nr)
            elif op == GenEvoConstants.ROUNDABOUT:
                change_intersection_to_roundabout(g_id, nr)
            elif op == GenEvoConstants.PRIORITY:
                _, e_id_1, e_id_2 = g_mod
                change_intersection_right_of_way(g_id, op, e_id_1, e_id_2, nr)
            elif op == GenEvoConstants.PRIORITY_STOP:
                _, e_id_1, e_id_2 = g_mod
                change_intersection_right_of_way(g_id, op, e_id_1, e_id_2, nr)
            else:
                pass
        elif g_type == GenEvoConstants.INTER_ROUNDABOUT:
            r_nodes, r_edges = g_id.split(GenEvoConstants.RA_SEP)
            op, *_ = g_mod
            if op == GenEvoConstants.DO_NOTHING:
                pass
            elif op == GenEvoConstants.RIGHT_BEFORE_LEFT:
                change_roundabout_to_right_before_left(r_edges, r_nodes, nr)
            elif op == GenEvoConstants.TRAFFIC_LIGHT_RIGHT_ON_RED:
                change_roundabout_to_traffic_light_right_on_red(r_edges, r_nodes, nr)
            elif op == GenEvoConstants.TRAFFIC_LIGHT:
                change_roundabout_to_traffic_light(r_edges, r_nodes, nr)
            elif op == GenEvoConstants.PRIORITY:
                _, e_id_1, e_id_2 = g_mod
                change_roundabout_to_right_of_way(r_edges, r_nodes, op, e_id_1, e_id_2, nr)
            elif op == GenEvoConstants.PRIORITY_STOP:
                _, e_id_1, e_id_2 = g_mod
                change_roundabout_to_right_of_way(r_edges, r_nodes, op, e_id_1, e_id_2, nr)
            else:
                pass
    
    nr.write_to_plain()
    cnvt_plain_to_net(netcnvt, plain_files, net_file, False)
    
def execute_simulation(s_config):
    res = subprocess.run([sumo_bin, str(s_config)],capture_output=True,cwd=s_config.parent)
    return res.returncode

def extract_results(tmpd):
    #TODO: Use a more sophisticated evaluation criterion
    log_file = Path(tmpd, LOG_FILE)
    with open(log_file, "r") as f:
        for line in f:
            tab = line.split(":")
            if len(tab) == 2:
                if tab[0].strip() == "TimeLoss":
                    return float(tab[1].strip())
    
def cleanup(tmpd):
    rm_tmpd_and_files(tmpd)

def evaluate_individual(individual):
    iid, *_ = individual
    
    # ~ _, dna = individual
    # ~ pprint("dna")
    # ~ pprint(hashlib.sha1(str(dna).encode("UTF-8")).hexdigest())
    
    if v_glb:
        print("Worker {} populating tmpd.".format(os.getpid()))
    nr, tmpd, plain_files, s_config, net_file, log_file = populate_tmpd()
    
    if v_glb:
        print("Worker {} modifing net.".format(os.getpid()))
    modify_net(individual, nr, plain_files, net_file)
    
    if v_glb:
        print("Worker {} starting sumo in {}.".format(os.getpid(),str(tmpd)))
    returncode = execute_simulation(s_config)
    if v_glb:
        print("Worker {} sumo finished with returncode: {}.".format(os.getpid(), returncode))
    
    time_loss = extract_results(tmpd)
    if v_glb:
        print("Worker {} sumo computed TimeLoss: {}.".format(os.getpid(), time_loss))
    
    if v_glb:
        print("Worker {} cleaning up.".format(os.getpid()))
    cleanup(tmpd)
    
    return iid, time_loss
