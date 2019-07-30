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
    
    change_node_to_roundabout("498751220", net_path, plain_files)
    cnvt_plain_to_net(netcnvt_bin, plain_files, new_net_path, switch_verbose)
    
    
    if not switch_keep_temp:
        rm_tmpd_and_files(plain_path)
    

if __name__=="__main__":
    main()

