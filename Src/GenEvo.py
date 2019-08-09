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
from ModMap import *
import GenEvoConstants


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
        population.append([id_ctr, dna, False])
        id_ctr += 1
    population.sort(key = lambda x: x[0])
    return population

def single_evaluate_population(population):
    results = []
    for individual in population:
        results.append(evaluate_individual(individual))
    return results
   
def local_mp_evaluate_population(population, pool):
    async_results=[]
    for individual in population:
        async_results.append(pool.apply_async(evaluate_individual,(individual,)))
    results=[]
    for result in async_results:
        results.append(result.get())
    return results
    
#TODO: Implement MPI similar to local_mp_evalutate_population
def mpi_evaluate_population(population):
    pass    

def main():
    
    err="{} -c <simulation.sumocfg (path)> -s <searchspace.json (path)> -p <Population size (int)> -g <Number of generations (int)> [-r <Seed (hex string)> -v verbose [-l local multiprocessing | -m mpi]]"
    
    individual_id_ctr = 1
    
    simulation_cfg_path = False
    searchspace_path = False
    population_size = False
    number_of_generations = False
    seed = False
    v = False
    use_local_mt = False
    use_mpi = False
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vlmc:s:p:g:r:")
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
        elif o == "-l":
            use_local_mt = True
        elif o == "-m":
            use_mpi = True
        
    if simulation_cfg_path is False or searchspace_path is False or population_size is False or number_of_generations is False:
        print(err.format(sys.argv[0]))
        sys.exit(1)
    
    #TODO: Remove if MPI is ready
    if use_mpi:
        print("Not implemented!")
        sys.exit(1)
    
    if use_local_mt and use_mpi:
        print("Only local multiprocessing xor mpi!")
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
    
    with open(searchspace_path, "r") as f:
        searchspace = json.loads(f.read())
    
    if v:
        print("Searchspace: {} intersections and {} roundabouts found.".format(len(searchspace["intersections"]), len(searchspace["roundabouts"])))
    
    genome = []
    for intersection in searchspace["intersections"]:
        intersection_id = intersection["id"]
        allowed_modifications = []
        for modification in intersection["allowedModifications"]:
            allowed_modifications.append(tuple(modification.split(" ")))
        genome.append((GenEvoConstants.INTER_NODE, intersection_id, tuple(allowed_modifications)))
    for roundabout in searchspace["roundabouts"]:
        roundabout_id = roundabout["id"]
        allowed_modifications = []
        for modification in roundabout["allowedModifications"]:
            allowed_modifications.append(tuple(modification.split(" ")))
        genome.append((GenEvoConstants.INTER_ROUNDABOUT, roundabout_id, tuple(allowed_modifications)))
    
    ##Prepare workers
    if v:
        print("Start preparing workers...", end="", flush=True)
    
    with open(simulation_cfg_path, "r") as f:
        simulation_cfg_str = f.read()
        
    with open(trips_path, "r") as f:
        trips_str = f.read()
        
    with open(vtypes_path, "r") as f:
        vtypes_str = f.read()
        
    netcnvt = load_netconvert_binary()
    tmpd, plain_files = cnvt_net_to_plain(net_path, netcnvt, "prepare", False)
    
    with open(plain_files["con"], "r") as f:
        plain_con_str = f.read()
    with open(plain_files["edg"], "r") as f:
        plain_edg_str = f.read()
    with open(plain_files["nod"], "r") as f:
        plain_nod_str = f.read()
    plain_tll_str = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<tlLogics version=\"1.1\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"http://sumo.dlr.de/xsd/tllogic_file.xsd\">\n</tlLogics>"
    with open(plain_files["typ"], "r") as f:
        plain_typ_str = f.read()
    
    rm_tmpd_and_files(tmpd)
    
    if v:
        print(" initializing workers ...", end="", flush=True)
    if use_local_mt:
        if v:
            print(" for local multiprocessing.")
        pool_size = cpu_count()
        pool = Pool(pool_size, initialize_worker, [simulation_cfg_str, trips_str, vtypes_str, plain_con_str, plain_edg_str, plain_nod_str, plain_tll_str, plain_typ_str, v])
    elif use_mpi:
        if v:
            print(" for mpi.")
        #TODO: Prepare MPI
        #TODO: create all variables which are needed and at least initialize workers by calling initialize_worker for each one.
    else:
        if v:
            print(" for single threading.")
        initialize_worker(simulation_cfg_str, trips_str, vtypes_str, plain_con_str, plain_edg_str, plain_nod_str, plain_tll_str, plain_typ_str, v)
    
    del plain_files
    del plain_con_str
    del plain_edg_str
    del plain_nod_str
    del plain_tll_str
    del plain_typ_str
    del simulation_cfg_str
    del trips_str
    del vtypes_str
    ##
    
    #possible gen only population_size - 1 individuals and inject a special individual with all genes do_nothing
    generation_A = initialize_first_generation(genome, population_size, stable_random, individual_id_ctr)
    individual_id_ctr += population_size
    # ~ generation_B = initialize_first_generation(genome, population_size, stable_random, individual_id_ctr)
    individual_id_ctr += population_size
    
    if use_local_mt:
        generation_A_fitness = local_mp_evaluate_population(generation_A, pool)
        # ~ generation_B_fitness = local_mp_evaluate_population(generation_B, pool)
    elif use_mpi:
        #TODO: Call mpi_evaluate_population with approbiate parameters
        pass
    else:
        generation_A_fitness = single_evaluate_population(generation_A)
        # ~ generation_B_fitness = single_evaluate_population(generation_B)
    
    generation_A_fitness.sort(key = lambda x: x[0])
    for individual, fitness in zip(generation_A, generation_A_fitness):
        individual[2] = fitness[1]
    
    # ~ generation_B_fitness.sort(key = lambda x: x[0])
    # ~ for individual, fitness in zip(generation_B, generation_B_fitness):
        # ~ individual[2] = fitness[1]
    
    ###LRS after: JEBARI, Khalid; MADIAFI, Mohammed. Selection methods for genetic algorithms. International Journal of Emerging Sciences, 2013, 3. Jg., Nr. 4, S. 333-344.
    
    
    # ~ sum_v = 1 / ( len(generation_A) - 2.001 )
    
    # ~ selected_individuals = []
    # ~ for individual in generation_A:
        # ~ alpha = stable_random.uniform(0, sum_v)
        
        
    
    if use_local_mt:
        pool.close()
        pool.join()
    elif use_mpi:
        #TODO: Do cleanups for MPI if needed
        pass
    
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

