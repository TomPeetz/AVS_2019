#!/bin/bash

mkdir -p ~/AVS_2019/results

nodes=`cat nodes`

for node in $nodes; do
  echo "Getting results from $node"
  rsync -av -e "ssh -i id.mpi -p2222" --include "5*" dennis@$node:~/AVS_2019/Src ~/AVS_2019/results
done
