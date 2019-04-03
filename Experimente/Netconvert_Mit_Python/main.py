#!/usr/bin/env python3

import os
import sys
import subprocess
from pathlib import Path
import tempfile
import random
import getopt

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
    patch_file = get_tmp_file_for_patch(plain_path)
    random_node_types(plain_files, patch_file, net_path, new_net_path, netcnvt_bin, switch_verbose)
    
    if not switch_keep_temp:
        rm_tmpd_and_files(plain_path)
    

if __name__=="__main__":
    main()
