#!/bin/bash

mpiexec --hostfile mpihosts.prod -mca plm_rsh_args "-p 2222" -mca orte_base_help_aggregate 0 -np 240 wrapper.sh

