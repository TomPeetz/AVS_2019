#!/usr/bin/env python3

from pprint import pprint
import os
import sys
import subprocess
from pathlib import Path
import tempfile
import math

if "SUMO_HOME" in os.environ:
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)
else:
    sys.exit("Umgebungsvariable 'SUMO_HOME' setzen.")

import sumolib

#global counter for unique ids
mod_map_py__glbl_cntr = 0

def glbl_cntr_get_next():
    global mod_map_py__glbl_cntr
    mod_map_py__glbl_cntr += 1
    return mod_map_py__glbl_cntr

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
    
#Create temporary file
def get_tmp_file_for_patch(tmpd):
    tmpf = tempfile.mkstemp(prefix="patch_", suffix=".xml", dir=tmpd, text=True)
    return tmpf
  
#Change Node to Roundabout: get coordinates of intersection between line from l through middle of circle c, r=radius of circle
def get_intersection(lx, ly, cx, cy, r):
    a = ly - cy
    b = cx - lx
    c = cx*ly - lx*cy
    x_1 = cx + ( a*(c - a*cx - b*cy) + b * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    x_2 = cx + ( a*(c - a*cx - b*cy) - b * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    y_2 = cy + ( b*(c - a*cx - b*cy) + a * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    y_1 = cy + ( b*(c - a*cx - b*cy) - a * math.sqrt( r**2 * (a**2 + b**2) - (c - a*cx - b*cy)**2 ) / ( a**2 + b**2 ) )
    #there are two intersections, return only the one closer to l
    return (x_1,y_1) if math.sqrt( (x_1 - lx)**2 + (y_1 - ly)**2 ) < math.sqrt( (x_2 - lx)**2 + (y_2 - ly)**2 ) else (x_2,y_2)

#remove all coordinates from edge shape, which would lie in the roundabout, and make a new end coordinate on the roundabout
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
                    
            #get new end coord
            x_i, y_i = get_intersection(nearest_x, nearest_y, node_x, node_y, node_r)
            #insert the coords at the right end of the list (prior or after the closes existing coord)
            if math.sqrt( (x_i - new_shape[0][0])**2 + (y_i - new_shape[0][1])**2 ) < math.sqrt( (x_i - new_shape[-1][0])**2 + (y_i - new_shape[-1][1])**2 ):
                new_shape.insert(0, (x_i, y_i))
            else:
                new_shape.append((x_i,y_i))
            
            modified_edges[edge.getID()] = {"nearest_x" : nearest_x, "nearest_y" : nearest_y, "nearest_dist" : nearest_dist, "new_shape" : new_shape, "match" : match, "is_incoming" : is_incoming, "x_i" : x_i, "y_i" : y_i}
    #return dict with key = id
    return modified_edges

#get the node from nodes list, that is closest to given x and y
def get_nearest_node_id(x, y, nodes):
    nearest_id = None
    dist = float("inf")
    for n in nodes:
        new_dist = math.sqrt( (x - n.x)**2 + (y - n.y)**2 )
        if dist > new_dist:
            nearest_id = n.id
            dist = new_dist
        
    #return only the id
    return nearest_id

#split a circle in 4 sectors
def get_sectors(cx, cy, r):
    xA = cx + r * math.cos(0)
    yA = cy + r * math.sin(0)
    xB = cx + r * math.cos(math.pi/2)
    yB = cy + r * math.sin(math.pi/2)
    xC = cx + r * math.cos(math.pi)
    yC = cy + r * math.sin(math.pi)
    xD = cx + r * math.cos(3*math.pi/2)
    yD = cy + r * math.sin(3*math.pi/2)
    
    return (xA, yA, xB, yB, xC, yC, xD, yD)

#calculate in which sector a point on a circle lies, and how far it is from the start of the sector
def in_sector_and_distance_from(x, y, xS):
    #xS should be obtained with get_sectors(...)
    xA, yA, xB, yB, xC, yC, xD, yD = xS
    
    if y >= yA and x > xB:
        d = math.sqrt( (x - xA)**2 + (y - yA)**2 )
        return (1,d)
    if x <= xB and y > yC:
        d = math.sqrt( (x - xB)**2 + (y - yB)**2 )
        return (2,d)
    if y <= yC and x < xD:
        d = math.sqrt( (x - xC)**2 + (y - yC)**2 )
        return (3,d)
    if x >= xD and y < yA:
        d = math.sqrt( (x - xD)**2 + (y - yD)**2 )
        return (4,d)
    return None
    
#order point on a circle counterclockwise, start with the first point in sector 0 (0 - 90 degrees)
def order_on_circle(c,xS):
    start=None
    inA=[]
    inB=[]
    inC=[]
    inD=[]
    
    for p in c:
        x,y,*_ = p
        #xS should be obtained with get_sectors(...)
        s, d = in_sector_and_distance_from(x, y, xS)
        if s == 1:
            inA.append((*p, d))
        if s == 2:
            inB.append((*p, d))
        if s == 3:
            inC.append((*p, d))
        if s == 4:
            inD.append((*p, d))
    
    inA.sort(key=lambda x : x[-1])
    inB.sort(key=lambda x : x[-1])
    inC.sort(key=lambda x : x[-1])
    inD.sort(key=lambda x : x[-1])
    l = inA+inB+inC+inD
    return l

#get the counterclockwise degree from 3 o clock (0 degrees) line on a circle. r = radius of circle, x,y coords of point
def get_theta_on_circle(r, x, y, xS):
    #xS should be obtained with get_sectors(...)
    xA, yA, xB, yB, xC, yC, xD, yD = xS
    
    s,_ = in_sector_and_distance_from(x, y, xS)
    #initialize with the degree given by the sector
    x0 = xA
    y0 = yA
    theta=0
    if s == 2:
        x0 = xB
        y0 = yB
        theta = math.pi/2
    if s == 3:
        x0 = xC
        y0 = yC
        theta = math.pi
    if s == 4:
        x0 = xD
        y0 = yD
        theta = 3*math.pi/2
        
    #add degrees from the start of the sector
    c = math.sqrt( (x - x0)**2 + (y - y0)**2 )
    if c != 0:
        add = 2 * math.asin( c / (2*r) )
        theta += add
    
    return theta

#Create new nodes for the roundabout and delete the no longer needed original node
def create_new_nodes_and_delete_old_node(node_id, all_edges, plain_files):
    xmlNodeClass = sumolib.xml.compound_object("node", ["id", "type", "x", "y"])
    
    loaded_nodes = list(sumolib.xml.parse(plain_files["nod"], "nodes"))[0]
    
    new_nodes = []
    for e_id in all_edges:
        if not all_edges[e_id]["is_incoming"]:
            continue
        new_nodes.append(xmlNodeClass(["newNode"+str(glbl_cntr_get_next()), "priority", all_edges[e_id]["x_i"], all_edges[e_id]["y_i"]],{}))
    loaded_nodes.node = loaded_nodes.node + new_nodes
    
    deleted_node_id = None
    keep_nodes = []
    for node in loaded_nodes.node:
        if node.id == node_id:
            deleted_node_id = node.id
            continue
        keep_nodes.append(node)
    loaded_nodes.node = keep_nodes
    
    with open(plain_files["nod"], "w") as file_handle:
        file_handle.write(loaded_nodes.toXML())
    
    return new_nodes, deleted_node_id

def create_new_edges(node_id, node_x, node_y, node_r, new_nodes, all_edges, plain_files):
    xmlEdgeClass = sumolib.xml.compound_object("edge", ["id", "from", "to", "priority", "type", "numLanes", "speed", "shape", "disallow"])
    xmlRoundaboutClass = sumolib.xml.compound_object("roundabout", ["nodes", "edges"])
    
    #Shape steps in a full circle
    shape_steps_on_full_circle = 40
    
    loaded_edges = list(sumolib.xml.parse(plain_files["edg"], "edges"))[0]
    
    #Change Shape
    for edge in loaded_edges.edge:
        if edge.id in all_edges:
            new_shape = ""
            for x,y in all_edges[edge.id]["new_shape"]:
                new_shape += "{},{} ".format(x, y)
            edge.shape=new_shape
    
    #Substitute to or from with a matching new node, created by create_new_nodes_and_delete_old_node(...)
    for edge in loaded_edges.edge:
        if edge.attr_from == node_id:
            edge.attr_from = get_nearest_node_id(all_edges[edge.id]["nearest_x"], all_edges[edge.id]["nearest_y"], new_nodes)
        elif edge.to == node_id:
            edge.to = get_nearest_node_id(all_edges[edge.id]["nearest_x"], all_edges[edge.id]["nearest_y"], new_nodes)
        
    #Create new edges for the roundabout and the needed shapes
    #Calculate circle segments
    xS = get_sectors(node_x, node_y, node_r)
    
    step=(2*math.pi)/shape_steps_on_full_circle
    
    #representation of the new nodes which is easier to handle
    nodes_e = []
    for node in new_nodes:
        nodes_e.append( (float(node.x), float(node.y), node.id) )
        
    nodes_e = order_on_circle(nodes_e, xS)
    
    new_edges=[]
    for i in range(len(nodes_e)):
        sx, sy, sid, *_ = nodes_e[i]
        ex, ey, eid, *_ = nodes_e[(i+1) % len(nodes_e)]
        
        s_arc = get_theta_on_circle(node_r, sx, sy, xS)
        e_arc = get_theta_on_circle(node_r, ex, ey, xS)
        
        shape=[]
        arc = s_arc
        #the last node needs to be connected to the first one which results in a crossing of the 0 degrees border
        if e_arc < s_arc:
            e_arc_tmp = 2*math.pi
            arc = s_arc
            while arc < e_arc_tmp:
                shape_x = node_x + node_r * math.cos(arc)
                shape_y = node_y + node_r * math.sin(arc)
                arc += step
                shape.append((shape_x,shape_y))
            arc = 0
        #calculate shape
        while arc < e_arc:
            shape_x = node_x + node_r * math.cos(arc)
            shape_y = node_y + node_r * math.sin(arc)
            arc += step
            shape.append((shape_x,shape_y))
        
        #change shape list to string for xml
        shape_str = ""
        for x,y in shape:
            shape_str += "{},{} ".format(x, y)
        new_edge = xmlEdgeClass(["tram rail_urban rail rail_electric ship", sid, "newEdge"+str(glbl_cntr_get_next()), "1", "9", shape_str, "13.89", eid, "highway.primary"], {})
        new_edges.append(new_edge)
    
    loaded_edges.edge = loaded_edges.edge + new_edges
    
    # add the new edges and nodes to a roundabout in xml
    roundabout_edge_str = ""
    for e in new_edges:
        roundabout_edge_str = "{} {}".format(roundabout_edge_str, e.id)
        
    roundabout_node_str = ""
    for n in new_nodes:
        roundabout_node_str = "{} {}".format(roundabout_node_str, n.id)
    
    new_roundabout = xmlRoundaboutClass([roundabout_edge_str, roundabout_node_str],{})
    loaded_edges.roundabout += [new_roundabout]
    
    #write to file
    with open(plain_files["edg"], "w") as file_handle:
        file_handle.write(loaded_edges.toXML())
    
    return new_edges

def delete_unneeded_connections(net, deleted_node_id, plain_files):
    loaded_connections = list(sumolib.xml.parse(plain_files["con"], "connections"))[0]
    
    deleted_node = net.getNode(deleted_node_id)
    
    inc = deleted_node.getIncoming()
    out = deleted_node.getOutgoing()
    relevant_edges = []
    for e in inc + out:
        relevant_edges.append(e.getID())
    
        keep_connections = []
        for connection in loaded_connections.connection:
            if connection.attr_from in relevant_edges and connection.to in relevant_edges:
                continue
            keep_connections.append(connection)
        loaded_connections.connection = keep_connections
    
    with open(plain_files["con"], "w") as file_handle:
        file_handle.write(loaded_connections.toXML())
    
    return True

def change_node_to_roundabout(change_node_id_to_roundabout, path, plain_files, radius = 20):
    net = sumolib.net.readNet(str(path))
    
    my_node = net.getNode(change_node_id_to_roundabout)
    node_x, node_y = my_node.getCoord()
    node_r = radius
    node_id = my_node.getID()
    
    #Change relevant edges
    all_edges = get_new_edge_shapes(my_node.getIncoming(), my_node.getOutgoing(), my_node, node_r)
    
    #Create needed new nodes, writing them directly to file
    new_nodes, deleted_node_id = create_new_nodes_and_delete_old_node(node_id, all_edges, plain_files)
    
    new_edges = create_new_edges(node_id, node_x, node_y, node_r, new_nodes, all_edges, plain_files)
    
    delete_unneeded_connections(net, deleted_node_id, plain_files)

def get_roundabout_center(roundabout_nodes):
    A, B, C, *_ = roundabout_nodes
    xA,yA = roundabout_nodes[A].getCoord()
    xB,yB = roundabout_nodes[B].getCoord()
    xC,yC = roundabout_nodes[C].getCoord()
    
    d_x_1 = xB - xA
    d_y_1 = yB - yA
    d_x_2 = xC - xB
    d_y_2 = yC - yB
    
    s1 = d_y_1 / d_x_1
    s2 = d_y_2 / d_x_2
    
    cx = ( s1*s2*(yA - yC) + s2*(xA + xB) - s1*(xB + xC) ) / ( 2 * (s2 - s1) )
    cy = -1 * ( cx - (xA + xB) /2 ) / s1 + (yA + yB)/2
    
    return (cx, cy)
    
def create_new_node_and_delete_old_nodes(new_node_x, new_node_y, roundabout_nodes, plain_files):
    xmlNodeClass = sumolib.xml.compound_object("node", ["id", "type", "x", "y"])
    
    loaded_nodes = list(sumolib.xml.parse(plain_files["nod"], "nodes"))[0]
    
    new_node = xmlNodeClass(["newNode"+str(glbl_cntr_get_next()), "priority", new_node_x, new_node_y],{})
    
    loaded_nodes.node = loaded_nodes.node + [new_node]
    
    keep_nodes = []
    deleted_node_ids = []
    
    for node in loaded_nodes.node:
        if node.id in roundabout_nodes:
            deleted_node_ids.append(node.id)
            continue
        keep_nodes.append(node)
    loaded_nodes.node = keep_nodes
    
    with open(plain_files["nod"], "w") as file_handle:
        file_handle.write(loaded_nodes.toXML())
    
    return new_node, deleted_node_ids

def change_shapes_and_connected_nodes(roundabout_nodes, roundabout_edges, new_node):
    modified_edges = dict()
    
    external_edges=[]
    for n_id in roundabout_nodes:
        node  = roundabout_nodes[n_id]
        all_edges = node.getIncoming() + node.getOutgoing()
        external_edges += list(filter(lambda x : x.getID() not in roundabout_edges, all_edges))
        
    for edge in external_edges:
        new_shape = edge.getRawShape()
        if edge.getFromNode().getID() in roundabout_nodes:
            from_node = new_node.id
            to_node = edge.getToNode().getID()
            new_shape.insert(0, (new_node.x, new_node.y))
        elif edge.getToNode().getID() in roundabout_nodes:
            to_node = new_node.id
            from_node = edge.getFromNode().getID()
            new_shape.append((new_node.x, new_node.y))
            
        modified_edges[edge.getID()] = {"from_node": from_node, "to_node": to_node, "new_shape": new_shape}
        
    return modified_edges

def delete_unneeded_edges_and_roundabout(modified_edges, roundabout_edges, roundabout_nodes, plain_files):
    xmlEdgeClass = sumolib.xml.compound_object("edge", ["id", "from", "to", "priority", "type", "numLanes", "speed", "shape", "disallow"])
    xmlRoundaboutClass = sumolib.xml.compound_object("roundabout", ["nodes", "edges"])
    
    loaded_edges = list(sumolib.xml.parse(plain_files["edg"], "edges"))[0]
    
    for edge in loaded_edges.edge:
        if edge.id in modified_edges:
            new_shape = ""
            for x,y in modified_edges[edge.id]["new_shape"]:
                new_shape += "{},{} ".format(x, y)
            edge.shape=new_shape
            edge.to = modified_edges[edge.id]["to_node"]
            edge.attr_from = modified_edges[edge.id]["from_node"]
            
            
    deleted_edge_ids = []
    keep_edges = []
    for edge in loaded_edges.edge:
        if edge.id in roundabout_edges:
            deleted_edge_ids.append(edge.id)
            continue
        keep_edges.append(edge)
    loaded_edges.edge = keep_edges
    
    keep_roundabouts = []
    for roundabout in loaded_edges.roundabout:
        delete = True
        for n_id in roundabout.nodes.split(" "):
            if n_id not in roundabout_nodes:
                delete = False
        for e_id in roundabout.edges.split(" "):
            if e_id not in roundabout_edges:
                delete = False
        if delete:
            continue
        keep_roundabouts.append(roundabout)
    loaded_edges.roundabout = keep_roundabouts
    
    #write to file
    with open(plain_files["edg"], "w") as file_handle:
        file_handle.write(loaded_edges.toXML())
        
    return deleted_edge_ids

def delete_connections_belonging_to_removed_edges(deleted_edge_ids, plain_files):
    loaded_connections = list(sumolib.xml.parse(plain_files["con"], "connections"))[0]
    
    keep_connections = []
    for connection in loaded_connections.connection:
        if connection.attr_from in deleted_edge_ids or connection.to in deleted_edge_ids:
            continue
        keep_connections.append(connection)
    loaded_connections.connection = keep_connections
    
    with open(plain_files["con"], "w") as file_handle:
        file_handle.write(loaded_connections.toXML())
    return True

def change_roundabout_to_node(roundabout_edge_ids, roundabout_node_ids, path, plain_files):
    net = sumolib.net.readNet(str(path))
    
    #identify external edges
    roundabout_nodes = dict()
    for n_id in roundabout_node_ids:
        roundabout_nodes[n_id] = net.getNode(n_id)
    
    roundabout_edges = dict()
    for e_id in roundabout_edge_ids:
        roundabout_edges[e_id] = net.getEdge(e_id)
    
    new_node_x, new_node_y = get_roundabout_center(roundabout_nodes)
    
    new_node, deleted_node_ids = create_new_node_and_delete_old_nodes(new_node_x, new_node_y, roundabout_nodes, plain_files)
    
    modified_edges = change_shapes_and_connected_nodes(roundabout_nodes, roundabout_edges, new_node)
    
    deleted_edge_ids = delete_unneeded_edges_and_roundabout(modified_edges, roundabout_edges, roundabout_nodes, plain_files)
    
    delete_connections_belonging_to_removed_edges(deleted_edge_ids, plain_files)
    