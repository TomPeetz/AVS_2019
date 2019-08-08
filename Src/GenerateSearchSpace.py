#!/usr/bin/env python3

from pprint import pprint
import json
from os import path
import subprocess
from pathlib import Path
import tempfile
import math
import os, sys

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib

import argparse

parser = argparse.ArgumentParser(description='GenerateSearchSpace')
parser.add_argument('--net', type=str, help='Input net.xml')
parser.add_argument('--searchspace', type=str, help='Output generated SearchSpace.json')
args = parser.parse_args()

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

class Net_Repr:
    
    net_nodes = {}
    
    net_edges = {}
    net_edges_from_idx = {}
    net_edges_to_idx = {}
    
    net_roundabouts = {}
    net_roundabouts_edges_nodes_idx = {}
    
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
                
    def get_edge_incoming_ids(self, node_id):
        return self.net_edges_to_idx[node_id].copy()
        
    def get_edge_outgoing_ids(self, node_id):
        return self.net_edges_from_idx[node_id].copy()
        
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
    
    def write_to_plain(self):
        nodes = []
        edges = []
        roundabouts = []
        connections = []
        
        for k,v in self.net_nodes.items():
            nodes.append(v) 
        
        for k,v in self.net_edges.items():
            edges.append(v)
            
        for k,v in self.net_roundabouts.items():
            roundabouts.append(v) 
        
        for k,v in self.net_connections.items():
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

netxml = path.abspath(args.net)

net = sumolib.net.readNet(str(netxml))

netcnvt = load_netconvert_binary()
tmpd, plain_files = cnvt_net_to_plain(netxml, netcnvt, "plain")

nr = Net_Repr(plain_files)

nodes = net.getNodes()
ranodes = []

roundabouts = []
for ra in net.getRoundabouts():
    ranodes.extend(ra.getNodes())
    
    allowedModifications=["do_nothing", "right_before_left", "traffic_light_right_on_red", "traffic_light"]
    ra_edges = [net.getEdge(r) for r in ra.getEdges()]
    all_inc_edges = []
    for node_id in ra.getNodes():
        n_inc_edges = net.getNode(node_id).getIncoming()
        for e_id in n_inc_edges:
            if not e_id in ra_edges:
                all_inc_edges.append(e_id)
        # ~ all_inc_edges += net.getNode(node_id).getIncoming()
    
    if len(all_inc_edges) > 1:        
        i=0
        for i in range(len(all_inc_edges)):
            for j in range(i):
                allowedModifications.append("priority {} {}".format(all_inc_edges[i].getID(), all_inc_edges[j].getID()))
                allowedModifications.append("priority_stop {} {}".format(all_inc_edges[i].getID(), all_inc_edges[j].getID()))
    
    roundabouts.append({"id": "  ".join([" ".join(ra.getNodes()), " ".join(ra.getEdges())]), 'allowedModifications': allowedModifications})



intersections = []

forbidden_edge_type = ["highway.motorway", "highway.motorway_link", "highway.trunk", "highway.trunk_link"]

for node in nodes:
    
    allowedModifications = ["do_nothing"]
    
    if node.getID() in ranodes: continue

    all_edges = node.getIncoming() + node.getOutgoing()

    has_forbidden_edge = False
    for edge in all_edges:
        if nr.net_edges[edge.getID()].type in forbidden_edge_type:
            has_forbidden_edge = True
            break
    if has_forbidden_edge:
        continue
        
    if len(node.getIncoming()) < 2 and len(node.getOutgoing()) < 2:
        continue
    
    ########### Roundabout
    to_roundabout = True
    
    uniqe_nodes = set()
    for edge in all_edges:
        uniqe_nodes.add(edge.getFromNode())
        uniqe_nodes.add(edge.getToNode())
    uniqe_nodes -= set([node])
    if len(uniqe_nodes) < 3:
        to_roundabout = False
    
    is_to_close = False
    for connected_node in uniqe_nodes:
        x0, y0 = node.getCoord()
        x1, y1 = connected_node.getCoord()
        if math.sqrt((x0 -x1)**2 + (y0 - y1)**2) <= 50:
            is_to_close = True
    if is_to_close:
        to_roundabout = False
        
    if to_roundabout:
        allowedModifications.append("roundabout")
    ########### Roundabout
    
    ########### Right before left
    allowedModifications.append("right_before_left")
    
    ########### 
    # ~ ["priority", "priority_stop"]
    incEdges = node.getIncoming()
    if len(incEdges) < 2:
        continue
    
    allowedModifications.append("traffic_light")
    allowedModifications.append("traffic_light_right_on_red")
    
    i=0
    for i in range(len(incEdges)):
        for j in range(i):
            allowedModifications.append("priority {} {}".format(incEdges[i].getID(), incEdges[j].getID()))
            allowedModifications.append("priority_stop {} {}".format(incEdges[i].getID(), incEdges[j].getID()))
    
    
    intersections.append({'id': node.getID(), 'currentType': node.getType(), 'allowedModifications': allowedModifications})
    # ~ intersections.append({'id': node.getID(), 'currentType': node.getType(), 'allowedModifications': ['intersection_priority', 'roundabout']})



searchspace = {}
searchspace['intersections'] = intersections
searchspace['roundabouts'] = roundabouts

json_data = json.dumps(searchspace)

with open(args.searchspace, 'w') as f:
    f.write(json_data)



rm_tmpd_and_files(tmpd)
