#!/usr/bin/env python3

from pprint import pprint
import os
import sys
import subprocess
from pathlib import Path
import tempfile
import random
import getopt
import math
#Ref
#https://sumo.dlr.de/pydoc/sumolib.net.html
#https://github.com/eclipse/sumo/blob/master/tests/tools/sumolib/patch_network/runner.py

if "SUMO_HOME" in os.environ:
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)
else:
    sys.exit("Umgebungsvariable 'SUMO_HOME' setzen.")

import sumolib

def load_netconvert_binary():
    netcnvt = sumolib.checkBinary("netconvert")
    return netcnvt

def rm_tmpd_and_files(tmpd):
    for f in tmpd.iterdir():
        os.unlink(f)
    os.rmdir(tmpd)

def cnvt_net_to_plain(net_path, netcnvt_bin, plain_output_prefix, verbose=False):
    cwd = Path(os.getcwd())
    tmpd = Path(tempfile.mkdtemp())
    #os.chdir(tmpd)
    res = subprocess.run([netcnvt_bin, "-s", str(net_path), "--plain-output-prefix", plain_output_prefix], capture_output=True, cwd=tmpd)
    #os.chdir(cwd)
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

def get_tmp_file_for_patch(tmpd):
    tmpf = tempfile.mkstemp(prefix="patch_", suffix=".xml", dir=tmpd, text=True)
    return tmpf

def usage(p):
    print("Benutzung: {0} -h (Hilfe) | <Optionen>".format(p))

def my_help(p):
    usage(p)
    print("-h: Diese Hilfe anzeigen und beenden.")
    print("-i <original.net.xml>: Original .net.xml Datei. Erforderlich.")
    print("-o <modifiziert.net.xml>: Ausgabe .net.xml Datei. Erforderlich.")
    print("-k: Temporäre Dateien nicht löschen.")
    print("-v: Mehr Meldungen.")

#Just for demonstration
def random_node_types(plain_files, patch_file, net_path, new_net_path, netcnvt_bin, verbose):
    node_types = ["priority", "right_before_left", "priority_stop"] 
    
    attrs = {"node": ["id", "type"]}
    nodes = list(sumolib.xml.parse(plain_files["nod"], "nodes", attrs))[0]
    for node in nodes.node:
        node.type = random.choice(node_types)
    
    with open(patch_file[1], "w") as patch_file_handle: 
        patch_file_handle.write(nodes.toXML())
    
    res = subprocess.run([netcnvt_bin, "-s", str(net_path), "-n", patch_file[1], "-o", str(new_net_path)], capture_output=True)
    if verbose:
        print("Output from: ")
        print(*res.args, sep=" ")
        print(str(res.stderr, "utf-8"), file=sys.stderr)
        print(str(res.stdout, "utf-8"))
        print("***")

def experiment2(path):
    net = sumoolib.net.readNet(str(path))
    
def get_intersection(lx, ly, cx, cy, r):
    a = ly - cy
    b = cx - lx
    c = cx*ly - lx*cy
    x_1 = cx + ( a*(c - a*cx - b*cy) + b * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    x_2 = cx + ( a*(c - a*cx - b*cy) - b * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    y_2 = cy + ( b*(c - a*cx - b*cy) + a * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    y_1 = cy + ( b*(c - a*cx - b*cy) - a * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    
    return (x_1,y_1) if math.sqrt( (x_1 - lx)**2 + (y_1 - ly)**2 ) < math.sqrt( (x_2 - lx)**2 + (y_2 - ly)**2 ) else (x_2,y_2)

def get_new_edge_shapes(inc, out, my_node, node_r):
    
    modified_edges = dict()
    
    #find matching edges (opposite directions)
    pairs = []
    for i in inc:
        p = [i]
        for o in out:
            if i.getFromNode() == o.getToNode():
                p.append(o)
        pairs.append(p)
    
    node_x, node_y = my_node.getCoord()
    for pair in pairs:
        for edge in pair:
            match = pair[0].getID() if edge.getID() == pair[1].getID() else pair[1].getID()
            is_incoming = False if edge.getID() == pair[1].getID() else True
            edge_shape = edge.getRawShape()
            nearest_x = float("inf")
            nearest_y = float("inf")
            nearest_dist = float("inf")
            
            new_shape=[]
            for x, y in edge_shape:
                dist = math.sqrt( (x - node_x)**2 + (y - node_y)**2 )
                
                if dist > node_r:
                    new_shape.append((x,y))
                
                if dist > node_r and dist < nearest_dist:
                    nearest_x = x
                    nearest_y = y
                    nearest_dist = dist
                    
            x_i, y_i = get_intersection(nearest_x, nearest_y, node_x, node_y, node_r)
            if math.sqrt( (x_i - new_shape[0][0])**2 + (y_i - new_shape[0][1])**2 ) < math.sqrt( (x_i - new_shape[-1][0])**2 + (y_i - new_shape[-1][1])**2 ):
                new_shape.insert(0, (x_i, y_i))
            else:
                new_shape.append((x_i,y_i))
            
            modified_edges[edge.getID()] = {"nearest_x" : nearest_x, "nearest_y" : nearest_y, "nearest_dist" : nearest_dist, "new_shape" : new_shape, "match" : match, "is_incoming" : is_incoming, "x_i" : x_i, "y_i" : y_i}
    return modified_edges

def get_nearest_node_id(x, y, nodes):
    nearest_id = None
    dist = float("inf")
    for n in nodes:
        new_dist = math.sqrt( (x - n.x)**2 + (y - n.y)**2 )
        if dist > new_dist:
            nearest_id = n.id
            dist = new_dist
        
    return nearest_id

def experiment(path, plain_files, net_path, new_net_path, netcnvt_bin, verbose):
    net = sumolib.net.readNet(str(path))
    
    my_node = net.getNode("498751220")
    
    node_x, node_y = my_node.getCoord()
    node_r = 20
    node_id = my_node.getID()
    
    all_edges = get_new_edge_shapes(my_node.getIncoming(), my_node.getOutgoing(), my_node, node_r)
    #outgoing_edges = get_new_edge_shapes(my_node.getOutgoing(), my_node, node_r)
    
    #all_edges = {**incoming_edges, **outgoing_edges}
    
    #################
    ############Nodes
    #################
    loaded_nodes = list(sumolib.xml.parse(plain_files["nod"], "nodes"))[0]
    
    xmlNodeClass = sumolib.xml.compound_object("node", ["id", "type", "x", "y"])
    
    new_nodes = []
    i=0
    for e_id in all_edges:
        if not all_edges[e_id]["is_incoming"]:
            continue
        new_nodes.append(xmlNodeClass(["newNode"+str(i), "priority", all_edges[e_id]["x_i"], all_edges[e_id]["y_i"]],{}))
        i+=1
    loaded_nodes.node = loaded_nodes.node + new_nodes
    
    
    keep_nodes = []
    for node in loaded_nodes.node:
        if node.id == node_id:
            continue
        keep_nodes.append(node)
    loaded_nodes.node = keep_nodes
    
    with open(plain_files["nod"], "w") as file_handle:
        file_handle.write(loaded_nodes.toXML())
    #################
    #################
    #################
    
    #################
    ############Edges
    #################
    loaded_edges = list(sumolib.xml.parse(plain_files["edg"], "edges"))[0]
    xmlEdgeClass = sumolib.xml.compound_object("edge", ["id", "from", "to", "priority", "type", "numLanes", "speed", "shape", "disallow"])
    #Change Shape
    for edge in loaded_edges.edge:
        if edge.id in all_edges:
            new_shape = ""
            for x,y in all_edges[edge.id]["new_shape"]:
                new_shape += "{},{} ".format(x, y)
            edge.shape=new_shape
    
    
    for edge in loaded_edges.edge:
        
        if edge.attr_from == node_id:
            edge.attr_from = get_nearest_node_id(all_edges[edge.id]["nearest_x"], all_edges[edge.id]["nearest_y"], new_nodes)
        elif edge.to == node_id:
            edge.to = get_nearest_node_id(all_edges[edge.id]["nearest_x"], all_edges[edge.id]["nearest_y"], new_nodes)
        
    for node in new_nodes:
        pprint(node)
        
    
    
    with open(plain_files["edg"], "w") as file_handle:
        file_handle.write(loaded_edges.toXML())
    
    #################
    #################
    #################
    
    
    
    #################
    ######Connections
    #################
    loaded_connections = list(sumolib.xml.parse(plain_files["con"], "connections"))[0]
    
    # ~ node_to_del = net.getNode(node_id)
    
    # ~ inc = node_to_del.getIncoming()
    # ~ out = node_to_del.getOutgoing()
    # ~ relevant_edges = []
    # ~ for e in inc + out:
        # ~ relevant_edges.append(e.getID())
    
    # ~ if False:
        # ~ new_connections = []
        # ~ for connection in loaded_connections.connection:
            # ~ #pprint(connection)
            # ~ if connection.attr_from in relevant_edges and connection.to in relevant_edges:
                # ~ pprint(connection)
            # ~ else:
                # ~ new_connections.append(connection)
        # ~ loaded_connections.connection = new_connections
    
    loaded_connections.connection=[]
    
    with open(plain_files["con"], "w") as file_handle:
        file_handle.write(loaded_connections.toXML())
    #################
    #################
    #################
    
    
    
    
    
    
    
    res = subprocess.run([netcnvt_bin, "-n", plain_files["nod"], "-e", plain_files["edg"],
                            "-x", plain_files["con"], "-i", plain_files["tll"], "-t", plain_files["typ"] , "-o", str(new_net_path)], capture_output=True)
    if verbose:
        print("Output from: ")
        print(*res.args, sep=" ")
        print(str(res.stderr, "utf-8"), file=sys.stderr)
        print(str(res.stdout, "utf-8"))
        print("***")
    
    #print("*")
    #for edge in loaded_edges:
    #    pprint(edge)
    #    node.type = random.choice(node_types)
    
    #roundabout_incoming = 
    #with open(new_edges_file[1], "w") as patch_file_handle: 
    #    patch_file_handle.write(nodes.toXML())

    
    
def main():
    
    PLAIN_PRFX="plain"
    random.seed()
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hkvi:o:")
    except getopt.GetoptError as err:
        print(err)
        usage(sys.argv[0])
        sys.exit(1)
    
    options_present = print_help = param_net_path = param_new_net_path = switch_keep_temp = switch_verbose = False
    for o, a in opts:
        options_present=True
        if o == "-h":
            print_help = True
        elif o == "-i":
            param_net_path = a
        elif o == "-o":
            param_new_net_path = a
        elif o == "-k":
            switch_keep_temp = True
        elif o =="-v":
            switch_verbose=True
            
    if print_help:
        my_help(sys.argv[0])
        sys.exit(0)
    
    if not options_present:
        usage(sys.argv[0])
        sys.exit(1)
    
    if not param_net_path or not param_new_net_path:
        usage(sys.argv[0])
        sys.exit(1)
    
    net_path = Path(param_net_path).resolve()
    #net_path = Path('minimal_invalid.net.xml').resolve()
    if not net_path.exists() or net_path.is_dir():
        sys.exit("Netz nicht gefunden")
    
    #load netconvert binary
    netcnvt_bin = load_netconvert_binary()
    
    #Disassemble net
    try:
        plain_path, plain_files = cnvt_net_to_plain(net_path, netcnvt_bin, PLAIN_PRFX, switch_verbose)
    except ValueError:
        sys.exit("Keine gültige .net.xml Datei spezifiziert.")
    
    new_net_path = Path(param_new_net_path).resolve()
    
    # ~ new_edges_file = get_tmp_file_for_patch(plain_path)
    # ~ new_nodes_file = get_tmp_file_for_patch(plain_path)
    # ~ new_connections_file = get_tmp_file_for_patch(plain_path)
    
    ###
    #random_node_types(plain_files, patch_file, net_path, new_net_path, netcnvt_bin, switch_verbose)
    ###
    experiment(net_path, plain_files, net_path, new_net_path, netcnvt_bin, switch_verbose)
    ###
    
    if not switch_keep_temp:
        rm_tmpd_and_files(plain_path)
    

if __name__=="__main__":
    main()
