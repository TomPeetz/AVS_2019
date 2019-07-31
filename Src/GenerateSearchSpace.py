import json
from os import path

import os, sys

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib

netxml = path.abspath(path.join("..", "Experimente/Netconvert_Mit_Python/Maps/Minimal/SUMO_Netz/minimal.net.xml"))
net = sumolib.net.readNet(str(netxml))

nodes = net.getNodes()
ranodes = []

roundabouts = []
for ra in net.getRoundabouts():
    ranodes.extend(ra.getNodes())
    roundabouts.append({'id': '-'.join(ra.getNodes()), 'nodes': ra.getNodes(), 'edges': ra.getEdges(), 'allowedModifications': ['intersection_priority', 'roundabout']})

intersections = []

for node in nodes:
    if len(node.getIncoming()) < 2 and len(node.getOutgoing()) < 2: continue
    if node.getID() in ranodes: continue
    intersections.append({'id': node.getID(), 'currentType': node.getType(), 'allowedModifications': ['intersection_priority', 'roundabout']})

    print("ID: %s, Type: %s,Incoming: %d, Outgoing: %d" % (node.getID(), node.getType(), len(node.getIncoming()), len(node.getOutgoing())))


searchspace = {}
searchspace['intersections'] = intersections
searchspace['roundabouts'] = roundabouts

json_data = json.dumps(searchspace)

with open('searchspace.json', 'w') as f:
    f.write(json_data)

print(searchspace)