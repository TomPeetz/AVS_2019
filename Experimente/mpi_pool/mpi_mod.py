
from pprint import pprint
import mpi
import os, sys
import time

import __main__

# ~ x_param = __main__.g_param

def a_func(param):
    
    time.sleep(1)
    pprint((param, os.getpid()))
    return __main__.g_param
    return -1
    
    
