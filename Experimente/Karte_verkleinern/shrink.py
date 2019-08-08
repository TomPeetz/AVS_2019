#!/usr/bin/env python3
 
from pprint import pprint
import random
from pathlib import Path
import sys
import os
import getopt
import time
import json
import subprocess
import tempfile
import copy
import xml.etree.ElementTree as ET
import collections
from multiprocessing import cpu_count
from multiprocessing import Pool
from ctypes import *
import re

if "SUMO_HOME" in os.environ:
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)
else:
    sys.exit("Umgebungsvariable 'SUMO_HOME' setzen.")

import sumolib

def hack_for_cologne(plain_files):
    #hack for cologne
    with open(plain_files["tll"], "w") as file_handle:
        file_handle.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<tlLogics version=\"1.1\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"http://sumo.dlr.de/xsd/tllogic_file.xsd\">\n</tlLogics>")

def load_netconvert_binary():
    netcnvt = sumolib.checkBinary("netconvert")
    return netcnvt

#Cleanup tmp directory
def rm_tmpd_and_files(tmpd):
    for f in tmpd.iterdir():
        os.unlink(f)
    os.rmdir(tmpd)

#Unpack provided net.xml file for modification
def cnvt_net_to_plain(net_path, netcnvt_bin, plain_output_prefix, verbose=False):
    cwd = Path(os.getcwd())
    tmpd = Path(tempfile.mkdtemp())
    res = subprocess.run([netcnvt_bin, "-s", str(net_path), "--plain-output-prefix", plain_output_prefix], capture_output=True, cwd=tmpd)
    if verbose:
        print("Output from: ")
        print(*res.args, sep=" ")
        print(str(res.stderr, "utf-8"), file=sys.stderr)
        print(str(res.stdout, "utf-8"))
        print("***")
    if res.returncode != 0:
        rm_tmpd_and_files(tmpd)
        raise ValueError("net_path does not point to a valid net.xml file.")
    plain_files = { "con" : os.path.join(tmpd, plain_output_prefix+".con.xml"),
                    "edg" : os.path.join(tmpd, plain_output_prefix+".edg.xml"),
                    "nod" : os.path.join(tmpd, plain_output_prefix+".nod.xml"),
                    "tll" : os.path.join(tmpd, plain_output_prefix+".tll.xml"),
                    "typ" : os.path.join(tmpd, plain_output_prefix+".typ.xml") }
    return tmpd, plain_files

#Pack changed plain files into new net.xml
def cnvt_plain_to_net(netcnvt_bin, plain_files, new_net_path, verbose):
    
    res = subprocess.run([netcnvt_bin, "-n", plain_files["nod"], "-e", plain_files["edg"],
                            "-x", plain_files["con"], "-i", plain_files["tll"], "-t", plain_files["typ"] , "-o", str(new_net_path)], capture_output=True)
    if verbose:
        print("Output from: ")
        print(*res.args, sep=" ")
        print(str(res.stderr, "utf-8"), file=sys.stderr)
        print(str(res.stdout, "utf-8"))
        print("***")
        
class Net_Repr:
    
    net_nodes = {}
    
    net_edges = {}
    net_edges_from_idx = {}
    net_edges_to_idx = {}
    
    net_roundabouts = {}
    net_roundabouts_edges_nodes_idx = {}
    net_roundabouts_edge_idx = {}
    net_roundabouts_node_idx = {}
    
    net_connections = {}
    net_connections_from_to_idx = {}
    net_connections_from_idx = {}
    net_connections_to_idx = {}
    
    art_id_ctr = 1
    
    xmlNodeClass = sumolib.xml.compound_object("node", ["id", "type", "x", "y"])
    xmlEdgeClass = sumolib.xml.compound_object("edge", ["id", "from", "to", "priority", "type", "numLanes", "speed", "shape", "disallow"])
    xmlRoundaboutClass = sumolib.xml.compound_object("roundabout", ["nodes", "edges"])
    
    loaded_nodes = None
    loaded_edges = None
    loaded_connections = None
    
    plain_files = None
    
    def __init__(self, plain_files):
        self.plain_files = plain_files
        
        self.loaded_nodes = list(sumolib.xml.parse(plain_files["nod"], "nodes"))[0]
        if self.loaded_nodes.node:        
            for node in self.loaded_nodes.node:
                self.net_nodes[node.id] = node
    
        self.loaded_edges = list(sumolib.xml.parse(plain_files["edg"], "edges"))[0]
        if self.loaded_edges.edge:
            for edge in self.loaded_edges.edge:
                self.net_edges[edge.id] = edge
                
                if edge.attr_from in self.net_edges_from_idx:
                    self.net_edges_from_idx[edge.attr_from].append(edge.id)
                else:
                    self.net_edges_from_idx[edge.attr_from] = [edge.id]
                if edge.to in self.net_edges_to_idx:
                    self.net_edges_to_idx[edge.to].append(edge.id)
                else:
                    self.net_edges_to_idx[edge.to] = [edge.id]
                
        self.loaded_connections = list(sumolib.xml.parse(plain_files["con"], "connections"))[0]
        if self.loaded_connections.connection:
            for connection in self.loaded_connections.connection:
                art_id = self.art_id_ctr
                self.art_id_ctr += 1
                
                self.net_connections[art_id] = connection
                key = "{} {}".format(connection.attr_from, connection.to)
                
                if key in self.net_connections_from_to_idx:
                    self.net_connections_from_to_idx[key].append(art_id)
                else:
                    self.net_connections_from_to_idx[key] = [art_id]
                if connection.attr_from in self.net_connections_from_idx:
                    self.net_connections_from_idx[connection.attr_from].append(art_id)
                else:
                    self.net_connections_from_idx[connection.attr_from] = [art_id]
                if connection.to in self.net_connections_to_idx:
                    self.net_connections_to_idx[connection.to].append(art_id)
                else:
                    self.net_connections_to_idx[connection.to] = [art_id]
                
        if self.loaded_edges.roundabout:
            for roundabout in self.loaded_edges.roundabout:
                art_id = self.art_id_ctr
                self.art_id_ctr += 1
                
                self.net_roundabouts[art_id] = roundabout
                self.net_roundabouts_edges_nodes_idx["{} {}".format(roundabout.edges, roundabout.nodes)] = art_id
                for edge_id in roundabout.edges.split(" "):
                    self.net_roundabouts_edge_idx[edge_id] = art_id
                for node_id in roundabout.nodes.split(" "):
                    self.net_roundabouts_node_idx[node_id] = art_id
                
                
    def get_edge_incoming_ids(self, node_id):
        if node_id in self.net_edges_to_idx:
            return self.net_edges_to_idx[node_id].copy()
        else:
            return []
        
    def get_edge_outgoing_ids(self, node_id):
        if node_id in self.net_edges_from_idx:
            return self.net_edges_from_idx[node_id].copy()
        else:
            return []
        
    def get_connections_in_from_ids(self, edge_id):
        if edge_id in self.net_connections_from_idx:
            return self.net_connections_from_idx[edge_id].copy()
        else:
            return []
            
    def get_connections_in_to_ids(self, edge_id):
        if edge_id in self.net_connections_to_idx:
            return self.net_connections_to_idx[edge_id].copy()
        else:
            return []
        
    def get_edge_shape(self, edge_id):
        shape=[]
        if self.net_edges[edge_id].shape == None:
            return shape
        for coord_pair in self.net_edges[edge_id].shape.split(" "):
            if coord_pair:
                x,y = coord_pair.split(",")
                shape.append((float(x),float(y)))
        return shape
    
    def add_new_nodes(self, nodes):
        for node in nodes:
            self.net_nodes[node.id] = node
    
    def add_new_edges(self, edges):
        for edge in edges:
            self.net_edges[edge.id] = edge
            
            if edge.attr_from in self.net_edges_from_idx:
                self.net_edges_from_idx[edge.attr_from].append(edge.id)
            else:
                self.net_edges_from_idx[edge.attr_from] = [edge.id]
            if edge.to in self.net_edges_to_idx:
                self.net_edges_to_idx[edge.to].append(edge.id)
            else:
                self.net_edges_to_idx[edge.to] = [edge.id]
    
    def add_new_roundabout(self, roundabout):
        art_id = self.art_id_ctr
        self.art_id_ctr += 1
        
        self.net_roundabouts[art_id] = roundabout
        self.net_roundabouts_edges_nodes_idx["{} {}".format(roundabout.edges, roundabout.nodes)] = art_id
    
    def remove_nodes_by_id(self, node_ids):
        for n_id in node_ids:
            del self.net_nodes[n_id]
        
    def set_edge_to(self, edge_id, node_id):
        old_to = self.net_edges[edge_id].to
        self.net_edges[edge_id].to = node_id
        self.net_edges_to_idx[old_to].remove(edge_id)
        
        if node_id in self.net_edges_to_idx:
            self.net_edges_to_idx[node_id].append(edge_id)
        else:
            self.net_edges_to_idx[node_id] = [edge_id]
        
    def set_edge_from(self, edge_id, node_id):
        old_from = self.net_edges[edge_id].attr_from
        self.net_edges[edge_id].attr_from = node_id
        self.net_edges_from_idx[old_from].remove(edge_id)
        
        if node_id in self.net_edges_from_idx:
            self.net_edges_from_idx[node_id].append(edge_id)
        else:
            self.net_edges_from_idx[node_id] = [edge_id]
    
    def get_connection_art_ids_by_from_to(self, from_edge_id, to_edge_id):
        key = "{} {}".format(from_edge_id,to_edge_id)
        if key in self.net_connections_from_to_idx:
            return self.net_connections_from_to_idx[key].copy()
        else:
            return None
        
    def remove_connection_by_art_id(self, connection_art_id):
        connection = self.net_connections[connection_art_id]
        del self.net_connections[connection_art_id]
        
        self.net_connections_from_to_idx["{} {}".format(connection.attr_from,connection.to)].remove(connection_art_id)
        self.net_connections_from_idx[connection.attr_from].remove(connection_art_id)
        self.net_connections_to_idx[connection.to].remove(connection_art_id)
        
    def remove_edge_by_id(self, edge_id):
        edge = self.net_edges[edge_id]
        del self.net_edges[edge_id]
        
        self.net_edges_from_idx[edge.attr_from].remove(edge_id)
        self.net_edges_to_idx[edge.to].remove(edge_id)
        
    def get_roundabout_art_idx_by_edges_nodes(self, edge_ids_str, node_ids_str):
        key = "{} {}".format(edge_ids_str, node_ids_str)
        if key in self.net_roundabouts_edges_nodes_idx:
            return self.net_roundabouts_edges_nodes_idx[key]
        else:
            return None
        
    def remove_roundabout_by_art_id(self, roundabout_art_id):
        roundabout = self.net_roundabouts[roundabout_art_id]
        
        del self.net_roundabouts[roundabout_art_id]
        del self.net_roundabouts_edges_nodes_idx["{} {}".format(roundabout.edges, roundabout.nodes)]
        for edge_id in roundabout.edges.split(" "):
            del self.net_roundabouts_edge_idx[edge_id]
        for node_id in roundabout.nodes.split(" "):
            del self.net_roundabouts_node_idx[node_id]
    
    def write_to_plain(self):
        nodes = []
        edges = []
        roundabouts = []
        connections = []
        
        for _,v in self.net_nodes.items():
            nodes.append(v) 
        
        for _,v in self.net_edges.items():
            edges.append(v)
            
        for _,v in self.net_roundabouts.items():
            roundabouts.append(v) 
        
        for _,v in self.net_connections.items():
            connections.append(v)

        self.loaded_nodes.node = nodes
        self.loaded_edges.edge = edges
        self.loaded_edges.roundabout = roundabouts
        self.loaded_connections.connection = connections
        
        with open(self.plain_files["nod"], "w") as file_handle:
            file_handle.write(self.loaded_nodes.toXML())
        
        with open(self.plain_files["edg"], "w") as file_handle:
            file_handle.write(self.loaded_edges.toXML())
        
        with open(self.plain_files["con"], "w") as file_handle:
            file_handle.write(self.loaded_connections.toXML())

def node_in(node, rect):
    return float(node.x) > rect[0] and float(node.x) < rect[2] and float(node.y) < rect[1] and float(node.y) > rect[3]
    
def check_trips(trips):
    
    trips_to_remove = set()
    l = len(trips)
    # ~ i=0
    for trip in trips:
        e_f_id, e_t_id, t_id = trip
        # ~ if i % 20000 == 0:
            # ~ print("ppid: {}, pid: {}; Check {}, Batch {} of {}".format(os.getppid(), os.getpid(), t_id, i, l))
        # ~ i+=1
        if e_f_id in remove_edges or e_t_id in remove_edges:
            trips_to_remove.add(t_id)
        elif e_f_id in nr.net_roundabouts_edge_idx or e_t_id in nr.net_roundabouts_edge_idx:
            trips_to_remove.add(t_id)
        elif not tc_lib.check_trip(c_ulonglong(map_e_ids_to_art_ids[e_f_id]), c_ulonglong(map_e_ids_to_art_ids[e_t_id]), c_ulonglong(edge_id_to_array_1d_len), edge_id_to_array_1d) == 1:
            trips_to_remove.add(t_id)
    
    return trips_to_remove

try:
    opts, args = getopt.getopt(sys.argv[1:], "vi:o:a:b:c:d:e:r:")
except getopt.GetoptError as err:
    print(err)
    print("i Input net; o Output net; a Input trips; b Output trips; c Input config; d Output config; e Log file name; r x0,y0,x1,y1")
    sys.exit(1)

param_net_path = False
param_new_net_path = False
param_trips_path = False
param_new_trips_path = False
param_conf_path = False
param_new_conf_path = False
param_new_log = False
x0, y0, x1, y1 = False, False, False, False
VERBOSE=False

for o, a in opts:
    if o == "-i":
        param_net_path = a
    elif o == "-o":
        param_new_net_path = a
    elif o == "-a":
        param_trips_path = a
    elif o == "-b":
        param_new_trips_path = a
    elif o =="-c":
        param_conf_path = a
    elif o =="-d":
        param_new_conf_path = a
    elif o =="-e":
        param_new_log = a
    elif o =="-r":
        x0, y0, x1, y1 = list(map(float,a.split(",")))
    elif o =="-v":
        VERBOSE=True


#Upper left
# ~ x0 = 7100.
# ~ y0 = 21000.

#lower right
# ~ x1 = 20300.
# ~ y1 = 8700.

#######################
net_path = Path(param_net_path).resolve()
if not net_path.exists() or net_path.is_dir():
    sys.exit("Netz nicht gefunden")
    
netcnvt_bin = load_netconvert_binary()

new_net_path = Path(param_new_net_path).resolve()

pprint("Extracting...")
try:
    plain_path, plain_files = cnvt_net_to_plain(net_path, netcnvt_bin, "PLAIN_PRFX", VERBOSE)
except ValueError:
    sys.exit("Keine gültige .net.xml Datei spezifiziert.")

pprint("Hack...")
hack_for_cologne(plain_files)

pprint("Load net...")
nr = Net_Repr(plain_files)


pprint("Load trips...")
original_trips_path = Path(param_trips_path).resolve()

original_trips_tree = ET.parse(original_trips_path)
original_trips_root = original_trips_tree.getroot()

###

pprint("Modify net...")

rect = (x0, y0, x1, y1)

keep_nodes = set()
keep_edges = set()

for e_id, edge in nr.net_edges.items():
    to_node = nr.net_nodes[edge.to]
    from_node = nr.net_nodes[edge.attr_from]
    
    to_node_in = node_in(to_node, rect)
    from_node_in = node_in(from_node, rect)
    
    if to_node_in or from_node_in:
        keep_edges.add(e_id)
        keep_nodes.add(to_node.id)
        keep_nodes.add(from_node.id)
    
remove_roundabouts = set()
remove_nodes = set()
for n_id in nr.net_nodes:
    if n_id not in keep_nodes:
        remove_nodes.add(n_id)
        if n_id in nr.net_roundabouts_node_idx:
            remove_roundabouts.add(nr.net_roundabouts_node_idx[n_id])
nr.remove_nodes_by_id(remove_nodes)

remove_edges = set()
for e_id in nr.net_edges:
    if e_id not in keep_edges:
        remove_edges.add(e_id)
        if e_id in nr.net_roundabouts_edge_idx:
            remove_roundabouts.add(nr.net_roundabouts_edge_idx[e_id])
for e_id in remove_edges:
    nr.remove_edge_by_id(e_id)

for art_r_id in remove_roundabouts:
    nr.remove_roundabout_by_art_id(art_r_id)

for e_id in remove_edges:
    for art_c_id in nr.get_connections_in_from_ids(e_id):
        nr.remove_connection_by_art_id(art_c_id)
        
    for art_c_id in nr.get_connections_in_to_ids(e_id):
        nr.remove_connection_by_art_id(art_c_id)

pprint("Modify trips...")

trips_list=list(original_trips_root.findall("trip"))
trips_l_small = []
for trip in trips_list:
    e_f_id = trip.get("from")
    e_t_id = trip.get("to")
    t_id = trip.get("id")
    
    trips_l_small.append((e_f_id, e_t_id, t_id))
del trips_list

###############
############
#########
map_e_ids_to_art_ids = {}
map_vertices=[[] for k in range(len(nr.net_edges))]
number_of_net_edges = len(nr.net_edges)
j=0
for e_id in nr.net_edges:
    map_e_ids_to_art_ids[e_id] = j
    j+=1
    
for e_id in nr.net_edges:
    one_lane = set()
    if e_id not in nr.net_connections_from_idx:
        continue
    
    for c_id in nr.net_connections_from_idx[e_id]:
        connection = nr.net_connections[c_id]
            
        if (connection.attr_from, connection.to) in one_lane:
            continue
        else:
            one_lane.add((connection.attr_from, connection.to))
        
        if connection.to:
            map_vertices[map_e_ids_to_art_ids[e_id]].append(map_e_ids_to_art_ids[connection.to])

tc_lib = CDLL("./tc.so") 
array_of_arrays=[]
for map_vert in map_vertices:
    edge_id_to_array_2d_len = len(map_vert) + 1
    edge_id_to_array_2d_type = c_ulonglong * edge_id_to_array_2d_len
    sub_array = [edge_id_to_array_2d_len]
    for ver in map_vert:
        sub_array.append(ver)
    array_of_arrays.append(edge_id_to_array_2d_type(*sub_array))

edge_id_to_array_1d_len = len(array_of_arrays)
edge_id_to_array_1d_type = POINTER(c_ulonglong) * edge_id_to_array_1d_len
edge_id_to_array_1d = edge_id_to_array_1d_type(*array_of_arrays)

tc_lib.check_trip.argtypes = (c_ulonglong, c_ulonglong, c_ulonglong, POINTER(POINTER(c_ulonglong)))

pool_size=multiprocessing.cpu_count()
n_chunks = pool_size * 4
a_results=[]
a_trips = [trips_l_small[i:i + int(len(trips_l_small)/n_chunks)] for i in range(0, len(trips_l_small), int(len(trips_l_small)/n_chunks))]


pool = Pool(pool_size)
for a_t in a_trips:
    a_results.append(pool.apply_async(check_trips, (a_t,)))
trips_to_delete = set()
for a_r in a_results:
    a_s = a_r.get()
    trips_to_delete = trips_to_delete.union(a_s)

pprint("Write trips...")

regex = re.compile("id=\"[^\"]+\"")

new_trips_path = Path(param_new_trips_path).resolve()
original_trips_tree.write(new_trips_path)
with open(original_trips_path) as old_file, open(new_trips_path, "w") as new_file:
    for line in old_file:
        reg_res = regex.search(line)
        if reg_res:
            if reg_res.group(0)[4:-1] in trips_to_delete:
                continue
        new_file.write(line)
        
pprint("Write net...")
nr.write_to_plain()

pprint("Updating config")

original_conf_path = Path(param_conf_path).resolve()
new_conf_path = Path(param_new_conf_path).resolve()

original_conf_tree = ET.parse(original_conf_path)
original_conf_root = original_conf_tree.getroot()

original_conf_root.find("input").find("net-file").attrib["value"] = new_net_path.name
original_conf_root.find("input").find("route-files").attrib["value"] = new_trips_path.name
original_conf_root.find("report").find("log").attrib["value"] = param_new_log

original_conf_tree.write(new_conf_path)

pprint("Converting back...")
cnvt_plain_to_net(netcnvt_bin, plain_files, new_net_path, VERBOSE)
rm_tmpd_and_files(plain_path)
