#!/usr/bin/env python3

### Beispielaufruf
# $./GenEvo.py -v -l -c Simulation/s1_test.sumocfg -s s1_searchspace.json -o Simulation/s1_best.net.xml -p 72 -g 16 -k 20 -x 0.05 -r 012345abcdef6789

from pprint import pprint
import json
from pathlib import Path
import math
import os, sys
import random
import getopt
import binascii
import time
import io
import xml.etree.ElementTree as ET
from multiprocessing import cpu_count, Pool
import GenEvoEvaluate 
from ModMap import *
import GenEvoConstants

from mpi4py import futures

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib


def initialize_first_generation(genome, population_size, stable_random, iid_ctr):
    population = []
    for _ in range(population_size):
        dna = []
        for gene in genome:
            # ( gene[0] <=> Type (Roundabout, Node), gene[1] <=> Id, gene[2] <=> Operation from list of possible operations )
            dna.append((gene[0], gene[1], stable_random.choice(gene[2])))
        #Individual = [ id, dna, fitness, accumulated_rank_fitness ]
        population.append([iid_ctr, dna, False, False])
        iid_ctr += 1
    return population

def generate_genom_from_searchspace(searchspace):
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
    return genome
    
def apply_fitness_to_individuals(generation, fitness):
    generation.sort(key = lambda x: x[0])
    fitness.sort(key = lambda x: x[0])
    i=0
    for f in fitness:
        while generation[i][0] < f[0]:
            i+=1
        generation[i][2] = f[1]

def generate_new_generation(old_generation, population_size, genome, k_num, mutation_rate, stable_random, iid_ctr):
    
    old_generation.sort(key = lambda x: x[2])
    
    ### LRS after: JEBARI, Khalid; MADIAFI, Mohammed. Selection methods for genetic algorithms. International Journal of Emerging Sciences, 2013, 3. Jg., Nr. 4, S. 333-344.    
    total_rank_fitness = (len(old_generation)+1) * len(old_generation)/2.
    
    accumulated_rank_fitness = 0.
    for rank in range(len(old_generation)):
        accumulated_rank_fitness += (len(old_generation) - rank) / total_rank_fitness
        old_generation[rank][3] = accumulated_rank_fitness
        
    number_of_parents = population_size / 2
    number_of_parents_selected = 0
    selected_parents = []
    while number_of_parents_selected < number_of_parents:
        alpha = stable_random.random()
        parent_idx = 0
        for i in range(len(old_generation)):
            if alpha < old_generation[i][3]:
                parent_idx = i
                break
        
        selected_parents.append(old_generation[parent_idx])
        number_of_parents_selected+=1
            
    ### k-point crossover after: WRIGHT, Alden H. Genetic algorithms for real parameter optimization. In: Foundations of genetic algorithms. Elsevier, 1991. S. 205-218.
    #Adapted from floating point values for discrete values
    children = []
    
    for i in range(0, len(selected_parents), 2):
        p_A = selected_parents[i]
        p_B = selected_parents[i+1]
        
        crossover_points = random.sample(range(0, len(p_A[1])), k_num)
        #Assure the dna is completely copied
        if len(p_A[1]) not in crossover_points:
            crossover_points.append(len(p_A[1]))
        
        crossover_points.sort()
        c_A_dna = []
        c_B_dna = []
        
        j = 0
        for x_point in crossover_points:
            while j < x_point:
                c_A_dna.append(p_A[1][j])
                c_B_dna.append(p_B[1][j])
                j+=1
            p_tmp = p_B
            p_B = p_A
            p_A = p_tmp
        
        children.append([iid_ctr, c_A_dna, False, False])
        iid_ctr += 1
        children.append([iid_ctr, c_A_dna, False, False])
        iid_ctr += 1
    
    ### Creep Mutation after: SONI, Nitasha; KUMAR, Tapas. Study of various mutation operators in genetic algorithms. International Journal of Computer Science and Information Technologies, 2014, 5. Jg., Nr. 3, S. 4519-4521.
    #Adapted from floating point values to discret values
    for child in children:
        for i in range(len(child[1])):
            alpha = stable_random.random()
            if alpha > mutation_rate:
                continue
            gene = genome[i]
            child[1][i] = (gene[0], gene[1], stable_random.choice(gene[2]))
            
    new_generation = selected_parents + children
    return new_generation
    
def single_evaluate_population(population):
    results = []
    for individual in filter(lambda x: x[2] is False, population):
        results.append(GenEvoEvaluate.evaluate_individual(individual, False))
    return results
   
def local_mp_evaluate_population(population, pool):
    async_results=[]
    for individual in filter(lambda x: x[2] is False, population):
        async_results.append(pool.apply_async(GenEvoEvaluate.evaluate_individual,(individual, False)))
    results=[]
    for result in async_results:
        results.append(result.get())
    return results
    
def mpi_evaluate_population(population, mpi_pool):
    async_results=[]
    for individual in filter(lambda x: x[2] is False, population):
        async_results.append(mpi_pool.submit(GenEvoEvaluate.evaluate_individual, individual, True))
    results=[]
    for result in async_results:
        results.append(result.result())
    return results

def main():
    
    t_t_0 = time.monotonic()
    
    err="{} -c <simulation.sumocfg (path)> -s <searchspace.json (path)> -p <Population size (int)> -g <Number of generations (int)> [-r <Seed (hex string)> -k <crossover points (int)> -x <mutation rate 0..1 (float)> -o <best net (Path)> -v verbose (specify multiple times for more messages) [-l local multiprocessing | -m mpi]]"
    
    individual_id_ctr = 1
    
    simulation_cfg_path = False
    searchspace_path = False
    population_size = False
    number_of_generations = False
    seed = False
    best_net_path = False
    v = 0
    use_local_mt = False
    use_mpi = False
    k_num = False
    mutation_rate = False
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vlmc:s:p:g:r:k:x:o:")
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
            v += 1
        elif o == "-l":
            use_local_mt = True
        elif o == "-m":
            use_mpi = True
        elif o == "-k":
            k_num = a
        elif o == "-x":
            mutation_rate = a
        elif o == "-o":
            best_net_path = a
        
    if simulation_cfg_path is False or searchspace_path is False or population_size is False or number_of_generations is False:
        print(err.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    
    if use_local_mt and use_mpi:
        print("Only local multiprocessing xor mpi!")
        print(err.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    
    searchspace_path = Path(searchspace_path).resolve()
    if not searchspace_path.exists() or searchspace_path.is_dir():
        print("No valid searchspace file found!", file=sys.stderr)
        print(err.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
        
    simulation_cfg_path = Path(simulation_cfg_path).resolve()
    if not simulation_cfg_path.exists() or searchspace_path.is_dir():
        print("No valid sumo config file found!", file=sys.stderr)
        print(err.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    
    if not best_net_path is False:
        best_net_path = Path(best_net_path).resolve()
        if best_net_path.is_dir() or not best_net_path.parent.is_dir():
            print("No valid location for best net specified!", file=sys.stderr)
            print(err.format(sys.argv[0]), file=sys.stderr)
            sys.exit(1)
    
    conf_tree = ET.parse(simulation_cfg_path)
    conf_root = conf_tree.getroot()
    net_path = Path(simulation_cfg_path.parent, conf_root.find("input").find("net-file").attrib["value"]).resolve()
    trips_path = Path(simulation_cfg_path.parent, conf_root.find("input").find("route-files").attrib["value"]).resolve()
    vtypes_path = Path(simulation_cfg_path.parent, conf_root.find("input").find("additional-files").attrib["value"]).resolve()
    del conf_root
    del conf_tree
    if v >= GenEvoConstants.V_INF:
        print("Using net file: <{}>.".format(str(net_path)))
        print("Using trips file: <{}>.".format(str(trips_path)))
        
    try:
        population_size = int(population_size)
        number_of_generations = int(number_of_generations)
        if population_size < 3 or population_size % 4 != 0:
            print("Please specify only numbers greater than 2 and dividable by 4 for population size!", file=sys.stderr)
            raise ValueError()
        if number_of_generations < 2:
            print("Please specify a number of generations greater than 1!", file=sys.stderr)
            raise ValueError()
    except ValueError:
        print("Population size and number of generations and number of crossover points must be integers!", file=sys.stderr)
        print(err.format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    
    if v >= GenEvoConstants.V_INF:
        print("Population size is {}; Number of generations is {}".format(population_size, number_of_generations))
    
    if k_num is False:
        k_num = 20
    else:
        try:
            k_num = int(k_num)
            if k_num < 1:
                raise ValueError()
        except ValueError:
            print("Number of crossover points must be nonnegativ integer", file=sys.stderr)
            print(err.format(sys.argv[0]), file=sys.stderr)
            sys.exit(1)
    
    if mutation_rate is False:
        mutation_rate = 0.05
    else:
        try:
            mutation_rate = float(mutation_rate)
            if mutation_rate < 0. or mutation_rate > 1.:
                raise ValueError
        except ValueError:
            print("Mutation rate must be a floating point value between 0 and 1!", file=sys.stderr)
            print(err.format(sys.argv[0]), file=sys.stderr)
            sys.exit(1)
    
    if v >= GenEvoConstants.V_INF:
        print("Using {}-point crossover and mutation rate of {}.".format(k_num, mutation_rate))
    
    if seed is False:
        seed = int(binascii.hexlify(os.urandom(16)), 16)
    else:
        try:
            seed = int(seed, 16)
        except ValueError:
            print("Seed has to be a hexadecimal string!", file=sys.stderr)
            print(err.format(sys.argv[0]), file=sys.stderr)
            sys.exit(1)
    stable_random = random.Random()
    stable_random.seed(seed)
    
    if v >= GenEvoConstants.V_INF:
        print("Using seed: {0:x}".format(seed))
    
    with open(searchspace_path, "r") as f:
        searchspace = json.loads(f.read())
    
    if v >= GenEvoConstants.V_INF:
        print("Searchspace: {} intersections and {} roundabouts found.".format(len(searchspace["intersections"]), len(searchspace["roundabouts"])))
    
    ##Prepare workers
    if v >= GenEvoConstants.V_DBG:
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
    
    if v >= GenEvoConstants.V_DBG:
        print(" initializing workers ...", end="", flush=True)
    if use_local_mt:
        if v >= GenEvoConstants.V_DBG:
            print(" for local multiprocessing.")
        pool_size = cpu_count()
        pool = Pool(pool_size, GenEvoEvaluate.initialize_worker, [simulation_cfg_str, trips_str, vtypes_str, plain_con_str, plain_edg_str, plain_nod_str, plain_tll_str, plain_typ_str, v])
    elif use_mpi:
        if v >= GenEvoConstants.V_DBG:
            print(" for mpi.")
        GenEvoEvaluate.initialize_worker(simulation_cfg_str, trips_str, vtypes_str, plain_con_str, plain_edg_str, plain_nod_str, plain_tll_str, plain_typ_str, v)
        glb_mpi = [("plain_con_m", GenEvoEvaluate.plain_con_g), ("plain_edg_m", GenEvoEvaluate.plain_edg_g), ("plain_nod_m", GenEvoEvaluate.plain_nod_g), ("plain_tll_m", GenEvoEvaluate.plain_tll_g), ("plain_typ_m", GenEvoEvaluate.plain_typ_g), ("sumo_cfg_m", GenEvoEvaluate.sumo_cfg_g), ("trips_m", GenEvoEvaluate.trips_g), ("vtypes_m", GenEvoEvaluate.vtypes_g), ("v_glb_m", GenEvoEvaluate.v_glb_g), ("netcnvt_m", GenEvoEvaluate.netcnvt_g), ("sumo_bin_m", GenEvoEvaluate.sumo_bin_g)]
        
        mpi_pool = futures.MPIPoolExecutor(globals=glb_mpi, main=True)
        mpi_pool.bootup(wait=True)
        
        del glb_mpi
    else:
        if v >= GenEvoConstants.V_DBG:
            print(" for single threading.")
        GenEvoEvaluate.initialize_worker(simulation_cfg_str, trips_str, vtypes_str, plain_con_str, plain_edg_str, plain_nod_str, plain_tll_str, plain_typ_str, v)
    
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
    
    genome = generate_genom_from_searchspace(searchspace)
    
    #possible gen only population_size - 1 individuals and inject a special individual with all genes do_nothing
    generation = initialize_first_generation(genome, population_size, stable_random, individual_id_ctr)
    individual_id_ctr += population_size
    
    if use_local_mt:
        generation_fitness = local_mp_evaluate_population(generation, pool)
    elif use_mpi:
        generation_fitness = mpi_evaluate_population(generation, mpi_pool)
    else:
        generation_fitness = single_evaluate_population(generation)
    
    apply_fitness_to_individuals(generation, generation_fitness)
    generation_ctr = 0
    
    fittest_individual = [generation[0], generation_ctr]
    for individual in generation:
        if individual[2] < fittest_individual[0][2]:
            fittest_individual = [individual, generation_ctr]
    
    if v >= GenEvoConstants.V_STAT:
        print("Current generation is {}. Fittest individuals name is {} and it has a fitness value of {}.".format(generation_ctr, fittest_individual[0][0], fittest_individual[0][2]))
    
    while generation_ctr < number_of_generations:
        if v >= GenEvoConstants.V_STAT:
            t_0 = time.monotonic()
            t_A_0 = t_0
        generation = generate_new_generation(generation, population_size, genome, k_num, mutation_rate, stable_random, individual_id_ctr)
        individual_id_ctr += population_size/2
        if v >= GenEvoConstants.V_INF:
            t_1 = time.monotonic()
            print("Generation {} created in {}s.".format(generation_ctr+1, t_1-t_0))
        if v >= GenEvoConstants.V_STAT:
            t_0 = time.monotonic()
        
        if use_local_mt:
            generation_fitness = local_mp_evaluate_population(generation, pool)
        elif use_mpi:
            generation_fitness = mpi_evaluate_population(generation, mpi_pool)
        else:
            generation_fitness = single_evaluate_population(generation)
        
        if v >= GenEvoConstants.V_STAT:
            t_1 = time.monotonic()
            t_E = t_1 - t_0
        if v >= GenEvoConstants.V_DBG:
            print("Evaluating the new individuals took {}s.".format(t_E))
            t_0 = time.monotonic()
        apply_fitness_to_individuals(generation, generation_fitness)
        generation_ctr += 1
        if v >= GenEvoConstants.V_INF:
            t_1 = time.monotonic()
            print("Calculated fitness applied to individuals in {}s.".format(t_1-t_0))
        
        if v >= GenEvoConstants.V_INF:
            t_0 = time.monotonic()
        fittest_individual_in_generation = [generation[0], generation_ctr]
        for individual in generation:
            if individual[2] < fittest_individual_in_generation[0][2]:
                fittest_individual_in_generation = [individual, generation_ctr]
        
        if fittest_individual_in_generation[0][2] < fittest_individual[0][2]:
            fittest_individual = fittest_individual_in_generation
        if v >= GenEvoConstants.V_INF:
            t_1 = time.monotonic()
        if v >= GenEvoConstants.V_STAT:
            print("Current generation is {}. Fittest individuals name is {}, it has a fitness value of {}.".format(generation_ctr, fittest_individual_in_generation[0][0], fittest_individual_in_generation[0][2]))
            print("Overall fittest individuals name is {}. It is from generation {} and has a fitness value of {}.".format(fittest_individual[0][0], fittest_individual[1], fittest_individual[0][2]))
        if v >= GenEvoConstants.V_INF:
            print("Fittest individual found in {}s.".format(t_1-t_0))
        if v >= GenEvoConstants.V_STAT:
            t_A_1 = time.monotonic()
            t_A = t_A_1 - t_A_0
            print("Generation took {}s, of which {}s where spend evaluating individuals and {}s managing the generation.".format(t_A, t_E, t_A - t_E))
            
    if use_local_mt:
        pool.close()
        pool.join()
    elif use_mpi:
        mpi_pool.shutdown(wait=True)
    
    if not best_net_path is False:
        netcnvt_bin = load_netconvert_binary()
        tmpd, best_plain_files = cnvt_net_to_plain(net_path, netcnvt_bin, "best", False)
        hack_for_cologne(best_plain_files)
        best_nr = Net_Repr(best_plain_files)
        GenEvoEvaluate.modify_net(fittest_individual[0], best_nr, best_plain_files, best_net_path, netcnvt_bin)
        rm_tmpd_and_files(tmpd)
        
    t_t_1 = time.monotonic()
    if v >= GenEvoConstants.V_STAT:
        print("\n*** Result ***")
        print("Tested {} individuals in {} generations. Best individual was {} from generation {} with fitness {}.".format(individual_id_ctr-1, generation_ctr, fittest_individual[0][0], fittest_individual[1], fittest_individual[0][2]))
        print("Overall runtime {}s.".format(t_t_1 - t_t_0))
        print("**************")
    
if __name__=="__main__":
    main()
