import ModMap
import sumolib
import json

netxml = "/home/dennnis/avs/AVS_2019/Experimente/Netconvert_Mit_Python/Maps/Minimal/SUMO_Netz/minimal.net.xml"
net = sumolib.net.readNet(str(netxml))

#netconvert = ModMap.load_netconvert_binary()
#print(netconvert)

#tmpd, plain_files = ModMap.cnvt_net_to_plain(net_path = "/home/dennnis/avs/AVS_2019/Experimente/Netconvert_Mit_Python/Maps/Minimal/SUMO_Netz/minimal.net.xml",
#                         netcnvt_bin = netconvert,
#                         plain_output_prefix = "test",
#                         verbose=True)
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

#print(nodes)
print(searchspace)