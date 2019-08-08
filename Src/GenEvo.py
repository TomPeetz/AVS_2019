#!/usr/bin/env python3

from pprint import pprint
import json
from pathlib import Path
import math
import os, sys
import random
import getopt
import binascii
import time
import xml.etree.ElementTree as ET
from multiprocessing import cpu_count, Pool
from GenEvoEvaluate import *

#######
#####
###
#
ROUNDABOUT=1
NODE=2
#######
#####
###
#

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib

def initialize_first_generation(genome, population_size, stable_random, id_ctr):
    population = []
    for _ in range(population_size):
        dna = []
        for gene in genome:
            dna.append((gene[0], gene[1], stable_random.choice(gene[2])))
        population.append((id_ctr, dna))
        id_ctr += 1
    return population

#### Interface with mpi somehow
def evaluate_population(population):
    results = []
    for individual in population:
        results.append(evaluate_individual(individual))
    return results
    

def main():
    
    err="{} -c <simulation.sumocfg (path)> -s <searchspace.json (path)> -p <Population size (int)> -g <Number of generations (int)> [-r <Seed (hex string) -v Switch verbose>]"
    
    individual_id_ctr = 1
    
    simulation_cfg_path = False
    searchspace_path = False
    population_size = False
    number_of_generations = False
    seed = False
    v = False
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vc:s:p:g:r:")
    except getopt.GetoptError:
        print(err.format(sys.argv[0]))
        sys.exit(1)
    
    for o, a in opts:
        if o == "-s":
            searchspace_path = a
        elif o == "-c":
            simulation_cfg_path = a
        elif o == "-p":
            population_size = a
        elif o  == "-g":
            number_of_generations = a
        elif o == "-r":
            seed = a
        elif o == "-v":
            v = True
        
    if simulation_cfg_path is False or searchspace_path is False or population_size is False or number_of_generations is False:
        print(err.format(sys.argv[0]))
        sys.exit(1)
    
    searchspace_path = Path(searchspace_path).resolve()
    if not searchspace_path.exists() or searchspace_path.is_dir():
        print("No valid searchspace file found!")
        print(err.format(sys.argv[0]))
        sys.exit(1)
        
    simulation_cfg_path = Path(simulation_cfg_path).resolve()
    if not simulation_cfg_path.exists() or searchspace_path.is_dir():
        print("No valid sumo config file found!")
        print(err.format(sys.argv[0]))
        sys.exit(1)
    
    conf_tree = ET.parse(simulation_cfg_path)
    conf_root = conf_tree.getroot()
    net_path = Path(simulation_cfg_path.parent, conf_root.find("input").find("net-file").attrib["value"]).resolve()
    trips_path = Path(simulation_cfg_path.parent, conf_root.find("input").find("route-files").attrib["value"]).resolve()
    vtypes_path = Path(simulation_cfg_path.parent, conf_root.find("input").find("additional-files").attrib["value"]).resolve()
    del conf_root
    del conf_tree
    if v:
        print("Using net file: <{}>.".format(str(net_path)))
        print("Using trips file: <{}>.".format(str(trips_path)))
        
    try:
        population_size = int(population_size)
        number_of_generations = int(number_of_generations)
    except ValueError:
        print("Population size and number of generations must be integers!")
        print(err.format(sys.argv[0]))
        sys.exit(1)
    
    if v:
        print("Population size is {}; Number of generations is {}".format(population_size, number_of_generations))
    
    if seed is False:
        seed = int(binascii.hexlify(os.urandom(16)), 16)
    else:
        try:
            seed = int(seed, 16)
        except ValueError:
            print("Seed has to be a hexadecimal string!")
            print(err.format(sys.argv[0]))
            sys.exit(1)
    stable_random = random.Random()
    stable_random.seed(seed)
    
    if v:
        print("Using seed: {0:x}".format(seed))
    
    with open(searchspace_path, 'r') as f:
        searchspace = json.loads(f.read())
    
    if v:
        print("Searchspace: {} intersections and {} roundabouts found.".format(len(searchspace["intersections"]), len(searchspace["roundabouts"])))
        
    genome = []
    for intersection in searchspace["intersections"]:
        intersection_id = intersection["id"]
        allowed_modifications = []
        for modification in intersection["allowedModifications"]:
            allowed_modifications.append(tuple(modification.split(" ")))
        genome.append((NODE, intersection_id, tuple(allowed_modifications)))
    for roundabout in searchspace["roundabouts"]:
        roundabout_id = roundabout["id"]
        allowed_modifications = []
        for modification in roundabout["allowedModifications"]:
            allowed_modifications.append(tuple(modification.split(" ")))
        genome.append((ROUNDABOUT, roundabout_id, tuple(allowed_modifications)))
    
    ##Prepare workers
    with open(simulation_cfg_path, "r") as f:
        simulation_cfg_str = f.read()
    
    with open(net_path, "r") as f:
        net_str = f.read()
        
    with open(trips_path, "r") as f:
        trips_str = f.read()
        
    with open(vtypes_path, "r") as f:
        vtypes_str = f.read()
        
    initialize_worker(simulation_cfg_str, net_str, trips_str, vtypes_str)
    del simulation_cfg_str
    del net_str
    del trips_str
    del vtypes_str
    ##
    
    #possible gen only population_size - 1 individuals and inject a special individual with all genes do_nothing
    generation_1 = initialize_first_generation(genome, population_size, stable_random, individual_id_ctr)

    # ~ netcnvt = load_netconvert_binary()
    
    finalize_worker()

if __name__=="__main__":
    main()


#TODO:
# Main
# Suchraum laden
# 1. Generation anlegen (Individuen generieren)
#                                               # Bewertungsfunktion ausfuehren
                      
    #Suchraum laden
    
    #
                              # Resultat zurueckgeben
# 2. Generation erzeugen (Mix Gen 1 & Ursprung)
# ...

# Abbruchbedingung erreichen
# Bestes Ergebnis zurueck

