#!/usr/bin/env python3

from pprint import pprint
import os
import sys
import subprocess
from pathlib import Path
import tempfile
import math
import uuid

if "SUMO_HOME" in os.environ:
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)
else:
    sys.exit("Umgebungsvariable 'SUMO_HOME' setzen.")

import sumolib

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

# ~ def get_all_nodes(plain_files):
    # ~ loaded_nodes = list(sumolib.xml.parse(plain_files["nod"], "nodes"))[0]
    # ~ net_nodes = {}
    # ~ if not loaded_nodes.node:
        # ~ return net_nodes
    # ~ for node in loaded_nodes.node:
        # ~ net_nodes[node.id] = node
    # ~ return net_nodes
    
# ~ def get_all_edges(plain_files):
    # ~ loaded_edges = list(sumolib.xml.parse(plain_files["edg"], "edges"))[0]
    # ~ net_edges = {}
    # ~ if not loaded_edges.edge:
        # ~ return net_edges
    # ~ for edge in loaded_edges.edge:
        # ~ net_edges[edge.id] = edge
    # ~ return net_edges
    
# ~ def get_all_connections(plain_files):
    # ~ loaded_connections = list(sumolib.xml.parse(plain_files["con"], "connections"))[0]
    # ~ net_connections = []
    # ~ if not loaded_connections.connection:
        # ~ return net_connections
    # ~ for connection in loaded_connections.connection:
        # ~ net_connections.append(connection)
    # ~ return net_connections

# ~ def get_all_roundabouts(plain_files):
    # ~ loaded_edges = list(sumolib.xml.parse(plain_files["edg"], "edges"))[0]
    # ~ net_roundabouts = []
    # ~ if not loaded_edges.roundabout:
        # ~ return net_roundabouts
    # ~ for roundabout in loaded_edges.roundabout:
        # ~ net_roundabouts.append(roundabout)
    # ~ return net_roundabouts

class Net_Repr:
    
    net_nodes = {}
    
    net_edges = {}
    net_edges_from_idx = {}
    net_edges_to_idx = {}
    
    net_roundabouts = {}
    net_roundabouts_edges_nodes_idx = {}
    
    net_connections = {}
    net_connections_from_to_idx = {}
    
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
                self.net_connections_from_to_idx["{} {}".format(connection.attr_from,connection.to)] = art_id
                
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
    
    def get_connection_art_id_by_from_to(self, from_edge_id, to_edge_id):
        key = "{} {}".format(from_edge_id,to_edge_id)
        if key in self.net_connections_from_to_idx:
            return self.net_connections_from_to_idx[key]
        else:
            return None
        
    def remove_connection_by_art_id(self, connection_art_id):
        connection = self.net_connections[connection_art_id]
        
        del self.net_connections[connection_art_id]
        del self.net_connections_from_to_idx["{} {}".format(connection.attr_from,connection.to)]
        
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
        
    
# ~ def get_incoming(node_id, net_edges):
    # ~ incoming = []
    # ~ for _, e in net_edges.items():
        # ~ if e.to == node_id:
            # ~ incoming.append(e)
    # ~ return incoming

# ~ def get_outgoing(node_id, net_edges):
    # ~ outgoing = []
    # ~ for e_id, e in net_edges.items():
        # ~ if e.attr_from == node_id:
            # ~ outgoing.append(e)
    # ~ return outgoing

# ~ def edge_get_shape(edge):
    # ~ shape = []
    # ~ for coord_pair in edge.shape.split(" "):
        # ~ if coord_pair:
            # ~ x,y = coord_pair.split(",")
            # ~ shape.append((float(x),float(y)))
    # ~ return shape

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
def get_new_edge_shapes(nr, my_node, node_r):
    
    modified_edges = {}
    
    edges = []
    
    inc = nr.get_edge_incoming_ids(my_node.id)
    out = nr.get_edge_outgoing_ids(my_node.id)
    
    for e_id in inc:
        i = nr.net_edges[e_id]
        edges.append((i, True))
        
        pair=None
        for o_id in out:
            o = nr.net_edges[o_id]
            if o.to == i.attr_from and o.attr_from == i.to:
                pair = o
                break
        if pair:
            edges.append((pair, False))
            out.remove(o_id)

    for o_id in out:
        o = nr.net_edges[o_id]
        edges.append((o, True))
    
    node_x, node_y = float(my_node.x), float(my_node.y)
    
    for edge, needs_node in edges:
            
        # ~ edge_shape = edge_get_shape(edge)
        edge_shape = nr.get_edge_shape(edge.id)
        
        if len(edge_shape) == 0:
            f_node = nr.net_nodes[edge.attr_from]
            t_node = nr.net_nodes[edge.to]
            edge_shape = [(float(f_node.x),float(f_node.y)),(float(t_node.x),float(t_node.y))]
        
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
        if len(new_shape) == 0:
            new_shape = [(x_i, y_i)]
        elif math.sqrt( (x_i - new_shape[0][0])**2 + (y_i - new_shape[0][1])**2 ) < math.sqrt( (x_i - new_shape[-1][0])**2 + (y_i - new_shape[-1][1])**2 ):
            new_shape.insert(0, (x_i, y_i))
        else:
            new_shape.append((x_i,y_i))
        
        modified_edges[edge.id] = {"nearest_x" : nearest_x, "nearest_y" : nearest_y, "nearest_dist" : nearest_dist, "new_shape" : new_shape, "needs_node" : needs_node, "x_i" : x_i, "y_i" : y_i}
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
def create_new_nodes(nr, node_id, modified_edges):
    
    new_nodes = []
    for e_id in modified_edges:
        if not modified_edges[e_id]["needs_node"]:
            continue
        new_nodes.append(nr.xmlNodeClass(["Node"+uuid.uuid4().hex, "priority", modified_edges[e_id]["x_i"], modified_edges[e_id]["y_i"]],{}))
    nr.add_new_nodes(new_nodes)
    
    return new_nodes

def create_new_edges(nr, node_id, node_x, node_y, node_r, new_nodes, modified_edges):
    
    #Shape steps in a full circle
    shape_steps_on_full_circle = 40
    
    for edge_id, data in modified_edges.items():
        new_shape = ""
        for x,y in data["new_shape"]:
            new_shape += "{},{} ".format(x, y)
        nr.net_edges[edge_id].shape = new_shape
    
    #Substitute to or from with a matching new node, created by create_new_nodes_and_delete_old_node(...)
    connection_relevant_edge_ids=[]
    for e_id in nr.get_edge_incoming_ids(node_id):
        nr.set_edge_to(e_id, get_nearest_node_id(modified_edges[e_id]["nearest_x"], modified_edges[e_id]["nearest_y"], new_nodes))
        connection_relevant_edge_ids.append(e_id)
    for e_id in nr.get_edge_outgoing_ids(node_id):
        nr.set_edge_from(e_id, get_nearest_node_id(modified_edges[e_id]["nearest_x"], modified_edges[e_id]["nearest_y"], new_nodes))
        connection_relevant_edge_ids.append(e_id)
        
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
        new_edge = nr.xmlEdgeClass(["tram rail_urban rail rail_electric ship", sid, "Edge"+uuid.uuid4().hex, "1", "9", shape_str, "13.89", eid, "highway.primary"], {})
        new_edges.append(new_edge)
    
    nr.add_new_edges(new_edges)
    
    # add the new edges and nodes to a roundabout in xml
    roundabout_edge_str = ""
    for e in new_edges:
        roundabout_edge_str = "{} {}".format(roundabout_edge_str, e.id)
        
    roundabout_node_str = ""
    for n in new_nodes:
        roundabout_node_str = "{} {}".format(roundabout_node_str, n.id)
    
    new_roundabout = nr.xmlRoundaboutClass([roundabout_edge_str, roundabout_node_str],{})
    nr.add_new_roundabout(new_roundabout)
    
    return new_edges, connection_relevant_edge_ids

def delete_unneeded_connections(nr, connection_relevant_edge_ids):
    
    for e_id_A in connection_relevant_edge_ids:
        for e_id_B in connection_relevant_edge_ids:
            art_id = nr.get_connection_art_id_by_from_to(e_id_A, e_id_B)
            if art_id:
                nr.remove_connection_by_art_id(art_id)
            art_id = nr.get_connection_art_id_by_from_to(e_id_B, e_id_A)
            if art_id:
                nr.remove_connection_by_art_id(art_id)

def hack_for_cologne(plain_files):
    #hack for cologne
    with open(plain_files["tll"], "w") as file_handle:
        file_handle.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<tlLogics version=\"1.1\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"http://sumo.dlr.de/xsd/tllogic_file.xsd\">\n</tlLogics>")
    

def change_node_to_roundabout(change_node_id_to_roundabout, nr, radius = 20):
    
    my_node = nr.net_nodes[change_node_id_to_roundabout]
    node_x, node_y = float(my_node.x), float(my_node.y)
    node_r = radius
    node_id = my_node.id
    

    modified_edges = get_new_edge_shapes(nr, my_node, node_r)

    new_nodes = create_new_nodes(nr, node_id, modified_edges)

    nr.remove_nodes_by_id([node_id])
   
    new_edges,connection_relevant_edge_ids = create_new_edges(nr, node_id, node_x, node_y, node_r, new_nodes, modified_edges)
    
    delete_unneeded_connections(nr, connection_relevant_edge_ids)
    
def get_roundabout_center(roundabout_nodes):
    A, B, C, *_ = roundabout_nodes
    xA = float(roundabout_nodes[A].x)
    yA = float(roundabout_nodes[A].y)
    xB = float(roundabout_nodes[B].x)
    yB = float(roundabout_nodes[B].y)
    xC = float(roundabout_nodes[C].x)
    yC = float(roundabout_nodes[C].y)
    d_x_1 = xB - xA
    d_y_1 = yB - yA
    d_x_2 = xC - xB
    d_y_2 = yC - yB
    
    s1 = d_y_1 / d_x_1
    s2 = d_y_2 / d_x_2
    
    cx = ( s1*s2*(yA - yC) + s2*(xA + xB) - s1*(xB + xC) ) / ( 2 * (s2 - s1) )
    cy = -1 * ( cx - (xA + xB) /2 ) / s1 + (yA + yB)/2
    
    return (cx, cy)
    
def create_new_node_and_delete_old_nodes(nr, new_node_x, new_node_y, roundabout_nodes):
    
    new_node = nr.xmlNodeClass(["Node"+uuid.uuid4().hex, "priority", new_node_x, new_node_y],{})
    
    nr.add_new_nodes([new_node])
    
    nr.remove_nodes_by_id(roundabout_nodes)
    
    return new_node

def change_shapes_and_connected_nodes(nr, roundabout_nodes, roundabout_edges, new_node):
    modified_edges = {}
    
    external_edges=[]
    for n_id, node in roundabout_nodes.items():
        all_edges = nr.get_edge_incoming_ids(n_id) + nr.get_edge_outgoing_ids(n_id)
        external_edges += list(filter(lambda x : x not in roundabout_edges, all_edges))
        
    for e_id in external_edges:
        edge = nr.net_edges[e_id]
        new_shape = nr.get_edge_shape(e_id)
        
        if edge.attr_from in roundabout_nodes:
            from_node = new_node.id
            to_node = edge.to
            new_shape.insert(0, (new_node.x, new_node.y))
        elif edge.to in roundabout_nodes:
            to_node = new_node.id
            from_node = edge.attr_from
            new_shape.append((new_node.x, new_node.y))
            
        modified_edges[edge.id] = {"from_node": from_node, "to_node": to_node, "new_shape": new_shape}
        
    return modified_edges

def delete_unneeded_edges_and_roundabout(nr, modified_edges, roundabout_edges, roundabout_edge_ids_str, roundabout_node_ids_str):
    
    for e_id, data in modified_edges.items():
        edge = nr.net_edges[e_id]
        new_shape = ""
        
        for x,y in data["new_shape"]:
            new_shape += "{},{} ".format(x,y)
        edge.shape = new_shape
        
        nr.set_edge_from(edge.id, data["from_node"])
        nr.set_edge_to(edge.id, data["to_node"])
            
    for e_id in roundabout_edges:
        nr.remove_edge_by_id(e_id)
    
    roundabout_art_id = nr.get_roundabout_art_idx_by_edges_nodes(roundabout_edge_ids_str, roundabout_node_ids_str)
    if roundabout_art_id:
        nr.remove_roundabout_by_art_id(roundabout_art_id)
    
# ~ def delete_connections_belonging_to_removed_edges(deleted_edge_ids, plain_files):
    # ~ loaded_connections = list(sumolib.xml.parse(plain_files["con"], "connections"))[0]
    
    # ~ keep_connections = []
    # ~ for connection in loaded_connections.connection:
        # ~ if connection.attr_from in deleted_edge_ids or connection.to in deleted_edge_ids:
            # ~ continue
        # ~ keep_connections.append(connection)
    # ~ loaded_connections.connection = keep_connections
    
    # ~ with open(plain_files["con"], "w") as file_handle:
        # ~ file_handle.write(loaded_connections.toXML())
    # ~ return True

def change_roundabout_to_node(roundabout_edge_ids_str, roundabout_node_ids_str, nr):
    
    roundabout_nodes = {}
    for n_id in roundabout_node_ids_str.split(" "):
        roundabout_nodes[n_id] = nr.net_nodes[n_id]
    
    roundabout_edges = {}
    for e_id in roundabout_edge_ids_str.split(" "):
        roundabout_edges[e_id] = nr.net_edges[e_id]
    
    connection_relevant_edge_ids = []
    for n_id in roundabout_nodes:
        connection_relevant_edge_ids = connection_relevant_edge_ids + nr.get_edge_incoming_ids(n_id) + nr.get_edge_outgoing_ids(n_id)
    
    new_node_x, new_node_y = get_roundabout_center(roundabout_nodes)
    
    new_node = create_new_node_and_delete_old_nodes(nr, new_node_x, new_node_y, roundabout_nodes)
   
    modified_edges = change_shapes_and_connected_nodes(nr, roundabout_nodes, roundabout_edges, new_node)
    
    delete_unneeded_edges_and_roundabout(nr, modified_edges, roundabout_edges, roundabout_edge_ids_str, roundabout_node_ids_str)
    
    delete_unneeded_connections(nr, connection_relevant_edge_ids)
    

#Vorfahrsregeln ändern Rechts-vor-Links, Priorität für eine Straße
#Ampeln (evtl.)
