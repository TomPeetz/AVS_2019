from mpi4py import futures
from pprint import pprint
from os import path
from fobj import sumo
import json

# execute with "mpiexec -n 1  python3.7 TrafficSimulation2.py --universe_size 2 --fun_evals xxx"
# -n 1 is important, the rest of the parameters can be changed.
# Still have to test this with two seperate hosts

import argparse

parser = argparse.ArgumentParser(description='TrafficSimulation')
parser.add_argument('--universe_size', type=int, help='')
parser.add_argument('--fun_evals', type=int, help='Number of objective function evaluations')
args = parser.parse_args()


with open(path.abspath(path.join("Simulation", "Simulation.json")), "r") as json_data:
    config = json.load(json_data)


def generate_search_space():
    with open(config['searchSpaceFile'], 'r') as f:
        json_data = json.loads(f.read())

    searchspace = []
    #for intersection in json_data['intersections']:
    #    searchspace.append(('i-'+intersection['id'], hp.choice('choice-' + intersection['id'], intersection['allowedModifications'])))
    #for roundabout in json_data['roundabouts']:
    #    raid = '-'.join(roundabout['nodes'])
    #    mods = roundabout['allowedModifications']
    #    searchspace.append(('r-'+raid, hp.choice('choice-'+raid, mods)))
    return searchspace


if __name__ == '__main__':
    fun_evals_left = args.fun_evals

    searchspace = generate_search_space()

    generation = 1
    while True:
        # Generate the different "Individuen" here and pass them as decision vectors to the objective function

        # example:
        decisionVector1 = [
            ["i-cluster_498751183_996951775", "priority 399638313#2 24814407#0"],
            ["i-996951809", "right_before_left"],
            ["i-498751220", "traffic_light"],
            ["i-996951907", "priority 399638313#1 -399638313#2"],
            ["r-292785669-292785688-76182923", "right_before_left"]
        ]
        decisionVector2 = [
            ["i-cluster_498751183_996951775", "priority 399638313#2 -24814407#2"],
            ["i-996951809", "do_nothing"],
            ["i-498751220", "traffic_light_right_on_red"],
            ["i-996951907", "traffic_light_right_on_red"],
            ["r-292785669-292785688-76182923", "do_nothing"]
        ]
        toEvaluate = [decisionVector1, decisionVector2]

        results = []
        with futures.MPIPoolExecutor(max_workers=args.universe_size) as executor:
            fun_evals_left -= len(toEvaluate)  # reduce the number of max fun evals
            results.extend(executor.map(sumo, toEvaluate, [generation] * len(toEvaluate)))

        # this is the results array. It contains the floats from the objective function evaluations
        pprint(results)

        generation += 1
        break  # do as long as we have fun evals left?
