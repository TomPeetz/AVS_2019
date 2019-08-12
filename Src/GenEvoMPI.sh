#!/bin/bash

### Beispielaufruf
# $./GenEvoMPI.sh -v -c Simulation/s1_test.sumocfg -s s1_searchspace.json -p 16 -g 4 -r aabbcc

num_cpus=8

mpiexec --use-hwthread-cpus --oversubscribe -n $(expr $num_cpus + 1) python -m mpi4py.futures GenEvo.py -m "$@"

