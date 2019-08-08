#!/usr/bin/env python3

############
# $./testModMap.py -i ../Experimente/Netconvert_Mit_Python/Maps/Minimal/SUMO_Netz/minimal.net.xml -o new.net.xml -k -v
############

from pprint import pprint
import random
from ModMap import *
from pathlib import Path
import sys
import getopt
import time
import json
import tempfile
import subprocess

def usage(p):
    print("Benutzung: {0} -h (Hilfe) | <Optionen>".format(p))

def my_help(p):
    usage(p)
    print("-h: Diese Hilfe anzeigen und beenden.")
    print("-i <original.net.xml>: Original .net.xml Datei. Erforderlich.")
    print("-o <modifiziert.net.xml>: Ausgabe .net.xml Datei. Erforderlich.")
    print("-k: Temporäre Dateien nicht löschen.")
    print("-v: Mehr Meldungen.")
    
#testing only
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
    
    #A
    # ~ change_roundabout_to_node(["26697422#0","26697422#1","26697422#2"], ["292785669","292785688","76182923"], net_path, plain_files)
    # ~ change_node_to_roundabout("498751220", net_path, plain_files)
    # ~ change_node_to_roundabout("cluster_498751183_996951775", net_path, plain_files)
    # ~ change_node_to_roundabout("996951907", net_path, plain_files)
    # ~ change_node_to_roundabout("996951809", net_path, plain_files)
    
    #B
    # ~ change_roundabout_to_node(["Edge20f6c6a95e204dd99f62efb1866f3002","Edge3d7222dcbda24ed4be98e935738b2e13","Edge6f6073efa02746de98b090434ffab635","Edgec8ec2c924765497ba1f2a3728c7d871d"], ["Node06bf3b82c14c436e93cc5b9deee9e002","Node122bc02d676a438e9501e5fb38305d22","Node137942f40ce548c5b3f2471fcf963d0f","Nodeb2a27d4a77674d22a93bfb54390f18e0"], net_path, plain_files)
    # ~ change_roundabout_to_node(["Edge58d840ec24ca4472ac5b24efb8816a44","Edge9cb14ecb7a3a4371aed0ba6f6334b05b","Edgec67c6f70e9d448d3b2d0e0732c53b5c5"], ["Node2295e5e38ad54248aad6d754171d6995","Node8afc0e4a3de8485a84a8bae231bf304a","Nodefe82e052b36e4e2d9a1a3c779ea3dfec"], net_path, plain_files)
    # ~ change_roundabout_to_node(["Edge1bde77912329409eacc8576eab41d9f9","Edge8eec627c2c8c40f58e3f27bb43248514","Edgeabd74cbf35da4db080f0c670dbdb6a77"], ["Node17756344b4d44e65bd85d01a23e64600","Node3346a37126f4422898b02de45ae7dc6a","Noded9f7dd47c6d3403ab7d4b8701a3be807"], net_path, plain_files)
    # ~ change_roundabout_to_node(["Edge8bf161297b75401faa02f7479271fe0f","Edgefa414cf8cd49474da5143dec102d7448","Edgefbc74baa80bd462a9b6e37650207853c"], ["Node240798b03498439b92eaa37ede599e90","Node8c7d3e29c3c348f790b1c06bf1b09899","Nodedf029caac7ac4792bee33eb4ff6138e8"], net_path, plain_files)
    # ~ change_node_to_roundabout("Node8ec8db3c99294cc7ba46928b452e0f6f", net_path, plain_files)
    
    json_str=""
    with open('searchspace.json', 'r') as f:
        json_str = f.read()
    
    # ~ {'id': node.getID(), 'currentType': node.getType(), 'allowedModifications': ['intersection_priority', 'roundabout']}
    # ~ pprint(json_str)
    search_space = json.loads(json_str)
    # ~ pprint(search_space)
    print("*****************")
    
    pprint("Laden...")
    pprint(time.monotonic())
    nr = Net_Repr(plain_files)
    pprint(time.monotonic())
    
    #Koeln
    pprint("Hack...")
    pprint(time.monotonic())
    hack_for_cologne(plain_files)
    pprint(time.monotonic())
    
    pprint("Modifizieren...")
    pprint(time.monotonic())
    
    for intersection in search_space["intersections"]:
        for am in intersection["allowedModifications"]:
            mparams = am.split(" ")
            if mparams[0] == "roundabout":
                change_intersection_to_roundabout(intersection["id"],nr)
            
        

    pprint(time.monotonic())
    
    #Minimal
    # ~ change_node_to_roundabout("498751220", nr)
    # ~ change_node_to_roundabout("996951907", nr)
    # ~ change_node_to_roundabout("996951809", nr)
    # ~ change_node_to_roundabout("cluster_498751183_996951775", nr)
    # ~ change_roundabout_to_node("26697422#0 26697422#1 26697422#2", "292785669 292785688 76182923", nr)
    
    pprint("Schreiben...")
    pprint(time.monotonic())
    nr.write_to_plain()
    pprint(time.monotonic())
    
    print("*****************")
    cnvt_plain_to_net(netcnvt_bin, plain_files, new_net_path, switch_verbose)
    
    #cnvt_plain_to_net(netcnvt_bin, plain_files, new_net_path, switch_verbose)
    
    
    if not switch_keep_temp:
        rm_tmpd_and_files(plain_path)
    

if __name__=="__main__":
    main()

