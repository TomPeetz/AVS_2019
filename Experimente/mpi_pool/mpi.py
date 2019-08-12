#!/usr/bin/env python3

from pprint import pprint
import os, sys
import getopt
from mpi_mod import *

from mpi4py import futures

def mpi():
    pprint("yeah...")
    
    mpi_pool = futures.MPIPoolExecutor(globals=[('g_param', 1)], main=True)
    
    ar = []
    for x in range(16):
        ar.append(mpi_pool.submit(a_func, x))
    for res in ar:
        pprint(res.result())
    
    mpi_pool.shutdown(wait=True)

if __name__=="__main__":
    mpi()
    
